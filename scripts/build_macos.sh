#!/usr/bin/env bash
# Builds Wolf AI for macOS on the current Mac's architecture:
#   dist/WolfAI.app
#   dist/WolfAI-<ver>-aarch64.dmg   (Apple silicon)  or  dist/WolfAI-<ver>-x64.dmg  (Intel)
#
# Needs Python 3.12 with requirements.txt + requirements-dev.txt.
# The app is ad-hoc signed (not notarized): on first launch users right-click > Open,
# or allow it in System Settings > Privacy & Security.
# Check the result with scripts/check_macos.sh.
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-$(python -c 'from backend.version import __version__; print(__version__)')}"
case "$(uname -m)" in
  arm64)  LABEL=aarch64 ;;
  x86_64) LABEL=x64 ;;
  *) echo "unsupported architecture $(uname -m)"; exit 1 ;;
esac
DMG="dist/WolfAI-${VERSION}-${LABEL}.dmg"
echo "Building Wolf AI ${VERSION} for macOS ${LABEL}"

rm -rf dist build/WolfAI
python -m PyInstaller --noconfirm --clean --windowed \
  --name WolfAI \
  --icon packaging/icons/wolfai.icns \
  --osx-bundle-identifier com.daxpatel.wolfai \
  --add-data "Web:Web" \
  --exclude-module tkinter \
  main.py

APP=dist/WolfAI.app
PLIST="$APP/Contents/Info.plist"
plutil -replace CFBundleName -string "Wolf AI" "$PLIST"
plutil -replace CFBundleDisplayName -string "Wolf AI" "$PLIST"
plutil -replace CFBundleShortVersionString -string "$VERSION" "$PLIST"
plutil -replace CFBundleVersion -string "$VERSION" "$PLIST"
plutil -replace NSHumanReadableCopyright -string "Copyright © Dax Patel" "$PLIST"
plutil -replace NSHighResolutionCapable -bool true "$PLIST"
plutil -replace LSMinimumSystemVersion -string "11.0" "$PLIST"

# Editing Info.plist invalidates PyInstaller's signature; re-sign ad hoc (required on Apple silicon).
codesign --force --deep --sign - "$APP"

echo "Creating ${DMG}"
STAGE="$(mktemp -d)"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname "Wolf AI ${VERSION}" -srcfolder "$STAGE" -ov -format UDZO "$DMG"
rm -rf "$STAGE"

ls -lh dist
