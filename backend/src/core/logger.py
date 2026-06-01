"""Настройка логгера loguru на старте приложения."""

import sys

from loguru import logger

# Убираем дефолтный хендлер loguru.
logger.remove()

# В stdout — JSON для Promtail/Loki.
logger.add(
    sys.stdout,
    serialize=True,  # JSON формат
    level='INFO',
    backtrace=True,  # Полный стек при ошибках
    diagnose=True,  # Значения переменных в трейсбэке (поменять на False в проде, если нужно)
)
