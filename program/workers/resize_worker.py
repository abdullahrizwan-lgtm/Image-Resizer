from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from core.resizer import process_folder
from core.types import NoImagesError, ResizeConfig, ResizeResult


class ResizeWorker(QObject):
    progress = pyqtSignal(int, int, str)  # processed, total, filename
    status = pyqtSignal(str)
    finished = pyqtSignal(object)  # ResizeResult
    failed = pyqtSignal(str)  # message

    def __init__(self, cfg: ResizeConfig):
        super().__init__()
        self._cfg = cfg

    def run(self) -> None:
        try:
            result = process_folder(
                self._cfg,
                on_progress=lambda p, t, f: self.progress.emit(p, t, f),
                on_status=lambda s: self.status.emit(s),
            )
            self.finished.emit(result)
        except NoImagesError as e:
            self.failed.emit(str(e))
        except FileNotFoundError as e:
            self.failed.emit(str(e))
        except Exception as e:
            self.failed.emit(str(e))


@dataclass(frozen=True)
class WorkerHandle:
    thread: QThread
    worker: ResizeWorker
