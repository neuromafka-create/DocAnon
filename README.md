# DocAnon — локальный анонимизатор документов

Обезличивание персональных данных (ПДн) **на вашем ПК** перед отправкой текста во внешние AI-сервисы.  
Детекция: **regex + чексуммы + spaCy NER + pymorphy3** (без локальных LLM для поиска ПДн).

---

## Требования

| Компонент | Версия / примечание |
|-----------|---------------------|
| ОС | Windows / Linux / macOS |
| Python | **3.10+** (проверено на 3.11, 3.12) |
| spaCy-модель | `ru_core_news_lg` (~500+ MB, скачивается отдельно) |
| Tesseract OCR | **опционально** — только для сканов PDF и изображений |
| GUI | PySide6 (идёт из зависимостей) |

---

## 1. Клонирование и окружение

```powershell
cd c:\Projects\anonymizer

# Рекомендуется виртуальное окружение
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Windows (cmd)
# .venv\Scripts\activate.bat

# Linux / macOS
# source .venv/bin/activate
```

---

## 2. Установка зависимостей

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt

# dev-тесты (по желанию)
pip install pytest pytest-cov
```

Либо editable-установка пакета:

```powershell
pip install -e ".[dev]"
```

### Модель spaCy (обязательно)

Без неё NER (ФИО, организации, адреса) не заработает:

```powershell
python -m spacy download ru_core_news_lg
```

Проверка:

```powershell
python -c "import spacy; spacy.load('ru_core_news_lg'); print('spaCy OK')"
```

### Tesseract (опционально, OCR)

1. Установите [Tesseract](https://github.com/tesseract-ocr/tesseract) с языковым пакетом **rus**.
2. Убедитесь, что `tesseract` есть в `PATH`, либо настройте путь в системе.

Нужен только для **сканов PDF** и **картинок** (PNG/JPG). Текстовые PDF, DOCX, XLSX, TXT работают без Tesseract.

---

## 3. Запуск

Все команды — из **корня проекта** (`anonymizer/`), с активированным venv.

### GUI (десктоп)

```powershell
python main.py
# или
python main.py --gui
```

Вкладки:

| Вкладка | Назначение |
|---------|------------|
| **Один файл** | загрузка, preview с подсветкой, экспорт TXT/DOCX/XLSX/JSON |
| **Пакетная обработка** | несколько файлов, общий mapping, `.mapenc` |
| **Восстановить** | de-anon по `.mapenc` + отправка обезличенного текста в AI |
| **Настройки** | типы сущностей, NER, pymorphy3, порог |

### CLI — один файл

```powershell
python main.py путь\к\документу.docx
# результат по умолчанию в .\output\

python main.py путь\к\файлу.xlsx .\my_output
```

Что появится в каталоге вывода:

- `*_anonymized.txt` — обезличенный текст  
- `*_report.json` — сущности и mapping  
- `*_anonymized.xlsx` — если вход был Excel (round-trip по ячейкам)

Примеры на тестовых данных:

```powershell
python main.py tests\fixtures\test_contract.txt .\output
python main.py test_docs\Договор_поставки.docx .\output
python main.py test_docs\Клиенты.xlsx .\output
```

### Из кода (Python)

```python
from pathlib import Path
from core.config import AnonymizerConfig
from core.pipeline import AnonymizationPipeline

config = AnonymizerConfig()
# config.ner_enabled = True
# config.morpho_enabled = True
# config.set_threshold("PERSON", 0.4)

pipeline = AnonymizationPipeline(config)
result = pipeline.process_file(Path("docs/contract.docx"))

print(result.anonymized_text)
print(result.stats)
print(result.mapping)
```

Пакетная обработка с единым mapping:

```python
from pathlib import Path
from core.batch_pipeline import BatchPipeline
from core.config import AnonymizerConfig

batch = BatchPipeline(AnonymizerConfig())
result = batch.process_batch([
    Path("a.docx"),
    Path("b.xlsx"),
])
result.mapping.save_encrypted("your-password", Path("session.mapenc"))
```

---

## 4. Тесты

```powershell
# все тесты (~1–2 мин: грузится spaCy)
python -m pytest tests/ -q

# только quality / golden
python -m pytest tests/test_golden.py -v

# без GUI-запуска, smoke на test_docs
python -m pytest tests/test_smoke_docs.py -v
```

Первый прогон дольше: инициализация `ru_core_news_lg` и Presidio.

---

## 5. Поддерживаемые форматы

| Формат | Извлечение | Экспорт обезличенного |
|--------|------------|------------------------|
| `.txt`, `.md`, `.csv` | ✅ | TXT |
| `.docx` | ✅ | DOCX (round-trip) / TXT |
| `.xlsx`, `.xlsm` | ✅ | XLSX (round-trip) / TXT |
| `.pdf` (текст) | ✅ pdfplumber | TXT |
| `.pdf` (скан), изображения | ✅ Tesseract | TXT |

---

## 6. Типичные проблемы

### `Can't find model 'ru_core_news_lg'`

