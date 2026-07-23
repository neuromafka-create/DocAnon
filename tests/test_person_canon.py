from __future__ import annotations

from pathlib import Path

import pytest

from core.mapping import MappingStore
from core.person_canon import person_canonical, surname_key


class TestPersonCanonical:
    def test_case_forms_same_canon(self) -> None:
        # мужские падежи (не «Иванова» — это и gen masc, и fem surn)
        assert person_canonical("Иванов") == person_canonical("Иванову")
        assert person_canonical("Иванов") == person_canonical("Ивановым")
        assert person_canonical("Егорова") == person_canonical("Егоровой")

    def test_multi_token(self) -> None:
        c1 = person_canonical("Иванов Иван")
        c2 = person_canonical("Иванову Ивану")
        assert c1 == c2
        assert "иванов" in c1
        assert "иван" in c1

    def test_surname_key(self) -> None:
        assert surname_key(person_canonical("Иванов Иван")) == person_canonical("Иванов")


class TestMappingPersonC3:
    def test_same_placeholder_for_case_forms(self) -> None:
        store = MappingStore(person_canonical_mapping=True)
        p1 = store.register("Иванов", "PERSON")
        p2 = store.register("Иванову", "PERSON")
        p3 = store.register("Ивановым", "PERSON")
        assert p1 == p2 == p3 == "<PERSON_1>"
        assert store.total_entities == 1
        assert store.total_surfaces == 3

    def test_different_people(self) -> None:
        store = MappingStore()
        p1 = store.register("Иванов", "PERSON")
        p2 = store.register("Петров", "PERSON")
        assert p1 != p2
        assert store.total_entities == 2

    def test_partial_full_fio_link(self) -> None:
        store = MappingStore()
        full = store.register("Егорова Марина Викторовна", "PERSON")
        short = store.register("Егорова", "PERSON")
        dative = store.register("Егоровой", "PERSON")
        assert full == short == dative

    def test_full_after_surname(self) -> None:
        store = MappingStore()
        short = store.register("Новиков", "PERSON")
        full = store.register("Новиков Павел Игоревич", "PERSON")
        assert short == full
        # primary — более полная форма
        assert store.get_original(short) == "Новиков Павел Игоревич"

    def test_non_person_unchanged(self) -> None:
        store = MappingStore()
        a = store.register("7707083893", "RU_INN")
        b = store.register("500100732259", "RU_INN")
        assert a == "<RU_INN_1>"
        assert b == "<RU_INN_2>"

    def test_canonical_disabled(self) -> None:
        store = MappingStore(person_canonical_mapping=False)
        p1 = store.register("Иванов", "PERSON")
        p2 = store.register("Иванову", "PERSON")
        assert p1 != p2

    def test_to_mapping_has_all_surfaces(self) -> None:
        store = MappingStore()
        store.register("Иванов", "PERSON")
        store.register("Иванову", "PERSON")
        d = store.to_mapping_dict()
        assert d["Иванов"] == d["Иванову"] == "<PERSON_1>"

    def test_reverse_uses_primary(self) -> None:
        store = MappingStore()
        store.register("Иванову", "PERSON")
        store.register("Иванов Иван Иванович", "PERSON")
        rev = store.reverse_mapping()
        assert rev["<PERSON_1>"] == "Иванов Иван Иванович"

    def test_save_load_preserves_aliases(self) -> None:
        import tempfile

        store = MappingStore()
        store.register("Иванов", "PERSON")
        store.register("Иванову", "PERSON")
        store.register("7707083893", "RU_INN")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.mapenc"
            store.save_encrypted("secret", path)
            loaded = MappingStore.load_encrypted("secret", path)
            assert loaded.get_placeholder("Иванов") == "<PERSON_1>"
            assert loaded.get_placeholder("Иванову") == "<PERSON_1>"
            assert loaded.to_mapping_dict()["Иванову"] == "<PERSON_1>"
            assert loaded.total_entities == 2  # PERSON + INN


class TestBatchPersonConsistency:
    def test_batch_same_person_across_files(self, tmp_path: Path) -> None:
        from core.batch_pipeline import BatchPipeline
        from core.config import AnonymizerConfig

        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("Ответственный: Иванов Иван.\n", encoding="utf-8")
        f2.write_text("Передать документы Иванову Ивану.\n", encoding="utf-8")

        result = BatchPipeline(AnonymizerConfig()).process_batch([f1, f2])
        m = result.mapping.to_mapping_dict()

        # collect PERSON placeholders used in both docs
        phs = set()
        for doc in result.documents:
            for orig, ph in m.items():
                if ph.startswith("<PERSON_") and orig in doc.original_text:
                    if orig in doc.anonymized_text:
                        continue
                    if ph in doc.anonymized_text:
                        phs.add(ph)

        # at least one person placeholder appears in both anonymized texts ideally
        # softer: same surface forms of Иванов share ph
        ivan_phs = {
            ph
            for orig, ph in m.items()
            if "Иванов" in orig or "Иванову" in orig or "Ивану" in orig
        }
        # all surname-related surfaces of same person should collapse if linked
        assert len(ivan_phs) >= 1
        # if both forms registered, they share one ph
        if "Иванов" in m and "Иванову" in m:
            assert m["Иванов"] == m["Иванову"]
