# -*- coding: windows-1251 -*-
import os
import sys
import time
from logging_engine import start_logger
import tkinter as tk
from pydantic import ValidationError
from tkinter import ttk, filedialog, messagebox
from tkinter import scrolledtext
from yaml_parser import read_yaml_file
from models import Settings, SendTime
import json
from engine import Engine
import threading

config = read_yaml_file('config.yml')
logger = start_logger(config['log_level'])


# noinspection PyUnboundLocalVariable
class App:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("IMessage Sender")

        self.engine = None

        buttons_style = ttk.Style()
        buttons_style.configure('TNotebook.Tab', padding=(10, 8), font=('Helvetica', 14))

        self.notebook = ttk.Notebook(root_window)
        self.page_main = tk.Frame(self.notebook)
        self.page_message = tk.Frame(self.notebook)
        self.page_profiles = tk.Frame(self.notebook)

        # Добавление страниц в Notebook
        self.notebook.add(self.page_main, text="Главная")
        self.notebook.add(self.page_message, text="Сообщение")
        self.notebook.add(self.page_profiles, text="Профили")

        self.settings = None

        self.numbers_entry = None
        self.start_button = None
        self.pause_button = None
        self.stop_button = None
        self.start_image = None
        self.stop_image = None
        self.pause_image = None
        self.send_delta_from_entry = None
        self.send_delta_to_entry = None
        self.delay_entry = None
        self.messages_counter = None
        self.counter_total = None
        self.pack_main()

        self.message_entry = None
        self.pack_message()

        self.pack_profiles()

        self.notebook.pack(expand=True, fill="both")
        thread = threading.Thread(target=self.check_finished)
        thread.start()

    def parse_phone_number(self, phone_number: str) -> None | str:
        phone_number = phone_number.replace(' ', '').replace('+', '').replace('(', '').replace(')', '').replace('-', '')
        if len(phone_number) not in [11, 12, 13]:
            return
        try:
            int(phone_number)
        except ValueError:
            return
        return phone_number

    def unpack_list(self, items: list, do_space: bool = True):
        out = ''
        for item in items:
            if do_space and item != items[-1]:
                item += ' '
            out += item

        return out

    def import_numbers(self):
        numbers_from_file = self.request_file()
        if not numbers_from_file:
            logger.error('Could not import numbers from file')
            return

        numbers = []
        numbers_failed = []

        for line in list(set(numbers_from_file.split("\n"))):
            parsed = self.parse_phone_number(line)
            if parsed is not None:
                numbers.append((parsed + "\n") if line != list(set(numbers_from_file.split("\n")))[-1] else parsed)
            else:
                numbers_failed.append(line)

        failed = ''
        for number in numbers_failed:
            if len(failed.split('\n')) < 10:
                failed += number + '\n'
            else:
                failed += f'И ещё {len(numbers_failed) - len(failed.split("\n"))} номеров...'
                break

        if len(numbers_failed) > 0:
            messagebox.showwarning('Предупреждение',
                                   f'Некоторые номера были пропущены, так-как они не соответствуют правильному формату:\n{failed}')

        if len(self.unpack_list(numbers)) == 0:
            return

        self.numbers_entry.insert(tk.END, self.unpack_list(numbers, do_space=False) + "\n")

        self.count_numbers(None)

    def check_finished(self):
        if int(self.messages_counter.get()) >= int(self.counter_total.get()) and int(self.counter_total.get()) > 0:
            messagebox.showinfo('Отправка завершена!', 'Все сообщения были отправлены!')
            self.stop()
            self.change_counter(0)
        time.sleep(1)
        self.check_finished()

    def get_settings(self):
        return Settings(message=self.message_entry.get("1.0", tk.END),
                        message_delay=self.delay_entry.get(),
                        send_time=SendTime(from_hour=int(self.send_delta_from_entry.get()),
                                           to_hour=int(self.send_delta_to_entry.get())),
                        numbers=self.numbers_entry.get("1.0", tk.END).split('\n'))

    def start(self):
        if self.engine is not None:
            self.engine._paused = False
            self.start_button: tk.Button
            self.start_button.configure(state='normal')

            self.pause_button: tk.Button
            self.pause_button.configure(state='normal')

            self.stop_button: tk.Button
            self.stop_button.configure(state='normal')
            return
        try:
            self.settings = self.get_settings()
        except ValidationError:
            messagebox.showerror('Ошибка валидатора',
                                 'Не удалось валидировать настройки. Проверьте, что указали все параметры')
            return
        except ValueError:
            messagebox.showerror('Ошибка валидации', 'Часы отправки должны быть числами')
            return

        numbers_parsed = []
        self.settings.numbers = [num for num in self.settings.numbers if num != '']

        for number in self.settings.numbers:
            parsed = self.parse_phone_number(number)
            if not parsed:
                continue
            if len(parsed) not in [11, 12, 13]:
                continue

            numbers_parsed.append(parsed)
        if len(numbers_parsed) != len(self.settings.numbers):
            messagebox.showwarning('Предупреждение',
                                   f'Было пропущено {len(self.settings.numbers) - len(numbers_parsed)} номеров')
        self.settings.numbers = numbers_parsed

        if self.settings.send_time.from_hour > self.settings.send_time.to_hour:
            messagebox.showerror('Ошибка валидации настроек',
                                 'Час, до которого нужно отправлять должен быть меньше, чем с которого нужно')
            return

        self.settings.numbers = list(set(self.settings.numbers))

        try:
            self.engine = Engine(self.settings, counter=self.messages_counter)
        except Exception:
            logger.exception('Unable to launch engine')
            messagebox.showerror('Ошибка запуска движка',
                                 'Движок не был запущен из-за внутренней ошибки. Свяжитесь с разработчиком и сообщите ошибку из консоли')

        logger.info('[cyan]Launching engine')
        thread = threading.Thread(target=self.engine.launch)
        thread.start()
        self.start_button: tk.Button
        self.start_button.configure(state='disabled')

        self.pause_button: tk.Button
        self.pause_button.configure(state='normal')

        self.stop_button: tk.Button
        self.stop_button.configure(state='normal')

    def pause(self):
        if not self.engine:
            return
        self.settings = self.get_settings()
        self.engine.settings = self.get_settings()
        self.engine._paused = True
        self.start_button: tk.Button
        self.start_button.configure(state='normal')

        self.stop_button: tk.Button
        self.stop_button.configure(state='disabled')

        self.pause_button: tk.Button
        self.pause_button.configure(state='disabled')

    def stop(self):
        if not self.engine:
            return
        self.settings = None
        self.change_counter(0)
        self.engine._stop = True
        self.engine = None

        self.start_button: tk.Button
        self.start_button.configure(state='normal')

        self.pause_button: tk.Button
        self.pause_button.configure(state='disabled')

        self.stop_button: tk.Button
        self.stop_button.configure(state='disabled')

    def check_exe(self):
        return getattr(sys, 'frozen', False)

    def join_root_path(self, *paths):
        if self.check_exe():
            path = os.path.join(sys.executable, *paths)
        else:
            path = os.path.join(os.path.dirname(__file__), *paths)
        return path

    def get_asset(self, asset_name: str):
        asset_path = self.join_root_path('assets', asset_name)
        return tk.PhotoImage(file=asset_path)

    def request_file(self, filetypes: list[tuple] = None) -> str | None:
        if not filetypes:
            filetypes = [("Text files", "*.txt"), ("All files", "*.*")]
        file_path = filedialog.askopenfilename(filetypes=filetypes)

        if file_path:
            try:
                with open(file_path) as file:
                    return file.read()
            except Exception as e:
                messagebox.showerror('Ошибка открытия файла', f'Файл открыть не удалось. Ошибка: {e}')
                return

    def export_file(self, filetypes: list[tuple] = None, default_extension: str = '.json') -> str:
        if not filetypes:
            filetypes = [("Text files", "*.txt"), ("All files", "*.*")]
        file_path = filedialog.asksaveasfilename(defaultextension=default_extension,
                                                 filetypes=filetypes)
        return file_path

    def import_message(self):
        message_from_file = self.request_file()
        if not message_from_file:
            return

        self.message_entry.insert(tk.END, message_from_file + "\n")

    def import_profile(self):
        profile_file = self.request_file([("JSON Files", "*.json")])
        if not profile_file:
            return
        try:
            profile_json = json.loads(profile_file)
        except Exception:
            logger.exception('Unable to unmarshal JSON')
            messagebox.showerror('Ошибка импорта', 'Не удалось прочитать JSON файл. Вероятно, он повреждён')
            return
        skip_values = False
        try:
            send_time = profile_json['send_time']
            del profile_json['send_time']
            self.settings = Settings(**profile_json,
                                     send_time=SendTime(from_hour=send_time['from'],
                                                        to_hour=send_time['to']))
        except ValidationError:
            logger.error('Pydantic Validation error')
            skip_values = True
        except KeyError as e:
            logger.exception('Unable to configure settings from json')
            messagebox.showerror('Ошибка настройки',
                                 f'В JSON файле отсутствуют необходимые ключи: {e}. Вероятно, он повреждён')
            return

        self.delay_entry.delete(0, tk.END)
        self.send_delta_from_entry.delete(0, tk.END)
        self.send_delta_to_entry.delete(0, tk.END)
        self.message_entry.delete("1.0", tk.END)
        self.numbers_entry.delete("1.0", tk.END)

        if not skip_values:
            self.delay_entry.insert(0, str(self.settings.message_delay))
            self.send_delta_from_entry.insert(0, str(self.settings.send_time.from_hour))
            self.send_delta_to_entry.insert(0, str(self.settings.send_time.to_hour))
            self.message_entry.insert("1.0", str(self.settings.message))
            self.numbers_entry.insert("1.0",
                                      self.unpack_list([number + '\n' for number in self.settings.numbers],
                                                       do_space=False))
        else:
            if profile_json['message_delay'] != "":
                self.delay_entry.insert(0, str(profile_json['message_delay']))
            if send_time['from'] != "":
                self.send_delta_from_entry.insert(0, str(send_time['from']))
            if send_time['to'] != "":
                self.send_delta_to_entry.insert(0, str(send_time['to']))
            if len([i for i in profile_json['message'].split('\n') if i.replace(' ', '') != '']) > 0:
                self.message_entry.insert("1.0", str(profile_json['message']))
            if len([num for num in profile_json['numbers'] if len(num) in [11, 12, 13]]) > 0:
                self.numbers_entry.insert("1.0",
                                          self.unpack_list([number + '\n' for number in
                                                            [num for num in profile_json['numbers'] if
                                                             len(num) in [11, 12, 13]]],
                                                           do_space=False))

        self.count_numbers(None)

        logger.info("[bold green]Profile successfully imported!")
        self.notebook.select(0)

    def export_profile(self):
        export_path = self.export_file([("JSON files", "*.json")])
        settings = {
            "message": self.message_entry.get("1.0", tk.END),
            "message_delay": self.delay_entry.get(),
            "send_time":
                {
                    "from": self.send_delta_from_entry.get(),
                    "to": self.send_delta_to_entry.get()
                },
            "numbers": self.numbers_entry.get("1.0", tk.END).split('\n')
        }

        if export_path:
            with open(export_path, "w+") as file:
                file.write(json.dumps(settings))
            messagebox.showinfo('Успешно', 'Конфигурация сохранена')

    def pack_profiles(self):
        tk.Label(self.page_profiles, text='Профили', font='Helvetica 15').pack()
        tk.Label(self.page_profiles,
                 text='Вы можете импортировать из файла настройки для быстрой установки в программу, или экспортировать текущие в файл',
                 font='Helvetica 13', wraplength=500).pack()

        import_conf = tk.Button(self.page_profiles, text="Импорт конфигурации",
                                command=lambda: self.import_profile(),
                                background='white', width=20, font='Helvetica 10')
        import_conf.pack(pady=20)

        export_conf = tk.Button(self.page_profiles, text="Экспорт текущей конфигурации",
                                command=lambda: self.export_profile(),
                                background='white', width=30, font='Helvetica 10')
        export_conf.pack(pady=20)

    def pack_message(self):
        tk.Label(self.page_message, text='Сообщение', font='Helvetica 15').pack()

        self.message_entry = scrolledtext.ScrolledText(self.page_message, wrap=tk.WORD,
                                                       highlightbackground="lightblue",
                                                       highlightcolor="lightblue", highlightthickness=4,
                                                       width=75,
                                                       height=18)
        self.message_entry.pack()

        import_message = tk.Button(self.page_message, text="Импорт сообщения", command=lambda: self.import_message(),
                                   background='white', width=20, font='Helvetica 10')
        import_message.pack(pady=20)

        tk.Label(self.page_message, text='Заменители', font='Helvetica 15').pack()
        tk.Label(self.page_message, text='{date} - Дата отправки сообщения', font='Helvetica 10').pack()
        tk.Label(self.page_message, text='{number} - Номер получателя', font='Helvetica 10').pack()

    def change_counter_total(self, value: int | str):
        self.counter_total.configure(state='normal')
        self.counter_total.delete(0, tk.END)
        self.counter_total.insert(0, str(value))
        self.counter_total.configure(state='readonly')

    def change_counter(self, value: int | str):
        self.messages_counter.configure(state='normal')
        self.messages_counter.delete(0, tk.END)
        self.messages_counter.insert(0, str(value))
        self.messages_counter.configure(state='readonly')

    def count_numbers(self, event):
        content = self.numbers_entry.get("1.0", tk.END)
        self.change_counter_total(len(list(set([self.parse_phone_number(i) for i in content.split("\n") if i != '']))))

    def pack_main(self):
        tk.Label(self.page_main, text='Список номеров', font='Helvetica 15').pack()

        self.numbers_entry = scrolledtext.ScrolledText(self.page_main, wrap=tk.WORD,
                                                       highlightbackground="lightblue",
                                                       highlightcolor="lightblue", highlightthickness=4,
                                                       height=10)
        self.numbers_entry.pack()
        self.numbers_entry.bind("<KeyRelease>", lambda i: self.count_numbers(i))

        import_numbers = tk.Button(self.page_main, text="Импорт номеров", command=lambda: self.import_numbers(),
                                   background='white', width=20, font='Helvetica 10')
        import_numbers.pack(pady=20)

        settings_label = tk.Label(self.page_main, text='Настройки отправки', font='Helvetica 15')
        settings_label.pack(pady=20)

        delay_frame = tk.Frame(self.page_main)
        delay_frame.pack()

        delay_label = tk.Label(delay_frame, text='Задержка отправки:', font='Helvetica 12')
        delay_label.pack(side='left')

        def validate_entry(why):
            if why == '':
                return True
            try:
                int(why)
            except ValueError:
                logger.error('Only integers allowed')
                return False
            return True

        def validate_hours_entry(why):
            if why == '':
                return True
            try:
                int(why)
            except ValueError:
                logger.error('Only integers allowed')
                return False

            if int(why) < 0:
                logger.error('Integers lower than 0 is not allowed')
                return False

            if len(why) > 2:
                logger.error('Integers length greater than 2 is not allowed')
                return False

            if int(why) > 23:
                logger.error('Integers higher than 23 is not allowed. Use 0 if you want to set 24 hour')
                return False

            return True

        validate_cmd = (self.page_main.register(validate_entry), '%P')
        validate_hours_cmd = (self.page_main.register(validate_hours_entry), '%P')

        self.delay_entry = tk.Entry(delay_frame, width=6, justify='center', validate='key',
                                    validatecommand=validate_cmd)
        self.delay_entry.pack(side='left', padx=10)

        after_entry_label = tk.Label(delay_frame, text='секунд', font='Helvetica 12')
        after_entry_label.pack(side='left')

        hours_frame = tk.Frame(self.page_main)
        hours_frame.pack()

        send_delta_label = tk.Label(hours_frame, text='Отправлять в часы с:', font='Helvetica 12')
        send_delta_label.pack(side='left')

        self.send_delta_from_entry = tk.Entry(hours_frame, width=4, justify='center', validate='key',
                                              validatecommand=validate_hours_cmd)
        self.send_delta_from_entry.pack(side='left', padx=10)

        after_from_label = tk.Label(hours_frame, text='по', font='Helvetica 12')
        after_from_label.pack(side='left')

        self.send_delta_to_entry = tk.Entry(hours_frame, width=4, justify='center', validate='key',
                                            validatecommand=validate_hours_cmd)
        self.send_delta_to_entry.pack(side='left', padx=10)

        # Sent counter
        counter_label = tk.Label(self.page_main, text='Отправлено:', font='Helvetica 14')
        counter_label.pack(pady=10)

        counter_frame = tk.Frame(self.page_main)
        counter_frame.pack()

        self.messages_counter = tk.Entry(counter_frame, width=4, justify='center', validate='key', font='Helvetica 14',
                                         state='readonly')
        self.messages_counter.pack(side='left', padx=10)

        after_counter_label = tk.Label(counter_frame, text='из', font='Helvetica 13')
        after_counter_label.pack(side='left')

        self.counter_total = tk.Entry(counter_frame, width=4, justify='center', validate='key', font='Helvetica 14', )
        self.counter_total.pack(side='left', padx=10)

        self.change_counter(0)
        self.change_counter_total(0)

        action_frame = tk.Frame(self.page_main, height=3)
        action_frame.pack(fill="both", side='bottom', pady=30)

        self.start_image = self.get_asset('start.png')
        self.stop_image = self.get_asset('stop.png')
        self.pause_image = self.get_asset('pause.png')

        self.start_button = tk.Button(action_frame, image=self.start_image, relief='flat', text="Старт",
                                      command=lambda: self.start(), width=170, height=55, font='Helvetica 10')
        self.pause_button = tk.Button(action_frame, image=self.pause_image, relief='flat', text="Стоп",
                                      command=lambda: self.pause(), width=170, height=55, font='Helvetica 10',
                                      state='disabled')
        self.stop_button = tk.Button(action_frame, image=self.stop_image, relief='flat', text="Стоп",
                                     command=lambda: self.stop(), width=170, height=55, font='Helvetica 10',
                                     state='disabled')
        self.start_button.pack(side='left', padx=30)
        self.pause_button.pack(side='left', padx=30)
        self.stop_button.pack(side='left', padx=30)


if __name__ == "__main__":
    root = tk.Tk()

    root.resizable(width=False, height=False)
    root.attributes('-fullscreen', False)

    window_width = 750
    window_height = 650
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    x_coordinate = (screen_width - window_width) // 2
    y_coordinate = (screen_height - window_height) // 2

    root.geometry(f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

    app = App(root)
    root.mainloop()
