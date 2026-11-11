"""
Loads Web/index.html in headless Chrome/Edge with a fake Python bridge and drives the UI
(tests/frontend/smoke.js). Catches JS errors and blank-window problems without starting the app.

The browser is taken from $BROWSER_BIN, else Edge/Chrome/Chromium in the usual places.
The test is skipped if none is found.
"""
import html
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web"
SMOKE = ROOT / "tests" / "frontend" / "smoke.js"


def find_browser():
    candidates = [os.environ.get("BROWSER_BIN")]
    candidates += [shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge", "chrome")]
    candidates += [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    return next((c for c in candidates if c and os.path.exists(c)), None)


def run_smoke(browser):
    with tempfile.TemporaryDirectory() as tmp:
        page = (WEB / "index.html").read_text(encoding="utf-8")
        page = page.replace('href="styles.css"', f'href="{(WEB / "styles.css").as_uri()}"')
        page = page.replace(
            '<script src="script.js"></script>',
            f'<script src="{SMOKE.as_uri()}"></script>\n<script src="{(WEB / "script.js").as_uri()}"></script>',
        )
        harness = Path(tmp) / "harness.html"
        harness.write_text(page, encoding="utf-8")

        result = subprocess.run(
            [browser, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-first-run",
             "--allow-file-access-from-files", f"--user-data-dir={Path(tmp) / 'profile'}",
             "--virtual-time-budget=15000", "--dump-dom", harness.as_uri()],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        )
    match = re.search(r'<pre id="out">(.*?)</pre>', result.stdout, re.S)
    assert match, f"smoke test produced no output.\nstdout: {result.stdout[-2000:]}\nstderr: {result.stderr[-2000:]}"
    return html.unescape(match.group(1))


def test_frontend_smoke():
    browser = find_browser()
    if not browser:
        pytest.skip("no Chrome/Edge/Chromium found (set BROWSER_BIN)")
    output = run_smoke(browser)
    print(output)
    failures = [line for line in output.splitlines() if line.startswith("FAIL")]
    assert "PASS" in output, output
    assert not failures, "\n".join(failures) + "\n\n" + output
