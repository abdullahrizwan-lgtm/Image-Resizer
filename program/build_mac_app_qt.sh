#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$SCRIPT_DIR"

"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r requirements.txt pyinstaller

rm -rf build dist "Image Resize Tool.app"
"$PYTHON_BIN" -m PyInstaller --clean --noconfirm ultra_resizer_qt.spec

APP_SRC="$SCRIPT_DIR/dist/Image Resize Tool.app"
APP_DST="$SCRIPT_DIR/Image Resize Tool.app"
if [[ -d "$APP_SRC" ]]; then
  mv "$APP_SRC" "$APP_DST"
  rm -rf "$SCRIPT_DIR/dist" "$SCRIPT_DIR/build"
fi

echo
echo "Built Qt app bundle:"
echo "  $APP_DST"
echo "Double-click ../Run Image Resize Tool.command from the folder above program/."
