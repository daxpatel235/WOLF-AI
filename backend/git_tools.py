"""
Small wrappers around the git CLI. Everything degrades gracefully when git
isn't installed or the folder isn't a repository.
"""
import os
import subprocess
import time

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # no console flash on Windows


def _git(cwd, *args, check=True):
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", creationflags=_NO_WINDOW,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result


def repo_root(path):
    """Top-level folder of the repo containing `path`, or None."""
    folder = path if os.path.isdir(path) else os.path.dirname(path)
    try:
        result = _git(folder, "rev-parse", "--show-toplevel", check=False)
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    return os.path.normpath(result.stdout.strip())


def current_branch(root):
    name = _git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    return None if name == "HEAD" else name  # None = detached HEAD


def repo_info(path):
    root = repo_root(path)
    if not root:
        return {"isRepo": False}
    try:
        branch = current_branch(root) or "(detached)"
    except RuntimeError:
        branch = "(no commits)"
    return {"isRepo": True, "root": root, "name": os.path.basename(root), "branch": branch}


def changed_files(root):
    """Absolute paths of modified, added and untracked files (not deleted ones)."""
    out = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
    entries = out.split("\0")
    paths = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        status, rel = entry[:2], entry[3:]
        if status[0] in "RC":
            i += 1  # rename/copy entries are followed by the old path
        if "D" in status:
            continue
        full = os.path.normpath(os.path.join(root, rel))
        if os.path.isfile(full):
            paths.append(full)
    return paths


def rel_path(path, root):
    """
    Repo-relative path. Git reports the root with symlinks resolved (e.g. macOS /var is really
    /private/var), so resolve both sides or the result points outside the repo.
    """
    return os.path.relpath(os.path.realpath(path), os.path.realpath(root))


def head_text(root, path):
    """File content at HEAD, or None if it isn't tracked there."""
    rel = rel_path(path, root).replace(os.sep, "/")
    result = _git(root, "show", f"HEAD:{rel}", check=False)
    return result.stdout if result.returncode == 0 else None


def commit_to_new_branch(root, paths, message):
    """
    Commits `paths` on a new branch and switches back, leaving the original
    branch as it was before the fixes. Returns the new branch name.
    """
    original = current_branch(root)
    original_ref = original or _git(root, "rev-parse", "HEAD").stdout.strip()
    branch = time.strftime("wolf-ai/fixes-%Y%m%d-%H%M%S")
    rels = [rel_path(p, root) for p in paths]

    _git(root, "switch", "-c", branch)
    try:
        _git(root, "add", "--", *rels)
        _git(root, "commit", "-m", message, "--", *rels)
    except RuntimeError:
        # Nothing committed: go back and drop the empty branch.
        _git(root, "switch", *(["--detach"] if not original else []), original_ref, check=False)
        _git(root, "branch", "-D", branch, check=False)
        raise

    switched = _git(root, "switch", *(["--detach"] if not original else []), original_ref, check=False)
    return {
        "branch": branch,
        "returnedTo": original or original_ref[:8],
        "switchedBack": switched.returncode == 0,
        "switchError": switched.stderr.strip() if switched.returncode else "",
    }
