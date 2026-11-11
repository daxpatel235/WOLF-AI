# Changelog

## [2.0.0] - 2026-11-11

Wolf AI now asks before it changes your code, and you can undo any fix it writes.

### Highlights
- **Review fixes before saving.** Fixes are shown side by side with the current code. Apply every change, only the ones you tick, or reject the fix. Nothing is written to disk until you click Apply.
- **Backups and undo.** Each file is backed up before a fix is written. **Revert last fix** restores it, and asks first if you have edited the file since.
- **Large files are analyzed in parts.** Files over ~12,000 characters are split at function and class boundaries instead of being cut short. A suggested fix that drops code is discarded.
- **Settings panel (⚙).** Enter your Groq API key in the app. You can also pick a model, set the temperature, choose how many files run at once, and turn on **analyze only, never write**.
- **Ask about a file.** Ask follow-up questions about any result, for example "why is this a bug?" or "explain this fix".
- **Click an issue to see the code.** The surrounding lines are shown with the reported line highlighted.
- **Choose what to check:** Bugs, Security, Performance, Style.
- **Faster folder scans.** Up to 5 files are analyzed at once, with automatic retry and backoff when Groq rate-limits.
- **Git aware.** Load only files with uncommitted changes, and commit applied fixes to a separate `wolf-ai/fixes-…` branch. Your own branch is left untouched.
- **Unchanged files are skipped.** The last result is reused when a file's content hasn't changed.
- **Drag & drop** files or folders anywhere on the window.
- **Installers for every desktop.** Windows `x64-setup.exe` and `.msi`, macOS `.dmg` for Apple silicon and Intel, and Linux `.AppImage`, `.deb` and `.rpm`.
- **New app icon** featuring the wolf mascot.

### Fixed
- Files larger than 12,000 characters were cut short and the shortened "fix" was saved over the original, losing the rest of the file.
- "Auto Detect" sent the literal word `auto` to the model instead of the detected language.
- The log always said "auto-saved", even when nothing changed.
- The file picker filter didn't match the supported file types.
- Line endings (CRLF) and UTF-8 BOMs are now kept when a fix is written. Files that aren't UTF-8 are refused instead of being corrupted.
- Dropping a file outside the drop zone could navigate the window away from the app.

### Security
- The API key is no longer stored in the repository or bundled into the `.exe`. It is saved in your user profile (`%APPDATA%\WolfAI`) and is never sent back to the UI. If you used a real key in `wolf_key.json` before, rotate it.

### Developer
- GitHub Actions: lint and tests (backend, UI contract, packaging, and a headless-browser UI smoke test) on Windows, macOS and Linux.
- Every push builds all installers. Each one is installed or mounted on a CI runner, the app's `--self-test` runs there, and Windows and Linux packages are uninstalled again. The `.rpm` is tested on Fedora.
- Pushing a `v*.*.*` tag builds and checks everything, then publishes a GitHub release with SHA-256 checksums.
- Build scripts per platform: `scripts/build.ps1`, `scripts/build_macos.sh`, `scripts/build_linux.sh`.

## [1.0.0]

- First release: animated wolf mascot, Groq-powered analysis and auto-fix, drag & drop, HTML report export.
