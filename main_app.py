"""
AI Manager Desktop Application v8.0
Менеджер нейросетей для Windows

Поддерживаемые нейросети:
- OpenAI GPT (GPT-4, GPT-3.5)
- Anthropic Claude (Claude 3)
- Google Gemini
- DeepSeek
- Groq (Llama, Mixtral)
- Mistral AI

Автор: DeskTop AI Team
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import threading
import os
import sys
import json
import requests
import socket
import time
from datetime import datetime
from typing import Dict, Optional, Callable
import webbrowser

# Версия приложения
APP_VERSION = "8.0"
APP_NAME = "AI Manager"


class AIProvider:
    """Базовый класс для AI провайдеров"""

    def __init__(self, name: str, api_key: str = ""):
        self.name = name
        self.api_key = api_key
        self.is_connected = False

    def test_connection(self) -> bool:
        raise NotImplementedError

    def query(self, question: str) -> str:
        raise NotImplementedError


class OpenAIProvider(AIProvider):
    """OpenAI GPT провайдер"""

    def __init__(self, api_key: str = ""):
        super().__init__("OpenAI GPT", api_key)
        self.base_url = "https://api.openai.com/v1"
        self.model = "gpt-4o-mini"

    def test_connection(self) -> bool:
        if not self.api_key:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.base_url}/models", headers=headers, timeout=10)
            self.is_connected = response.status_code == 200
            return self.is_connected
        except:
            self.is_connected = False
            return False

    def query(self, question: str) -> str:
        if not self.api_key:
            return "Ошибка: Введите API ключ OpenAI"

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Вы - полезный ассистент. Отвечайте на русском языке."},
                    {"role": "user", "content": question}
                ],
                "max_tokens": 2000,
                "temperature": 0.7
            }
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            elif response.status_code == 401:
                return "Ошибка: Неверный API ключ OpenAI"
            elif response.status_code == 429:
                return "Ошибка: Превышен лимит запросов OpenAI"
            else:
                return f"Ошибка OpenAI: {response.status_code} - {response.text}"
        except requests.exceptions.Timeout:
            return "Ошибка: Таймаут запроса к OpenAI"
        except Exception as e:
            return f"Ошибка OpenAI: {str(e)}"


class AnthropicProvider(AIProvider):
    """Anthropic Claude провайдер"""

    def __init__(self, api_key: str = ""):
        super().__init__("Anthropic Claude", api_key)
        self.base_url = "https://api.anthropic.com/v1"
        self.model = "claude-3-haiku-20240307"

    def test_connection(self) -> bool:
        if not self.api_key:
            return False
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            # Простой тест - отправляем минимальный запрос
            data = {
                "model": self.model,
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hi"}]
            }
            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=data,
                timeout=15
            )
            self.is_connected = response.status_code == 200
            return self.is_connected
        except:
            self.is_connected = False
            return False

    def query(self, question: str) -> str:
        if not self.api_key:
            return "Ошибка: Введите API ключ Anthropic"

        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": question}]
            }
            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                return response.json()["content"][0]["text"]
            elif response.status_code == 401:
                return "Ошибка: Неверный API ключ Anthropic"
            elif response.status_code == 429:
                return "Ошибка: Превышен лимит запросов Anthropic"
            else:
                return f"Ошибка Anthropic: {response.status_code} - {response.text}"
        except requests.exceptions.Timeout:
            return "Ошибка: Таймаут запроса к Anthropic"
        except Exception as e:
            return f"Ошибка Anthropic: {str(e)}"


class GeminiProvider(AIProvider):
    """Google Gemini провайдер"""

    def __init__(self, api_key: str = ""):
        super().__init__("Gemini", api_key)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "gemini-1.5-flash"

    def test_connection(self) -> bool:
        if not self.api_key:
            return False
        try:
            url = f"{self.base_url}/models?key={self.api_key}"
            response = requests.get(url, timeout=10)
            self.is_connected = response.status_code == 200
            return self.is_connected
        except:
            self.is_connected = False
            return False

    def query(self, question: str) -> str:
        if not self.api_key:
            return "Ошибка: Введите API ключ Gemini"

        try:
            url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [
                    {
                        "parts": [
                            {"text": question}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 2000
                }
            }
            response = requests.post(url, headers=headers, json=data, timeout=60)

            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    return result["candidates"][0]["content"]["parts"][0]["text"]
                return "Ошибка: Пустой ответ от Gemini"
            elif response.status_code == 400:
                return "Ошибка: Неверный запрос к Gemini"
            elif response.status_code == 403:
                return "Ошибка: Неверный API ключ Gemini или недостаточно прав"
            elif response.status_code == 429:
                return "Ошибка: Превышен лимит запросов Gemini"
            else:
                return f"Ошибка Gemini: {response.status_code} - {response.text}"
        except requests.exceptions.Timeout:
            return "Ошибка: Таймаут запроса к Gemini"
        except Exception as e:
            return f"Ошибка Gemini: {str(e)}"


class DeepSeekProvider(AIProvider):
    """DeepSeek провайдер"""

    def __init__(self, api_key: str = ""):
        super().__init__("DeepSeek", api_key)
        self.base_url = "https://api.deepseek.com/v1"
        self.model = "deepseek-chat"

    def test_connection(self) -> bool:
        if not self.api_key:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.base_url}/models", headers=headers, timeout=10)
            self.is_connected = response.status_code == 200
            return self.is_connected
        except:
            self.is_connected = False
            return False

    def query(self, question: str) -> str:
        if not self.api_key:
            return "Ошибка: Введите API ключ DeepSeek"

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Вы - полезный ассистент. Отвечайте на русском языке."},
                    {"role": "user", "content": question}
                ],
                "max_tokens": 2000,
                "temperature": 0.7
            }
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            elif response.status_code == 401:
                return "Ошибка: Неверный API ключ DeepSeek"
            elif response.status_code == 402:
                return "Ошибка: Недостаточно средств на балансе DeepSeek"
            elif response.status_code == 429:
                return "Ошибка: Превышен лимит запросов DeepSeek"
            else:
                return f"Ошибка DeepSeek: {response.status_code} - {response.text}"
        except requests.exceptions.Timeout:
            return "Ошибка: Таймаут запроса к DeepSeek"
        except Exception as e:
            return f"Ошибка DeepSeek: {str(e)}"


class GroqProvider(AIProvider):
    """Groq провайдер"""

    def __init__(self, api_key: str = ""):
        super().__init__("Groq", api_key)
        self.base_url = "https://api.groq.com/openai/v1"
        self.models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768"
        ]

    def test_connection(self) -> bool:
        if not self.api_key:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.base_url}/models", headers=headers, timeout=10)
            self.is_connected = response.status_code == 200
            return self.is_connected
        except:
            self.is_connected = False
            return False

    def query(self, question: str) -> str:
        if not self.api_key:
            return "Ошибка: Введите API ключ Groq"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        last_error = ""
        for model in self.models:
            try:
                data = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Вы - полезный ассистент. Отвечайте на русском языке."},
                        {"role": "user", "content": question}
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.7
                }
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60
                )

                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                elif response.status_code == 401:
                    return "Ошибка: Неверный API ключ Groq"
                elif response.status_code == 429:
                    return "Ошибка: Превышен лимит запросов Groq"
                elif response.status_code == 400:
                    last_error = f"Модель {model} недоступна"
                    continue
                else:
                    last_error = f"{response.status_code} - {response.text}"
                    continue
            except requests.exceptions.Timeout:
                last_error = "Таймаут"
                continue
            except Exception as e:
                last_error = str(e)
                continue

        return f"Ошибка Groq: {last_error}"


class MistralProvider(AIProvider):
    """Mistral AI провайдер"""

    def __init__(self, api_key: str = ""):
        super().__init__("Mistral AI", api_key)
        self.base_url = "https://api.mistral.ai/v1"
        self.model = "mistral-small-latest"

    def test_connection(self) -> bool:
        if not self.api_key:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.base_url}/models", headers=headers, timeout=10)
            self.is_connected = response.status_code == 200
            return self.is_connected
        except:
            self.is_connected = False
            return False

    def query(self, question: str) -> str:
        if not self.api_key:
            return "Ошибка: Введите API ключ Mistral AI"

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": question}
                ],
                "max_tokens": 2000,
                "temperature": 0.7
            }
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            elif response.status_code == 401:
                return "Ошибка: Неверный API ключ Mistral AI"
            elif response.status_code == 429:
                return "Ошибка: Превышен лимит запросов Mistral AI"
            else:
                return f"Ошибка Mistral AI: {response.status_code} - {response.text}"
        except requests.exceptions.Timeout:
            return "Ошибка: Таймаут запроса к Mistral AI"
        except Exception as e:
            return f"Ошибка Mistral AI: {str(e)}"


class AIManagerApp:
    """Главное окно приложения"""

    # Список поддерживаемых нейросетей
    SUPPORTED_NETWORKS = [
        "OpenAI GPT",
        "Anthropic Claude",
        "Gemini",
        "DeepSeek",
        "Groq",
        "Mistral AI"
    ]

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1100x800")
        self.root.minsize(900, 700)

        # Устанавливаем иконку (если есть)
        self._set_icon()

        # Конфигурация
        self.config_file = "config.json"
        self.config = self._load_config()

        # Инициализация провайдеров
        self.providers: Dict[str, AIProvider] = {}
        self._init_providers()

        # Статусы подключений
        self.connection_status = {name: False for name in self.SUPPORTED_NETWORKS}

        # Переменные UI
        self.api_key_vars = {}
        self.network_vars = {}
        self.status_labels = {}
        self.status_text_vars = {}

        # Создаем интерфейс
        self._setup_styles()
        self._create_ui()

        # Загружаем конфигурацию в UI
        self._load_config_to_ui()

        # Проверяем соединения в фоне
        self.root.after(1000, self._check_connections_background)

    def _set_icon(self):
        """Установка иконки приложения"""
        try:
            # Для Windows .ico файл
            if sys.platform == 'win32':
                icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
        except:
            pass

    def _load_config(self) -> dict:
        """Загрузка конфигурации"""
        default_config = {
            "api_keys": {
                "openai": "",
                "anthropic": "",
                "gemini": "",
                "deepseek": "",
                "groq": "",
                "mistral": ""
            },
            "telegram": {
                "bot_token": "",
                "chat_id": ""
            },
            "settings": {
                "last_directory": "",
                "theme": "default",
                "language": "ru"
            }
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Мержим с дефолтными значениями
                    for key in default_config:
                        if key in loaded:
                            if isinstance(default_config[key], dict):
                                default_config[key].update(loaded[key])
                            else:
                                default_config[key] = loaded[key]
                    return default_config
            except:
                pass

        return default_config

    def _save_config(self) -> bool:
        """Сохранение конфигурации"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    def _init_providers(self):
        """Инициализация провайдеров AI"""
        self.providers = {
            "OpenAI GPT": OpenAIProvider(self.config["api_keys"].get("openai", "")),
            "Anthropic Claude": AnthropicProvider(self.config["api_keys"].get("anthropic", "")),
            "Gemini": GeminiProvider(self.config["api_keys"].get("gemini", "")),
            "DeepSeek": DeepSeekProvider(self.config["api_keys"].get("deepseek", "")),
            "Groq": GroqProvider(self.config["api_keys"].get("groq", "")),
            "Mistral AI": MistralProvider(self.config["api_keys"].get("mistral", ""))
        }

    def _setup_styles(self):
        """Настройка стилей"""
        style = ttk.Style()

        # Пробуем установить тему
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')

        # Настройка стилей
        style.configure("Title.TLabel", font=('Segoe UI', 14, 'bold'))
        style.configure("Header.TLabel", font=('Segoe UI', 11, 'bold'))
        style.configure("Status.TLabel", font=('Segoe UI', 9))
        style.configure("Success.TLabel", foreground='green')
        style.configure("Error.TLabel", foreground='red')
        style.configure("Accent.TButton", font=('Segoe UI', 10, 'bold'))

    def _create_ui(self):
        """Создание пользовательского интерфейса"""
        # Создаем notebook (вкладки)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Вкладка 1: Чат
        self._create_chat_tab()

        # Вкладка 2: Настройки API
        self._create_api_tab()

        # Вкладка 3: Пакетная обработка
        self._create_batch_tab()

        # Вкладка 4: Статус соединений
        self._create_status_tab()

        # Вкладка 5: История
        self._create_history_tab()

        # Вкладка 6: О программе
        self._create_about_tab()

    def _create_chat_tab(self):
        """Создание вкладки чата"""
        self.chat_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.chat_tab, text="Чат")

        # Верхняя панель - выбор нейросети
        top_frame = ttk.Frame(self.chat_tab)
        top_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(top_frame, text="Нейросеть:", style="Header.TLabel").pack(side='left', padx=(0, 10))

        self.chat_network_var = tk.StringVar(value=self.SUPPORTED_NETWORKS[0])
        network_combo = ttk.Combobox(
            top_frame,
            textvariable=self.chat_network_var,
            values=self.SUPPORTED_NETWORKS,
            state='readonly',
            width=25
        )
        network_combo.pack(side='left', padx=(0, 20))

        # Индикатор статуса
        self.chat_status_label = ttk.Label(top_frame, text="", style="Status.TLabel")
        self.chat_status_label.pack(side='left')

        # Область чата
        chat_frame = ttk.LabelFrame(self.chat_tab, text="Диалог", padding=10)
        chat_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Текстовое поле для чата
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap='word',
            font=('Consolas', 10),
            state='disabled'
        )
        self.chat_display.pack(fill='both', expand=True)

        # Настройка тегов для форматирования
        self.chat_display.tag_configure('user', foreground='blue', font=('Consolas', 10, 'bold'))
        self.chat_display.tag_configure('assistant', foreground='green')
        self.chat_display.tag_configure('error', foreground='red')
        self.chat_display.tag_configure('system', foreground='gray', font=('Consolas', 9, 'italic'))

        # Поле ввода
        input_frame = ttk.Frame(self.chat_tab)
        input_frame.pack(fill='x', padx=10, pady=5)

        self.chat_input = scrolledtext.ScrolledText(
            input_frame,
            wrap='word',
            font=('Consolas', 10),
            height=4
        )
        self.chat_input.pack(side='left', fill='x', expand=True, padx=(0, 10))
        self.chat_input.bind('<Control-Return>', lambda e: self._send_chat_message())

        # Кнопки
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(side='right', fill='y')

        ttk.Button(btn_frame, text="Отправить\n(Ctrl+Enter)",
                   command=self._send_chat_message, style="Accent.TButton").pack(fill='x', pady=2)
        ttk.Button(btn_frame, text="Очистить",
                   command=self._clear_chat).pack(fill='x', pady=2)

    def _create_api_tab(self):
        """Создание вкладки настроек API"""
        self.api_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.api_tab, text="Настройки API")

        # Scrollable frame
        canvas = tk.Canvas(self.api_tab)
        scrollbar = ttk.Scrollbar(self.api_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Привязка прокрутки колесом мыши
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # API настройки для каждой нейросети
        api_configs = [
            ("OpenAI GPT", "openai", "https://platform.openai.com/api-keys",
             "Модели: GPT-4o, GPT-4, GPT-3.5-turbo"),
            ("Anthropic Claude", "anthropic", "https://console.anthropic.com/",
             "Модели: Claude 3.5 Sonnet, Claude 3 Haiku"),
            ("Gemini", "gemini", "https://aistudio.google.com/apikey",
             "Модели: Gemini 1.5 Flash, Gemini 1.5 Pro"),
            ("DeepSeek", "deepseek", "https://platform.deepseek.com/",
             "Модели: DeepSeek-Chat, DeepSeek-Coder"),
            ("Groq", "groq", "https://console.groq.com/keys",
             "Модели: Llama 3.3, Mixtral (быстрые!)"),
            ("Mistral AI", "mistral", "https://console.mistral.ai/api-keys/",
             "Модели: Mistral Small, Mistral Large")
        ]

        for name, key_name, url, description in api_configs:
            frame = ttk.LabelFrame(scrollable_frame, text=name, padding=10)
            frame.pack(fill='x', padx=10, pady=5)

            # Описание
            ttk.Label(frame, text=description, font=('Segoe UI', 8, 'italic'),
                      foreground='gray').grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 5))

            # API ключ
            ttk.Label(frame, text="API ключ:").grid(row=1, column=0, sticky='w')

            key_var = tk.StringVar()
            self.api_key_vars[key_name] = key_var

            entry = ttk.Entry(frame, textvariable=key_var, width=60, show="*")
            entry.grid(row=1, column=1, padx=5, pady=2)

            # Кнопки
            btn_frame = ttk.Frame(frame)
            btn_frame.grid(row=1, column=2, padx=5)

            ttk.Button(btn_frame, text="Показать", width=10,
                       command=lambda e=entry: self._toggle_password(e)).pack(side='left', padx=2)
            ttk.Button(btn_frame, text="Получить ключ", width=12,
                       command=lambda u=url: webbrowser.open(u)).pack(side='left', padx=2)

        # Telegram настройки
        telegram_frame = ttk.LabelFrame(scrollable_frame, text="Telegram (опционально)", padding=10)
        telegram_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(telegram_frame, text="Токен бота:").grid(row=0, column=0, sticky='w')
        self.telegram_token_var = tk.StringVar()
        ttk.Entry(telegram_frame, textvariable=self.telegram_token_var, width=60).grid(
            row=0, column=1, padx=5, pady=2)

        ttk.Label(telegram_frame, text="Chat ID:").grid(row=1, column=0, sticky='w')
        self.telegram_chat_id_var = tk.StringVar()
        ttk.Entry(telegram_frame, textvariable=self.telegram_chat_id_var, width=60).grid(
            row=1, column=1, padx=5, pady=2)

        # Кнопка сохранения
        save_frame = ttk.Frame(scrollable_frame)
        save_frame.pack(fill='x', padx=10, pady=20)

        ttk.Button(save_frame, text="Сохранить настройки",
                   command=self._save_api_settings, style="Accent.TButton").pack(side='left', padx=5)
        ttk.Button(save_frame, text="Проверить все соединения",
                   command=self._check_all_connections).pack(side='left', padx=5)

    def _create_batch_tab(self):
        """Создание вкладки пакетной обработки"""
        self.batch_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.batch_tab, text="Пакетная обработка")

        # Выбор файла
        file_frame = ttk.LabelFrame(self.batch_tab, text="Файл с вопросом", padding=10)
        file_frame.pack(fill='x', padx=10, pady=5)

        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=80).pack(side='left', fill='x', expand=True, padx=(0, 10))
        ttk.Button(file_frame, text="Выбрать...", command=self._select_file).pack(side='left')

        # Директория сохранения
        save_frame = ttk.LabelFrame(self.batch_tab, text="Директория сохранения", padding=10)
        save_frame.pack(fill='x', padx=10, pady=5)

        self.save_path_var = tk.StringVar()
        ttk.Entry(save_frame, textvariable=self.save_path_var, width=80).pack(side='left', fill='x', expand=True, padx=(0, 10))
        ttk.Button(save_frame, text="Выбрать...", command=self._select_save_dir).pack(side='left')

        # Выбор нейросетей
        networks_frame = ttk.LabelFrame(self.batch_tab, text="Нейросети для запроса", padding=10)
        networks_frame.pack(fill='x', padx=10, pady=5)

        for i, name in enumerate(self.SUPPORTED_NETWORKS):
            var = tk.BooleanVar(value=True)
            self.network_vars[name] = var
            cb = ttk.Checkbutton(networks_frame, text=name, variable=var)
            cb.grid(row=i // 3, column=i % 3, sticky='w', padx=20, pady=2)

        # Кнопки управления
        button_frame = ttk.Frame(self.batch_tab)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="Отправить запросы",
                   command=self._send_batch_requests, style="Accent.TButton").pack(side='left', padx=5)
        ttk.Button(button_frame, text="Очистить лог",
                   command=self._clear_batch_log).pack(side='left', padx=5)

        # Прогресс
        self.batch_progress = ttk.Progressbar(self.batch_tab, mode='indeterminate')
        self.batch_progress.pack(fill='x', padx=10, pady=5)

        # Лог
        log_frame = ttk.LabelFrame(self.batch_tab, text="Лог выполнения", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.batch_log = scrolledtext.ScrolledText(log_frame, wrap='word', height=15)
        self.batch_log.pack(fill='both', expand=True)

    def _create_status_tab(self):
        """Создание вкладки статуса соединений"""
        self.status_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.status_tab, text="Статус")

        # Заголовок
        ttk.Label(self.status_tab, text="Статус подключения к API",
                  style="Title.TLabel").pack(pady=20)

        # Статусы
        status_frame = ttk.Frame(self.status_tab)
        status_frame.pack(fill='both', expand=True, padx=20)

        for i, name in enumerate(self.SUPPORTED_NETWORKS):
            row_frame = ttk.Frame(status_frame)
            row_frame.pack(fill='x', pady=10)

            # Название
            ttk.Label(row_frame, text=name, width=20, anchor='w',
                      font=('Segoe UI', 11)).pack(side='left', padx=10)

            # Индикатор (Canvas)
            canvas = tk.Canvas(row_frame, width=24, height=24, highlightthickness=0)
            canvas.pack(side='left', padx=10)
            canvas.create_oval(2, 2, 22, 22, fill='gray', outline='')
            self.status_labels[name] = canvas

            # Текст статуса
            status_var = tk.StringVar(value="Не проверено")
            self.status_text_vars[name] = status_var
            ttk.Label(row_frame, textvariable=status_var, width=20).pack(side='left', padx=10)

            # Кнопка проверки
            ttk.Button(row_frame, text="Проверить", width=12,
                       command=lambda n=name: self._check_single_connection(n)).pack(side='left', padx=10)

        # Кнопка проверки всех
        ttk.Button(self.status_tab, text="Проверить все соединения",
                   command=self._check_all_connections, style="Accent.TButton").pack(pady=30)

    def _create_history_tab(self):
        """Создание вкладки истории"""
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="История")

        # Панель управления
        control_frame = ttk.Frame(self.history_tab)
        control_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(control_frame, text="Обновить", command=self._load_history).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Отправить в Telegram",
                   command=self._send_to_telegram).pack(side='left', padx=5)

        # Список файлов
        list_frame = ttk.Frame(self.history_tab)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Левая панель - список
        left_frame = ttk.LabelFrame(list_frame, text="Файлы", padding=5)
        left_frame.pack(side='left', fill='y', padx=(0, 5))

        self.history_listbox = tk.Listbox(left_frame, width=40, height=20)
        scrollbar = ttk.Scrollbar(left_frame, command=self.history_listbox.yview)
        self.history_listbox.configure(yscrollcommand=scrollbar.set)
        self.history_listbox.pack(side='left', fill='y')
        scrollbar.pack(side='right', fill='y')
        self.history_listbox.bind('<<ListboxSelect>>', self._on_history_select)

        # Правая панель - содержимое
        right_frame = ttk.LabelFrame(list_frame, text="Содержимое", padding=5)
        right_frame.pack(side='left', fill='both', expand=True)

        self.history_text = scrolledtext.ScrolledText(right_frame, wrap='word')
        self.history_text.pack(fill='both', expand=True)

    def _create_about_tab(self):
        """Создание вкладки 'О программе'"""
        self.about_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.about_tab, text="О программе")

        # Центрированный контент
        center_frame = ttk.Frame(self.about_tab)
        center_frame.place(relx=0.5, rely=0.5, anchor='center')

        ttk.Label(center_frame, text=f"{APP_NAME}",
                  font=('Segoe UI', 24, 'bold')).pack(pady=10)
        ttk.Label(center_frame, text=f"Версия {APP_VERSION}",
                  font=('Segoe UI', 14)).pack(pady=5)

        ttk.Label(center_frame, text="Менеджер нейросетей для Windows",
                  font=('Segoe UI', 11)).pack(pady=20)

        # Поддерживаемые нейросети
        networks_text = "Поддерживаемые нейросети:\n" + "\n".join(f"  - {n}" for n in self.SUPPORTED_NETWORKS)
        ttk.Label(center_frame, text=networks_text,
                  font=('Segoe UI', 10), justify='left').pack(pady=20)

        ttk.Label(center_frame, text="2024-2025 DeskTop AI Team",
                  font=('Segoe UI', 9, 'italic'), foreground='gray').pack(pady=20)

    # ==================== Методы работы ====================

    def _toggle_password(self, entry):
        """Переключение видимости пароля"""
        current = entry.cget('show')
        entry.config(show='' if current == '*' else '*')

    def _load_config_to_ui(self):
        """Загрузка конфигурации в UI"""
        # API ключи
        key_mapping = {
            "openai": "openai",
            "anthropic": "anthropic",
            "gemini": "gemini",
            "deepseek": "deepseek",
            "groq": "groq",
            "mistral": "mistral"
        }

        for ui_key, config_key in key_mapping.items():
            if ui_key in self.api_key_vars:
                self.api_key_vars[ui_key].set(self.config["api_keys"].get(config_key, ""))

        # Telegram
        self.telegram_token_var.set(self.config["telegram"].get("bot_token", ""))
        self.telegram_chat_id_var.set(self.config["telegram"].get("chat_id", ""))

        # Последняя директория
        if self.config["settings"].get("last_directory"):
            self.save_path_var.set(self.config["settings"]["last_directory"])

    def _save_api_settings(self):
        """Сохранение настроек API"""
        # API ключи
        key_mapping = {
            "openai": "openai",
            "anthropic": "anthropic",
            "gemini": "gemini",
            "deepseek": "deepseek",
            "groq": "groq",
            "mistral": "mistral"
        }

        for ui_key, config_key in key_mapping.items():
            if ui_key in self.api_key_vars:
                self.config["api_keys"][config_key] = self.api_key_vars[ui_key].get()

        # Telegram
        self.config["telegram"]["bot_token"] = self.telegram_token_var.get()
        self.config["telegram"]["chat_id"] = self.telegram_chat_id_var.get()

        # Обновляем провайдеры
        self._update_providers()

        # Сохраняем
        if self._save_config():
            messagebox.showinfo("Успех", "Настройки сохранены!")
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить настройки")

    def _update_providers(self):
        """Обновление API ключей в провайдерах"""
        provider_keys = {
            "OpenAI GPT": self.api_key_vars.get("openai", tk.StringVar()).get(),
            "Anthropic Claude": self.api_key_vars.get("anthropic", tk.StringVar()).get(),
            "Gemini": self.api_key_vars.get("gemini", tk.StringVar()).get(),
            "DeepSeek": self.api_key_vars.get("deepseek", tk.StringVar()).get(),
            "Groq": self.api_key_vars.get("groq", tk.StringVar()).get(),
            "Mistral AI": self.api_key_vars.get("mistral", tk.StringVar()).get()
        }

        for name, key in provider_keys.items():
            if name in self.providers:
                self.providers[name].api_key = key

    def _check_connections_background(self):
        """Фоновая проверка соединений"""
        thread = threading.Thread(target=self._check_all_connections_thread, daemon=True)
        thread.start()

    def _check_all_connections_thread(self):
        """Поток проверки всех соединений"""
        self._update_providers()
        for name in self.SUPPORTED_NETWORKS:
            self._check_single_connection_internal(name)
            time.sleep(0.5)

    def _check_all_connections(self):
        """Проверка всех соединений с UI"""
        self._add_batch_log("Проверяем соединения...")
        thread = threading.Thread(target=self._check_all_connections_thread, daemon=True)
        thread.start()

    def _check_single_connection(self, name: str):
        """Проверка одного соединения"""
        thread = threading.Thread(
            target=self._check_single_connection_internal,
            args=(name,),
            daemon=True
        )
        thread.start()

    def _check_single_connection_internal(self, name: str):
        """Внутренняя проверка соединения"""
        if name not in self.providers:
            return

        # Обновляем ключ
        key_mapping = {
            "OpenAI GPT": "openai",
            "Anthropic Claude": "anthropic",
            "Gemini": "gemini",
            "DeepSeek": "deepseek",
            "Groq": "groq",
            "Mistral AI": "mistral"
        }

        if key_mapping[name] in self.api_key_vars:
            self.providers[name].api_key = self.api_key_vars[key_mapping[name]].get()

        # Проверяем
        status = self.providers[name].test_connection()
        self.connection_status[name] = status

        # Обновляем UI
        self.root.after(0, lambda: self._update_status_ui(name, status))

    def _update_status_ui(self, name: str, status: bool):
        """Обновление UI статуса"""
        if name in self.status_labels:
            canvas = self.status_labels[name]
            canvas.delete("all")

            if status:
                canvas.create_oval(2, 2, 22, 22, fill='green', outline='')
                self.status_text_vars[name].set("Подключено")
            else:
                canvas.create_oval(2, 2, 22, 22, fill='red', outline='')
                self.status_text_vars[name].set("Ошибка")

    # ==================== Чат ====================

    def _send_chat_message(self):
        """Отправка сообщения в чат"""
        message = self.chat_input.get("1.0", "end-1c").strip()
        if not message:
            return

        network = self.chat_network_var.get()
        if network not in self.providers:
            self._add_chat_message("Ошибка: Выбрана неизвестная нейросеть", "error")
            return

        # Обновляем ключ
        key_mapping = {
            "OpenAI GPT": "openai",
            "Anthropic Claude": "anthropic",
            "Gemini": "gemini",
            "DeepSeek": "deepseek",
            "Groq": "groq",
            "Mistral AI": "mistral"
        }

        if key_mapping[network] in self.api_key_vars:
            self.providers[network].api_key = self.api_key_vars[key_mapping[network]].get()

        # Очищаем поле ввода
        self.chat_input.delete("1.0", "end")

        # Добавляем сообщение пользователя
        self._add_chat_message(f"Вы: {message}", "user")
        self._add_chat_message(f"[{network}] Думает...", "system")

        # Отправляем в отдельном потоке
        thread = threading.Thread(
            target=self._process_chat_message,
            args=(network, message),
            daemon=True
        )
        thread.start()

    def _process_chat_message(self, network: str, message: str):
        """Обработка сообщения чата"""
        try:
            response = self.providers[network].query(message)
            self.root.after(0, lambda: self._show_chat_response(network, response))
        except Exception as e:
            self.root.after(0, lambda: self._show_chat_response(network, f"Ошибка: {str(e)}", True))

    def _show_chat_response(self, network: str, response: str, is_error: bool = False):
        """Показ ответа в чате"""
        # Удаляем "Думает..."
        self.chat_display.config(state='normal')
        content = self.chat_display.get("1.0", "end")
        lines = content.split('\n')
        new_lines = [l for l in lines if "Думает..." not in l]
        self.chat_display.delete("1.0", "end")
        self.chat_display.insert("1.0", '\n'.join(new_lines))
        self.chat_display.config(state='disabled')

        # Добавляем ответ
        tag = "error" if is_error or response.startswith("Ошибка") else "assistant"
        self._add_chat_message(f"{network}: {response}", tag)

    def _add_chat_message(self, message: str, tag: str = None):
        """Добавление сообщения в чат"""
        self.chat_display.config(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert("end", f"[{timestamp}] {message}\n\n", tag)
        self.chat_display.see("end")
        self.chat_display.config(state='disabled')

    def _clear_chat(self):
        """Очистка чата"""
        self.chat_display.config(state='normal')
        self.chat_display.delete("1.0", "end")
        self.chat_display.config(state='disabled')

    # ==================== Пакетная обработка ====================

    def _select_file(self):
        """Выбор файла"""
        filename = filedialog.askopenfilename(
            title="Выберите файл с вопросом",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if filename:
            self.file_path_var.set(filename)

    def _select_save_dir(self):
        """Выбор директории сохранения"""
        directory = filedialog.askdirectory(title="Выберите папку для сохранения")
        if directory:
            self.save_path_var.set(directory)
            self.config["settings"]["last_directory"] = directory
            self._save_config()

    def _send_batch_requests(self):
        """Отправка пакетных запросов"""
        question_file = self.file_path_var.get()
        save_dir = self.save_path_var.get()

        if not question_file or not os.path.exists(question_file):
            messagebox.showerror("Ошибка", "Выберите файл с вопросом")
            return

        if not save_dir or not os.path.exists(save_dir):
            messagebox.showerror("Ошибка", "Выберите папку для сохранения")
            return

        # Читаем вопрос
        try:
            with open(question_file, 'r', encoding='utf-8') as f:
                question = f.read().strip()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")
            return

        if not question:
            messagebox.showerror("Ошибка", "Файл пустой")
            return

        # Выбранные сети
        selected = [name for name, var in self.network_vars.items() if var.get()]
        if not selected:
            messagebox.showerror("Ошибка", "Выберите хотя бы одну нейросеть")
            return

        # Обновляем провайдеры
        self._update_providers()

        # Запуск в потоке
        self.batch_progress.start()
        thread = threading.Thread(
            target=self._process_batch_requests,
            args=(question, selected, save_dir, question_file),
            daemon=True
        )
        thread.start()

    def _process_batch_requests(self, question: str, networks: list, save_dir: str, original_file: str):
        """Обработка пакетных запросов"""
        self._add_batch_log(f"Начинаем обработку для {len(networks)} нейросетей...")

        responses = {}
        for network in networks:
            self._add_batch_log(f"Запрос к {network}...")

            if network not in self.providers:
                self._add_batch_log(f"  Ошибка: провайдер {network} не найден")
                continue

            try:
                response = self.providers[network].query(question)
                if response.startswith("Ошибка"):
                    self._add_batch_log(f"  {response}")
                else:
                    responses[network] = response
                    self._add_batch_log(f"  Получен ответ ({len(response)} символов)")
            except Exception as e:
                self._add_batch_log(f"  Ошибка: {str(e)}")

        # Сохраняем результаты
        if responses:
            filepath = self._save_responses(responses, save_dir, original_file)
            if filepath:
                self._add_batch_log(f"Результаты сохранены: {filepath}")

                # Отправляем в Telegram
                bot_token = self.telegram_token_var.get()
                chat_id = self.telegram_chat_id_var.get()
                if bot_token and chat_id:
                    self._send_file_to_telegram(filepath, bot_token, chat_id)
        else:
            self._add_batch_log("Не получено ни одного ответа")

        self.root.after(0, self.batch_progress.stop)
        self._add_batch_log("Готово!")

    def _save_responses(self, responses: dict, save_dir: str, original_file: str) -> Optional[str]:
        """Сохранение ответов"""
        try:
            base_name = os.path.splitext(os.path.basename(original_file))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{base_name}_answers_{timestamp}.txt"
            filepath = os.path.join(save_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Исходный файл: {original_file}\n")
                f.write("=" * 60 + "\n\n")

                for network, response in responses.items():
                    f.write(f"--- {network} ---\n")
                    f.write(response + "\n")
                    f.write("=" * 60 + "\n\n")

            return filepath
        except Exception as e:
            self._add_batch_log(f"Ошибка сохранения: {e}")
            return None

    def _add_batch_log(self, message: str):
        """Добавление в лог пакетной обработки"""
        def _add():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.batch_log.insert("end", f"[{timestamp}] {message}\n")
            self.batch_log.see("end")
        self.root.after(0, _add)

    def _clear_batch_log(self):
        """Очистка лога"""
        self.batch_log.delete("1.0", "end")

    # ==================== История ====================

    def _load_history(self):
        """Загрузка истории"""
        save_dir = self.save_path_var.get()
        if not save_dir or not os.path.exists(save_dir):
            return

        self.history_listbox.delete(0, "end")

        try:
            files = [f for f in os.listdir(save_dir)
                     if f.endswith('.txt') and ('_answer' in f or '_answers_' in f)]
            files.sort(reverse=True)

            for f in files:
                self.history_listbox.insert("end", f)
        except:
            pass

    def _on_history_select(self, event):
        """Обработка выбора файла истории"""
        selection = self.history_listbox.curselection()
        if not selection:
            return

        filename = self.history_listbox.get(selection[0])
        save_dir = self.save_path_var.get()
        filepath = os.path.join(save_dir, filename)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            self.history_text.delete("1.0", "end")
            self.history_text.insert("1.0", content)
        except Exception as e:
            self.history_text.delete("1.0", "end")
            self.history_text.insert("1.0", f"Ошибка чтения: {e}")

    # ==================== Telegram ====================

    def _send_to_telegram(self):
        """Отправка выбранного файла в Telegram"""
        selection = self.history_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите файл")
            return

        bot_token = self.telegram_token_var.get()
        chat_id = self.telegram_chat_id_var.get()

        if not bot_token or not chat_id:
            messagebox.showerror("Ошибка", "Настройте Telegram API")
            return

        filename = self.history_listbox.get(selection[0])
        save_dir = self.save_path_var.get()
        filepath = os.path.join(save_dir, filename)

        if self._send_file_to_telegram(filepath, bot_token, chat_id):
            messagebox.showinfo("Успех", "Файл отправлен в Telegram")
        else:
            messagebox.showerror("Ошибка", "Не удалось отправить файл")

    def _send_file_to_telegram(self, filepath: str, bot_token: str, chat_id: str) -> bool:
        """Отправка файла в Telegram"""
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
            with open(filepath, 'rb') as f:
                response = requests.post(
                    url,
                    files={'document': f},
                    data={'chat_id': chat_id},
                    timeout=30
                )
            return response.status_code == 200
        except:
            return False


def main():
    """Точка входа"""
    root = tk.Tk()

    # Устанавливаем DPI awareness для Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = AIManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
