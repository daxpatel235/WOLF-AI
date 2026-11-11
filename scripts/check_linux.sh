#!/usr/bin/env bash
# Checks the Linux packages:
#   AppImage: runs its self-test
#   .deb:     metadata + contents, installs with apt (resolving dependencies), self-tests, removes
#   .rpm:     metadata + contents, installs with dnf in a Fedora container, self-tests there
# Needs sudo, and docker for the .rpm check.
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-$(python -c 'from backend.version import __version__; print(__version__)')}"
APPIMAGE="dist/WolfAI-${VERSION}-amd64.AppImage"
DEB="dist/WolfAI-${VERSION}-amd64.deb"
RPM="dist/WolfAI-${VERSION}-x86_64.rpm"
fail() { echo "CHECK FAILED: $*" >&2; exit 1; }
step() { echo; echo "=== $*"; }

# No display in CI: Qt only needs to load, not draw.
export QT_QPA_PLATFORM=offscreen

step "AppImage"
[ -f "$APPIMAGE" ] || fail "$APPIMAGE not found"
chmod +x "$APPIMAGE"
file "$APPIMAGE" | grep -q "ELF 64-bit" || fail "AppImage is not an x86_64 executable"
APPIMAGE_EXTRACT_AND_RUN=1 "./$APPIMAGE" --self-test /tmp/wolfai-appimage.txt \
  || { cat /tmp/wolfai-appimage.txt 2>/dev/null; fail "AppImage self-test failed"; }
cat /tmp/wolfai-appimage.txt

step ".deb"
[ -f "$DEB" ] || fail "$DEB not found"
dpkg-deb --info "$DEB"
[ "$(dpkg-deb --field "$DEB" Version)" = "${VERSION}-1" ] || fail "deb version is not ${VERSION}-1"
[ "$(dpkg-deb --field "$DEB" Architecture)" = "amd64" ] || fail "deb architecture is not amd64"
CONTENTS="$(dpkg-deb --contents "$DEB")"
for f in ./opt/wolf-ai/WolfAI ./usr/bin/wolf-ai ./usr/share/applications/wolf-ai.desktop \
         ./usr/share/icons/hicolor/256x256/apps/wolf-ai.png; do
  grep -q " $f" <<<"$CONTENTS" || fail "deb is missing $f"
done
desktop-file-validate packaging/linux/wolf-ai.desktop
sudo apt-get install -y "./$DEB"
wolf-ai --self-test /tmp/wolfai-deb.txt || { cat /tmp/wolfai-deb.txt 2>/dev/null; fail ".deb self-test failed"; }
cat /tmp/wolfai-deb.txt
sudo apt-get remove -y wolf-ai
[ ! -e /opt/wolf-ai/WolfAI ] || fail "apt remove left /opt/wolf-ai behind"

step ".rpm"
[ -f "$RPM" ] || fail "$RPM not found"
rpm -qpi "$RPM"
[ "$(rpm -qp --queryformat '%{VERSION}' "$RPM")" = "$VERSION" ] || fail "rpm version is not $VERSION"
[ "$(rpm -qp --queryformat '%{ARCH}' "$RPM")" = "x86_64" ] || fail "rpm architecture is not x86_64"
rpm -qpl "$RPM" | grep -qx /opt/wolf-ai/WolfAI || fail "rpm is missing /opt/wolf-ai/WolfAI"
docker run --rm -e QT_QPA_PLATFORM=offscreen -v "$PWD/dist:/dist:ro" fedora:latest bash -euo pipefail -c "
  dnf install -y -q /dist/$(basename "$RPM")
  wolf-ai --self-test /tmp/report.txt || { cat /tmp/report.txt; exit 1; }
  cat /tmp/report.txt
  dnf remove -y -q wolf-ai
  test ! -e /opt/wolf-ai/WolfAI
" || fail ".rpm install/self-test in Fedora failed"

echo
echo "All Linux checks passed."
