from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from core.config import AnonymizerConfig
from core.models import ENTITY_LABELS_RU
from core.pipeline import AnonymizationPipeline
from exporters.txt_exporter import TxtExporter
from exporters.json_exporter import JsonExporter
from exporters.xlsx_exporter import XLSX_EXTENSIONS, XlsxExporter


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def process_file(input_path: Path, output_dir: Path) -> None:
    config = AnonymizerConfig()
    pipeline = AnonymizationPipeline(config)

    result = pipeline.process_file(input_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem

    txt_out = TxtExporter().export(result, output_dir / f"{stem}_anonymized")
    json_out = JsonExporter().export(result, output_dir / f"{stem}_report")
    xlsx_out = None
    if input_path.suffix.lower() in XLSX_EXTENSIONS:
        xlsx_out = XlsxExporter().export(
            result, output_dir / f"{stem}_anonymized{input_path.suffix}"
        )

    print(f"\nОбработано: {input_path.name}")
    print(f"Найдено сущностей: {result.total_entities}")
    for label, count in result.stats.items():
        label_ru = ENTITY_LABELS_RU.get(label, label)
        print(f"  {label_ru}: {count}")
    print(f"\nРезультат: {txt_out}")
    print(f"Отчёт:    {json_out}")
    if xlsx_out:
        print(f"Excel:    {xlsx_out}")

def main() -> None:
    setup_logging()

    # Frozen exe (установщик Windows): GUI по умолчанию; CLI: DocAnon.exe file.docx
    frozen = getattr(sys, "frozen", False)
    if frozen:
        # cwd = папка рядом с exe (для output/, drag&drop)
        try:
            os.chdir(Path(sys.executable).resolve().parent)
        except Exception:
            pass

    args = [a for a in sys.argv[1:] if a]
    if args and args[0] not in ("--gui", "-g"):
        input_path = Path(args[0])
        if not input_path.exists():
            print(f"Файл не найден: {input_path}")
            sys.exit(1)
        output_dir = Path(args[1]) if len(args) > 1 else Path("./output")
        process_file(input_path, output_dir)
    else:
        from gui.main_window import run_gui
        run_gui()


if __name__ == "__main__":
    main()
