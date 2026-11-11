#!/usr/bin/env bash
# Builds Wolf AI for Linux x86_64:
#   dist/WolfAI-<ver>-amd64.AppImage
#   dist/WolfAI-<ver>-amd64.deb     (Debian/Ubuntu)
#   dist/WolfAI-<ver>-x86_64.rpm    (Fedora/RHEL/openSUSE)
#
# Needs Python 3.12 with requirements.txt + requirements-linux.txt + requirements-dev.txt,
# plus fpm (gem install fpm), rpm, and the Qt runtime libraries (see .github/workflows/build.yml).
# Build on the oldest distro you want to support (CI uses Ubuntu 22.04).
# Check the result with scripts/check_linux.sh.
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-$(python -c 'from backend.version import __version__; print(__version__)')}"
echo "Building Wolf AI ${VERSION} for Linux x86_64"

rm -rf dist build/WolfAI build/AppDir build/pkgroot
python -m PyInstaller --noconfirm --clean --windowed \
  --name WolfAI \
  --add-data "Web:Web" \
  --exclude-module tkinter \
  main.py
[ -x dist/WolfAI/WolfAI ] || { echo "dist/WolfAI/WolfAI was not created"; exit 1; }

# ---------- .deb and .rpm: /opt/wolf-ai + /usr/bin/wolf-ai + menu entry ----------
ROOT=build/pkgroot
mkdir -p "$ROOT/opt" "$ROOT/usr/bin" "$ROOT/usr/share/applications" "$ROOT/usr/share/icons/hicolor/256x256/apps"
cp -a dist/WolfAI "$ROOT/opt/wolf-ai"
ln -s /opt/wolf-ai/WolfAI "$ROOT/usr/bin/wolf-ai"
cp packaging/linux/wolf-ai.desktop "$ROOT/usr/share/applications/wolf-ai.desktop"
cp packaging/icons/wolfai-256.png "$ROOT/usr/share/icons/hicolor/256x256/apps/wolf-ai.png"

FPM_COMMON=(
  -s dir -C "$ROOT" -n wolf-ai -v "$VERSION" --iteration 1
  --maintainer "Dax Patel <pateldax23056@gmail.com>"
  --vendor "Dax Patel"
  --url "https://github.com/daxpatel235/WOLF-AI"
  --description "Wolf AI Code Debugger - AI-powered code debugger with fix review, undo and git integration"
  --category devel
)

# Runtime libraries for the bundled Qt WebEngine (Qt itself is inside /opt/wolf-ai).
DEB_DEPS=(libegl1 libgl1 libgbm1 libdrm2 libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4
  libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0
  libxcb-xkb1 libxshmfence1 libnss3 libxcomposite1 libxdamage1 libxrandr2 libxtst6 libxkbfile1
  libfontconfig1 libfreetype6 libdbus-1-3 libgssapi-krb5-2 "libglib2.0-0 | libglib2.0-0t64"
  "libasound2 | libasound2t64")
RPM_DEPS=(mesa-libEGL mesa-libGL mesa-libgbm libdrm libxkbcommon libxkbcommon-x11 xcb-util-cursor
  xcb-util-wm xcb-util-image xcb-util-keysyms xcb-util-renderutil libxshmfence nss libXcomposite
  libXdamage libXrandr libXtst libxkbfile fontconfig freetype dbus-libs krb5-libs glib2 alsa-lib)

deb_args=(); for d in "${DEB_DEPS[@]}"; do deb_args+=(-d "$d"); done
rpm_args=(); for d in "${RPM_DEPS[@]}"; do rpm_args+=(-d "$d"); done

fpm "${FPM_COMMON[@]}" -t deb -a amd64 "${deb_args[@]}" -p "dist/WolfAI-${VERSION}-amd64.deb" .
fpm "${FPM_COMMON[@]}" -t rpm -a x86_64 "${rpm_args[@]}" --rpm-os linux -p "dist/WolfAI-${VERSION}-x86_64.rpm" .

# ---------- AppImage ----------
APPDIR=build/AppDir
mkdir -p "$APPDIR/usr/lib"
cp -a dist/WolfAI "$APPDIR/usr/lib/wolf-ai"
cp packaging/linux/wolf-ai.desktop "$APPDIR/wolf-ai.desktop"
cp packaging/icons/wolfai-256.png "$APPDIR/wolf-ai.png"
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/lib/wolf-ai/WolfAI" "$@"
EOF
chmod +x "$APPDIR/AppRun"

TOOL=build/appimagetool-x86_64.AppImage
if [ ! -x "$TOOL" ]; then
  curl -fsSL -o "$TOOL" https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi
# Run appimagetool without FUSE (not available in CI containers).
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" --no-appstream "$APPDIR" "dist/WolfAI-${VERSION}-amd64.AppImage"

ls -lh dist
