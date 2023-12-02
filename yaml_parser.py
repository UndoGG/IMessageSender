# -*- coding: windows-1251 -*-
import os
import sys
import yaml
import logging_engine

logger = logging_engine.get_logger()


def read_yaml_file(file_name):
    file_path = file_name
    if getattr(sys, 'frozen', False):
        # Этот код выполняется, если приложение работает как EXE
        file_path = os.path.join(sys.executable, file_name)
    else:
        file_path = os.path.join(os.path.dirname(__file__), file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{file_path}' not found.")

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            res = yaml.safe_load(f)
            return res if res is not None else {}
    except yaml.YAMLError:
        logger.exception('Не удалось прочитать YAML файл!')
        return {}
    except PermissionError:
        logger.error(f'Отказано в доступе к {file_path}!')
        return {}
    except Exception:
        logger.exception(f'Ошибка при чтении {file_path}!')
        return {}


def edit_yaml_file(filename, main_key, sub_key, new_value):
    file_path = filename
    if getattr(sys, 'frozen', False):
        file_path = os.path.join(os.path.dirname(sys.executable), filename)
    else:
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if main_key not in data:
            data[main_key] = {}
        data[main_key][sub_key] = new_value

        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, encoding='utf-8')
    except FileNotFoundError:
        logger.error(f'Файл {file_path} не найден!')
    except PermissionError:
        logger.error(f'Отказано в доступе к {file_path}!')
    except Exception:
        logger.exception(f'Ошибка при записи {file_path}!')


def edit_yaml_file_short(filename, key, new_value):
    file_path = filename
    if getattr(sys, 'frozen', False):
        file_path = os.path.join(os.path.dirname(sys.executable), filename)
    else:
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        data[key] = new_value

        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, encoding='utf-8')
    except FileNotFoundError:
        logger.error(f'Файл {file_path} не найден!')
    except PermissionError:
        logger.error(f'Отказано в доступе к {file_path}!')
    except Exception:
        logger.exception(f'Ошибка при записи {file_path}!')
