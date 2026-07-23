# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for DocAnon (Windows)
# Build:  pyinstaller build/docanon.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None
ROOT = Path(SPECPATH).parent.resolve()

datas = []
binaries = []
hiddenimports = [
    "core",
    "core.pipeline",
    "core.batch_pipeline",
    "core.engine",
    "core.analyze",
    "core.mapping",
    "core.morpho",
    "core.person_canon",
    "core.xlsx_enrich",
    "core.xlsx_cells",
    "core.entity_filter",
    "core.ner_config",
    "core.ai_client",
    "core.deanon",
    "core.metrics",
    "core.golden",
    "extractors",
    "exporters",
    "recognizers",
    "gui",
    "gui.main_window",
    "gui.settings_panel",
    "gui.highlight",
    "gui.file_list_panel",
    "gui.restore_panel",
    "presidio_analyzer",
    "presidio_anonymizer",
    "spacy",
    "pymorphy3",
    "pymorphy3_dicts_ru",
    "openpyxl",
    "docx",
    "pdfplumber",
    "PIL",
    "cryptography",
    "PySide6",
]

# spaCy + model
for pkg in ("spacy", "thinc", "catalogue", "srsly", "cymem", "preshed", "blis", "confection"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

try:
    import ru_core_news_lg

    model_path = Path(ru_core_news_lg.__path__[0])
    datas.append((str(model_path), "ru_core_news_lg"))
except Exception as e:
    print("WARNING: ru_core_news_lg not found — install: python -m spacy download ru_core_news_lg")
    print(e)

# pymorphy3 dictionaries
try:
    d, b, h = collect_all("pymorphy3_dicts_ru")
    datas += d
    binaries += b
    hiddenimports += h
except Exception:
    try:
        datas += collect_data_files("pymorphy3_dicts_ru")
    except Exception:
        pass

try:
    d, b, h = collect_all("pymorphy3")
    datas += d
    binaries += b
    hiddenimports += h
except Exception:
    pass

# PySide6 plugins
try:
    d, b, h = collect_all("PySide6")
    datas += d
    binaries += b
    hiddenimports += h
except Exception:
    pass

# presidio
for pkg in ("presidio_analyzer", "presidio_anonymizer"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

hiddenimports += collect_submodules("recognizers")
hiddenimports += collect_submodules("extractors")
hiddenimports += collect_submodules("exporters")
hiddenimports += collect_submodules("core")

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "build" / "rthook_docanon.py")],
    excludes=["pytest", "IPython", "jupyter", "notebook", "tkinter", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DocAnon",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # GUI, no black console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "build" / "docanon.ico") if (ROOT / "build" / "docanon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DocAnon",
)
