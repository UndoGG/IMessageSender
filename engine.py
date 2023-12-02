# -*- coding: windows-1251 -*-
import threading

from models import Settings
from logging_engine import get_logger
import time
from datetime import datetime
import subprocess
import tkinter as tk


logger = get_logger()


class Engine:
    def __init__(self, settings: Settings, counter: tk.Entry):
        self.settings = settings
        self.counter_obj = counter
        logger.debug(f'Engine Settings: {self.settings}')

        self._paused = False
        self._stop = False

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

        print(datetime.now().hour)

        if datetime.now().hour not in range(self.settings.send_time.from_hour, self.settings.send_time.to_hour + 1):
            logger.error(f'Skipped [cyan]{number}[/cyan]: Out of send time')
            return False
        return True

    def send(self, phone, content):
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
            subprocess.run(['osascript', '-e', applescript])
            logger.info(f'[bold green]Message sent to {phone}')
        except Exception:
            logger.exception('Unable to send message')

    def launch(self):
        for number_i, number in enumerate(self.settings.numbers):
            def validate():
                if not self.validate(number):
                    time.sleep(1)
                    validate()
            validate()
            self.send(number, self.settings.message)
            if self._stop:
                break
            self.counter_obj.configure(state='normal')
            self.counter_obj.delete(0, tk.END)
            self.counter_obj.insert(0, str(number_i + 1))
            self.counter_obj.configure(state='readonly')
            logger.debug(f'Sleeping for message delay {number}')
            time.sleep(self.settings.message_delay)
