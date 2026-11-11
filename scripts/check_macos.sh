#!/usr/bin/env bash
# Checks the macOS .dmg: mounts it, verifies the app bundle (layout, version, architecture,
# signature) and runs the app's self-test from the mounted image.
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-$(python -c 'from backend.version import __version__; print(__version__)')}"
case "$(uname -m)" in
  arm64)  LABEL=aarch64; ARCH=arm64 ;;
  x86_64) LABEL=x64; ARCH=x86_64 ;;
esac
DMG="dist/WolfAI-${VERSION}-${LABEL}.dmg"
fail() { echo "CHECK FAILED: $*" >&2; exit 1; }

[ -f "$DMG" ] || fail "$DMG not found"
hdiutil verify "$DMG"

MNT="$(mktemp -d)"
hdiutil attach "$DMG" -nobrowse -readonly -mountpoint "$MNT" >/dev/null
trap 'hdiutil detach "$MNT" -quiet || true' EXIT

APP="$MNT/WolfAI.app"
BIN="$APP/Contents/MacOS/WolfAI"
[ -d "$APP" ] || fail "WolfAI.app missing from the dmg"
[ -L "$MNT/Applications" ] || fail "Applications shortcut missing from the dmg"
[ -x "$BIN" ] || fail "app executable missing"

PLIST="$APP/Contents/Info.plist"
[ "$(plutil -extract CFBundleShortVersionString raw "$PLIST")" = "$VERSION" ] || fail "bundle version is not $VERSION"
[ "$(plutil -extract CFBundleIdentifier raw "$PLIST")" = "com.daxpatel.wolfai" ] || fail "wrong bundle identifier"

ARCHS="$(lipo -archs "$BIN")"
echo "executable architectures: $ARCHS"
[[ " $ARCHS " == *" $ARCH "* ]] || fail "executable is not built for $ARCH"

codesign --verify --deep --strict --verbose=2 "$APP" || fail "code signature is invalid"

REPORT="$(mktemp)"
"$BIN" --self-test "$REPORT" || { cat "$REPORT"; fail "self-test failed"; }
cat "$REPORT"

echo "All macOS checks passed for $DMG"
