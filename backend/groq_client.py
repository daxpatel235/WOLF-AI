import json
import random
import re
import time

from .config import DEFAULT_MODEL, FALLBACK_MODELS

CHECK_PROMPTS = {
    "bugs": ["Syntax errors", "Logic bugs", "Type errors", "Missing error handling"],
    "security": ["Security vulnerabilities"],
    "performance": ["Performance issues"],
    "style": ["Bad practices, readability and naming problems"],
}

SEVERITIES = {"high", "medium", "low"}

# Lines that usually start a new top-level block (def/class/function/etc.).
_CLOSERS = ("}", ")", "]", "@", "#", "//", "*", "else", "elif", "except", "finally", "catch")


def _is_boundary(line, prev_line):
    if not line.strip() or line[0] in " \t":
        return False
    if line.lstrip().startswith(_CLOSERS):
        return False
    # Don't split a decorator from the function under it.
    return not (prev_line or "").lstrip().startswith("@")


def split_into_chunks(code, max_chars):
    """
    Splits code into consecutive, non-overlapping chunks of at most ~max_chars,
    preferring to cut just before a top-level definition. Returns a list of
    (start_line, text) with 1-based start lines. Joining the texts gives back
    the original code exactly.
    """
    if len(code) <= max_chars:
        return [(1, code)]

    lines = code.splitlines(keepends=True)
    chunks = []
    start = 0          # index of first line in the current chunk
    size = 0
    last_boundary = None

    for i, line in enumerate(lines):
        if i > start and _is_boundary(line, lines[i - 1]):
            last_boundary = i
        if size + len(line) > max_chars and i > start:
            # Cut at the last boundary if it keeps the chunk reasonably full.
            if last_boundary and last_boundary > start and (
                sum(len(l) for l in lines[start:last_boundary]) >= max_chars * 0.3
            ):
                cut = last_boundary
            else:
                cut = i
            chunks.append((start + 1, "".join(lines[start:cut])))
            start = cut
            size = sum(len(l) for l in lines[start:i])
            last_boundary = None
        size += len(line)

    chunks.append((start + 1, "".join(lines[start:])))
    return chunks


def _is_retryable(exc):
    status = getattr(exc, "status_code", None)
    if status in (408, 409, 429) or (isinstance(status, int) and status >= 500):
        return True
    name = type(exc).__name__
    return name in ("RateLimitError", "APIConnectionError", "APITimeoutError", "InternalServerError")


def _retry_after(exc):
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


def with_retry(fn, attempts=5, base_delay=1.5, max_delay=30.0, sleep=time.sleep):
    """Calls fn(), retrying rate-limit / transient errors with exponential backoff."""
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if attempt == attempts - 1 or not _is_retryable(exc):
                raise
            delay = _retry_after(exc)
            if delay is None:
                delay = min(max_delay, base_delay * (2 ** attempt)) + random.uniform(0, 1)
            sleep(min(delay, max_delay))


def _normalise_issue(issue, line_offset):
    try:
        line = int(issue.get("line") or 0)
    except (TypeError, ValueError):
        line = 0
    severity = str(issue.get("severity", "medium")).lower()
    return {
        "line": line + line_offset if line > 0 else 0,
        "type": str(issue.get("type", "Issue")),
        "category": str(issue.get("category", "")).lower(),
        "severity": severity if severity in SEVERITIES else "medium",
        "description": str(issue.get("description", "")),
        "fix": str(issue.get("fix", "")),
    }


