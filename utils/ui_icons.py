"""
Что: утилиты для "анимированных" UI-иконок.
Зачем: визуально оживить интерфейс без тяжелых медиа-файлов.
"""

SPINNER_FRAMES: tuple[str, ...] = ("◐", "◓", "◑", "◒")
SPARK_FRAMES: tuple[str, ...] = ("✨", "💫", "⭐", "🌟")


def spinner_frame(step: int) -> str:
    """
    Возвращает кадр спиннера по индексу шага.
    """
    return SPINNER_FRAMES[step % len(SPINNER_FRAMES)]


def spark_frame(step: int) -> str:
    """
    Возвращает "живой" декоративный символ.
    """
    return SPARK_FRAMES[step % len(SPARK_FRAMES)]
