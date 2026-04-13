from __future__ import annotations

import os
from typing import cast

from PyQt6.QtCore import QEvent, Qt, QThread, QTimer, QUrl, QVariant
from PyQt6.QtGui import QCloseEvent, QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.types import PadFillMode, ResizeConfig, ResizeMode, ResizeResult
from ui import theme
from ui.components.glass_card import GlassCard
from workers.resize_worker import ResizeWorker, WorkerHandle
from workers.padding_scan_worker import PaddingScanResult, PaddingScanWorker


def _output_folder_preview(input_path: str) -> str:
    p = input_path.strip().rstrip(os.sep)
    if not p:
        return ""
    folder_name = os.path.basename(p)
    parent_dir = os.path.dirname(p)
    return os.path.join(parent_dir, f"{folder_name}-Resized-v1.4")


class MainWindow(QMainWindow):
    BREAKPOINT = 1000
    CONTENT_MAX_W = 1100
    CONTENT_MIN_W = 280
    DEFAULT_W = 920
    DEFAULT_H = 680
    COMPACT_W = 540
    COMPACT_H = 580

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image Resize Tool")
        self.setMinimumSize(320, 360)
        self.resize(self.DEFAULT_W, self.DEFAULT_H)

        self._handle: WorkerHandle | None = None
        self._splitter_wide_sizes = [520, 520]
        self._splitter_narrow_sizes = [340, 220]
        self._compact_ui: bool | None = None
        self._glass_cards: list[GlassCard] = []
        self._scan_handle: WorkerHandle | None = None
        self._scan_debounce = QTimer(self)
        self._scan_debounce.setSingleShot(True)
        self._scan_debounce.timeout.connect(self._start_padding_scan)
        self._scan_total = 0
        self._scan_need = 0

        app_root = QWidget()
        app_root.setObjectName("AppRoot")
        self.setCentralWidget(app_root)
        outer = QVBoxLayout(app_root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("MainScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll_row = QWidget()
        scroll_row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        scroll_row_l = QHBoxLayout(scroll_row)
        scroll_row_l.setContentsMargins(0, 0, 0, 0)
        scroll_row_l.setSpacing(0)
        scroll_row_l.addStretch(1)

        center = QWidget()
        center.setMinimumWidth(self.CONTENT_MIN_W)
        center.setMaximumWidth(self.CONTENT_MAX_W)
        center.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        scroll_row_l.addWidget(center, 0, Qt.AlignmentFlag.AlignTop)
        scroll_row_l.addStretch(1)

        scroll.setWidget(scroll_row)
        outer.addWidget(scroll, 1)

        self._center_layout = QVBoxLayout(center)
        self._center_layout.setContentsMargins(28, 24, 28, 24)
        self._center_layout.setSpacing(20)

        # Hero: title left, Appearance (top-right)
        hero_wrap = QWidget()
        hero_bar = QHBoxLayout(hero_wrap)
        hero_bar.setContentsMargins(0, 0, 0, 0)
        hero_bar.setSpacing(12)

        hero_left = QVBoxLayout()
        hero_left.setSpacing(6)
        self._title = QLabel("Image Resize Tool")
        self._title.setObjectName("HeroTitle")
        self._title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._title.setWordWrap(True)
        self._sub = QLabel("Batch resize images to a target resolution.")
        self._sub.setObjectName("HeroSubtitle")
        self._sub.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._sub.setWordWrap(True)
        hero_left.addWidget(self._title)
        hero_left.addWidget(self._sub)
        hero_bar.addLayout(hero_left, 1)

        appearance_col = QVBoxLayout()
        appearance_col.setSpacing(4)
        appearance_col.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight
        )
        self._appearance_label = QLabel("Appearance")
        self._appearance_label.setObjectName("AppearanceLabel")
        self._appearance_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.appearance_box = QComboBox()
        self.appearance_box.setObjectName("AppearanceCombo")
        self.appearance_box.setMinimumWidth(150)
        self.appearance_box.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        modes: list[tuple[str, str]] = [
            ("Follow system", "system"),
            ("Light", "light"),
            ("Dark", "dark"),
        ]
        for label, key in modes:
            self.appearance_box.addItem(label, key)
        idx = 0
        current = theme.get_appearance_mode()
        for i in range(self.appearance_box.count()):
            data = self.appearance_box.itemData(i)
            if data is not None and str(data) == current:
                idx = i
                break
        self.appearance_box.blockSignals(True)
        self.appearance_box.setCurrentIndex(idx)
        self.appearance_box.blockSignals(False)
        self.appearance_box.currentIndexChanged.connect(self._on_appearance_changed)
        appearance_col.addWidget(self._appearance_label, 0, Qt.AlignmentFlag.AlignRight)
        appearance_col.addWidget(self.appearance_box, 0, Qt.AlignmentFlag.AlignRight)
        hero_bar.addLayout(appearance_col, 0)

        self._center_layout.addWidget(hero_wrap)

        self._splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(8)

        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)

        # Input card
        input_card = GlassCard()
        il = input_card.content
        st_in = QLabel("Input")
        st_in.setObjectName("SectionTitle")
        il.addWidget(st_in)
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Choose a folder containing images…")
        self.input_path.setClearButtonEnabled(True)
        self.input_path.textChanged.connect(self._update_output_preview)
        self.input_path.textChanged.connect(lambda _=None: self._schedule_padding_scan())
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        path_stack = QVBoxLayout()
        path_stack.setSpacing(8)
        path_stack.addWidget(self.input_path)
        browse_row = QHBoxLayout()
        browse_row.addStretch(1)
        browse_row.addWidget(browse_btn)
        path_stack.addLayout(browse_row)
        il.addLayout(path_stack)
        self.include_subfolders = QCheckBox(
            "Include nested folders (all levels; mirror layout in output)"
        )
        self.include_subfolders.setChecked(True)
        self.include_subfolders.setToolTip(
            "Walks the whole tree under the folder you choose (skips hidden dirs and "
            "*-Resized-v1.4 folders). Output mirrors subfolders. One Audit_Report.csv at "
            "the output root. Turn off to only use images in the top-level folder."
        )
        il.addWidget(self.include_subfolders)
        self.include_subfolders.toggled.connect(lambda _=False: self._schedule_padding_scan())
        cap = QLabel("Output folder (preview)")
        cap.setObjectName("Caption")
        il.addWidget(cap)
        self.output_preview = QLineEdit()
        self.output_preview.setReadOnly(True)
        self.output_preview.setPlaceholderText("Select a folder to see output path…")
        il.addWidget(self.output_preview)
        left_layout.addWidget(input_card)
        self._glass_cards.append(input_card)

        # Output settings card
        settings_card = GlassCard()
        sl = settings_card.content
        st_out = QLabel("Output settings")
        st_out.setObjectName("SectionTitle")
        sl.addWidget(st_out)
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Format"))
        self.format_box = QComboBox()
        self.format_box.addItems(["JPG", "PNG", "WebP"])
        self.format_box.setCurrentText("JPG")
        fmt_row.addWidget(self.format_box, 1)
        sl.addLayout(fmt_row)
        self._hint_jpeg = QLabel(
            "JPEG/WebP may reduce quality if file exceeds ~1 MB (same as v1.4)."
        )
        self._hint_jpeg.setObjectName("Caption")
        self._hint_jpeg.setWordWrap(True)
        sl.addWidget(self._hint_jpeg)
        left_layout.addWidget(settings_card)
        self._glass_cards.append(settings_card)

        # Dimensions card
        dim_card = GlassCard()
        dl = dim_card.content
        st_dim = QLabel("Dimensions")
        st_dim.setObjectName("SectionTitle")
        dl.addWidget(st_dim)
        dim_row = QHBoxLayout()
        dim_row.setSpacing(12)
        dim_row.addWidget(QLabel("Width"))
        self.width_box = QSpinBox()
        self.width_box.setRange(1, 20000)
        self.width_box.setValue(850)
        self.width_box.valueChanged.connect(lambda _=0: self._schedule_padding_scan())
        dim_row.addWidget(self.width_box, 1)
        dim_row.addWidget(QLabel("Height"))
        self.height_box = QSpinBox()
        self.height_box.setRange(1, 20000)
        self.height_box.setValue(1280)
        self.height_box.valueChanged.connect(lambda _=0: self._schedule_padding_scan())
        dim_row.addWidget(self.height_box, 1)
        dl.addLayout(dim_row)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Sizing"))
        self.resize_mode_box = QComboBox()
        self.resize_mode_box.setObjectName("ResizeModeCombo")
        for label, key in (
            (
                "Fit inside box (keep aspect)",
                "fit",
            ),
            (
                "Exact width × height (letterbox)",
                "exact_pad",
            ),
            (
                "Exact width × height (stretch)",
                "exact_stretch",
            ),
        ):
            self.resize_mode_box.addItem(label, key)
        self.resize_mode_box.setCurrentIndex(0)
        self.resize_mode_box.setToolTip(
            "Fit: a square image in an 850×1280 box stays square (your case). "
            "Letterbox: always outputs the exact pixel size, adds bars if needed. "
            "Stretch: always exact size, may distort."
        )
        self.resize_mode_box.currentIndexChanged.connect(
            lambda _=0: (self._sync_pad_fill_visibility(), self._schedule_padding_scan())
        )
        mode_row.addWidget(self.resize_mode_box, 1)
        dl.addLayout(mode_row)
        self.pad_fill_row = QWidget()
        pad_row = QHBoxLayout(self.pad_fill_row)
        pad_row.setContentsMargins(0, 0, 0, 0)
        pad_row.addWidget(QLabel("Bars/Fill"))
        self.pad_fill_box = QComboBox()
        self.pad_fill_box.setObjectName("PadFillCombo")
        self.pad_fill_box.addItem("White bars", "white")
        self.pad_fill_box.addItem("Black bars", "black")
        self.pad_fill_box.addItem("Extend match", "extend")
        self.pad_fill_box.addItem("Blurred background", "blur")
        self.pad_fill_box.addItem("Auto solid color", "auto")
        self.pad_fill_box.setToolTip(
            "Only applies when padding is needed in letterbox mode."
        )
        pad_row.addWidget(self.pad_fill_box, 1)
        dl.addWidget(self.pad_fill_row)
        self.pad_fill_caption = QLabel("")
        self.pad_fill_caption.setObjectName("Caption")
        self.pad_fill_caption.setWordWrap(True)
        dl.addWidget(self.pad_fill_caption)
        self.scan_caption = QLabel("Analyzing images for padding requirements…")
        self.scan_caption.setObjectName("Caption")
        self.scan_caption.setVisible(False)
        dl.addWidget(self.scan_caption)
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 0)  # indeterminate/busy
        self.scan_progress.setTextVisible(False)
        self.scan_progress.setMaximumHeight(8)
        self.scan_progress.setVisible(False)
        dl.addWidget(self.scan_progress)
        dim_hint = QLabel(
            "Fit inside: largest side ≤ width/height; aspect unchanged (850×850 stays 850×850 "
            "in an 850×1280 box). Use letterbox or stretch for true 850×1280 files."
        )
        dim_hint.setObjectName("Caption")
        dim_hint.setWordWrap(True)
        dl.addWidget(dim_hint)
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        for label, w, h in (
            ("850×1280", 850, 1280),
            ("1080p", 1920, 1080),
            ("4K", 3840, 2160),
            ("Square", 1080, 1080),
        ):
            b = QPushButton(label)
            b.setObjectName("PresetButton")
            b.clicked.connect(lambda _=False, ww=w, hh=h: self._apply_preset(ww, hh))
            preset_row.addWidget(b)
        preset_row.addStretch(1)
        dl.addLayout(preset_row)
        left_layout.addWidget(dim_card)
        self._glass_cards.append(dim_card)

        self.start_btn = QPushButton("Start processing")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self._start)
        left_layout.addWidget(self.start_btn)

        # Right column: progress + activity
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)

        progress_card = GlassCard()
        pl = progress_card.content
        st_prog = QLabel("Progress")
        st_prog.setObjectName("SectionTitle")
        pl.addWidget(st_prog)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("StatusLabel")
        self._set_status_state("idle")
        pl.addWidget(self.status_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        pl.addWidget(self.progress)
        log_cap = QLabel("Activity")
        log_cap.setObjectName("Caption")
        pl.addWidget(log_cap)
        self.activity_log = QPlainTextEdit()
        self.activity_log.setObjectName("ActivityLog")
        self.activity_log.setReadOnly(True)
        self.activity_log.setPlaceholderText("Per-file progress will appear here…")
        self.activity_log.setMinimumHeight(96)
        self.activity_log.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        pl.addWidget(self.activity_log, 1)
        right_layout.addWidget(progress_card, 1)
        self._glass_cards.append(progress_card)

        self._splitter.addWidget(left_col)
        self._splitter.addWidget(right_col)
        self._splitter.setSizes(self._splitter_wide_sizes)

        self._center_layout.addWidget(self._splitter, 1)

        ver = QLabel("Made by Abdullah Rizwan & Asif Nawaz - Development Project")
        ver.setObjectName("Caption")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(ver)

        QTimer.singleShot(0, self._apply_splitter_orientation)
        QTimer.singleShot(0, self._sync_compact_layout)
        QTimer.singleShot(0, self._sync_pad_fill_visibility)
        QTimer.singleShot(0, self._schedule_padding_scan)
        self._update_output_preview()

    def _sync_pad_fill_visibility(self) -> None:
        mode_data = self.resize_mode_box.currentData()
        mode = str(mode_data) if mode_data is not None else "fit"
        should_show = mode == "exact_pad" and self._scan_need > 0
        self.pad_fill_row.setVisible(should_show)
        self.pad_fill_caption.setVisible(should_show)
        if should_show:
            self.pad_fill_caption.setText(
                f"Padding needed for {self._scan_need}/{self._scan_total} images."
            )
        else:
            self.pad_fill_caption.setText("")

    def _schedule_padding_scan(self) -> None:
        # Debounce to avoid scanning on every keystroke/spin.
        self._scan_debounce.start(350)

    def _stop_padding_scan(self) -> None:
        self._scan_debounce.stop()
        if self._scan_handle:
            try:
                if self._scan_handle.thread.isRunning():
                    self._scan_handle.thread.quit()
                    self._scan_handle.thread.wait(1500)
            except RuntimeError:
                # Underlying Qt object may already be deleted.
                pass
        self._scan_handle = None

    def _set_scan_busy(self, busy: bool) -> None:
        self.scan_caption.setVisible(busy)
        self.scan_progress.setVisible(busy)

    def _start_padding_scan(self) -> None:
        input_path = self.input_path.text().strip()
        if not input_path or not os.path.isdir(input_path):
            self._scan_total = 0
            self._scan_need = 0
            self._set_scan_busy(False)
            self._sync_pad_fill_visibility()
            return

        # Only relevant for letterbox mode.
        mode_data = self.resize_mode_box.currentData()
        mode = str(mode_data) if mode_data is not None else "fit"
        if mode != "exact_pad":
            self._scan_total = 0
            self._scan_need = 0
            self._set_scan_busy(False)
            self._sync_pad_fill_visibility()
            return

        # Stop a previous scan if still running.
        self._stop_padding_scan()

        self._set_scan_busy(True)
        thread = QThread(self)
        worker = PaddingScanWorker(
            input_path,
            recursive=self.include_subfolders.isChecked(),
            target_w=int(self.width_box.value()),
            target_h=int(self.height_box.value()),
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_scan_finished)
        worker.failed.connect(lambda _m: self._on_scan_finished(PaddingScanResult(0, 0)))
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        self._scan_handle = WorkerHandle(thread=thread, worker=worker)  # type: ignore[arg-type]
        thread.start()

    def _on_scan_finished(self, result_obj: object) -> None:
        self._set_scan_busy(False)
        if isinstance(result_obj, PaddingScanResult):
            self._scan_total = int(result_obj.total)
            self._scan_need = int(result_obj.needs_padding)
        else:
            self._scan_total = 0
            self._scan_need = 0
        self._sync_pad_fill_visibility()

    def _apply_preset(self, w: int, h: int) -> None:
        self.width_box.setValue(w)
        self.height_box.setValue(h)

    def _set_status_state(self, state: str) -> None:
        if state == "idle":
            self.status_label.setProperty("status", QVariant())
        else:
            self.status_label.setProperty("status", state)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _update_output_preview(self) -> None:
        prev = _output_folder_preview(self.input_path.text())
        self.output_preview.setText(prev)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if path:
            self.input_path.setText(path)

    def _append_log(self, line: str) -> None:
        self.activity_log.appendPlainText(line)
        self.activity_log.verticalScrollBar().setValue(
            self.activity_log.verticalScrollBar().maximum()
        )

    def _apply_splitter_orientation(self) -> None:
        self._sync_splitter_to_width(self.width())

    def _sync_splitter_to_width(self, w: int) -> None:
        if w >= self.BREAKPOINT:
            if self._splitter.orientation() != Qt.Orientation.Horizontal:
                self._splitter.setOrientation(Qt.Orientation.Horizontal)
                self._splitter.setSizes(self._splitter_wide_sizes)
        else:
            if self._splitter.orientation() != Qt.Orientation.Vertical:
                self._splitter.setOrientation(Qt.Orientation.Vertical)
                self._splitter.setSizes(self._splitter_narrow_sizes)

    def _sync_compact_layout(self) -> None:
        w, h = self.width(), self.height()
        compact = w < self.COMPACT_W or h < self.COMPACT_H
        if compact == self._compact_ui:
            return
        self._compact_ui = compact

        lm = 12 if compact else 28
        tm = 10 if compact else 24
        self._center_layout.setContentsMargins(lm, tm, lm, tm)
        self._center_layout.setSpacing(10 if compact else 20)

        for card in self._glass_cards:
            card.set_compact(compact)

        self._splitter.setHandleWidth(6 if compact else 8)

        if compact:
            self._title.setProperty("compact", "true")
            self._sub.setProperty("compact", "true")
            self.activity_log.setMinimumHeight(72)
            self._hint_jpeg.setVisible(h >= 520)
        else:
            self._title.setProperty("compact", QVariant())
            self._sub.setProperty("compact", QVariant())
            self.activity_log.setMinimumHeight(96)
            self._hint_jpeg.setVisible(True)

        self._title.style().unpolish(self._title)
        self._title.style().polish(self._title)
        self._sub.style().unpolish(self._sub)
        self._sub.style().polish(self._sub)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._sync_splitter_to_width(self.width())
        self._sync_compact_layout()

    def changeEvent(self, event) -> None:  # type: ignore[override]
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange and theme.get_appearance_mode() == "system":
            theme.apply_to_application()
            self._polish_theme_widgets()

    def _on_appearance_changed(self, index: int) -> None:
        key = self.appearance_box.itemData(index)
        if key is None:
            return
        theme.set_appearance_mode(str(key))
        theme.apply_to_application()
        self._polish_theme_widgets()

    def _polish_theme_widgets(self) -> None:
        for w in (
            self._title,
            self._sub,
            self._appearance_label,
            self.appearance_box,
            self.resize_mode_box,
            self.pad_fill_box,
            self.status_label,
            self.start_btn,
            self._splitter,
        ):
            w.style().unpolish(w)
            w.style().polish(w)
        for card in self._glass_cards:
            card.style().unpolish(card)
            card.style().polish(card)

    def _start(self) -> None:
        input_path = self.input_path.text().strip()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.critical(self, "Error", "Please select a valid folder.")
            return

        self.activity_log.clear()
        self._append_log("Starting batch…")

        mode_data = self.resize_mode_box.currentData()
        resize_mode = cast(ResizeMode, str(mode_data) if mode_data is not None else "fit")
        fill_data = self.pad_fill_box.currentData()
        pad_fill_mode = cast(
            PadFillMode, str(fill_data) if fill_data is not None else "white"
        )

        # Fit mode does not guarantee exact W×H output.
        if resize_mode == "fit":
            w = int(self.width_box.value())
            h = int(self.height_box.value())
            if w != h:
                msg = QMessageBox(self)
                msg.setWindowTitle("Sizing warning")
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setText("“Fit inside box” will not force the exact output size.")
                msg.setInformativeText(
                    f"For example, an 850×850 image in a {w}×{h} box will remain square.\n\n"
                    "Choose a different sizing mode if you need every file to be exactly "
                    f"{w}×{h}."
                )
                letterbox_btn = msg.addButton(
                    "Switch to letterbox", QMessageBox.ButtonRole.AcceptRole
                )
                stretch_btn = msg.addButton(
                    "Switch to stretch", QMessageBox.ButtonRole.DestructiveRole
                )
                msg.addButton("Continue anyway", QMessageBox.ButtonRole.RejectRole)
                msg.exec()

                if msg.clickedButton() == letterbox_btn:
                    idx = self.resize_mode_box.findData("exact_pad")
                    if idx >= 0:
                        self.resize_mode_box.setCurrentIndex(idx)
                    # Only switch UI mode; let the user press Start again.
                    return
                elif msg.clickedButton() == stretch_btn:
                    idx = self.resize_mode_box.findData("exact_stretch")
                    if idx >= 0:
                        self.resize_mode_box.setCurrentIndex(idx)
                    # Only switch UI mode; let the user press Start again.
                    return

        cfg = ResizeConfig(
            input_path=input_path,
            width=int(self.width_box.value()),
            height=int(self.height_box.value()),
            output_format=self.format_box.currentText(),  # type: ignore[arg-type]
            include_subfolders=self.include_subfolders.isChecked(),
            resize_mode=resize_mode,
            pad_fill_mode=pad_fill_mode,
        )

        self.start_btn.setEnabled(False)
        self.include_subfolders.setEnabled(False)
        self.resize_mode_box.setEnabled(False)
        self.pad_fill_box.setEnabled(False)
        self._stop_padding_scan()
        self.progress.setValue(0)
        self.status_label.setText("Starting…")
        self._set_status_state("running")

        thread = QThread(self)
        worker = ResizeWorker(cfg)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.status.connect(self._on_status)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)

        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)

        self._handle = WorkerHandle(thread=thread, worker=worker)
        thread.start()

    def _on_status(self, text: str) -> None:
        if text == "COMPLETED!":
            self._set_status_state("done")
        else:
            self._set_status_state("running")
        self.status_label.setText(text)
        if text.startswith("Starting"):
            self._append_log(text)

    def _on_progress(self, processed: int, total: int, filename: str) -> None:
        pct = int((processed / total) * 100) if total else 0
        self.progress.setValue(pct)
        self._set_status_state("running")
        self.status_label.setText(f"Processing: {processed} / {total} done…")
        self._append_log(f"[{processed}/{total}] {filename}")

    def _on_failed(self, message: str) -> None:
        self.start_btn.setEnabled(True)
        self.include_subfolders.setEnabled(True)
        self.resize_mode_box.setEnabled(True)
        self.pad_fill_box.setEnabled(True)
        self._sync_pad_fill_visibility()
        self.progress.setValue(0)
        self.status_label.setText("Ready")
        self._set_status_state("error")
        self._append_log(f"Error: {message}")
        QMessageBox.critical(self, "Error", message)
        self._set_status_state("idle")

    def _on_finished(self, result_obj: object) -> None:
        self.start_btn.setEnabled(True)
        self.include_subfolders.setEnabled(True)
        self.resize_mode_box.setEnabled(True)
        self.pad_fill_box.setEnabled(True)
        self._sync_pad_fill_visibility()
        self.progress.setValue(100)
        self.status_label.setText("COMPLETED!")
        self._set_status_state("done")
        if isinstance(result_obj, ResizeResult):
            self._append_log(f"Output: {result_obj.output_path}")
            self._append_log(f"Audit report: {result_obj.audit_csv_path}")
            self._append_log(f"Comparison report: {result_obj.comparison_html_path}")
        report_path = (
            result_obj.comparison_html_path
            if isinstance(result_obj, ResizeResult)
            else ""
        )
        has_report = bool(report_path) and os.path.isfile(report_path)

        box = QMessageBox(self)
        box.setWindowTitle("Completed")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText("Processing completed successfully.")
        if has_report:
            box.setInformativeText("Open the comparison report (HTML) now?")
            open_btn = box.addButton("Open report", QMessageBox.ButtonRole.AcceptRole)
            box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(report_path))
        else:
            box.setInformativeText(
                "Comparison report was not found on disk. Check the output folder."
            )
            box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            box.exec()
        self._set_status_state("done")

    def closeEvent(self, event: QCloseEvent) -> None:  # type: ignore[override]
        self._stop_padding_scan()
        if self._handle:
            try:
                if self._handle.thread.isRunning():
                    self._handle.thread.quit()
                    self._handle.thread.wait(3000)
            except RuntimeError:
                pass
        super().closeEvent(event)
