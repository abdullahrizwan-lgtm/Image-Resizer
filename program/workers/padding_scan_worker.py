from __future__ import annotations

import os
from dataclasses import dataclass

from PIL import Image, ImageOps
from PyQt6.QtCore import QObject, pyqtSignal


_RESIZED_DIR_SUFFIX = "-Resized-v1.4"
_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff")


@dataclass(frozen=True)
class PaddingScanResult:
    total: int
    needs_padding: int


def _collect_paths(root: str, *, recursive: bool) -> list[str]:
    root = os.path.abspath(root)
    paths: list[str] = []

    if not recursive:
        for name in os.listdir(root):
            if name.lower().endswith(_EXTENSIONS):
                paths.append(os.path.join(root, name))
        paths.sort(key=lambda p: os.path.basename(p).lower())
        return paths

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if not d.startswith(".") and not d.endswith(_RESIZED_DIR_SUFFIX)
        ]
        for name in filenames:
            if name.lower().endswith(_EXTENSIONS):
                paths.append(os.path.join(dirpath, name))
    paths.sort(key=lambda p: os.path.relpath(p, root).lower())
    return paths


class PaddingScanWorker(QObject):
    finished = pyqtSignal(object)  # PaddingScanResult
    failed = pyqtSignal(str)

    def __init__(self, input_path: str, *, recursive: bool, target_w: int, target_h: int):
        super().__init__()
        self._input_path = input_path
        self._recursive = recursive
        self._tw = int(target_w)
        self._th = int(target_h)

    def run(self) -> None:
        try:
            root = self._input_path.strip()
            if not root or not os.path.isdir(root):
                self.finished.emit(PaddingScanResult(total=0, needs_padding=0))
                return

            paths = _collect_paths(root, recursive=self._recursive)
            total = len(paths)
            if total == 0:
                self.finished.emit(PaddingScanResult(total=0, needs_padding=0))
                return

            need = 0
            for p in paths:
                try:
                    with Image.open(p) as raw:
                        img = ImageOps.exif_transpose(raw)
                        w, h = img.size
                    if w * self._th != h * self._tw:
                        need += 1
                except Exception:
                    # If we can't read it, ignore it for scan purposes.
                    continue

            self.finished.emit(PaddingScanResult(total=total, needs_padding=need))
        except Exception as e:
            self.failed.emit(str(e))