```powershell
python -m spacy download ru_core_news_lg
```

Убедитесь, что download был в **том же** venv, из которого запускаете приложение.

### GUI не открывается / ошибка Qt

```powershell
pip install --upgrade PySide6
```

На сервере без дисплея GUI не нужен — используйте CLI.

### OCR не видит текст на скане

- Установлен ли Tesseract и язык `rus`?
- В PATH ли бинарник `tesseract`?

```powershell
tesseract --version
```

### Медленный первый запуск

Нормально: один раз грузятся spaCy и recognizers Presidio (десятки секунд на CPU).

### PowerShell: «не удаётся загрузить модуль» / execution policy

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

---

## 7. Структура проекта (кратко)

```
anonymizer/
├── main.py              # CLI + GUI entry
├── requirements.txt
├── core/                # pipeline, NER, morpho, mapping, metrics
├── extractors/          # txt, docx, xlsx, pdf, image
├── recognizers/         # ИНН, СНИЛС, паспорт, телефон, …
├── exporters/           # txt, docx, xlsx, json
├── gui/                 # PySide6
├── tests/               # pytest + fixtures/gold
├── test_docs/           # примеры DOCX/XLSX
└── plan.md              # статус задач
```

Подробный план и архитектура: `plan.md`, `ARCHITECTURE.md`.

---

## 8. Безопасность (кратко)

- Анализ документов **локальный**; исходник по умолчанию не уходит в сеть.
- Вкладка «Восстановить» / AI-клиент отправляет **уже обезличенный** текст — только если вы сами настроите API-ключ.
- Файл mapping `.mapenc` шифруется паролем (AES-GCM + PBKDF2). Пароль не храните рядом с файлом.

---

## Быстрый чеклист

```powershell
cd c:\Projects\anonymizer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download ru_core_news_lg
python main.py
# или
python main.py tests\fixtures\test_contract.txt .\output
```

---

## 9. Сборка установщика Windows

Скрипт собирает **portable**-папку (можно копировать без установки) и, при наличии [Inno Setup 6](https://jrsoftware.org/isinfo.php), — **Setup.exe**.

### Требования для сборки

- Windows 10/11 x64  
- Python 3.10+ с зависимостями проекта и `ru_core_news_lg`  
- `pyinstaller` (ставится скриптом)  
- **Опционально:** [Inno Setup 6](https://jrsoftware.org/isdl.php) — для `DocAnon-Setup-*.exe`  

Место на диске: **~2–4 GB** на время сборки (модель spaCy ~500 MB + зависимости).

### Сборка одной командой

```powershell
cd c:\Projects\anonymizer
.\.venv\Scripts\Activate.ps1   # если используете venv
.\build\build_windows.ps1
```

Параметры:

```powershell
.\build\build_windows.ps1 -Clean          # очистить dist/ перед сборкой
.\build\build_windows.ps1 -SkipInstaller  # только portable, без Inno
```

### Результат

| Артефакт | Путь |
|----------|------|
| Portable (запуск без установки) | `dist\DocAnon\DocAnon.exe` |
| ZIP portable | `dist\DocAnon-portable-0.1.0.zip` (~100–200 MB) |
| Установщик Inno Setup | `dist\installer\DocAnon-Setup-0.1.0.exe` |

### Установка без Inno Setup

После сборки portable:

```powershell
.\build\install_portable.ps1
```

Скопирует приложение в `%LOCALAPPDATA%\Programs\DocAnon`, создаст ярлыки в меню «Пуск» и на рабочем столе.  
Удаление: `%LOCALAPPDATA%\Programs\DocAnon\uninstall.ps1`.

### Полноценный Setup.exe (Inno Setup)

1. Установите [Inno Setup 6](https://jrsoftware.org/isdl.php).  
2. Убедитесь, что есть `dist\DocAnon\DocAnon.exe` (после `build_windows.ps1`).  
3. Соберите установщик:

```powershell
.\build\build_windows.ps1
# или только Inno:
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" build\docanon.iss
```

### Замечания

- Установщик **не требует прав администратора**, ставится в профиль пользователя.  
- **Tesseract OCR** в сборку не входит — для сканов ставьте отдельно.  
- Первая сборка долгая (5–15+ минут), папка `dist\DocAnon` ~1.5 GB.  
- Размер большой из‑за `ru_core_news_lg` — это нормально для offline NLP.
