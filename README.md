# 🐺 Wolf AI Code Debugger

[![CI](https://github.com/daxpatel235/WOLF-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/daxpatel235/WOLF-AI/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/daxpatel235/WOLF-AI)](https://github.com/daxpatel235/WOLF-AI/releases/latest)

A modern, AI-powered code debugging tool with an intuitive desktop interface and an **animated wolf mascot** that responds to your interactions!

## ⬇️ Download (Windows)

Get the latest version from the [Releases page](https://github.com/daxpatel235/WOLF-AI/releases/latest):

| File | What it is |
|---|---|
| `WolfAI-<version>-x64.msi` | Installer: adds Start Menu and desktop shortcuts, uninstall from Settings → Apps |
| `WolfAI-<version>-portable.exe` | Single file, no install needed (starts a little slower) |
| `WolfAI-<version>-win64.zip` | The app folder, unzip and run `WolfAI.exe` |

Requires Windows 10/11 with the Microsoft Edge WebView2 Runtime (already included in Windows 11 and up-to-date Windows 10).
The builds aren't code-signed yet, so Windows SmartScreen may warn on first run: click **More info → Run anyway**.

See [CHANGELOG.md](CHANGELOG.md) for what's new in each version.

## 🎨 What's New in This Version

### ✨ Enhanced Features

1. **🐺 Animated Wolf Mascot**
   - Follows your cursor with realistic eye movement
   - Shows different moods: Happy, Bored, Sleeping, Alert
   - Blinks naturally and unpredictably
   - Falls asleep when inactive for 30 seconds
   - Wakes up and becomes alert when you move the mouse
   - Displays different facial expressions based on activity

2. **🧠 "Brain Active" Status**
   - Single connection indicator showing both Internet AND API status
   - "Brain Active" = Everything working
   - "Brain Off" = Either no internet OR invalid API key
   - Clear, simple status messages

3. **📂 Redesigned File Controls**
   - "New Chat" button at the top of sidebar
   - "Select Files" and "Select Folder" buttons side-by-side
   - Full-width drop zone below buttons
   - Better visual hierarchy

4. **🏷️ Rebranded as "Code Debugger"**
   - More accurate description of functionality
   - Detects AND solves code issues
   - Title bar updated everywhere

5. **🎯 Other Improvements**
   - Drag & drop fully functional
   - Files persist in queue after execution
   - VS Code-style collapsible activity log
   - Log auto-opens on execution

## 📋 Features

- ✅ **Animated Wolf Companion** - Interactive mascot with moods and behaviors
- ✅ **Smart Status Monitoring** - Know when both internet and API are ready
- ✅ **Drag & Drop** - Easy file/folder loading
- ✅ **Multi-language Support** - Python, JavaScript, TypeScript, Java, C++, Go, Rust, and more
- ✅ **Real-time Analysis** - Instant syntax and logic error detection
- ✅ **Review before saving** - Fixes are shown side by side; apply all changes, only the ones you tick, or reject them. Nothing is written until you click Apply
- ✅ **Backups & undo** - Every file is backed up before a fix is written; "Revert last fix" restores it
- ✅ **Large files** - Files over ~12,000 characters are analyzed in parts (split at function/class boundaries), never truncated
- ✅ **Click an issue** - Shows the surrounding code with the line highlighted
- ✅ **Ask follow-up questions** - "Why is this a bug?", "Explain this fix", per file
- ✅ **Choose what to check** - Bugs, Security, Performance, Style
- ✅ **Parallel analysis** - 1–5 files at once, with automatic retry and backoff on rate limits
- ✅ **Git aware** - Load only files with uncommitted changes; commit applied fixes to a separate `wolf-ai/fixes-…` branch
- ✅ **Skips unchanged files** - Reuses the last result when a file's content hasn't changed
- ✅ **Settings panel** - API key, model, temperature, parallelism, and an "analyze only, never write" mode
- ✅ **Export Reports** - Save analysis results as HTML
- ✅ **Persistent Queue** - Files stay after analysis
- ✅ **Session Management** - New chat option for fresh starts

## 🔑 API Key

Open **Settings** (⚙ in the title bar) and paste your Groq API key (from console.groq.com).
It's saved to your user profile (`%APPDATA%\WolfAI\settings.json` on Windows, `~/.config/WolfAI` elsewhere), never to the project folder.

Alternatives: set the `GROQ_API_KEY` environment variable, or put a `wolf_key.json` (see `wolf_key.example.json`) next to the app.
`wolf_key.json` is git-ignored and is **not** bundled into the .exe.

Backups and the analysis cache live in the same app-data folder.

## 🛠️ Supported Languages

- Python (.py)
- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)
- Java (.java)
- C/C++ (.c, .cpp)
- Go (.go)
- Rust (.rs)
- PHP, Ruby, Swift, Kotlin

## 🧑‍💻 Development

```bash
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

python main.py          # run from source
ruff check .            # lint
python -m pytest        # tests (the UI smoke test uses headless Chrome/Edge if installed)
```

Build the Windows app locally (needs the WiX v5 tool for the MSI: `dotnet tool install --global wix --version 5.0.2`):

```powershell
.\scripts\build.ps1            # exe + zip + msi in dist\
.\scripts\build.ps1 -SkipMsi   # without the installer
```

### Releasing

1. Update `backend/version.py` and add a section to `CHANGELOG.md`.
2. Push to `main` and wait for CI to pass. CI also builds the exe and MSI.
3. Tag and push: `git tag -a v2.0.1 -m "Wolf AI 2.0.1"` then `git push origin v2.0.1`.
   The Release workflow builds the installer and publishes the GitHub release.

## 📧 Support

For issues:
1. Check Activity Log for detailed errors
2. Verify API key configuration
3. Check internet connection
4. If the app doesn't start, see the log at `%APPDATA%\WolfAI\wolfai.log`

---

**Made with 🐺 and ❤️ by Wolf Team**
*The wolf is watching... and ready to debug!*
