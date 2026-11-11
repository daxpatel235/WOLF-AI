import json
import os
import shutil
import subprocess
import tempfile
import types

import pytest

from backend.diffing import apply_hunks, compute_hunks, match_newlines
from backend.groq_client import GroqService, split_into_chunks, with_retry


@pytest.fixture
def appdata(monkeypatch):
    """Points the app-data folder (settings, backups, cache) at a temp dir."""
    path = tempfile.mkdtemp()
    monkeypatch.setenv("APPDATA", path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    yield path
    shutil.rmtree(path, ignore_errors=True)


BIG_CODE = "".join(f"def f{i}():\n" + "    x = 1\n" * 40 + "\n" for i in range(60))


class FakeClient:
    """Stands in for the Groq SDK client. The 2nd call returns a fix that drops code."""

    def __init__(self):
        self.calls = 0
        self.chat = self
        self.completions = self

    def create(self, messages, **kwargs):
        self.calls += 1
        prompt = messages[-1]["content"]
        body = prompt.split("CODE:\n```python\n", 1)[1].rsplit("\n```\n\nLook ONLY", 1)[0]
        fixed = body[:50] if self.calls == 2 else body.replace("x = 1", "x = 2", 1)
        content = json.dumps({
            "errors": [{"line": 2, "type": "T", "severity": "HIGH", "description": "d", "fix": "f"}],
            "fixedCode": fixed,
            "summary": "s",
        })
        message = types.SimpleNamespace(content=content)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


# ---------- chunking ----------

def test_chunks_round_trip_and_split_at_definitions():
    chunks = split_into_chunks(BIG_CODE, 2000)
    assert len(chunks) > 1
    assert "".join(text for _, text in chunks) == BIG_CODE
    assert all(text.startswith("def ") for _, text in chunks)
    assert all(len(text) <= 2000 for _, text in chunks)
    lines = BIG_CODE.splitlines(keepends=True)
    for start, text in chunks:
        assert lines[start - 1] == text.splitlines(keepends=True)[0]


def test_small_file_is_one_chunk():
    assert split_into_chunks("x = 1\n", 2000) == [(1, "x = 1\n")]


# ---------- analysis ----------

def test_large_file_analyzed_in_parts_and_never_truncated():
    service = GroqService()
    service.CHUNK_CHARS = 2000
    client = FakeClient()
    result = service.analyze_code("", BIG_CODE, "big.py", "Python", client=client)
    chunks = split_into_chunks(BIG_CODE, 2000)

    assert result["success"]
    assert result["chunks"] == len(chunks) == client.calls
    # the chunk whose fix dropped code is kept as-is, with a warning
    assert len(result["warnings"]) == 1 and "incomplete" in result["warnings"][0]
    assert result["fixedCode"].count("\n") == BIG_CODE.count("\n")
    # issue line numbers are mapped back to whole-file lines
    assert [e["line"] for e in result["errors"]] == [start + 1 for start, _ in chunks]
    assert result["errors"][0]["severity"] == "high"


def test_prompt_only_asks_for_selected_checks():
    prompt = GroqService()._build_prompt(
        "x", "f.py", "Python",
        {"bugs": False, "security": True, "performance": False, "style": False}, 1, 0, "",
    )
    assert "- Security vulnerabilities" in prompt
    assert "Logic bugs" not in prompt and "Performance" not in prompt


def test_missing_key_is_reported():
    result = GroqService().analyze_code("", "x = 1", "a.py", "Python")
    assert not result["success"] and "API key" in result["error"]


def test_retry_backs_off_on_rate_limit():
    calls = {"n": 0}

    class RateLimited(Exception):
        status_code = 429

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RateLimited()
        return "ok"

    assert with_retry(flaky, sleep=lambda s: None) == "ok"
    assert calls["n"] == 3


def test_retry_does_not_retry_other_errors():
    calls = {"n": 0}

    def broken():
        calls["n"] += 1
        raise ValueError("bad request")

    with pytest.raises(ValueError):
        with_retry(broken, sleep=lambda s: None)
    assert calls["n"] == 1


# ---------- diff / review ----------

def test_hunks_can_be_applied_individually():
    a = "a\nb\nc\nd\ne\n"
    b = "a\nB\nc\nd\ne\nf\n"
    assert len(compute_hunks(a, b)) == 2
    assert apply_hunks(a, b, [0]) == "a\nB\nc\nd\ne\n"
    assert apply_hunks(a, b, [1]) == "a\nb\nc\nd\ne\nf\n"
    assert apply_hunks(a, b, [0, 1]) == b
    assert apply_hunks(a, b, []) == a


def test_line_endings_follow_the_original_file():
    assert match_newlines("x\ny\n", "a\r\nb\r\n") == "x\r\ny\r\n"
    assert match_newlines("x\r\ny\n", "a\nb\n") == "x\ny\n"


# ---------- bridge end to end ----------

def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _make_bridge():
    from backend.bridge import ApiBridge
    bridge = ApiBridge()
    bridge.save_settings({"api_key": "gsk_test_key_0123456789"})
    bridge._groq._client = lambda key: FakeClient()
    return bridge


def test_review_apply_revert_and_commit_flow(appdata):
    repo = os.path.join(appdata, "repo")
    os.makedirs(repo)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "core.autocrlf", "false")
    path = os.path.join(repo, "app.py")
    original = "import os\r\nx = 1\r\nprint(x)\r\n"
    with open(path, "w", newline="") as f:
        f.write(original)
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")

    bridge = _make_bridge()

    # analysis never writes; "auto" becomes the detected language
    result = bridge.start_analysis(path, "auto")
    assert result["success"] and result["language"] == "Python" and result["hunks"]
    assert open(path, newline="").read() == original

    # unchanged file -> cached result
    assert bridge.start_analysis(path, "auto")["cached"] is True

    # apply keeps CRLF and creates a backup
    applied = bridge.apply_fix(path, None)
    assert applied["success"], applied
    assert open(path, newline="").read() == "import os\r\nx = 2\r\nprint(x)\r\n"
    assert bridge.undo_status()["count"] == 1

    # git awareness
    assert bridge.git_info(path)["branch"] == "main"
    changed = bridge.git_changed_files(path)["files"]
    assert [os.path.basename(f["path"]) for f in changed] == ["app.py"]

    commit = bridge.commit_fixes()
    assert commit["success"], commit
    info = commit["results"][0]
    assert info["switchedBack"] and info["branch"].startswith("wolf-ai/fixes-")
    # the user's branch is unchanged; the fix lives on the new branch
    assert "x = 1" in open(path).read()
    on_branch = subprocess.run(["git", "show", f"{info['branch']}:app.py"], cwd=repo,
                               capture_output=True, text=True).stdout
    assert "x = 2" in on_branch

    # the file changed after the fix (branch switch), so revert asks first
    assert bridge.revert_last()["needsConfirm"]

    # apply again, then revert cleanly
    bridge.start_analysis(path, "auto")
    bridge.apply_fix(path, None)
    reverted = bridge.revert_last()
    assert reverted["success"], reverted
    assert "x = 1" in open(path).read()


