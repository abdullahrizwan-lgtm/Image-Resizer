#!/bin/zsh
set -euo pipefail

# Creates a zip you can send to anyone on Apple Silicon (arm64) macOS.
# Run from Terminal inside program/: ./ship_mac_app.sh

PROG_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$PROG_DIR/.." && pwd)"
VERSION="1.4"
ZIP_NAME="Image-Resize-Tool-v${VERSION}-macOS-arm64.zip"
ZIP_PATH="${ROOT}/${ZIP_NAME}"
APP="${PROG_DIR}/Image Resize Tool.app"

cd "$ROOT"

if [[ ! -d "$APP" ]]; then
  echo "No app bundle found. Building…"
  (cd "$PROG_DIR" && ./build_mac_app_qt.sh)
fi

rm -f "$ZIP_PATH"
# -y: store symlinks (helps .app bundles). Exclude Python cruft.
zip -ry "$ZIP_PATH" README.md run_app build_app program \
  -x "**/.DS_Store" \
  -x "**/__pycache__/*" \
  -x "**/*.pyc" \
  -x "**/build/*" \
  -x "**/dist/*"

echo
echo "Ship archive ready:"
echo "  ${ZIP_PATH}"
ls -lh "$ZIP_PATH"
