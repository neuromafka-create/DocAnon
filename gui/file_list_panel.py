from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

SUPPORTED_EXTENSIONS = (
    "*.txt *.md *.csv "
    "*.docx "
    "*.xlsx *.xlsm "
    "*.pdf "
    "*.png *.jpg *.jpeg *.tiff *.bmp"
)


class FileListPanel(QWidget):
    files_changed = Signal()
    process_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Файлы для обработки")
        header.setStyleSheet("font-weight: bold; font-size: 13px; padding: 4px;")
        layout.addWidget(header)

        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._file_list.setStyleSheet(
            "QListWidget { border: 2px dashed #ccc; border-radius: 8px; padding: 8px; }"
        )
        layout.addWidget(self._file_list, stretch=1)

        btn_row = QHBoxLayout()

        self._btn_add = QPushButton("Добавить")
        self._btn_add.clicked.connect(self._add_files)
        btn_row.addWidget(self._btn_add)

        self._btn_remove = QPushButton("Удалить")
        self._btn_remove.clicked.connect(self._remove_selected)
        btn_row.addWidget(self._btn_remove)

        self._btn_clear = QPushButton("Очистить")
        self._btn_clear.clicked.connect(self._clear_all)
        btn_row.addWidget(self._btn_clear)

        btn_row.addStretch()

        self._btn_process = QPushButton("Обработать")
        self._btn_process.setStyleSheet(
            "QPushButton { background: #4CAF50; color: white; font-weight: bold; "
            "padding: 6px 16px; border-radius: 4px; } "
            "QPushButton:hover { background: #45a049; }"
        )
        self._btn_process.clicked.connect(self.process_requested.emit)
        btn_row.addWidget(self._btn_process)

        layout.addLayout(btn_row)

        self._count_label = QLabel("Файлов: 0")
        self._count_label.setStyleSheet("color: #666; padding: 2px;")
        layout.addWidget(self._count_label)

    def get_files(self) -> list[Path]:
        files: list[Path] = []
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            if item:
                files.append(Path(item.data(Qt.ItemDataRole.UserRole)))
        return files

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы",
            "",
            f"Все поддерживаемые ({SUPPORTED_EXTENSIONS});;"
            "Текстовые (*.txt *.md *.csv);;"
            "Word (*.docx);;"
            "PDF (*.pdf);;"
            "Изображения (*.png *.jpg *.jpeg *.tiff *.bmp)",
        )
        for path_str in paths:
            self._add_file(Path(path_str))

    def _add_file(self, path: Path) -> None:
        for i in range(self._file_list.count()):
            item = self._file_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == str(path):
                return

        item = QListWidgetItem(f"  {path.name}  ({path.suffix})")
        item.setData(Qt.ItemDataRole.UserRole, str(path))
        self._file_list.addItem(item)
        self._update_count()
        self.files_changed.emit()

    def _remove_selected(self) -> None:
        for item in reversed(self._file_list.selectedItems()):
            self._file_list.takeItem(self._file_list.row(item))
        self._update_count()
        self.files_changed.emit()

    def _clear_all(self) -> None:
        self._file_list.clear()
        self._update_count()
        self.files_changed.emit()

    def _update_count(self) -> None:
        count = self._file_list.count()
        self._count_label.setText(f"Файлов: {count}")
        self._btn_process.setEnabled(count > 0)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_file():
                self._add_file(path)
