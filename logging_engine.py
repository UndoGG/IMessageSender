# -*- coding: windows-1251 -*-
import logging
import click
from rich.logging import RichHandler


def start_logger(level) -> logging.Logger:
    """Регистрирует логгер. Используйте только при запуске программы"""
    logging.basicConfig(
        level=level,  # Установите уровень логирования на DEBUG
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(rich_tracebacks=True, tracebacks_suppress=[click], omit_repeated_times=False, markup=True)]
    )

    logger = logging.getLogger("rich")
    logger.info(msg="[green]Logger registered successfully [/]")
    return logger


def get_logger() -> logging.Logger:
    logger = logging.getLogger("rich")
    return logger


def log_critical(message):
    logger = get_logger()
    logger.critical(f"""[bold red]
                КРИТИЧЕСКАЯ ОШИБКА
          ******************************
          {message}
          ******************************
                КРИТИЧЕСКАЯ ОШИБКА
          """)
