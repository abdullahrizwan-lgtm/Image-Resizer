from __future__ import annotations

import html
import os
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class ComparisonPair:
    """Paths to one original file and its resized output (both must exist)."""

    label: str  # display name, e.g. audit path with forward slashes
    original_abs: str
    resized_abs: str


def _img_src(html_path: str, image_abs: str) -> str:
    """Relative URL from the HTML file when possible; else file:// (different drives)."""
    base = os.path.dirname(os.path.abspath(html_path))
    try:
        rel = os.path.relpath(os.path.abspath(image_abs), start=base)
    except ValueError:
        return Path(image_abs).resolve().as_uri()
    rel = rel.replace(os.sep, "/")
    return urllib.parse.quote(rel, safe="/")


def write_comparison_html(
    html_output_path: str,
    *,
    input_folder: str,
    output_folder: str,
    pairs: Iterable[ComparisonPair],
) -> None:
    """Write a self-contained comparison page using relative image URLs."""
    rows: List[ComparisonPair] = list(pairs)
    esc_in = html.escape(input_folder)
    esc_out = html.escape(output_folder)

    if rows:
        blocks = []
        for p in rows:
            o = _img_src(html_output_path, p.original_abs)
            r = _img_src(html_output_path, p.resized_abs)
            cap = html.escape(p.label)
            blocks.append(
                f'<article class="pair"><h2 class="fn">{cap}</h2>'
                f'<div class="grid">'
                f'<figure><figcaption>Original</figcaption>'
                f'<img src="{o}" alt="Original: {cap}" loading="lazy"></figure>'
                f'<figure><figcaption>Resized</figcaption>'
                f'<img src="{r}" alt="Resized: {cap}" loading="lazy"></figure>'
                f"</div></article>"
            )
        body_main = "\n".join(blocks)
    else:
        body_main = '<p class="empty">No images were resized successfully, so there is nothing to compare.</p>'

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Original vs Resized</title>
  <style>
    :root {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
    body {{ margin: 0 auto; max-width: 1200px; padding: 1.25rem; background: #f4f4f5; color: #18181b; }}
    h1 {{ font-size: 1.35rem; margin: 0 0 0.5rem; }}
    .meta {{ font-size: 0.85rem; color: #52525b; margin: 0 0 1.25rem; word-break: break-all; }}
    .note {{ font-size: 0.8rem; color: #71717a; margin-bottom: 1.5rem; padding: 0.75rem; background: #fff; border-radius: 8px; border: 1px solid #e4e4e7; }}
    .pair {{ background: #fff; border-radius: 10px; padding: 1rem 1rem 1.25rem; margin-bottom: 1.25rem; border: 1px solid #e4e4e7; box-shadow: 0 1px 2px rgb(0 0 0 / 0.04); }}
    .fn {{ font-size: 0.95rem; font-weight: 600; margin: 0 0 0.75rem; word-break: break-all; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; align-items: start; }}
    @media (max-width: 720px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    figure {{ margin: 0; }}
    figcaption {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; color: #71717a; margin-bottom: 0.35rem; }}
    img {{ width: 100%; height: auto; max-height: 70vh; object-fit: contain; background: #fafafa; border-radius: 6px; vertical-align: middle; }}
    .empty {{ padding: 1rem; background: #fff; border-radius: 8px; border: 1px solid #e4e4e7; }}
  </style>
</head>
<body>
  <h1>Original vs Resized</h1>
  <p class="meta"><strong>Input</strong> {esc_in}<br><strong>Output</strong> {esc_out}</p>
  <p class="note">Double-click this HTML file to open it. Images load from your disk via relative paths. If previews are blank, try Chrome or Firefox.</p>
{body_main}
</body>
</html>
"""
    out_dir = os.path.dirname(os.path.abspath(html_output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(html_output_path, "w", encoding="utf-8") as f:
        f.write(doc)


def write_fallback_comparison_html(
    html_output_path: str,
    *,
    input_folder: str,
    output_folder: str,
    error_message: str,
) -> None:
    """Minimal valid HTML if the full comparison page cannot be built."""
    esc = html.escape
    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Comparison report</title></head>
<body>
  <h1>Comparison report</h1>
  <p><strong>Input</strong> {esc(input_folder)}</p>
  <p><strong>Output</strong> {esc(output_folder)}</p>
  <p style="color:#b91c1c;">The detailed comparison view could not be generated:</p>
  <pre style="white-space:pre-wrap;background:#f4f4f5;padding:1rem;">{esc(error_message)}</pre>
</body></html>
"""
    out_dir = os.path.dirname(os.path.abspath(html_output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(html_output_path, "w", encoding="utf-8") as f:
        f.write(doc)


def ensure_comparison_report(
    html_output_path: str,
    *,
    input_folder: str,
    output_folder: str,
    pairs: Iterable[ComparisonPair],
) -> None:
    """Always leaves a readable HTML file at html_output_path (never raises)."""
    try:
        write_comparison_html(
            html_output_path,
            input_folder=input_folder,
            output_folder=output_folder,
            pairs=pairs,
        )
    except Exception as e:
        try:
            write_fallback_comparison_html(
                html_output_path,
                input_folder=input_folder,
                output_folder=output_folder,
                error_message=str(e),
            )
        except Exception as e2:
            # Last resort: plain text so something exists beside the audit CSV.
            out_dir = os.path.dirname(os.path.abspath(html_output_path))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(html_output_path, "w", encoding="utf-8") as f:
                f.write(
                    "<!DOCTYPE html><html><head><meta charset=utf-8><title>Error</title></head>"
                    f"<body><pre>{html.escape(repr(e))}\n{html.escape(repr(e2))}</pre></body></html>"
                )
