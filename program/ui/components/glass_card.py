from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget


class GlassCard(QFrame):
    """Rounded glass-styled panel; children go in inner layout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self._inner = QVBoxLayout(self)
        self._inner.setContentsMargins(20, 18, 20, 18)
        self._inner.setSpacing(12)
        self._compact = False

    def set_compact(self, compact: bool) -> None:
        if compact == self._compact:
            return
        self._compact = compact
        if compact:
            self._inner.setContentsMargins(12, 10, 12, 10)
            self._inner.setSpacing(8)
        else:
            self._inner.setContentsMargins(20, 18, 20, 18)
            self._inner.setSpacing(12)

    @property
    def content(self) -> QVBoxLayout:
        return self._inner
