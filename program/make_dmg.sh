#!/bin/zsh
set -euo pipefail

# Create a DMG installer for Image Resize Tool.
# Run from Terminal inside program/: ./make_dmg.sh

PROG_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$PROG_DIR/.." && pwd)"
VERSION="1.4"
APP_NAME="Image Resize Tool.app"
APP_PATH="$PROG_DIR/$APP_NAME"
DMG_NAME="Image-Resize-Tool-v${VERSION}-macOS-arm64.dmg"
DMG_PATH="$ROOT/$DMG_NAME"

if [[ ! -d "$APP_PATH" ]]; then
  echo "App bundle not found, building first..."
  "$PROG_DIR/build_mac_app_qt.sh"
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "Build failed: $APP_PATH not found."
  exit 1
fi

STAGE_DIR="$PROG_DIR/.dmg_stage"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

cp -R "$APP_PATH" "$STAGE_DIR/"
ln -s /Applications "$STAGE_DIR/Applications"

rm -f "$DMG_PATH"
hdiutil create \
  -volname "Image Resize Tool Installer" \
  -srcfolder "$STAGE_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

rm -rf "$STAGE_DIR"

echo
echo "DMG ready:"
echo "  $DMG_PATH"
ls -lh "$DMG_PATH"
