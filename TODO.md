# Wolf AI – To-Do

## Bug fixes
- [x] Large files truncated at 12,000 chars and the cut-down "fix" saved over the original
- [x] "Auto Detect" sends the literal word `auto` as the language
- [x] "auto-saved" log message always shown, even when nothing changed
- [x] File picker filter doesn't match the supported extensions
- [x] `wolf_key.json` tracked in git and bundled into the .exe

## Features
- [x] Review fixes before saving (side-by-side diff, accept/reject per change or per file)
- [x] Backups before every write + "Revert last fix" button
- [x] Split large files into chunks and merge the results
- [x] Settings panel (API key, model picker, temperature, analyze-only mode)
- [x] Click an issue to see the surrounding code with the line highlighted
- [x] Ask follow-up questions about a file's results
- [x] Choose what to check (Bugs / Security / Performance / Style)
- [x] Analyze files in parallel with retry + backoff on rate limits
- [x] Git awareness: load only changed files, commit accepted fixes to a separate branch
- [x] Skip files whose content hash hasn't changed since the last run

## Release 2.0.0
- [x] Security and startup review (bridge internals hidden from JS, startup log + error dialog, working drag & drop)
- [x] Tests: backend, UI contract, headless-browser UI smoke test
- [x] GitHub Actions: CI (lint, tests, Windows build) and tag-triggered release
- [x] Windows packaging: portable exe, zip, MSI installer (scripts/build.ps1, packaging/WolfAI.wxs)

## Later (not started)
- [ ] Results dashboard (severity totals, top files, issue-type chart)
- [ ] Run history
- [ ] Markdown / JSON / SARIF export
- [ ] Command-line mode for CI
- [ ] Offline mode via Ollama
- [ ] Mascot reacts to results
