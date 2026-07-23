from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.config import AnonymizerConfig
from core.models import AnonymizedDocument, ENTITY_LABELS_RU
from core.pipeline import AnonymizationPipeline
from core.batch_pipeline import BatchPipeline, BatchResult
from exporters.json_exporter import JsonExporter
from exporters.txt_exporter import TxtExporter
from exporters.xlsx_exporter import XLSX_EXTENSIONS, XlsxExporter
from gui.file_list_panel import FileListPanel
from gui.highlight import legend_html, set_document_preview
from gui.restore_panel import RestorePanel
from gui.settings_panel import SettingsPanel


class ProcessWorker(QThread):
    finished = Signal(AnonymizedDocument)
    error = Signal(str)

    def __init__(self, file_path: Path, config: AnonymizerConfig) -> None:
        super().__init__()
        self.file_path = file_path
        self.config = config

    def run(self) -> None:
        try:
            pipeline = AnonymizationPipeline(self.config)
            result = pipeline.process_file(self.file_path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class BatchWorker(QThread):
    finished = Signal(BatchResult)
    error = Signal(str)

    def __init__(self, files: list[Path], config: AnonymizerConfig) -> None:
        super().__init__()
        self.files = files
        self.config = config

    def run(self) -> None:
        try:
            # D1: один AnonymizationPipeline → BatchPipeline
            single = AnonymizationPipeline(self.config)
            pipeline = BatchPipeline(pipeline=single)
            result = pipeline.process_batch(self.files)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DocAnon — Анонимизатор документов по 152-ФЗ")
        self.setMinimumSize(1200, 800)
        self._result: AnonymizedDocument | None = None
        self._batch_result: BatchResult | None = None
        self._worker: ProcessWorker | None = None
        self._batch_worker: BatchWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        header = QLabel("DocAnon — Обезличивание документов по 152-ФЗ")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("padding: 12px; color: #333;")
        layout.addWidget(header)

        tabs = QTabWidget()

        single_tab = QWidget()
        self._setup_single_tab(single_tab)
        tabs.addTab(single_tab, "Один файл")

        batch_tab = QWidget()
        self._setup_batch_tab(batch_tab)
        tabs.addTab(batch_tab, "Пакетная обработка")

        restore_tab = RestorePanel()
        tabs.addTab(restore_tab, "Восстановить")

        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        self._settings = SettingsPanel()
        settings_layout.addWidget(self._settings)
        tabs.addTab(settings_tab, "Настройки")

        layout.addWidget(tabs, stretch=1)

    def _setup_single_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)

        btn_row = QHBoxLayout()

        self._btn_open = QPushButton("Открыть файл")
        self._btn_open.setFixedSize(180, 36)
        self._btn_open.setStyleSheet(
            "QPushButton { background: #4CAF50; color: white; font-weight: bold; "
            "border-radius: 4px; } QPushButton:hover { background: #45a049; }"
        )
        self._btn_open.clicked.connect(self._open_file)
        btn_row.addWidget(self._btn_open)

        self._btn_save_txt = QPushButton("Сохранить TXT")
        self._btn_save_txt.setEnabled(False)
        self._btn_save_txt.clicked.connect(self._save_txt)
        btn_row.addWidget(self._btn_save_txt)

        self._btn_save_docx = QPushButton("Сохранить DOCX")
        self._btn_save_docx.setEnabled(False)
        self._btn_save_docx.clicked.connect(self._save_docx)
        btn_row.addWidget(self._btn_save_docx)

        self._btn_save_xlsx = QPushButton("Сохранить XLSX")
        self._btn_save_xlsx.setEnabled(False)
        self._btn_save_xlsx.clicked.connect(self._save_xlsx)
        btn_row.addWidget(self._btn_save_xlsx)

        self._btn_save_json = QPushButton("Отчёт JSON")
        self._btn_save_json.setEnabled(False)
        self._btn_save_json.clicked.connect(self._save_json)
        btn_row.addWidget(self._btn_save_json)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._status = QLabel("Загрузите документ для обезличивания")
        self._status.setStyleSheet("color: #666; padding: 4px;")
        layout.addWidget(self._status)

        self._legend = QLabel("")
        self._legend.setTextFormat(Qt.TextFormat.RichText)
        self._legend.setStyleSheet("padding: 4px;")
        layout.addWidget(self._legend)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Исходный текст (подсветка ПДн):"))
        self._text_original = QTextEdit()
        self._text_original.setReadOnly(True)
        self._text_original.setFont(QFont("Consolas", 10))
        left_layout.addWidget(self._text_original)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("Обезличенный текст:"))
        self._text_anonymized = QTextEdit()
        self._text_anonymized.setReadOnly(True)
        self._text_anonymized.setFont(QFont("Consolas", 10))
        right_layout.addWidget(self._text_anonymized)
        splitter.addWidget(right)

        splitter.setSizes([500, 500])
        layout.addWidget(splitter, stretch=1)

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet(
            "padding: 6px; background: #f5f5f5; border-radius: 4px; font-size: 11px;"
        )
        layout.addWidget(self._stats_label)

    def _setup_batch_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)

        self._file_list = FileListPanel()
        self._file_list.process_requested.connect(self._process_batch)
        layout.addWidget(self._file_list)

        batch_btn_row = QHBoxLayout()

        self._btn_save_mapping = QPushButton("Сохранить mapping (.mapenc)")
        self._btn_save_mapping.setEnabled(False)
        self._btn_save_mapping.clicked.connect(self._save_mapping)
        batch_btn_row.addWidget(self._btn_save_mapping)

        batch_btn_row.addStretch()

        self._batch_stats = QLabel("")
        self._batch_stats.setStyleSheet(
            "padding: 6px; background: #f5f5f5; border-radius: 4px; font-size: 11px;"
        )
        batch_btn_row.addWidget(self._batch_stats)
        layout.addLayout(batch_btn_row)

        self._batch_progress = QProgressBar()
        self._batch_progress.setVisible(False)
        layout.addWidget(self._batch_progress)

        self._batch_status = QLabel("Добавьте файлы и нажмите 'Обработать'")
        self._batch_status.setStyleSheet("color: #666; padding: 4px;")
        layout.addWidget(self._batch_status)

    def _current_config(self) -> AnonymizerConfig:
        return self._settings.build_config()

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите документ",
            "",
            "Все поддерживаемые (*.txt *.md *.csv *.docx *.xlsx *.xlsm *.pdf *.png *.jpg *.jpeg);;"
            "Текстовые (*.txt *.md *.csv);;"
            "Word (*.docx);;"
            "Excel (*.xlsx *.xlsm);;"
            "PDF (*.pdf);;"
            "Изображения (*.png *.jpg *.jpeg)",
        )
        if not path:
            return

        self._btn_open.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)
        self._status.setText(f"Обработка: {Path(path).name}...")

        self._worker = ProcessWorker(Path(path), self._current_config())
        self._worker.finished.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_result(self, result: AnonymizedDocument) -> None:
        self._result = result
        # D3: подсветка spans
        set_document_preview(
            self._text_original, self._text_anonymized, result
        )
        self._legend.setText(legend_html(result.entities))

        self._btn_open.setEnabled(True)
        self._btn_save_txt.setEnabled(True)
        self._btn_save_docx.setEnabled(True)
        self._btn_save_json.setEnabled(True)
        can_xlsx = bool(
            result.source_path
            and Path(result.source_path).suffix.lower() in XLSX_EXTENSIONS
        )
        self._btn_save_xlsx.setEnabled(can_xlsx)
        self._progress.setVisible(False)

        stats_parts = []
        for label, count in result.stats.items():
            label_ru = ENTITY_LABELS_RU.get(label, label)
            stats_parts.append(f"{label_ru}: {count}")

        self._stats_label.setText(
            f"Найдено сущностей: {result.total_entities} | "
            + " | ".join(stats_parts)
        )
        self._status.setText(
            f"Готово: {result.source_file} — {result.total_entities} сущностей"
        )

    def _on_error(self, msg: str) -> None:
        self._btn_open.setEnabled(True)
        self._progress.setVisible(False)
        self._status.setText(f"Ошибка: {msg}")
        QMessageBox.critical(self, "Ошибка", msg)

    def _process_batch(self) -> None:
        files = self._file_list.get_files()
        if not files:
            QMessageBox.warning(self, "Ошибка", "Добавьте файлы для обработки")
            return

        self._file_list.setEnabled(False)
        self._batch_progress.setVisible(True)
        self._batch_progress.setRange(0, 0)
        self._batch_status.setText(f"Обработка {len(files)} файлов...")

        self._batch_worker = BatchWorker(files, self._current_config())
        self._batch_worker.finished.connect(self._on_batch_result)
        self._batch_worker.error.connect(self._on_batch_error)
        self._batch_worker.start()

    def _on_batch_result(self, result: BatchResult) -> None:
        self._batch_result = result
        self._file_list.setEnabled(True)
        self._batch_progress.setVisible(False)
        self._btn_save_mapping.setEnabled(True)

        types = result.mapping.entity_types
        stats_parts = [f"{k}: {v}" for k, v in types.items()]
        self._batch_stats.setText(
            f"Всего сущностей: {result.total_entities} | "
            + " | ".join(stats_parts)
        )
        self._batch_status.setText(
            f"Готово: {len(result.documents)} файлов, "
            f"{result.mapping.total_entities} уникальных сущностей"
        )

        output_dir = Path("./output_batch")
        output_dir.mkdir(exist_ok=True)
        final_mapping = result.mapping.to_mapping_dict()
        xlsx_exporter = XlsxExporter()
        from exporters.docx_exporter import DocxExporter

        docx_exporter = DocxExporter()
        for doc in result.documents:
            stem = Path(doc.source_file).stem
            TxtExporter().export(doc, output_dir / f"{stem}_anonymized")
            src = Path(doc.source_path) if doc.source_path else None
            if src and src.suffix.lower() in XLSX_EXTENSIONS and src.exists():
                xlsx_exporter.export_workbook(
                    src,
                    final_mapping,
                    output_dir / f"{stem}_anonymized{src.suffix}",
                )
            if src and src.suffix.lower() == ".docx" and src.exists():
                docx_exporter.export_from_source(
                    src,
                    final_mapping,
                    output_dir / f"{stem}_anonymized.docx",
                )

        self._batch_status.setText(
            self._batch_status.text() + f" | Результаты: {output_dir}"
        )

    def _on_batch_error(self, msg: str) -> None:
        self._file_list.setEnabled(True)
        self._batch_progress.setVisible(False)
        self._batch_status.setText(f"Ошибка: {msg}")
        QMessageBox.critical(self, "Ошибка", msg)

    def _save_mapping(self) -> None:
        if not self._batch_result:
            return

        password, ok = QFileDialog.getSaveFileName(
            self, "Сохранить mapping", "", "DocAnon Mapping (*.mapenc)"
        )
        if not password:
            return

        pw, ok = QInputDialog.getText(
            self, "Пароль", "Введите пароль для шифрования mapping:",
            QLineEdit.EchoMode.Password,
        )
        if not ok or not pw:
            return

        pw2, ok = QInputDialog.getText(
            self, "Подтверждение", "Повторите пароль:",
            QLineEdit.EchoMode.Password,
        )
        if not ok or pw != pw2:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return

        try:
            path = self._batch_result.mapping.save_encrypted(pw, Path(password))
            QMessageBox.information(
                self, "OK", f"Mapping сохранён: {path.name}\n"
                f"({self._batch_result.mapping.total_entities} сущностей)"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _save_txt(self) -> None:
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить TXT", "", "Text (*.txt)"
        )
        if path:
            TxtExporter().export(self._result, Path(path))

    def _save_docx(self) -> None:
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить DOCX", "", "Word (*.docx)"
        )
        if path:
            from exporters.docx_exporter import DocxExporter
            DocxExporter().export(self._result, Path(path))

    def _save_xlsx(self) -> None:
        if not self._result or not self._result.source_path:
            return
        src = Path(self._result.source_path)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить XLSX",
            f"{src.stem}_anonymized{src.suffix}",
            "Excel (*.xlsx *.xlsm)",
        )
        if path:
            try:
                out = XlsxExporter().export(self._result, Path(path))
                QMessageBox.information(self, "OK", f"Сохранено: {out}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def _save_json(self) -> None:
        if not self._result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт", "", "JSON (*.json)"
        )
        if path:
            JsonExporter().export(self._result, Path(path))


def run_gui() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
