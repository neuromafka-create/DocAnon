from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.config import DEFAULT_ENTITY_THRESHOLDS, AnonymizerConfig
from core.models import ENTITY_LABELS_RU

# Типы, которые показываем в GUI (часто используемые + РФ)
_SETTINGS_ENTITY_ORDER: list[str] = [
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "RU_INN",
    "RU_SNILS",
    "RU_PASSPORT",
    "RU_DRIVER_LICENSE",
    "RU_VEHICLE_PLATE",
    "RU_ACCOUNT",
    "RU_BIK",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "MAC_ADDRESS",
    "GPS_COORDS",
    "TG_CHAT_ID",
    "DATE_TIME",
    "RU_OMS",
    "RU_INT_PASSPORT",
    "IBAN_CODE",
    "CRYPTO",
    "NORP",
    "GPE",
    "EME_IMEI",
]


class SettingsPanel(QWidget):
    """D2: вкл/выкл типов сущностей, порог NER, morpho, person canon."""

    config_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checkboxes: dict[str, QCheckBox] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        # NLP toggles
        nlp_box = QGroupBox("NLP")
        nlp_layout = QVBoxLayout(nlp_box)

        self._chk_ner = QCheckBox("spaCy NER (ФИО, организации, локации)")
        self._chk_ner.setChecked(True)
        self._chk_ner.stateChanged.connect(self._emit_changed)
        nlp_layout.addWidget(self._chk_ner)

        self._chk_morpho = QCheckBox("pymorphy3 — ФИО во всех падежах")
        self._chk_morpho.setChecked(True)
        self._chk_morpho.stateChanged.connect(self._emit_changed)
        nlp_layout.addWidget(self._chk_morpho)

        self._chk_person_canon = QCheckBox(
            "Единый placeholder на персону (канон ФИО, batch)"
        )
        self._chk_person_canon.setChecked(True)
        self._chk_person_canon.stateChanged.connect(self._emit_changed)
        nlp_layout.addWidget(self._chk_person_canon)

        thr_row = QHBoxLayout()
        thr_row.addWidget(QLabel("Порог NER:"))
        self._ner_threshold = QDoubleSpinBox()
        self._ner_threshold.setRange(0.0, 1.0)
        self._ner_threshold.setSingleStep(0.05)
        self._ner_threshold.setDecimals(2)
        self._ner_threshold.setValue(0.35)
        self._ner_threshold.valueChanged.connect(self._emit_changed)
        thr_row.addWidget(self._ner_threshold)
        thr_row.addStretch()
        nlp_layout.addLayout(thr_row)

        root.addWidget(nlp_box)

        # Entity types
        types_box = QGroupBox("Типы сущностей")
        types_layout = QVBoxLayout(types_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(220)
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setContentsMargins(4, 4, 4, 4)

        defaults = set(AnonymizerConfig().enabled_entity_types)
        for i, et in enumerate(_SETTINGS_ENTITY_ORDER):
            label = ENTITY_LABELS_RU.get(et, et)
            cb = QCheckBox(f"{label} ({et})")
            cb.setChecked(et in defaults)
            cb.stateChanged.connect(self._emit_changed)
            self._checkboxes[et] = cb
            grid.addWidget(cb, i // 2, i % 2)

        scroll.setWidget(inner)
        types_layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        from PySide6.QtWidgets import QPushButton

        btn_all = QPushButton("Все")
        btn_all.clicked.connect(self._select_all)
        btn_none = QPushButton("Сбросить")
        btn_none.clicked.connect(self._select_none)
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        btn_row.addStretch()
        types_layout.addLayout(btn_row)

        root.addWidget(types_box)
        root.addStretch()

    def _emit_changed(self, *_args) -> None:
        self.config_changed.emit()

    def _select_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.setChecked(True)

    def _select_none(self) -> None:
        for cb in self._checkboxes.values():
            cb.setChecked(False)

    def build_config(self) -> AnonymizerConfig:
        enabled = [et for et, cb in self._checkboxes.items() if cb.isChecked()]
        # сохранить прочие типы из дефолта, если не в списке GUI
        for et in AnonymizerConfig().enabled_entity_types:
            if et not in self._checkboxes and et not in enabled:
                enabled.append(et)

        cfg = AnonymizerConfig(
            enabled_entity_types=enabled,
            ner_enabled=self._chk_ner.isChecked(),
            morpho_enabled=self._chk_morpho.isChecked(),
            person_canonical_mapping=self._chk_person_canon.isChecked(),
            ner_confidence_threshold=self._ner_threshold.value(),
        )
        # PERSON/ORG/LOC порог через NER
        if "PERSON" in DEFAULT_ENTITY_THRESHOLDS:
            cfg.set_threshold("PERSON", self._ner_threshold.value())
        return cfg
