from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

OutputFormat = Literal["JPG", "PNG", "WebP"]

# fit = max edge fits in box (square stays square). exact_pad = always WxH with bars.
# exact_stretch = always WxH, may distort.
ResizeMode = Literal["fit", "exact_pad", "exact_stretch"]
PadFillMode = Literal["white", "black", "extend", "blur", "auto"]


@dataclass(frozen=True)
class ResizeConfig:
    input_path: str
    width: int
    height: int
    output_format: OutputFormat
    include_subfolders: bool = True
    resize_mode: ResizeMode = "fit"
    pad_fill_mode: PadFillMode = "white"


@dataclass(frozen=True)
class ResizeResult:
    output_path: str
    audit_csv_path: str
    comparison_html_path: str
    total_files: int
    processed_count: int


class NoImagesError(Exception):
    pass