def test_apply_refused_if_file_changed_since_analysis(appdata):
    path = os.path.join(appdata, "a.py")
    with open(path, "w") as f:
        f.write("x = 1\n")
    bridge = _make_bridge()
    bridge.start_analysis(path)
    with open(path, "w") as f:
        f.write("x = 1\ny = 0\n")
    result = bridge.apply_fix(path, None)
    assert not result["success"] and "changed" in result["error"]


def test_analyze_only_mode_never_writes(appdata):
    path = os.path.join(appdata, "a.py")
    with open(path, "w") as f:
        f.write("x = 1\n")
    bridge = _make_bridge()
    bridge.save_settings({"analyze_only": True})
    assert bridge.start_analysis(path)["analyzeOnly"] is True
    assert not bridge.apply_fix(path, None)["success"]
    assert open(path).read() == "x = 1\n"


def test_non_utf8_file_is_refused(appdata):
    path = os.path.join(appdata, "bad.py")
    with open(path, "wb") as f:
        f.write(b"x = '\xff'\n")
    result = _make_bridge().start_analysis(path)
    assert not result["success"] and "UTF-8" in result["error"]


def test_settings_never_return_the_key(appdata):
    bridge = _make_bridge()
    public = bridge.get_settings()
    assert public["api_key"] == "" and public["has_key"] and public["key_hint"].startswith("gsk_")


def test_dialog_filter_matches_supported_extensions(appdata):
    from backend.file_manager import LANGUAGE_MAP
    patterns = _make_bridge()._file_manager.dialog_filter()[0]
    for ext in LANGUAGE_MAP:
        assert f"*{ext}" in patterns
    assert ".html" not in patterns and ".css" not in patterns


def test_dropped_paths_are_filtered_and_folders_scanned(appdata):
    folder = os.path.join(appdata, "proj")
    os.makedirs(os.path.join(folder, "node_modules"))
    for name in ("a.py", "b.txt", os.path.join("node_modules", "c.js")):
        with open(os.path.join(folder, name), "w") as f:
            f.write("x")
    names = [f["name"] for f in _make_bridge().files_from_paths([folder, os.path.join(folder, "b.txt")])]
    assert names == ["a.py"]


def test_version_is_2():
    from backend.version import __version__
    assert __version__.startswith("2.")
