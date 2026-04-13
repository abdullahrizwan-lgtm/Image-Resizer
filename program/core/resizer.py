from __future__ import annotations

import os
from typing import Callable, Optional, Sequence, Tuple

import pandas as pd
from PIL import Image, ImageFilter, ImageOps

from .comparison_html import ComparisonPair, ensure_comparison_report
from .types import NoImagesError, PadFillMode, ResizeConfig, ResizeMode, ResizeResult


ProgressCallback = Callable[[int, int, str], None]
StatusCallback = Callable[[str], None]

ImageJob = Tuple[str, str]  # (absolute_path, relative_path_for_audit_and_log)

# Do not descend into prior output trees nested under the input folder.
_RESIZED_DIR_SUFFIX = "-Resized-v1.4"
_V14_OUTPUT_SUFFIX = "-Resized-v1.4"


def _output_folder_slug(cfg: ResizeConfig) -> str:
    if cfg.resize_mode == "fit":
        return "resized_fit"
    if cfg.resize_mode == "exact_stretch":
        return "resized_stretch"
    if cfg.resize_mode == "exact_pad":
        # letterbox with fill mode detail
        fill = cfg.pad_fill_mode
        if fill == "white":
            return "resized_letterbox_white"
        if fill == "black":
            return "resized_letterbox_black"
        if fill == "extend":
            return "resized_letterbox_extend"
        if fill == "blur":
            return "resized_letterbox_blur"
        if fill == "auto":
            return "resized_letterbox_auto"
        return f"resized_letterbox_{fill}"
    return "resized"


def _increment_if_exists(path: str) -> str:
    if not os.path.exists(path):
        return path
    base = path
    i = 2
    while True:
        cand = f"{base}-{i}"
        if not os.path.exists(cand):
            return cand
        i += 1


def _make_output_path(input_path: str, cfg: ResizeConfig) -> str:
    input_path = os.path.abspath(input_path.rstrip(os.sep))
    folder_name = os.path.basename(input_path)
    parent_dir = os.path.dirname(input_path)
    out_name = f"{folder_name}_{_output_folder_slug(cfg)}"
    return _increment_if_exists(os.path.join(parent_dir, out_name))


def _collect_image_jobs(
    input_path: str, extensions: Sequence[str], *, recursive: bool
) -> list[ImageJob]:
    """Return sorted (abs_path, path relative to input root, using os.sep)."""
    root = os.path.abspath(input_path)
    jobs: list[ImageJob] = []

    if not recursive:
        for name in os.listdir(root):
            if name.lower().endswith(tuple(extensions)):
                jobs.append((os.path.join(root, name), name))
        jobs.sort(key=lambda j: j[1].lower())
        return jobs

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".") and not d.endswith(_RESIZED_DIR_SUFFIX)
        ]
        for name in filenames:
            if not name.lower().endswith(tuple(extensions)):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            jobs.append((full, rel))
    jobs.sort(key=lambda j: j[1].lower())
    return jobs


def _audit_rel_path(rel: str) -> str:
    return rel.replace("\\", "/")


