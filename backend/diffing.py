"""
Turns (original, fixed) into reviewable hunks and applies the accepted ones.
"""
import difflib

CONTEXT = 3


def _split(text):
    return text.splitlines(keepends=True)


def detect_newline(text):
    return "\r\n" if "\r\n" in text else "\n"


def match_newlines(fixed, original):
    """The model answers with \\n; keep the file's own line endings."""
    fixed = fixed.replace("\r\n", "\n")
    if detect_newline(original) == "\r\n":
        fixed = fixed.replace("\n", "\r\n")
    return fixed


def compute_hunks(original, fixed):
    """
    Returns a list of hunks. Each hunk is one contiguous change with a few lines
    of context, shaped for the side-by-side view in the UI.
    """
    a, b = _split(original), _split(fixed)
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    hunks = []
    for opcode in matcher.get_opcodes():
        tag, i1, i2, j1, j2 = opcode
        if tag == "equal":
            continue
        ctx_start = max(0, i1 - CONTEXT)
        ctx_end = min(len(a), i2 + CONTEXT)
        hunks.append({
            "id": len(hunks),
            "op": [i1, i2, j1, j2],
            "oldStart": i1 + 1,
            "newStart": j1 + 1,
            "before": [l.rstrip("\r\n") for l in a[ctx_start:i1]],
            "beforeStart": ctx_start + 1,
            "removed": [l.rstrip("\r\n") for l in a[i1:i2]],
            "added": [l.rstrip("\r\n") for l in b[j1:j2]],
            "after": [l.rstrip("\r\n") for l in a[i2:ctx_end]],
        })
    return hunks


def apply_hunks(original, fixed, accepted_ids):
    """Builds the new file text: original, with only the accepted hunks replaced."""
    a, b = _split(original), _split(fixed)
    accepted = set(accepted_ids)
    out = []
    pos = 0
    for hunk in compute_hunks(original, fixed):
        i1, i2, j1, j2 = hunk["op"]
        out += a[pos:i1]
        out += b[j1:j2] if hunk["id"] in accepted else a[i1:i2]
        pos = i2
    out += a[pos:]
    return "".join(out)
