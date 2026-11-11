#!/usr/bin/env bash
# Fails if any bundled Qt binary of an installed Wolf AI needs a system library that isn't
# installed, i.e. a dependency missing from the .deb/.rpm. Run inside a clean distro container
# after installing the package. Usage: linux_ldd_check.sh [/opt/wolf-ai]
set -euo pipefail

APP="${1:-/opt/wolf-ai}"
INTERNAL="$APP/_internal"
QTCORE="$(find "$INTERNAL" -name 'libQt6Core.so.6' -print -quit)"
[ -n "$QTCORE" ] || { echo "Qt libraries not found under $INTERNAL"; exit 1; }

# Same search path the app uses at runtime (PyInstaller adds its bundle dir).
export LD_LIBRARY_PATH="$INTERNAL:$(dirname "$QTCORE")"

# What the app actually loads: the Qt modules pywebview's Qt backend imports (and the Qt
# libraries behind them), the X11/Wayland/offscreen platform plugins, and the WebEngine helper.
# Optional plugins (e.g. the GTK theme plugin) may need more and are left out on purpose.
MODULES='Core|Gui|Widgets|Network|DBus|WebChannel|WebEngineCore|WebEngineWidgets|OpenGL|OpenGLWidgets|PrintSupport|Qml|QmlModels|QmlMeta|QmlWorkerScript|Quick|QuickWidgets|Positioning|XcbQpa|WaylandClient'
PATTERN="/(libQt6(${MODULES})\.so\.6|Qt(${MODULES})\.abi3\.so|libqxcb\.so|libqwayland-generic\.so|libqoffscreen\.so|QtWebEngineProcess)$"

checked=0
missing=0
while IFS= read -r -d '' f; do
  [[ "$f" =~ $PATTERN ]] || continue
  checked=$((checked + 1))
  out="$(ldd "$f" 2>&1 || true)"
  if grep -q "not found" <<<"$out"; then
    echo "MISSING for ${f#"$INTERNAL"/}:"
    grep "not found" <<<"$out" | sed 's/^/    /'
    missing=1
  fi
done < <(find "$INTERNAL" \( -type f -o -type l \) -print0)

echo "ldd checked $checked Qt binaries"
[ "$checked" -ge 10 ] || { echo "Expected at least 10 Qt binaries, found $checked: bundle layout changed?"; exit 1; }
if [ "$missing" -ne 0 ]; then
  echo "Some system libraries are missing: add them to packaging/linux/qt-sonames.txt and deb-depends.txt"
  exit 1
fi
echo "All Qt binaries resolve their system libraries."
