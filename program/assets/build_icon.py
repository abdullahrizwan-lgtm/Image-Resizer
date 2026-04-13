#!/usr/bin/env python3
"""Generate Ultra Resizer app icon (PNG + macOS .icns) using Pillow only."""
from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 1024
OUT_DIR = Path(__file__).resolve().parent


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = ImageDraw.Draw(img)

    # Rounded background with vertical-ish gradient (teal -> deep blue)
    pad = int(size * 0.06)
    r_bg = int(size * 0.22)
    for y in range(size):
        t = y / max(size - 1, 1)
        r = int(_lerp(22, 12, t))
        g = int(_lerp(160, 90, t))
        b = int(_lerp(150, 200, t))
        px.line([(0, y), (size, y)], fill=(r, g, b, 255))

    # Clip to rounded rect (simulate by drawing rounded rect on mask)
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([pad, pad, size - pad, size - pad], radius=r_bg, fill=255)
    bg_only = img.copy()
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(bg_only, (0, 0), mask)

    d = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    frame_w = int(size * 0.42)
    frame_h = int(size * 0.34)
    fx0 = cx - frame_w // 2
    fy0 = cy - frame_h // 2 - int(size * 0.02)
    fx1 = fx0 + frame_w
    fy1 = fy0 + frame_h
    corner_r = int(size * 0.04)

    # Inner "photo" area (slightly lighter)
    inner_pad = int(size * 0.025)
    d.rounded_rectangle(
        [fx0 + inner_pad, fy0 + inner_pad, fx1 - inner_pad, fy1 - inner_pad],
        radius=max(4, corner_r - inner_pad // 2),
        fill=(255, 255, 255, 38),
        outline=(255, 255, 255, 220),
        width=max(2, size // 128),
    )

    # Outer frame stroke
    d.rounded_rectangle(
        [fx0, fy0, fx1, fy1],
        radius=corner_r,
        outline=(255, 255, 255, 245),
        width=max(3, size // 100),
    )

    # Resize arrows (diagonal): from bottom-left toward top-right and opposite
    aw = max(4, size // 80)
    col_arrow = (255, 255, 255, 255)
    col_accent = (46, 204, 113, 255)

    def arrow_line(x0: float, y0: float, x1: float, y1: float, color, width_: int) -> None:
        d.line([(x0, y0), (x1, y1)], fill=color, width=width_, joint="curve")
        # Arrow head
        ang = math.atan2(y1 - y0, x1 - x0)
        ah = size * 0.055
        for da in (2.6, -2.6):
            ax = x1 + ah * math.cos(ang + da)
            ay = y1 + ah * math.sin(ang + da)
            d.line([(x1, y1), (ax, ay)], fill=color, width=width_, joint="curve")

    # Position arrows outside frame corners
    ox = size * 0.08
    oy = size * 0.07
    # Enlarge: bottom-left to top-right
    arrow_line(
        fx0 - ox,
        fy1 + oy * 0.3,
        fx1 + ox * 0.4,
        fy0 - oy * 0.5,
        col_accent,
        aw,
    )
    # Shrink: top-right to bottom-left (lighter)
    arrow_line(
        fx1 + ox * 0.35,
        fy0 - oy * 0.45,
        fx0 - ox * 0.35,
        fy1 + oy * 0.35,
        col_arrow,
        max(2, aw - 1),
    )

    return img


def write_png(path: Path, im: Image.Image) -> None:
    im.save(path, "PNG", compress_level=6)


def build_icns(master: Path, icns_out: Path) -> None:
    iconset = master.parent / "UltraResizer.iconset"
    if iconset.exists():
        import shutil

        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)

    sizes = [
        ("icon_16x16.png", 16),
        ("icon_16x16@2x.png", 32),
        ("icon_32x32.png", 32),
        ("icon_32x32@2x.png", 64),
        ("icon_128x128.png", 128),
        ("icon_128x128@2x.png", 256),
        ("icon_256x256.png", 256),
        ("icon_256x256@2x.png", 512),
        ("icon_512x512.png", 512),
        ("icon_512x512@2x.png", 1024),
    ]
    base = Image.open(master).convert("RGBA")
    for name, dim in sizes:
        resized = base.resize((dim, dim), Image.Resampling.LANCZOS)
        write_png(iconset / name, resized)

    subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(icns_out)],
        check=True,
    )


def main() -> int:
    master_path = OUT_DIR / "ultra_resizer_icon_1024.png"
    icns_path = OUT_DIR / "UltraResizer.icns"

    im = draw_icon(SIZE)
    write_png(master_path, im)
    print(f"Wrote {master_path}")

    if sys.platform == "darwin":
        build_icns(master_path, icns_path)
        print(f"Wrote {icns_path}")
    else:
        print("Skipping .icns (iconutil is macOS-only). PNG is still usable.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
