# -*- coding: utf-8 -*-
import json

from models import Settings
from logging_engine import get_logger
import time
from datetime import datetime
import sys
import tkinter as tk
import random

logger = get_logger()
sys.setrecursionlimit(10_000_000)


class Engine:
    def __init__(self, settings: Settings, counter: tk.Entry):
        self.settings = settings
        self.counter_obj = counter

        self.emojis = ["😁", "👋", "🤑", "😎", "✅", "🤪", "🥸"]

        logger.debug(f'Engine Settings: {self.settings}')

        self._paused = False
        self._stop = False

    def save_number(self, number):
        current_history = None
        try:
            with open('history.json') as history:
                current_history = json.loads(history.read())
        except FileNotFoundError:
            current_history = {'history': []}

        current_history['history'].append(number)
        with open('history.json', mode='w+') as history:
            json.dump(current_history, history)

    def validate(self, number):
        if self._paused:
            logger.info('[bold yellow]Paused')

            def check_paused():
                if self._paused:
                    time.sleep(1)
                    check_paused()
                else:
                    logger.info('[bold green]Resumed')

            check_paused()
            return True

        try:
            with open('history.json') as history:
                history = json.loads(history.read())['history']
        except FileNotFoundError:
            history = []

        if str(number) in [str(i) for i in history]:
            logger.error(f'Skipped [cyan]{number}[/cyan]: Already sent to this number before')
            return False

        if datetime.now().hour not in range(self.settings.send_time.from_hour, self.settings.send_time.to_hour + 1):
            logger.error(f'Skipped [cyan]{number}[/cyan]: Out of send time')
            return False
        return True

    def send(self, phone, content):
        phone = "+" + str(phone)
        content = content.replace('{date}', f"{datetime.now():%y-%m-%d}").replace("{number}", phone)
        logger.info(f'[yellow]Messaging {phone}')
        try:
            applescript = f"""
                tell application "Messages"
                    set targetService to 1st service whose service type = iMessage
                    set targetBuddy to buddy "{phone}" of targetService
                    send "{content}" to targetBuddy
                end tell
            """
            # subprocess.run(['osascript', '-e', applescript])
            logger.info(f'[bold green]Message sent to {phone}')
        except Exception:
            logger.exception('Unable to send message')

        time.sleep(2)

        try:
            applescript = f"""
                tell application "Messages"
                    set targetService to 1st service whose service type = SMS
                    set targetBuddy to buddy "{phone}" of targetService
                    send "{content}" to targetBuddy
                end tell
            """
            # subprocess.run(['osascript', '-e', applescript])
            logger.info(f'[bold green]SMS sent to {phone}')
        except Exception:
            logger.exception('Unable to send SMS')

    def parse_message(self, message: str):
        parsed = ''
        added_spaces = 0
        for index, i in enumerate(list(message)):
            if i != ' ':
                parsed += i
                continue
            if i == ' ' and index not in [0, len(list(message)) - 1] and (
                    ' ' in [list(message)[index + 1], list(message)[index - 1]]):
                continue
            if random.randint(1, 2) == 1:
                added_spaces += 1
                parsed += i + ' '
            else:
                parsed += i

        logger.debug(f'[green]Added {added_spaces} random spaces')

        if random.randint(1, 4) != 1:
            logger.debug('[green]Emojis will be added!')
            emojis_to_add = ''
            emojis_added = 0
            for emoji in self.emojis:
                if random.randint(1, 3) == 1:
                    emojis_added += 1
                    emojis_to_add += emoji
            if emojis_added == 0:
                logger.debug('[bold red]No emojis was added, but it should be!')
                logger.debug('[bold cyan]Adding one random emoji to make it at least 1 emoji happened')
                emojis_to_add += self.emojis[random.randint(0, len(self.emojis) - 1)]
            else:
                logger.debug(f'[green]Added {emojis_added} emojis')

            parsed += self.unpack_list([i + ' ' for i in emojis_to_add])
        else:
            logger.debug("[bold red]Emojis will not be added. (Its 25% chanced)")
        return parsed

    def unpack_list(self, items: list, do_space: bool = True, do_comma: bool = False):
        out = ''
        for item in items:
            if do_comma and item != items[-1]:
                item += ', '
            elif do_space and item != items[-1]:
                item += ' '
            out += item

        return out

    def launch(self):
        for number_i, number in enumerate(self.settings.numbers):
            def validate():
                if not self.validate(number):
                    time.sleep(1)
                    validate()

            validate()

            rnd_index = random.randint(0, len(self.settings.messages) - 1)
            message = self.settings.messages[rnd_index]

            logger.info(f"[cyan]Selected random message with index: {rnd_index}")

            if message.startswith('\n'):
                message = message[1:]
            if message.endswith('\n'):
                message = message[:-1]
            if message.startswith('\n'):
                message = message[1:]
            if message.endswith('\n'):
                message = message[:-1]
            message = message.lstrip()

            message = self.parse_message(message)
            if message.startswith('\n'):
                message = message[1:]
            if message.endswith('\n'):
                message = message[:-1]
            if message.startswith('\n'):
                message = message[1:]
            if message.endswith('\n'):
                message = message[:-1]
            message = message.lstrip()

            self.send(number, message)
            print(message)
            self.save_number(number)

            if self._stop:
                break
            self.counter_obj.configure(state='normal')
            self.counter_obj.delete(0, tk.END)
            self.counter_obj.insert(0, str(number_i + 1))
            self.counter_obj.configure(state='readonly')
            logger.debug(f'Sleeping for message delay {number}')

            to_sleep = random.randint(self.settings.message_delay.from_seconds, self.settings.message_delay.to_seconds)

            logger.info(f'[cyan]Sleep period randomly selected: {to_sleep}')

            time.sleep(to_sleep)
