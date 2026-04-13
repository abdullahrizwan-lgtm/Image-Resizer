app_name = "Image Resize Tool"
bundle_id = "com.local.imageresizetool"


a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[("ui/styles", "ui/styles")],
    hiddenimports=["core.comparison_html", "workers.padding_scan_worker"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    exclude_binaries=True,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)

app = BUNDLE(
    coll,
    name=f"{app_name}.app",
    icon="assets/UltraResizer.icns",
    bundle_identifier=bundle_id,
    info_plist={
        "CFBundleName": app_name,
        "CFBundleDisplayName": app_name,
        "CFBundleIconFile": "UltraResizer",
        "CFBundleShortVersionString": "1.4",
        "CFBundleVersion": "1.4",
        "NSHighResolutionCapable": True,
    },
)
