"""
User settings and app-data storage.

Everything Wolf AI writes for itself (settings, backups, analysis cache) lives in
a per-user folder, never next to the source code or inside the .exe:
  Windows: %APPDATA%\\WolfAI
  macOS/Linux: ~/.config/WolfAI
"""
import copy
import json
import os
import sys
import threading

DEFAULT_MODEL = "llama-3.3-70b-versatile"

# Shown in the model picker if the live model list can't be fetched.
FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3-32b",
]

CHECK_CATEGORIES = ("bugs", "security", "performance", "style")

DEFAULTS = {
    "api_key": "",
    "model": DEFAULT_MODEL,
    "temperature": 0.2,
    "analyze_only": False,
    "concurrency": 3,
    "skip_unchanged": True,
    "checks": {"bugs": True, "security": True, "performance": True, "style": False},
}


def app_data_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, "WolfAI")
    os.makedirs(path, exist_ok=True)
    return path


def atomic_write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _legacy_key():
    """
    Older builds read the key from wolf_key.json. Still honoured (next to the
    .exe / working dir, or in the source folder) so existing setups keep working,
    but the file is no longer bundled or tracked in git.
    """
    candidates = [os.path.join(os.getcwd(), "wolf_key.json")]
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), "wolf_key.json"))
    candidates.append(os.path.join(os.path.dirname(__file__), "..", "wolf_key.json"))
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                key = json.load(f).get("api_key", "")
            if key and key.startswith("gsk_"):
                return key
        except (OSError, ValueError):
            continue
    return ""


class Settings:
    def __init__(self, path=None):
        self.path = path or os.path.join(app_data_dir(), "settings.json")
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self):
        data = copy.deepcopy(DEFAULTS)
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                stored = json.load(f)
            for key, value in stored.items():
                if key == "checks" and isinstance(value, dict):
                    data["checks"].update({k: bool(v) for k, v in value.items() if k in CHECK_CATEGORIES})
                elif key in DEFAULTS:
                    data[key] = value
        except (OSError, ValueError):
            pass
        return data

    def get(self, key):
        with self._lock:
            return copy.deepcopy(self._data[key])

    def api_key(self):
        return self.get("api_key") or os.environ.get("GROQ_API_KEY", "") or _legacy_key()

    def snapshot(self):
        with self._lock:
            return copy.deepcopy(self._data)

    def public(self):
        """Settings safe to send to the UI: the key is masked."""
        data = self.snapshot()
        key = self.api_key()
        data["api_key"] = ""
        data["has_key"] = bool(key)
        data["key_hint"] = f"{key[:4]}…{key[-4:]}" if len(key) > 8 else ""
        data["key_source"] = (
            "settings" if self._data["api_key"]
            else "environment" if os.environ.get("GROQ_API_KEY")
            else "wolf_key.json" if key else ""
        )
        return data

    def update(self, changes):
        """Validates and saves the given changes. An empty api_key keeps the stored one."""
        with self._lock:
            data = self._data
            if "api_key" in changes:
                key = str(changes["api_key"] or "").strip()
                if key:
                    data["api_key"] = key
            if changes.get("clear_api_key"):
                data["api_key"] = ""
            if "model" in changes and str(changes["model"]).strip():
                data["model"] = str(changes["model"]).strip()
            if "temperature" in changes:
                data["temperature"] = min(1.0, max(0.0, float(changes["temperature"])))
            if "concurrency" in changes:
                data["concurrency"] = min(5, max(1, int(changes["concurrency"])))
            for flag in ("analyze_only", "skip_unchanged"):
                if flag in changes:
                    data[flag] = bool(changes[flag])
            if isinstance(changes.get("checks"), dict):
                for k, v in changes["checks"].items():
                    if k in CHECK_CATEGORIES:
                        data["checks"][k] = bool(v)
            atomic_write_json(self.path, data)