class GroqService:
    CHUNK_CHARS = 12000
    CONTEXT_LINES = 25

    def __init__(self):
        self.DEFAULT_MODEL = DEFAULT_MODEL

    def _client(self, api_key):
        from groq import Groq  # imported lazily so the rest of the backend works without it
        return Groq(api_key=api_key, max_retries=0)  # we do our own backoff

    def _build_prompt(self, code, filename, language, checks, start_line, total_lines, context):
        wanted = [item for cat, on in checks.items() if on for item in CHECK_PROMPTS.get(cat, [])]
        if not wanted:
            wanted = CHECK_PROMPTS["bugs"]
        categories = ", ".join(cat for cat, on in checks.items() if on) or "bugs"

        parts = [
            f"You are Wolf AI, an elite code analyzer. Analyze this {language} code.",
            "",
            f"FILE: {filename}",
            f"LANGUAGE: {language}",
        ]
        if total_lines:
            end_line = start_line + code.count("\n")
            parts += [
                "",
                f"NOTE: This is only PART of the file (lines {start_line}-{end_line} of {total_lines}).",
                "Names used here may be defined in other parts of the file; do not report them as undefined.",
                "Report line numbers relative to the START OF THIS PART (its first line is line 1).",
            ]
        if context:
            parts += [
                "",
                "PRECEDING CONTEXT (read-only, do NOT analyze it and do NOT include it in fixedCode):",
                f"```{language.lower()}",
                context,
                "```",
            ]
        parts += [
            "",
            "CODE:",
            f"```{language.lower()}",
            code,
            "```",
            "",
            "Look ONLY for these kinds of issues:",
            *[f"- {item}" for item in wanted],
            "",
            "Respond ONLY with valid JSON in this exact format:",
            "{",
            '  "errors": [',
            "    {",
            '      "line": <number>,',
            '      "type": "Error Type",',
            f'      "category": "one of: {categories}",',
            '      "severity": "high/medium/low",',
            '      "description": "What is wrong",',
            '      "fix": "How to fix it"',
            "    }",
            "  ],",
            '  "fixedCode": "The COMPLETE corrected code shown under CODE, with every line kept. '
            'Change only what is needed to fix the reported issues.",',
            '  "summary": "Brief summary of issues found"',
            "}",
            "",
            "If no issues are found, return an empty errors array and fixedCode identical to the input.",
        ]
        return "\n".join(parts)

    def _analyze_chunk(self, client, model, temperature, prompt):
        def call():
            return client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are Wolf AI, an expert code analyzer. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                model=model,
                temperature=temperature,
                max_tokens=8000,
                response_format={"type": "json_object"},
            )
        completion = with_retry(call)
        return json.loads(completion.choices[0].message.content)

    def analyze_code(self, api_key, code, filename, language, model=None, temperature=0.2,
                     checks=None, client=None):
        """
        Analyzes a whole file, chunk by chunk. The returned fixedCode always covers
        the entire file: chunks without a usable fix keep their original text.
        """
        if not api_key and client is None:
            return {"success": False, "error": "API key is missing. Add it in Settings."}

        checks = checks or {"bugs": True, "security": True, "performance": True, "style": False}
        model = model or self.DEFAULT_MODEL
        chunks = split_into_chunks(code, self.CHUNK_CHARS)
        multi = len(chunks) > 1
        total_lines = code.count("\n") + 1

        try:
            client = client or self._client(api_key)
        except Exception as e:
            return {"success": False, "error": f"Groq client error: {e}"}

        errors, summaries, warnings, fixed_parts = [], [], [], []
        failed_chunks = 0
        all_lines = code.splitlines(keepends=True)

        for start_line, text in chunks:
            end_line = start_line + max(0, text.count("\n") - (1 if text.endswith("\n") else 0))
            context = ""
            if multi and start_line > 1:
                context = "".join(all_lines[max(0, start_line - 1 - self.CONTEXT_LINES):start_line - 1])
            prompt = self._build_prompt(text, filename, language, checks,
                                        start_line, total_lines if multi else 0, context)
            try:
                data = self._analyze_chunk(client, model, temperature, prompt)
            except Exception as e:
                failed_chunks += 1
                fixed_parts.append(text)
                label = f" (lines {start_line}-{end_line})" if multi else ""
                warnings.append(f"Analysis failed{label}: {e}")
                continue

            errors += [_normalise_issue(i, start_line - 1) for i in data.get("errors", []) if isinstance(i, dict)]
            if data.get("summary"):
                summaries.append(str(data["summary"]))

            fixed = data.get("fixedCode")
            if not isinstance(fixed, str) or not fixed.strip():
                fixed_parts.append(text)
                continue
            # A fix that is much shorter than the original almost always means the
            # model dropped code. Never offer it.
            if len(text) > 200 and len(fixed) < len(text) * 0.5:
                warnings.append(
                    f"The suggested fix for lines {start_line}-{end_line} was incomplete and was discarded."
                )
                fixed_parts.append(text)
                continue
            if text.endswith("\n") and not fixed.endswith("\n"):
                fixed += "\n"
            fixed_parts.append(fixed)

        if failed_chunks == len(chunks):
            return {"success": False, "error": warnings[0] if warnings else "Analysis failed"}

        if multi:
            summary = f"Analyzed in {len(chunks)} parts. " + " ".join(summaries)
        else:
            summary = summaries[0] if summaries else "Analysis complete"

        return {
            "success": True,
            "errors": sorted(errors, key=lambda e: e["line"]),
            "fixedCode": "".join(fixed_parts),
            "summary": summary.strip(),
            "warnings": warnings,
            "chunks": len(chunks),
        }

    def ask(self, api_key, question, filename, language, code, analysis, history=None,
            model=None, temperature=0.3):
        """Answers a follow-up question about a file and its analysis."""
        if not api_key:
            return {"success": False, "error": "API key is missing. Add it in Settings."}

        if len(code) > self.CHUNK_CHARS:
            # Too big to send whole: send the regions around each reported issue.
            lines = code.splitlines()
            keep = set()
            for issue in analysis.get("errors", []):
                ln = issue.get("line") or 0
                keep.update(range(max(1, ln - 15), min(len(lines), ln + 15) + 1))
            excerpt, prev = [], None
            for ln in sorted(keep):
                if prev is not None and ln != prev + 1:
                    excerpt.append("...")
                excerpt.append(f"{ln}: {lines[ln - 1]}")
                prev = ln
            code_block = "\n".join(excerpt)[: self.CHUNK_CHARS] or code[: self.CHUNK_CHARS]
            code_note = "Excerpts of the file around the reported issues (line numbers prefixed):"
        else:
            code_block = "\n".join(f"{i}: {l}" for i, l in enumerate(code.splitlines(), 1))
            code_note = "The full file (line numbers prefixed):"

        issues = json.dumps(analysis.get("errors", []), indent=1)[:6000]
        system = (
            "You are Wolf AI, a friendly expert code reviewer. You previously analyzed a file. "
            "Answer the user's follow-up questions about it clearly and concisely. "
            "Use Markdown code blocks for code."
        )
        context = (
            f"FILE: {filename} ({language})\n\n{code_note}\n```\n{code_block}\n```\n\n"
            f"Your analysis summary: {analysis.get('summary', '')}\n\nIssues you reported:\n{issues}"
        )
        messages = [{"role": "system", "content": system}, {"role": "user", "content": context},
                    {"role": "assistant", "content": "Got it. What would you like to know about this file?"}]
        for turn in (history or [])[-10:]:
            if turn.get("role") in ("user", "assistant") and turn.get("content"):
                messages.append({"role": turn["role"], "content": str(turn["content"])})
        messages.append({"role": "user", "content": question})

        try:
            client = self._client(api_key)
            completion = with_retry(lambda: client.chat.completions.create(
                messages=messages, model=model or self.DEFAULT_MODEL,
                temperature=temperature, max_tokens=2000,
            ))
            answer = completion.choices[0].message.content or ""
            # Some reasoning models wrap their thinking in <think> tags.
            answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.S).strip()
            return {"success": True, "answer": answer}
        except Exception as e:
            return {"success": False, "error": f"Groq API error: {e}"}

    def list_models(self, api_key):
        if not api_key:
            return {"success": False, "models": FALLBACK_MODELS, "error": "No API key"}
        try:
            models = self._client(api_key).models.list()
            ids = sorted(
                m.id for m in models.data
                if getattr(m, "active", True) and not re.search(r"whisper|tts|guard|playai", m.id)
            )
            return {"success": True, "models": ids or FALLBACK_MODELS}
        except Exception as e:
            return {"success": False, "models": FALLBACK_MODELS, "error": str(e)}
