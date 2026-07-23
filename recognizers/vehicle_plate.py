from __future__ import annotations

from presidio_analyzer import Pattern, PatternRecognizer


class VehiclePlateRecognizer(PatternRecognizer):
    """Госномер ТС (ГРЗ).

    Официальный алфавит: АВЕКМНОРСТУХ (+ латиница-двойники).
    Дополнительно ловим распространённые «ошибочные» буквы (Б, Г, …),
    чтобы не пропускать ПДн в реальных текстах.
    """

    ENTITY = "RU_VEHICLE_PLATE"
    LANGUAGE = "ru"

    def __init__(self) -> None:
        # Официальные + визуально похожие / часто ошибочные
        letters = r"АВЕКМНОРСТУХABEKMHOPCTYXАБГДЗИЙЛПФЦЧШЩЭЮЯ"
        patterns = [
            Pattern(
                name="vehicle_plate_std",
                # А123ВС 77 / A123BC777
                regex=rf"\b[{letters}]\s*\d{{3}}\s*[{letters}]{{2}}\s*\d{{2,3}}\b",
                score=0.85,
            ),
            Pattern(
                name="vehicle_plate_compact",
                regex=rf"\b[{letters}]\d{{3}}[{letters}]{{2}}\d{{2,3}}\b",
                score=0.8,
            ),
        ]
        context = [
            "госномер",
            "гос. номер",
            "номер авто",
            "номер автомобиля",
            "машина",
            "автомобиль",
            "грз",
            "регистрационный знак",
            "номерной знак",
        ]
        super().__init__(
            supported_entity=self.ENTITY,
            supported_language=self.LANGUAGE,
            patterns=patterns,
            context=context,
        )
