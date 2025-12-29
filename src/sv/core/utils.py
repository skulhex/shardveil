from pathlib import Path
import sys

def resource_path(relative_path: str) -> Path:
    """
    Возвращает абсолютный путь к ресурсам.
    Работает и в dev, и в сборках (Nuitka, PyInstaller).
    """
    if getattr(sys, "frozen", False):
        # Standalone бинарник / .app
        base_path = Path(sys.executable).parent.parent / "Resources"
    else:
        # Запуск из исходников, корень проекта на 3 уровня выше utils.py
        base_path = Path(__file__).resolve().parent.parent.parent.parent
    return base_path / relative_path