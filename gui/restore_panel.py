from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.ai_client import AIConfig, send_to_ai, test_ai_connection
from core.deanon import DeAnonymizer
from core.mapping import MappingStore


class AIThread(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, text: str, config: AIConfig) -> None:
        super().__init__()
        self.text = text
        self.config = config

    def run(self) -> None:
        try:
            result = send_to_ai(self.text, self.config)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class RestorePanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store: MappingStore | None = None
        self._ai_thread: AIThread | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        mapenc_row = QHBoxLayout()
        mapenc_row.addWidget(QLabel("Mapping-файл (.mapenc):"))
        self._mapenc_path = QLineEdit()
        self._mapenc_path.setPlaceholderText("Выберите .mapenc файл...")
        self._mapenc_path.setReadOnly(True)
        mapenc_row.addWidget(self._mapenc_path, stretch=1)
        self._btn_load_mapenc = QPushButton("Обзор")
        self._btn_load_mapenc.clicked.connect(self._load_mapenc)
        mapenc_row.addWidget(self._btn_load_mapenc)
        layout.addLayout(mapenc_row)

        pw_row = QHBoxLayout()
        pw_row.addWidget(QLabel("Пароль:"))
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("Введите пароль для .mapenc")
        pw_row.addWidget(self._password_input, stretch=1)
        self._btn_unlock = QPushButton("Расшифровать")
        self._btn_unlock.clicked.connect(self._unlock_mapping)
        pw_row.addWidget(self._btn_unlock)
        layout.addLayout(pw_row)

        self._mapping_status = QLabel("")
        self._mapping_status.setStyleSheet("padding: 4px;")
        layout.addWidget(self._mapping_status)

        tabs = QTabWidget()

        manual_tab = QWidget()
        self._setup_manual_tab(manual_tab)
        tabs.addTab(manual_tab, "Ручной ввод")

        auto_tab = QWidget()
        self._setup_auto_tab(auto_tab)
        tabs.addTab(auto_tab, "Автоинтеграция с AI")

        layout.addWidget(tabs, stretch=1)

        result_group = QGroupBox("Результат")
        result_layout = QVBoxLayout(result_group)
        self._result_text = QPlainTextEdit()
        self._result_text.setReadOnly(True)
        self._result_text.setPlaceholderText("Здесь появится восстановленный текст...")
        result_layout.addWidget(self._result_text)

        result_btn_row = QHBoxLayout()
        self._btn_copy = QPushButton("Копировать")
        self._btn_copy.clicked.connect(self._copy_result)
        result_btn_row.addWidget(self._btn_copy)
        self._btn_save = QPushButton("Сохранить в файл")
        self._btn_save.clicked.connect(self._save_result)
        result_btn_row.addWidget(self._btn_save)
        result_btn_row.addStretch()
        result_layout.addLayout(result_btn_row)

        layout.addWidget(result_group, stretch=1)

    def _setup_manual_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.addWidget(QLabel("Вставьте текст от AI:"))
        self._ai_input = QPlainTextEdit()
        self._ai_input.setPlaceholderText("Скопируйте ответ AI сюда...")
        layout.addWidget(self._ai_input, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_restore_manual = QPushButton("Восстановить")
        self._btn_restore_manual.setStyleSheet(
            "QPushButton { background: #2196F3; color: white; font-weight: bold; "
            "padding: 6px 16px; border-radius: 4px; } "
            "QPushButton:hover { background: #1976D2; }"
        )
        self._btn_restore_manual.clicked.connect(self._restore_manual)
        btn_row.addWidget(self._btn_restore_manual)
        layout.addLayout(btn_row)

    def _setup_auto_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)

        ai_row = QHBoxLayout()
        ai_row.addWidget(QLabel("Сервис:"))
        self._ai_service_input = QLineEdit("openai")
        self._ai_service_input.setPlaceholderText("openai / anthropic / ollama / custom")
        ai_row.addWidget(self._ai_service_input)
        ai_row.addWidget(QLabel("Модель:"))
        self._ai_model_input = QLineEdit("gpt-4o")
        ai_row.addWidget(self._ai_model_input)
        layout.addLayout(ai_row)

        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API Key:"))
        self._ai_key_input = QLineEdit()
        self._ai_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._ai_key_input.setPlaceholderText("sk-...")
        key_row.addWidget(self._ai_key_input, stretch=1)
        layout.addLayout(key_row)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("Base URL (опционально):"))
        self._ai_url_input = QLineEdit()
        self._ai_url_input.setPlaceholderText("https://api.openai.com/v1")
        url_row.addWidget(self._ai_url_input, stretch=1)
        layout.addLayout(url_row)

        layout.addWidget(QLabel("Промпт:"))
        self._ai_prompt_input = QPlainTextEdit()
        self._ai_prompt_input.setMaximumHeight(100)
        from core.ai_client import DEFAULT_PROMPT
        self._ai_prompt_input.setPlainText(DEFAULT_PROMPT)
        layout.addWidget(self._ai_prompt_input)

        layout.addWidget(QLabel("Текст для AI (обезличенный):"))
        self._ai_text_input = QPlainTextEdit()
        self._ai_text_input.setPlaceholderText("Вставьте обезличенный текст или загрузите файл...")
        layout.addWidget(self._ai_text_input, stretch=1)

        btn_row = QHBoxLayout()
        self._btn_load_ai_text = QPushButton("Загрузить файл")
        self._btn_load_ai_text.clicked.connect(self._load_ai_text)
        btn_row.addWidget(self._btn_load_ai_text)
        btn_row.addStretch()

        self._btn_test_ai = QPushButton("Тест соединения")
        self._btn_test_ai.clicked.connect(self._test_ai)
        btn_row.addWidget(self._btn_test_ai)

        self._btn_send_ai = QPushButton("Отправить в AI")
        self._btn_send_ai.setStyleSheet(
            "QPushButton { background: #9C27B0; color: white; font-weight: bold; "
            "padding: 6px 16px; border-radius: 4px; } "
            "QPushButton:hover { background: #7B1FA2; }"
        )
        self._btn_send_ai.clicked.connect(self._send_to_ai)
        btn_row.addWidget(self._btn_send_ai)
        layout.addLayout(btn_row)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

    def _load_mapenc(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите .mapenc файл", "", "DocAnon Mapping (*.mapenc)"
        )
        if path:
            self._mapenc_path.setText(path)

    def _unlock_mapping(self) -> None:
        path = self._mapenc_path.text()
        password = self._password_input.text()

        if not path or not password:
            QMessageBox.warning(self, "Ошибка", "Укажите путь к .mapenc и пароль")
            return

        try:
            self._store = MappingStore.load_encrypted(password, Path(path))
            count = self._store.total_entities
            types = self._store.entity_types
            stats = ", ".join(f"{k}: {v}" for k, v in types.items())
            self._mapping_status.setText(
                f"Расшифровано: {count} сущностей ({stats})"
            )
            self._mapping_status.setStyleSheet("color: green; padding: 4px;")
        except Exception as e:
            self._mapping_status.setText(f"Ошибка: {e}")
            self._mapping_status.setStyleSheet("color: red; padding: 4px;")
            self._store = None

    def _restore_manual(self) -> None:
        if not self._store:
            QMessageBox.warning(self, "Ошибка", "Сначала расшифруйте .mapenc файл")
            return

        ai_text = self._ai_input.toPlainText()
        if not ai_text.strip():
            QMessageBox.warning(self, "Ошибка", "Вставьте текст от AI")
            return

        deanon = DeAnonymizer()
        reverse = self._store.reverse_mapping()
        restored = deanon.restore_text(ai_text, reverse)
        self._result_text.setPlainText(restored)

    def _load_ai_text(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить текст для AI", "", "Text (*.txt);;All (*)"
        )
        if path:
            text = Path(path).read_text(encoding="utf-8")
            self._ai_text_input.setPlainText(text)

    def _test_ai(self) -> None:
        config = self._get_ai_config()
        try:
            ok = test_ai_connection(config)
            if ok:
                QMessageBox.information(self, "OK", "Соединение установлено")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось подключиться")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _send_to_ai(self) -> None:
        if not self._store:
            QMessageBox.warning(self, "Ошибка", "Сначала расшифруйте .mapenc файл")
            return

        text = self._ai_text_input.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Ошибка", "Введите текст для AI")
            return

        config = self._get_ai_config()

        self._btn_send_ai.setEnabled(False)
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)

        self._ai_thread = AIThread(text, config)
        self._ai_thread.finished.connect(self._on_ai_response)
        self._ai_thread.error.connect(self._on_ai_error)
        self._ai_thread.start()

    def _on_ai_response(self, response: str) -> None:
        self._btn_send_ai.setEnabled(True)
        self._progress.setVisible(False)

        deanon = DeAnonymizer()
        reverse = self._store.reverse_mapping() if self._store else {}
        restored = deanon.restore_text(response, reverse)
        self._result_text.setPlainText(restored)

    def _on_ai_error(self, msg: str) -> None:
        self._btn_send_ai.setEnabled(True)
        self._progress.setVisible(False)
        QMessageBox.critical(self, "Ошибка AI", msg)

    def _get_ai_config(self) -> AIConfig:
        return AIConfig(
            service=self._ai_service_input.text().strip(),
            model=self._ai_model_input.text().strip(),
            api_key=self._ai_key_input.text().strip(),
            base_url=self._ai_url_input.text().strip(),
            prompt=self._ai_prompt_input.toPlainText(),
        )

    def _copy_result(self) -> None:
        from PySide6.QtWidgets import QApplication
        text = self._result_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _save_result(self) -> None:
        text = self._result_text.toPlainText()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить результат", "", "Text (*.txt)"
        )
        if path:
            Path(path).write_text(text, encoding="utf-8")
