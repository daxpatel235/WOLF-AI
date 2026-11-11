"""
Checks that the app's self-test works and that the build scripts, installer definitions and
release workflow agree on versions and file names (the builds themselves run in CI).
"""
import os
import re
import struct
from pathlib import Path

import pytest
import yaml

import main
from backend.version import __version__

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / "packaging" / "icons"

EXPECTED_ASSETS = [
    "WolfAI-{v}-x64-setup.exe",
    "WolfAI-{v}-x64.msi",
    "WolfAI-{v}-aarch64.dmg",
    "WolfAI-{v}-x64.dmg",
    "WolfAI-{v}-amd64.AppImage",
    "WolfAI-{v}-amd64.deb",
    "WolfAI-{v}-x86_64.rpm",
]


# ---------- self-test ----------

@pytest.fixture
def restore_appdata():
    old = os.environ.get("APPDATA")
    yield
    if old is None:
        os.environ.pop("APPDATA", None)
    else:
        os.environ["APPDATA"] = old


def test_self_test_passes_from_source(tmp_path, restore_appdata):
    report = tmp_path / "report.txt"
    assert main.self_test(str(report), check_gui=False) == 0
    assert "self-test: OK" in report.read_text(encoding="utf-8")


def test_self_test_reports_missing_ui_files(tmp_path, monkeypatch, restore_appdata):
    monkeypatch.setattr(main, "get_resource_path", lambda rel: str(tmp_path / rel))
    report = tmp_path / "report.txt"
    assert main.self_test(str(report), check_gui=False) == 1
    text = report.read_text(encoding="utf-8")
    assert "FAILED" in text and "Web/index.html" in text


def test_every_platform_has_a_gui_backend():
    for platform in ("win32", "darwin", "linux"):
        assert main.GUI_BY_PLATFORM[platform]
        assert main.SELF_TEST_MODULES[platform]


# ---------- versions & names ----------

def test_changelog_has_current_version():
    assert re.search(rf"^## \[{re.escape(__version__)}\]", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)


def test_build_scripts_produce_the_release_asset_names():
    scripts = "".join((ROOT / "scripts" / n).read_text(encoding="utf-8")
                      for n in ("build.ps1", "build_macos.sh", "build_linux.sh"))
    iss = (ROOT / "packaging" / "WolfAI.iss").read_text(encoding="utf-8")
    produced = scripts + iss
    patterns = {
        "x64-setup.exe": "WolfAI-{#AppVersion}-x64-setup",
        "x64.msi": "WolfAI-$Version-x64.msi",
        ".dmg": "WolfAI-${VERSION}-${LABEL}.dmg",
        ".AppImage": "WolfAI-${VERSION}-amd64.AppImage",
        ".deb": "WolfAI-${VERSION}-amd64.deb",
        ".rpm": "WolfAI-${VERSION}-x86_64.rpm",
    }
    for kind, pattern in patterns.items():
        assert pattern in produced, f"build scripts no longer produce the {kind} name {pattern}"


def test_release_workflow_publishes_every_asset():
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    for name in EXPECTED_ASSETS:
        assert name.replace("{v}", "$v") in release, f"release.yml doesn't check/publish {name}"


def test_workflows_are_valid_yaml():
    for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
        data = yaml.safe_load(wf.read_text(encoding="utf-8"))
        assert data.get("jobs"), f"{wf.name} has no jobs"


def test_build_workflow_covers_all_platforms():
    build = yaml.safe_load((ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8"))
    jobs = build["jobs"]
    assert set(jobs) == {"windows", "macos", "linux"}
    labels = {m["label"] for m in jobs["macos"]["strategy"]["matrix"]["include"]}
    assert labels == {"aarch64", "x64"}
    for job in jobs.values():
        steps = " ".join(str(s.get("run", "")) for s in job["steps"])
        assert "check_" in steps, "every platform job must run its check script"


def test_installer_ids_are_fixed_guids():
    # Changing these breaks upgrades from older versions.
    assert "7B1E5C2A-9F44-4C3B-8E61-2D0A6F3B9C17" in (ROOT / "packaging" / "WolfAI.wxs").read_text(encoding="utf-8")
    assert "B0D3A6E2-5C1F-4E8A-9D47-3F2C8A1B6E90" in (ROOT / "packaging" / "WolfAI.iss").read_text(encoding="utf-8")


# ---------- icons ----------

def test_icons_are_valid():
    png = (ICONS / "wolfai.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", png[16:24]) == (512, 512)

    ico = (ICONS / "wolfai.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", ico[:6])
    assert (reserved, kind) == (0, 1) and count >= 5

    icns = (ICONS / "wolfai.icns").read_bytes()
    assert icns[:4] == b"icns" and struct.unpack(">I", icns[4:8])[0] == len(icns)

    assert (ICONS / "wolfai-256.png").exists()


def _data_lines(path):
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip() and not raw.lstrip().startswith("#"):
            lines.append(raw)
    return lines


def test_every_qt_system_library_has_a_deb_dependency():
    linux = ROOT / "packaging" / "linux"
    sonames = {line.strip() for line in _data_lines(linux / "qt-sonames.txt")}
    covered = set()
    for line in _data_lines(linux / "deb-depends.txt"):
        assert "#" in line, f"deb-depends.txt line has no soname comment: {line}"
        dep, comment = line.split("#", 1)
        assert dep.strip(), f"empty dependency: {line}"
        covered |= set(comment.split())
    assert sonames, "qt-sonames.txt is empty"
    assert not sonames - covered, f"no .deb dependency provides: {sorted(sonames - covered)}"
    assert not covered - sonames, f"deb-depends.txt lists unknown sonames: {sorted(covered - sonames)}"
    for must in ("libEGL.so.1", "libxcb-cursor.so.0", "libnss3.so", "libatomic.so.1"):
        assert must in sonames


def test_desktop_entry():
    entry = (ROOT / "packaging" / "linux" / "wolf-ai.desktop").read_text(encoding="utf-8")
    for line in ("Type=Application", "Exec=wolf-ai", "Icon=wolf-ai", "Terminal=false"):
        assert line in entry
