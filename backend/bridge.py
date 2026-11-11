import os
import socket
import sys
import threading

import webview

from . import git_tools
from .config import Settings
from .diffing import apply_hunks, compute_hunks, match_newlines
from .file_manager import FileManager
from .groq_client import GroqService
from .storage import AnalysisCache, BackupStore, sha256_text
from .version import __version__

# Bump when the prompt changes so cached results from the old prompt aren't reused.
PROMPT_VERSION = 2


def _key(path):
    return os.path.normcase(os.path.abspath(path))


def _same_text(a, b):
    norm = lambda t: t.lstrip("﻿").replace("\r\n", "\n")
    return norm(a) == norm(b)


class ApiBridge:
    def __init__(self):
        self._file_manager = FileManager()
        self._groq = GroqService()
        self._settings = Settings()
        self._backups = BackupStore()
        self._cache = AnalysisCache()
        self._window = None
        self._lock = threading.Lock()
        self._analyses = {}   # path key -> last analysis of the file this session (for review + chat)
        self._applied = {}    # path key -> {"path", "pre_text"}: files changed this session (for git commit)

    def get_version(self):
        return __version__

    def files_from_paths(self, paths):
        """Queue entries for dropped paths: folders are scanned, other files filtered by extension."""
        found = []
        for path in paths or []:
            if os.path.isdir(path):
                found.extend(self._file_manager.scan_folder(path))
            elif os.path.isfile(path) and self._file_manager._is_valid_file(path):
                details = self._file_manager.get_file_details(path)
                if details:
                    found.append(details)
        return found

    def set_window(self, window):
        """Allows the bridge to access window features like file dialogs."""
        self._window = window

    # ==========================
    # Connection & app
    # ==========================

    def check_connection(self):
        """True if the internet is reachable (Google DNS on port 53)."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3).close()
            return True
        except OSError:
            return False

    def check_api_key(self):
        key = self._settings.api_key()
        return bool(key and key.startswith("gsk_"))

    def quit_app(self):
        try:
            if self._window:
                self._window.destroy()
        finally:
            sys.exit(0)

    # ==========================
    # Settings
    # ==========================

    def get_settings(self):
        return self._settings.public()

    def save_settings(self, changes):
        try:
            self._settings.update(changes or {})
            return {"success": True, "settings": self._settings.public()}
        except (ValueError, TypeError, OSError) as e:
            return {"success": False, "error": str(e)}

    def list_models(self):
        return self._groq.list_models(self._settings.api_key())

    def clear_cache(self):
        self._cache.clear()
        return True

    # ==========================
    # File selection
    # ==========================

    def select_folder(self):
        if not self._window:
            return []
        folder_path = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if folder_path:
            return self._file_manager.scan_folder(folder_path[0])
        return []

    def select_files(self):
        if not self._window:
            return []
        file_paths = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=self._file_manager.dialog_filter(),
        )
        valid_files = []
        for path in file_paths or []:
            details = self._file_manager.get_file_details(path)
            if details:
                valid_files.append(details)
        return valid_files

    # ==========================
    # Analysis
    # ==========================

    def _fingerprint(self, language):
        s = self._settings.snapshot()
        checks = ",".join(k for k, v in sorted(s["checks"].items()) if v)
        return f"v{PROMPT_VERSION}|{s['model']}|{checks}|{language}"

    def start_analysis(self, file_path, language="auto"):
        """
        Analyzes one file. Nothing is written to disk: the fix comes back as
        hunks for the user to review, then apply_fix() writes the accepted ones.
        """
        name = os.path.basename(file_path)
        try:
            code = self._file_manager.read_file_content(file_path)
        except (OSError, ValueError) as e:
            return {"success": False, "error": str(e)}

        if not language or language == "auto":
            language = self._file_manager._detect_language(name)

        content_hash = sha256_text(code)
        fingerprint = self._fingerprint(language)
        s = self._settings.snapshot()

        result = self._cache.get(file_path, content_hash, fingerprint) if s["skip_unchanged"] else None
        cached = result is not None
        if not cached:
            result = self._groq.analyze_code(
                self._settings.api_key(), code, name, language,
                model=s["model"], temperature=s["temperature"], checks=s["checks"],
            )
            if not result["success"]:
                return result
            if not result.get("warnings"):  # don't cache partial results
                self._cache.put(file_path, content_hash, fingerprint, result)

        fixed = match_newlines(result.get("fixedCode") or code, code)
        hunks = compute_hunks(code, fixed)

        with self._lock:
            self._analyses[_key(file_path)] = {
                "path": file_path, "name": name, "language": language,
                "code": code, "fixed": fixed, "hash": content_hash, "result": result,
            }

        return {
            "success": True,
            "errors": result.get("errors", []),
            "summary": result.get("summary", ""),
            "warnings": result.get("warnings", []),
            "chunks": result.get("chunks", 1),
            "cached": cached,
            "language": language,
            "code": code,
            "hunks": hunks,
            "analyzeOnly": s["analyze_only"],
        }

    # ==========================
    # Review, apply, revert
    # ==========================

    def apply_fix(self, file_path, hunk_ids=None):
        """Writes the accepted hunks (all of them if hunk_ids is None), after a backup."""
        if self._settings.get("analyze_only"):
            return {"success": False, "error": "Analyze-only mode is on, so files are never written."}

        with self._lock:
            analysis = self._analyses.get(_key(file_path))
        if not analysis:
            return {"success": False, "error": "No pending fix for this file. Run the analysis again."}

        try:
            current = self._file_manager.read_file_content(file_path)
        except (OSError, ValueError) as e:
            return {"success": False, "error": str(e)}
        if sha256_text(current) != analysis["hash"]:
            return {"success": False, "error": "The file changed after it was analyzed. Run the analysis again."}

        ids = [h["id"] for h in compute_hunks(analysis["code"], analysis["fixed"])] if hunk_ids is None else hunk_ids
        new_text = apply_hunks(analysis["code"], analysis["fixed"], ids)
        if new_text == current:
            return {"success": False, "error": "No changes selected."}

        try:
            bom = self._file_manager.has_bom(file_path)
            backup_id = self._backups.backup(file_path, new_text)
            self._file_manager.save_file_content(file_path, new_text, bom=bom)
        except OSError as e:
            return {"success": False, "error": f"Could not write file: {e}"}

        with self._lock:
            self._analyses.pop(_key(file_path), None)
            self._applied.setdefault(_key(file_path), {"path": file_path, "pre_text": current})
        return {"success": True, "backupId": backup_id, "applied": len(ids),
                "undoCount": self._backups.available_count()}

    def reject_fix(self, file_path):
        with self._lock:
            analysis = self._analyses.get(_key(file_path))
            if analysis:
                analysis["fixed"] = analysis["code"]  # keep it for chat, drop the fix
        return True

    def undo_status(self):
        latest = self._backups.latest()
        return {"count": self._backups.available_count(),
                "latest": os.path.basename(latest["path"]) if latest else ""}

    def revert_last(self, force=False):
        result = self._backups.revert_last(force=bool(force))
        if result.get("success"):
            with self._lock:
                entry = self._applied.get(_key(result["path"]))
                if entry:
                    try:
                        if _same_text(self._file_manager.read_file_content(result["path"]), entry["pre_text"]):
                            self._applied.pop(_key(result["path"]), None)
                    except (OSError, ValueError):
                        pass
        result["undoCount"] = self._backups.available_count()
        return result

    # ==========================
    # Git
    # ==========================

    def git_info(self, path):
        try:
            return git_tools.repo_info(path)
        except (OSError, RuntimeError) as e:
            return {"isRepo": False, "error": str(e)}

    def git_changed_files(self, path):
        root = git_tools.repo_root(path)
        if not root:
            return {"success": False, "error": "Not a git repository."}
        try:
            paths = git_tools.changed_files(root)
        except (OSError, RuntimeError) as e:
            return {"success": False, "error": str(e)}
        files = [self._file_manager.get_file_details(p) for p in paths if self._file_manager._is_valid_file(p)]
        return {"success": True, "root": root, "files": [f for f in files if f]}

    def git_commit_status(self):
        with self._lock:
            applied = list(self._applied.values())
        repos = {}
        for entry in applied:
            root = git_tools.repo_root(entry["path"])
            if root:
                repos.setdefault(root, []).append(entry["path"])
        return {"count": sum(len(v) for v in repos.values()), "repos": len(repos)}

    def commit_fixes(self):
        """
        Commits the files fixed this session to a new branch per repo, then switches
        back so the user's branch is unchanged. Files that weren't clean at HEAD
        before the fix are skipped, so none of the user's own edits move branches.
        """
        with self._lock:
            applied = list(self._applied.items())

        by_repo, skipped = {}, []
        for key, entry in applied:
            path = entry["path"]
            root = git_tools.repo_root(path)
            if not root:
                continue
            name = os.path.basename(path)
            head = git_tools.head_text(root, path)
            if head is None:
                skipped.append(f"{name} (not committed in git yet)")
            elif not _same_text(head, entry["pre_text"]):
                skipped.append(f"{name} (had your own uncommitted changes)")
            else:
                by_repo.setdefault(root, []).append((key, path))

        if not by_repo:
            return {"success": False, "skipped": skipped,
                    "error": "No fixed files can be committed." + (" Skipped: " + ", ".join(skipped) if skipped else "")}

        results = []
        for root, items in by_repo.items():
            paths = [p for _, p in items]
            message = "Wolf AI fixes\n\n" + "\n".join(f"- {os.path.relpath(p, root)}" for p in paths)
            try:
                info = git_tools.commit_to_new_branch(root, paths, message)
            except (OSError, RuntimeError) as e:
                results.append({"repo": os.path.basename(root), "success": False, "error": str(e)})
                continue
            with self._lock:
                for key, _ in items:
                    self._applied.pop(key, None)
            results.append({"repo": os.path.basename(root), "success": True, "files": len(paths), **info})

        return {"success": any(r["success"] for r in results), "results": results, "skipped": skipped}

    # ==========================
    # Follow-up questions
    # ==========================

    def ask_question(self, file_path, question, history=None):
        with self._lock:
            analysis = self._analyses.get(_key(file_path))
        if analysis:
            code, result, language = analysis["code"], analysis["result"], analysis["language"]
        else:
            # The fix was applied; answer about the file as it is now.
            try:
                code = self._file_manager.read_file_content(file_path)
            except (OSError, ValueError) as e:
                return {"success": False, "error": str(e)}
            result = {"summary": "(fix applied since)", "errors": []}
            language = self._file_manager._detect_language(file_path)

        s = self._settings.snapshot()
        return self._groq.ask(
            self._settings.api_key(), question, os.path.basename(file_path), language,
            code, result, history=history, model=s["model"],
        )

    # ==========================
    # Report
    # ==========================

    def save_report(self, filename, content):
        if not self._window:
            return False
        save_path = self._window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=filename, file_types=('HTML Files (*.html)',)
        )
        if save_path:
            try:
                final_path = save_path if isinstance(save_path, str) else save_path[0]
                with open(final_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            except OSError:
                return False
        return False
