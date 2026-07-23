# DocAnon — план работ

> Локальный анонимизатор документов по 152-ФЗ.  
> Детекция: regex + validators + spaCy NER + (план) pymorphy3.  
> **Без локальных LLM** для поиска ПДн. Внешние AI — только после обезличивания.

---

## Выполнено

### Фаза A — Форматы и стабильность

| ID | Задача | Статус |
|----|--------|--------|
| A1 | XLSX extractor (`openpyxl`, GUI/CLI, тесты) | ✅ |
| A2 | BatchPipeline: numbered placeholders из MappingStore реально в тексте | ✅ |
| A3 | XLSX round-trip exporter (ячейки, формулы, `source_path`) | ✅ |

### Инфраструктура (ранее)

| Задача | Статус |
|--------|--------|
| Ядро Presidio + spaCy `ru_core_news_lg` | ✅ |
| Extractors: txt, docx, pdf, image | ✅ |
| Кастомные РФ-recognizers (ИНН, СНИЛС, …) — базовая версия | ✅ |
| MappingStore AES-GCM `.mapenc` + DeAnonymizer | ✅ |
| GUI: один файл / пакет / восстановление + AI-клиент | ✅ |
| CLI `main.py` | ✅ |
| Экспорт TXT / DOCX / JSON | ✅ |

---

## В работе / далее

### Фаза A (остаток)

| ID | Задача | Статус |
|----|--------|--------|
| **A4** | Smoke на `test_docs/*` (xlsx/docx) через pipeline | ✅ |

### Фаза B — Structured PII (regex + validation)

| ID | Задача | Статус |
|----|--------|--------|
| **B1** | Добить пропуски: паспорт, телефон, госномер, ВУ, MAC, р/с, БИК | ✅ |
| **B2** | Context boost / меньше ложных срабатываний (цифры ≠ ИНН/паспорт) | ✅ |
| **B3** | Пороги confidence **по типу** сущности | ✅ |
| B4 | Unit-тесты на каждый recognizer + fixtures | ✅ (базово с B1) |

### Фаза C — Классический NLP

| ID | Задача | Статус |
|----|--------|--------|
| **C1** | Явная настройка spaCy NER → entity types | ✅ |
| **C2** | pymorphy3: ФИО во всех падежах | ✅ |
| **C3** | Cross-file словарь персон (канон → один placeholder) | ✅ |
| C4 | (опц.) GLiNER, если recall spaCy мало — **не LLM** | ⏳ |
| C5 | Не тащить generative LLM в детекцию | правило |

### Фаза D — Пайплайн и UX

| ID | Задача | Статус |
|----|--------|--------|
| **D1** | Единый engine: убрать дубль analyze/dedup single vs batch | ✅ |
| **D2** | GUI: вкл/выкл типов, порог NER | ✅ |
| **D3** | Preview с подсветкой spans | ✅ |
| **D4** | DOCX export с лучшим форматированием | ✅ |

### Фаза E — Качество

| ID | Задача | Статус |
|----|--------|--------|
| **E1** | Золотой набор: contract + xlsx/docx + expected entities | ✅ |
| **E2** | Метрики precision/recall/F1 по типам | ✅ |
| **E3** | Регрессия в pytest / CI | ✅ |

### Полировка (бэклог)

| Задача | Статус |
|--------|--------|
| README (установка, запуск) | ⏳ |
| Сборка .exe (PyInstaller) | ⏳ |
| Обновить ARCHITECTURE.md под фактический стек (Presidio, не GLiNER) | ⏳ |

---

## Принципы

1. **Детекция:** PatternRecognizer + чексуммы + spaCy NER + pymorphy3.  
2. **Не используем:** Ollama/Qwen и др. generative LLM для поиска ПДн.  
3. **После replace:** внешние AI (OpenAI/Anthropic/Ollama) для анализа обезличенного текста — ок.  
4. **Batch:** один original → один `<LABEL_N>` во всех файлах + `.mapenc`.

---

## Рекомендуемый порядок

