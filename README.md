# Image Resize Tool (v1.4)

Batch-resize images to a max width × height (aspect ratio preserved). Nested folders are supported by default; output mirrors your folder tree with one **Audit_Report.csv** at the output root.

## Run (Mac)

1. **Double-click `Run Image Resize Tool.command`** in this folder (next to this README).
2. That opens **`program/Image Resize Tool.app`** if a build is included. If the bundle is missing, it falls back to running from Python in `program/` (installs dependencies first).

Everything except this README and that launcher lives in **`program/`** (source, icons, build script, optional `run/` dev launcher).

## Ship to someone else (Mac)

From this folder in Terminal:

```bash
cd program
./ship_mac_app.sh
```

That creates **`Image-Resize-Tool-v1.4-macOS-arm64.zip`** next to this README. Send that zip; they unzip, read **README.md**, and double-click **`Run Image Resize Tool.command`**.

## Create a DMG installer (Mac)

From this folder in Terminal:

```bash
cd program
./make_dmg.sh
```

This creates **`Image-Resize-Tool-v1.4-macOS-arm64.dmg`** in the project root.

### Install from DMG

1. Double-click the `.dmg` file to mount it.
2. Drag **`Image Resize Tool.app`** into **Applications**.
3. Launch from Applications.

If macOS blocks first launch (unsigned app), use:
- Right-click app -> **Open**
- Click **Open** in the warning dialog.

Apple Silicon (**M1/M2/M3…**) only; built with arm64. For Intel Macs you’d need to rebuild on an Intel machine or adjust PyInstaller’s `target_arch`.

## Rebuild the `.app`

Terminal:

```bash
cd program
./build_mac_app_qt.sh
```

The bundle is written to **`program/Image Resize Tool.app`**.

## Optional: classic Tk UI

```bash
cd program
python3 ultra_resizer_v1_4.py
```
