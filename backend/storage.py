"""
Backups (for undo) and the analysis cache (for skipping unchanged files).
Both live in the app-data folder; see config.app_data_dir().
"""
import hashlib
import json
import os
import shutil
import threading
import time
import uuid

from .config import app_data_dir, atomic_write_json


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm(path):
    return os.path.normcase(os.path.abspath(path))


class BackupStore:
    """Keeps a copy of every file before Wolf AI writes to it."""

    MAX_ENTRIES = 200

    def __init__(self, root=None):
        self.root = root or os.path.join(app_data_dir(), "backups")
        os.makedirs(self.root, exist_ok=True)
        self.index_path = os.path.join(self.root, "index.json")
        self._lock = threading.Lock()

    def _read_index(self):
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return []

    def _write_index(self, entries):
        # Drop the oldest entries (and their files) beyond the limit.
        while len(entries) > self.MAX_ENTRIES:
            old = entries.pop(0)
            try:
                os.remove(old["backup_file"])
            except OSError:
                pass
        atomic_write_json(self.index_path, entries)

    def backup(self, path, written_text):
        """
        Copies `path` to the backup folder. Call before overwriting it.
        `written_text` is what is about to be written, so a later revert can tell
        whether the file has been edited since.
        """
        with self._lock:
            entry_id = uuid.uuid4().hex[:12]
            backup_file = os.path.join(self.root, f"{entry_id}_{os.path.basename(path)}.wolfbak")
            shutil.copy2(path, backup_file)
            entries = self._read_index()
            entries.append({
                "id": entry_id,
                "path": os.path.abspath(path),
                "backup_file": backup_file,
                "written_hash": sha256_text(written_text),
                "time": time.time(),
                "reverted": False,
            })
            self._write_index(entries)
            return entry_id

    def latest(self):
        with self._lock:
            for entry in reversed(self._read_index()):
                if not entry["reverted"] and os.path.exists(entry["backup_file"]):
                    return entry
        return None

    def available_count(self):
        with self._lock:
            return sum(1 for e in self._read_index()
                       if not e["reverted"] and os.path.exists(e["backup_file"]))

    def revert_last(self, force=False):
        """
        Restores the most recent backup. Refuses (unless force) when the file
        was changed after Wolf AI wrote it, so the user's later edits aren't lost.
        """
        entry = self.latest()
        if not entry:
            return {"success": False, "error": "Nothing to revert."}

        path = entry["path"]
        if not force and os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                current = f.read()
            if sha256_text(current) != entry["written_hash"]:
                return {
                    "success": False,
                    "needsConfirm": True,
                    "path": path,
                    "error": f"{os.path.basename(path)} changed after the fix was applied. "
                             "Reverting will discard those changes.",
                }

        with self._lock:
            shutil.copy2(entry["backup_file"], path)
            entries = self._read_index()
            for e in entries:
                if e["id"] == entry["id"]:
                    e["reverted"] = True
            self._write_index(entries)
        return {"success": True, "path": path, "name": os.path.basename(path)}


class AnalysisCache:
    """Maps file path -> (content hash, settings fingerprint, result)."""

    MAX_ENTRIES = 1000

    def __init__(self, path=None):
        self.path = path or os.path.join(app_data_dir(), "analysis_cache.json")
        self._lock = threading.Lock()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except (OSError, ValueError):
            self._data = {}

    def get(self, path, content_hash, fingerprint):
        with self._lock:
            entry = self._data.get(_norm(path))
        if entry and entry["hash"] == content_hash and entry["fingerprint"] == fingerprint:
            return entry["result"]
        return None

    def put(self, path, content_hash, fingerprint, result):
        with self._lock:
            self._data[_norm(path)] = {
                "hash": content_hash,
                "fingerprint": fingerprint,
                "result": result,
                "time": time.time(),
            }
            if len(self._data) > self.MAX_ENTRIES:
                oldest = sorted(self._data.items(), key=lambda kv: kv[1]["time"])
                for key, _ in oldest[: len(self._data) - self.MAX_ENTRIES]:
                    del self._data[key]
            atomic_write_json(self.path, self._data)

    def clear(self):
        with self._lock:
            self._data = {}
            atomic_write_json(self.path, self._data)