```
B1 → B2/B4 → A4 → C2 → C3 → E1/E2 → D2/D3 → …
```

---

## Заметки по B1 (сделано)

По `tests/fixtures/test_contract.txt` закрыто:

- паспорт `45 12 345678` — `PassportRfRecognizer` (серия с пробелом)
- телефон `+7 495 123 45 67` — `RuPhoneRecognizer` (score ≥ 0.9)
- госномер `А123БВ 777` — расширенный алфавит букв
- ВУ `77 АВ 123456` — паттерн с пробелами + validate
- MAC `00:1A:2B:3C:4D:5E` — `RuMacAddressRecognizer`
- р/с / БИК — `RuAccountRecognizer`, `RuBikRecognizer` (`RU_ACCOUNT`, `RU_BIK`)

## Заметки по B2 (сделано)

- `core/entity_filter.py`: reject-правила, context boost/penalty, priority-dedup
- ИНН ≠ паспорт (чексумма); СНИЛС/IP/БИК ≠ телефон; TG без широкого `\d{5,15}`
- Pipeline + Batch используют общий `filter_entities`
- `RuMacAddressRecognizer` — без конфликта с Presidio predefined MAC

## Заметки по B3 (сделано)

- `DEFAULT_ENTITY_THRESHOLDS` + `AnonymizerConfig.threshold_for()` / `set_threshold()`
- NER (PERSON/ORG/LOC) ниже (0.35–0.40); DATE_TIME строже (0.65); INT_PASSPORT 0.70
- `filter_entities(..., threshold_for=config.threshold_for)` в single и batch
- Переопределение: `config.set_threshold("PHONE_NUMBER", 0.9)`

## Заметки по A4 (сделано)

- `tests/test_smoke_docs.py`: extract + pipeline + xlsx round-trip + batch на `test_docs/*`
- Договор: phone/email маскируются; ИНН `7725483912` в файле **невалиден** по чексумме → не ловится (ожидаемо)
- Известное ограничение: NER-span через ` | ` в xlsx-extract ≠ одна ячейка

## Заметки по C1/C2 (сделано)

- **C1** `core/ner_config.py`: PER/ORG/LOC → PERSON/ORGANIZATION/LOCATION в `NerModelConfiguration`
- `normalize_entity_label`, `ner_enabled=False` отключает NER-типы
- **C2** `core/morpho.py`: merge соседних PERSON + pymorphy3 словоформы (падежи)
- `core/analyze.py`: единый analyze для single/batch
- `morpho_enabled` в `AnonymizerConfig` (default True)
- зависимость `pymorphy3`

## Заметки по C3 (сделано)

- `core/person_canon.py`: леммы ФИО (учёт женских -ова/-ева)
- `MappingStore`: PERSON surface-формы → один `<PERSON_N>`; partial ↔ full FIO
- `to_mapping_dict` — все алиасы; `reverse_mapping` → **primary** (самое полное ФИО)
- `person_canonical_mapping` в config (default True); `.mapenc` v2 с primary/canon
- De-anon: падеж surface может не восстановиться (primary form)

## Заметки по D (сделано)

- **D1** `BatchPipeline(pipeline=AnonymizationPipeline)` — один analyzer; `apply_placeholders` / `anonymize_with_store`
- **D2** вкладка «Настройки»: типы сущностей, NER on/off, morpho, person canon, порог NER
- **D3** `gui/highlight.py`: цветные span'ы в исходнике + плейсхолдеры справа + легенда
- **D4** DOCX round-trip: параграфы/таблицы/header-footer; fallback — новый doc из текста

## Заметки по E (сделано)

- **E1** `tests/fixtures/gold/*.json` — contract, dogovor, klienty, structured_ids
- **E2** `core/metrics.py` — P/R/F1: `exact` / `label_text` (containment) / `overlap`
- **E2** `core/golden.py` — загрузка кейсов, `run_gold_case`
- **E3** `tests/test_golden.py` — регрессия min_recall/precision/f1
- **E3** `.github/workflows/test.yml` — CI pytest + spaCy model
