from __future__ import annotations

from pathlib import Path

from core.mapping import MappingStore


class DeAnonymizer:
    """Восстановление обезличенных данных по зашифрованному маппингу."""

    def restore_text(self, text: str, reverse_mapping: dict[str, str]) -> str:
        result = text
        sorted_items = sorted(
            reverse_mapping.items(), key=lambda item: len(item[0]), reverse=True
        )
        for placeholder, original in sorted_items:
            result = result.replace(placeholder, original)
        return result

    def restore_batch(
        self,
        texts: list[str],
        reverse_mapping: dict[str, str],
    ) -> list[str]:
        return [self.restore_text(t, reverse_mapping) for t in texts]

    def restore_from_file(
        self,
        text: str,
        mapenc_path: Path,
        password: str,
    ) -> str:
        store = MappingStore.load_encrypted(password, mapenc_path)
        reverse = store.reverse_mapping()
        return self.restore_text(text, reverse)

    def restore_file(
        self,
        input_path: Path,
        mapenc_path: Path,
        password: str,
        output_path: Path | None = None,
    ) -> Path:
        text = input_path.read_text(encoding="utf-8")
        restored = self.restore_from_file(text, mapenc_path, password)

        if output_path is None:
            output_path = input_path.with_stem(input_path.stem + "_restored")
        output_path.write_text(restored, encoding="utf-8")
        return output_path
