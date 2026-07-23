from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from core.person_canon import person_canonical, surname_key


@dataclass
class EntityRecord:
    original: str
    label: str
    placeholder: str
    first_seen: str = ""
    files: list[str] = field(default_factory=list)
    # C3: канонический ключ (для PERSON); primary — «лучшая» surface-форма для de-anon
    canonical: str = ""
    primary: str = ""
    aliases: list[str] = field(default_factory=list)


class MappingStore:
    """Общий маппинг для всех документов в пакете.

    - Один и тот же surface-текст → один плейсхолдер.
    - PERSON (C3): словоформы / partial FIO сходятся к одному
      ``<PERSON_N>`` через канон pymorphy3.
    """

    SALT_SIZE = 32
    NONCE_SIZE = 12
    KDF_ITERATIONS = 600_000
    MAGIC = b"DOCANON1"

    def __init__(self, *, person_canonical_mapping: bool = True) -> None:
        self.person_canonical_mapping = person_canonical_mapping
        self._entities: dict[str, EntityRecord] = {}
        self._counters: dict[str, int] = {}
        # canon_key → placeholder
        self._person_canon: dict[str, str] = {}
        # surname lemma → placeholder (связь «Иванов» ↔ «Иванов Иван»)
        self._person_surname: dict[str, str] = {}
        # placeholder → primary surface (для reverse / de-anon)
        self._primary: dict[str, str] = {}

    def register(self, original: str, label: str, source_file: str = "") -> str:
        if original in self._entities:
            rec = self._entities[original]
            if source_file and source_file not in rec.files:
                rec.files.append(source_file)
            return rec.placeholder

        if label == "PERSON" and self.person_canonical_mapping:
            return self._register_person(original, source_file)

        return self._register_new(original, label, source_file)

    def _register_new(
        self,
        original: str,
        label: str,
        source_file: str = "",
        *,
        placeholder: str | None = None,
        canonical: str = "",
    ) -> str:
        if placeholder is None:
            counter = self._counters.get(label, 0) + 1
            self._counters[label] = counter
            placeholder = f"<{label}_{counter}>"

        rec = EntityRecord(
            original=original,
            label=label,
            placeholder=placeholder,
            first_seen=datetime.now(timezone.utc).isoformat(),
            files=[source_file] if source_file else [],
            canonical=canonical,
            primary=original,
            aliases=[original],
        )
        self._entities[original] = rec
        if placeholder not in self._primary:
            self._primary[placeholder] = original
        return placeholder

    def _register_person(self, original: str, source_file: str = "") -> str:
        canon = person_canonical(original)
        sur = surname_key(canon)

        placeholder = self._resolve_person_placeholder(canon, sur)

        if placeholder is None:
            placeholder = self._register_new(
                original,
                "PERSON",
                source_file,
                canonical=canon,
            )
            self._person_canon[canon] = placeholder
            if sur:
                # не перезаписываем, если фамилия уже занята другим человеком
                self._person_surname.setdefault(sur, placeholder)
            self._maybe_upgrade_primary(placeholder, original)
            return placeholder

        # alias к существующей персоне
        if original not in self._entities:
            primary = self._primary.get(placeholder, original)
            self._entities[original] = EntityRecord(
                original=original,
                label="PERSON",
                placeholder=placeholder,
                first_seen=datetime.now(timezone.utc).isoformat(),
                files=[source_file] if source_file else [],
                canonical=canon,
                primary=primary,
                aliases=[original],
            )
            # обновить aliases у primary-записи
            if primary in self._entities:
                rec = self._entities[primary]
                if original not in rec.aliases:
                    rec.aliases.append(original)
            if source_file and primary in self._entities:
                pref = self._entities[primary]
                if source_file not in pref.files:
                    pref.files.append(source_file)

        self._person_canon[canon] = placeholder
        if sur:
            self._person_surname.setdefault(sur, placeholder)
        self._maybe_upgrade_primary(placeholder, original)
        return placeholder

    def _resolve_person_placeholder(self, canon: str, sur: str) -> str | None:
        if canon in self._person_canon:
            return self._person_canon[canon]

        # partial: полное ФИО vs уже известная фамилия
        parts = canon.split()
        if len(parts) >= 2 and sur in self._person_surname:
            return self._person_surname[sur]

        # partial: только фамилия, а уже есть полное ФИО с этой фамилией
        if len(parts) == 1 and sur in self._person_surname:
            return self._person_surname[sur]

        # полное канон-совпадение по префиксу: «иванов иван» vs «иванов иван иванович»
        for key, ph in self._person_canon.items():
            if key == canon:
                return ph
            if key.startswith(canon + " ") or canon.startswith(key + " "):
                return ph

        return None

    def _maybe_upgrade_primary(self, placeholder: str, surface: str) -> None:
        """Primary для de-anon: более полное ФИО (больше токенов).

        При равном числе токенов оставляем первую увиденную форму
        (обычно номинатив от NER), а не более длинный падеж.
        """
        current = self._primary.get(placeholder)
        if current is None:
            self._primary[placeholder] = surface
            return
        cur_tokens = len(current.split())
        new_tokens = len(surface.split())
        if new_tokens > cur_tokens:
            self._primary[placeholder] = surface
            for rec in self._entities.values():
                if rec.placeholder == placeholder:
                    rec.primary = surface

    def get_placeholder(self, original: str) -> str | None:
        rec = self._entities.get(original)
        if rec:
            return rec.placeholder
        # C3: попытка по канону без предварительного register
        if self.person_canonical_mapping:
            canon = person_canonical(original)
            sur = surname_key(canon)
            return self._resolve_person_placeholder(canon, sur)
        return None

    def get_original(self, placeholder: str) -> str | None:
        if placeholder in self._primary:
            return self._primary[placeholder]
        for rec in self._entities.values():
            if rec.placeholder == placeholder:
                return rec.primary or rec.original
        return None

    def to_mapping_dict(self) -> dict[str, str]:
        """Все surface-формы → placeholder (для replace в тексте/xlsx)."""
        return {r.original: r.placeholder for r in self._entities.values()}

    def reverse_mapping(self) -> dict[str, str]:
        """placeholder → primary surface (для de-anon; падеж может не сохраниться)."""
        result: dict[str, str] = {}
        for ph, primary in self._primary.items():
            result[ph] = primary
        for rec in self._entities.values():
            if rec.placeholder not in result:
                result[rec.placeholder] = rec.primary or rec.original
        return result

    @property
    def total_entities(self) -> int:
        """Уникальные плейсхолдеры (не surface-алиасы)."""
        return len({r.placeholder for r in self._entities.values()})

    @property
    def total_surfaces(self) -> int:
        return len(self._entities)

    @property
    def entity_types(self) -> dict[str, int]:
        """Число уникальных placeholder'ов по типу."""
        seen: dict[str, set[str]] = {}
        for rec in self._entities.values():
            seen.setdefault(rec.label, set()).add(rec.placeholder)
        return {label: len(phs) for label, phs in seen.items()}

    def save_encrypted(self, password: str, path: Path) -> Path:
        path = path.with_suffix(".mapenc")

        salt = os.urandom(self.SALT_SIZE)
        nonce = os.urandom(self.NONCE_SIZE)

        key = self._derive_key(password, salt)

        payload = {
            "version": 2,
            "created": datetime.now(timezone.utc).isoformat(),
            "total_entities": self.total_entities,
            "entity_types": self.entity_types,
            "mapping": self.to_mapping_dict(),
            "primary": dict(self._primary),
            "person_canon": dict(self._person_canon),
            "person_surname": dict(self._person_surname),
        }
        json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        aesgcm = AESGCM(key)
        encrypted = aesgcm.encrypt(nonce, json_bytes, None)

        with open(path, "wb") as f:
            f.write(self.MAGIC)
            f.write(salt)
            f.write(nonce)
            f.write(encrypted)

        return path

    @classmethod
    def load_encrypted(cls, password: str, path: Path) -> MappingStore:
        with open(path, "rb") as f:
            magic = f.read(len(cls.MAGIC))
            if magic != cls.MAGIC:
                raise ValueError("Неверный формат файла (не .mapenc)")

            salt = f.read(cls.SALT_SIZE)
            nonce = f.read(cls.NONCE_SIZE)
            encrypted = f.read()

        store = cls()
        key = store._derive_key(password, salt)

        aesgcm = AESGCM(key)
        try:
            json_bytes = aesgcm.decrypt(nonce, encrypted, None)
        except Exception:
            raise ValueError("Неверный пароль или повреждённый файл")

        payload = json.loads(json_bytes.decode("utf-8"))

        store._primary = dict(payload.get("primary") or {})
        store._person_canon = dict(payload.get("person_canon") or {})
        store._person_surname = dict(payload.get("person_surname") or {})

        for original, placeholder in payload["mapping"].items():
            inner = placeholder.strip("<>")
            if "_" in inner and inner.rsplit("_", 1)[-1].isdigit():
                label = inner.rsplit("_", 1)[0]
                counter = int(inner.rsplit("_", 1)[1])
            else:
                label = inner
                counter = 0

            primary = store._primary.get(placeholder, original)
            store._entities[original] = EntityRecord(
                original=original,
                label=label,
                placeholder=placeholder,
                primary=primary,
                aliases=[original],
            )
            if counter and (
                label not in store._counters or counter > store._counters[label]
            ):
                store._counters[label] = counter

        # rebuild primary if missing (v1 files)
        if not store._primary:
            for rec in store._entities.values():
                store._maybe_upgrade_primary(rec.placeholder, rec.original)

        return store

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.KDF_ITERATIONS,
        )
        return kdf.derive(password.encode("utf-8"))