def _resize_to_dimensions(
    img: Image.Image,
    width: int,
    height: int,
    mode: ResizeMode,
    pad_fill_mode: PadFillMode,
) -> Image.Image:
    if mode == "fit":
        return ImageOps.contain(img, (width, height), Image.Resampling.LANCZOS)
    if mode == "exact_stretch":
        return img.resize((width, height), Image.Resampling.LANCZOS)
    if mode == "exact_pad":
        # Foreground always preserves aspect.
        fg = ImageOps.contain(img, (width, height), Image.Resampling.LANCZOS)

        if pad_fill_mode in ("white", "black", "auto"):
            if pad_fill_mode == "white":
                fill_color = (255, 255, 255)
            elif pad_fill_mode == "black":
                fill_color = (0, 0, 0)
            else:
                # Auto solid: sample a few edge pixels from the foreground.
                sample = fg.convert("RGB")
                w, h = sample.size
                pts = [
                    (0, 0),
                    (w - 1, 0),
                    (0, h - 1),
                    (w - 1, h - 1),
                    (w // 2, 0),
                    (w // 2, h - 1),
                    (0, h // 2),
                    (w - 1, h // 2),
                ]
                rs = gs = bs = 0
                for x, y in pts:
                    r, g, b = sample.getpixel((max(0, x), max(0, y)))
                    rs += int(r)
                    gs += int(g)
                    bs += int(b)
                n = max(1, len(pts))
                fill_color = (rs // n, gs // n, bs // n)

            return ImageOps.pad(
                fg,
                (width, height),
                Image.Resampling.LANCZOS,
                color=fill_color,
                centering=(0.5, 0.5),
            )

        if pad_fill_mode == "blur":
            bg = ImageOps.fit(img, (width, height), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=max(8, min(width, height) // 60)))
            out = bg.copy()
            x = (width - fg.size[0]) // 2
            y = (height - fg.size[1]) // 2
            out.paste(fg, (x, y))
            return out

        if pad_fill_mode == "extend":
            # Extend match: fill the padded areas by repeating edge pixels outward.
            fg2 = fg
            tw, th = width, height
            fw, fh = fg2.size
            x0 = (tw - fw) // 2
            y0 = (th - fh) // 2

            canvas = Image.new(fg2.mode, (tw, th))
            canvas.paste(fg2, (x0, y0))

            # Left / right bars
            if x0 > 0:
                left_col = fg2.crop((0, 0, 1, fh)).resize((x0, fh))
                canvas.paste(left_col, (0, y0))
            right_w = tw - (x0 + fw)
            if right_w > 0:
                right_col = fg2.crop((fw - 1, 0, fw, fh)).resize((right_w, fh))
                canvas.paste(right_col, (x0 + fw, y0))

            # Top / bottom bars (fill full width using extended edges)
            if y0 > 0:
                row = fg2.crop((0, 0, fw, 1))
                row_full = Image.new(fg2.mode, (tw, 1))
                row_full.paste(row, (x0, 0))
                if x0 > 0:
                    lpx = row.crop((0, 0, 1, 1)).resize((x0, 1))
                    row_full.paste(lpx, (0, 0))
                if right_w > 0:
                    rpx = row.crop((fw - 1, 0, fw, 1)).resize((right_w, 1))
                    row_full.paste(rpx, (x0 + fw, 0))
                top = row_full.resize((tw, y0))
                canvas.paste(top, (0, 0))
            bottom_h = th - (y0 + fh)
            if bottom_h > 0:
                row = fg2.crop((0, fh - 1, fw, fh))
                row_full = Image.new(fg2.mode, (tw, 1))
                row_full.paste(row, (x0, 0))
                if x0 > 0:
                    lpx = row.crop((0, 0, 1, 1)).resize((x0, 1))
                    row_full.paste(lpx, (0, 0))
                if right_w > 0:
                    rpx = row.crop((fw - 1, 0, fw, 1)).resize((right_w, 1))
                    row_full.paste(rpx, (x0 + fw, 0))
                bottom = row_full.resize((tw, bottom_h))
                canvas.paste(bottom, (0, y0 + fh))

            return canvas

        raise ValueError(f"Unknown pad_fill_mode: {pad_fill_mode}")
    raise ValueError(f"Unknown resize_mode: {mode}")


def process_folder(
    cfg: ResizeConfig,
    *,
    on_progress: Optional[ProgressCallback] = None,
    on_status: Optional[StatusCallback] = None,
) -> ResizeResult:
    input_path = os.path.abspath(cfg.input_path.strip())
    selected_format = cfg.output_format
    width = int(cfg.width)
    height = int(cfg.height)

    if not input_path or not os.path.exists(input_path):
        raise FileNotFoundError("Please select a valid folder.")

    if not os.path.isdir(input_path):
        raise FileNotFoundError("Please select a valid folder.")

    extensions = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")
    jobs = _collect_image_jobs(
        input_path, extensions, recursive=cfg.include_subfolders
    )
    total_files = len(jobs)

    if total_files == 0:
        raise NoImagesError("No supported images were found in this folder.")

    if on_status:
        on_status(f"Starting... Total: {total_files}")

    output_path = _make_output_path(input_path, cfg)

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    audit_data = []
    comparison_pairs: list[ComparisonPair] = []
    processed_count = 0

    for img_full_path, rel_path in jobs:
        filename = os.path.basename(img_full_path)
        new_filename = filename.rsplit(".", 1)[0] + f".{selected_format.lower()}"
        rel_dir = os.path.dirname(rel_path)
        if rel_dir:
            out_dir = os.path.join(output_path, rel_dir)
            os.makedirs(out_dir, exist_ok=True)
            save_full_path = os.path.join(out_dir, new_filename)
        else:
            save_full_path = os.path.join(output_path, new_filename)
        audit_file = _audit_rel_path(rel_path)

        try:
            with Image.open(img_full_path) as raw:
                # Apply camera orientation so width/height match what you see on screen.
                img = ImageOps.exif_transpose(raw)
                resized_img = _resize_to_dimensions(
                    img, width, height, cfg.resize_mode, cfg.pad_fill_mode
                )

                if selected_format == "JPG":
                    if resized_img.mode in ("RGBA", "P"):
                        resized_img = resized_img.convert("RGB")
                    quality = 100
                    resized_img.save(
                        save_full_path, "JPEG", quality=quality, optimize=True, subsampling=0
                    )
                    while os.path.getsize(save_full_path) / 1024 > 1000 and quality > 85:
                        quality -= 1
                        resized_img.save(
                            save_full_path,
                            "JPEG",
                            quality=quality,
                            optimize=True,
                            subsampling=0,
                        )

                elif selected_format == "PNG":
                    resized_img.save(save_full_path, "PNG", compress_level=3)

                elif selected_format == "WebP":
                    quality = 100
                    resized_img.save(save_full_path, "WebP", quality=quality, lossless=False)
                    while os.path.getsize(save_full_path) / 1024 > 1000 and quality > 85:
                        quality -= 1
                        resized_img.save(save_full_path, "WebP", quality=quality)
                else:
                    raise ValueError(f"Unsupported format: {selected_format}")

            processed_count += 1
            if on_progress:
                on_progress(processed_count, total_files, audit_file)
            audit_data.append({"File": audit_file, "Status": "Success"})
            comparison_pairs.append(
                ComparisonPair(
                    label=audit_file,
                    original_abs=img_full_path,
                    resized_abs=save_full_path,
                )
            )
        except Exception as e:
            audit_data.append(
                {"File": audit_file, "Status": "Failed", "Error": str(e)}
            )

    audit_csv_path = os.path.join(output_path, "Audit_Report.csv")
    comparison_html_path = os.path.join(output_path, "Comparison_Report.html")

    try:
        pd.DataFrame(audit_data).to_csv(audit_csv_path, index=False)
    finally:
        ensure_comparison_report(
            comparison_html_path,
            input_folder=input_path,
            output_folder=output_path,
            pairs=comparison_pairs,
        )

    if on_status:
        on_status("COMPLETED!")

    return ResizeResult(
        output_path=output_path,
        audit_csv_path=audit_csv_path,
        comparison_html_path=comparison_html_path,
        total_files=total_files,
        processed_count=processed_count,
    )
