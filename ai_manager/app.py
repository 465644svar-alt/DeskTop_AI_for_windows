# НАЗНАЧЕНИЕ ФАЙЛА: Модуль приложения AI Manager: UI-логика, события, маршрутизация действий пользователя.
"""
AI Manager Desktop Application v11.0
Main Application Module with thread-safe UI and modular architecture
"""

import customtkinter as ctk  # ПОЯСНЕНИЕ: импортируется модуль customtkinter as ctk.
from tkinter import filedialog, messagebox  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
import tkinter as tk  # ПОЯСНЕНИЕ: импортируется модуль tkinter as tk.
import threading  # ПОЯСНЕНИЕ: импортируется модуль threading.
import os  # ПОЯСНЕНИЕ: импортируется модуль os.
import json  # ПОЯСНЕНИЕ: импортируется модуль json.
import contextlib  # ПОЯСНЕНИЕ: импортируется модуль contextlib.
from datetime import datetime  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from typing import Dict, List, Tuple, Optional  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from concurrent.futures import ThreadPoolExecutor, as_completed  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.

from . import __version__, __app_name__  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from .services import UIQueue, UIMessage, MessageType, get_logger, get_branch_manager  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from .providers import (  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
    PROVIDER_REGISTRY, PROVIDER_INFO, create_provider,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    OpenAIProvider, AnthropicProvider, GeminiProvider,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    DeepSeekProvider, GroqProvider, MistralProvider  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
from .utils import SecureKeyStorage, get_key_storage  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from .ui.widgets import APIKeyCard, ModernSwitch, ProviderMetricsCard  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.

# Theme settings
ctk.set_appearance_mode("dark")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
ctk.set_default_color_theme("blue")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.


# ЛОГИЧЕСКИЙ БЛОК: класс `AIManagerApp(ctk.CTk)` — объединяет состояние и поведение подсистемы.
class AIManagerApp(ctk.CTk):  # ПОЯСНЕНИЕ: объявляется класс AIManagerApp.
    """Main application window"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.

    # ЛОГИЧЕСКИЙ БЛОК: функция `__init__` — выполняет отдельный шаг бизнес-логики.
    def __init__(self):  # ПОЯСНЕНИЕ: объявляется функция __init__ с параметрами из сигнатуры.
        """Описание: функция `__init__`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        super().__init__()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # App state
        self.is_processing = False  # ПОЯСНЕНИЕ: обновляется значение переменной self.is_processing.
        self.output_dir = "responses"  # ПОЯСНЕНИЕ: обновляется значение переменной self.output_dir.
        os.makedirs(self.output_dir, exist_ok=True)  # ПОЯСНЕНИЕ: обновляется значение переменной os.makedirs(self.output_dir, exist_ok.

        # Services
        self.logger = get_logger()  # ПОЯСНЕНИЕ: обновляется значение переменной self.logger.
        self.branch_manager = get_branch_manager()  # ПОЯСНЕНИЕ: обновляется значение переменной self.branch_manager.
        self.key_storage = get_key_storage()  # ПОЯСНЕНИЕ: обновляется значение переменной self.key_storage.

        # Thread-safe UI queue
        self.ui_queue = UIQueue(poll_interval=50)  # ПОЯСНЕНИЕ: обновляется значение переменной self.ui_queue.

        # Initialize providers
        self.providers: Dict[str, any] = {}  # ПОЯСНЕНИЕ: обновляется значение переменной self.providers: Dict[str, any].
        self._init_providers()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # UI state
        self.provider_switches: Dict[str, ModernSwitch] = {}  # ПОЯСНЕНИЕ: обновляется значение переменной self.provider_switches: Dict[str, ModernSwitch].
        self.api_cards: Dict[str, APIKeyCard] = {}  # ПОЯСНЕНИЕ: обновляется значение переменной self.api_cards: Dict[str, APIKeyCard].
        self.metrics_cards: Dict[str, ProviderMetricsCard] = {}  # ПОЯСНЕНИЕ: обновляется значение переменной self.metrics_cards: Dict[str, ProviderMetricsCard].

        # Window setup
        self.title(f"{__app_name__} v{__version__}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.geometry("1200x800")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.minsize(900, 600)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Build UI
        self._create_ui()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Load saved config
        self._load_config()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Start UI queue polling
        self.ui_queue.start_polling(self, self._handle_ui_message)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Migrate keys from old config if needed
        self._migrate_keys()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_init_providers` — выполняет отдельный шаг бизнес-логики.
    def _init_providers(self):  # ПОЯСНЕНИЕ: объявляется функция _init_providers с параметрами из сигнатуры.
        """Initialize all AI providers"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for key in PROVIDER_REGISTRY:  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            self.providers[key] = create_provider(key)  # ПОЯСНЕНИЕ: обновляется значение переменной self.providers[key].

    # ЛОГИЧЕСКИЙ БЛОК: функция `_migrate_keys` — выполняет отдельный шаг бизнес-логики.
    def _migrate_keys(self):  # ПОЯСНЕНИЕ: объявляется функция _migrate_keys с параметрами из сигнатуры.
        """Migrate API keys from plain config to secure storage"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        config_path = "config.json"  # ПОЯСНЕНИЕ: обновляется значение переменной config_path.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if os.path.exists(config_path):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            migrated = self.key_storage.migrate_from_config(config_path)  # ПОЯСНЕНИЕ: обновляется значение переменной migrated.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if migrated > 0:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                self.logger.logger.info(f"Migrated {migrated} API keys to secure storage")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_create_ui` — выполняет отдельный шаг бизнес-логики.
    def _create_ui(self):  # ПОЯСНЕНИЕ: объявляется функция _create_ui с параметрами из сигнатуры.
        """Create main UI"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # Main container
        self.grid_rowconfigure(0, weight=1)  # ПОЯСНЕНИЕ: обновляется значение переменной self.grid_rowconfigure(0, weight.
        self.grid_columnconfigure(0, weight=1)  # ПОЯСНЕНИЕ: обновляется значение переменной self.grid_columnconfigure(0, weight.

        # Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=15)  # ПОЯСНЕНИЕ: обновляется значение переменной self.tabview.
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)  # ПОЯСНЕНИЕ: обновляется значение переменной self.tabview.grid(row.

        # Create tabs
        self.tab_chat = self.tabview.add("Chat")  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_chat.
        self.tab_settings = self.tabview.add("Settings")  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_settings.
        self.tab_logs = self.tabview.add("Logs")  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_logs.
        self.tab_metrics = self.tabview.add("Metrics")  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_metrics.

        self._create_chat_tab()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self._create_settings_tab()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self._create_logs_tab()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self._create_metrics_tab()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_create_chat_tab` — выполняет отдельный шаг бизнес-логики.
    def _create_chat_tab(self):  # ПОЯСНЕНИЕ: объявляется функция _create_chat_tab с параметрами из сигнатуры.
        """Create chat tab with provider selection"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.tab_chat.grid_rowconfigure(1, weight=1)  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_chat.grid_rowconfigure(1, weight.
        self.tab_chat.grid_columnconfigure(0, weight=1)  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_chat.grid_columnconfigure(0, weight.

        # Header with provider toggles
        header = ctk.CTkFrame(self.tab_chat, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной header.
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))  # ПОЯСНЕНИЕ: обновляется значение переменной header.grid(row.

        ctk.CTkLabel(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            header, text="Ask AI",  # ПОЯСНЕНИЕ: обновляется значение переменной header, text.
            font=ctk.CTkFont(size=20, weight="bold")  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        ).pack(side="left")  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

        # Status label
        self.status_label = ctk.CTkLabel(  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_label.
            header, text="Ready",  # ПОЯСНЕНИЕ: обновляется значение переменной header, text.
            font=ctk.CTkFont(size=12), text_color="gray"  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.status_label.pack(side="right")  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_label.pack(side.

        # Provider toggles
        toggles_frame = ctk.CTkFrame(self.tab_chat, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной toggles_frame.
        toggles_frame.grid(row=0, column=0, sticky="e", pady=(0, 10), padx=(0, 100))  # ПОЯСНЕНИЕ: обновляется значение переменной toggles_frame.grid(row.

        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for key, info in PROVIDER_INFO.items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            switch = ModernSwitch(  # ПОЯСНЕНИЕ: обновляется значение переменной switch.
                toggles_frame, info["name"], info["color"]  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            switch.pack(side="left", padx=5)  # ПОЯСНЕНИЕ: обновляется значение переменной switch.pack(side.
            self.provider_switches[key] = switch  # ПОЯСНЕНИЕ: обновляется значение переменной self.provider_switches[key].

        # Chat display
        self.chat_display = ctk.CTkTextbox(  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.
            self.tab_chat, corner_radius=12,  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_chat, corner_radius.
            font=ctk.CTkFont(family="Consolas", size=12),  # ПОЯСНЕНИЕ: обновляется значение переменной font.
            state="disabled"  # ПОЯСНЕНИЕ: обновляется значение переменной state.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.chat_display.grid(row=1, column=0, sticky="nsew", pady=(0, 10))  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.grid(row.

        # Input area
        input_frame = ctk.CTkFrame(self.tab_chat, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной input_frame.
        input_frame.grid(row=2, column=0, sticky="ew")  # ПОЯСНЕНИЕ: обновляется значение переменной input_frame.grid(row.
        input_frame.grid_columnconfigure(0, weight=1)  # ПОЯСНЕНИЕ: обновляется значение переменной input_frame.grid_columnconfigure(0, weight.

        self.chat_input = ctk.CTkTextbox(  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_input.
            input_frame, height=100, corner_radius=12,  # ПОЯСНЕНИЕ: обновляется значение переменной input_frame, height.
            font=ctk.CTkFont(size=13)  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0, 10))  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_input.grid(row.

        # Keyboard shortcuts for chat input
        self.chat_input.bind("<Return>", self._handle_enter_key)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.chat_input.bind("<Shift-Return>", self._handle_shift_enter)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self._setup_chat_bindings()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Buttons
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame.
        btn_frame.grid(row=0, column=1)  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame.grid(row.

        self.send_btn = ctk.CTkButton(  # ПОЯСНЕНИЕ: обновляется значение переменной self.send_btn.
            btn_frame, text="Send", width=100, height=40,  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame, text.
            corner_radius=10, font=ctk.CTkFont(size=14, weight="bold"),  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
            command=self._send_query  # ПОЯСНЕНИЕ: обновляется значение переменной command.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.send_btn.pack(pady=(0, 4))  # ПОЯСНЕНИЕ: обновляется значение переменной self.send_btn.pack(pady.

        ctk.CTkButton(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            btn_frame, text="Clear", width=100, height=30,  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame, text.
            corner_radius=10, fg_color="gray30",  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
            command=self._clear_chat  # ПОЯСНЕНИЕ: обновляется значение переменной command.
        ).pack(pady=(0, 4))  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(pady.

        ctk.CTkButton(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            btn_frame, text="New Chat", width=100, height=30,  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame, text.
            corner_radius=10, fg_color="#e74c3c", hover_color="#c0392b",  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
            command=self._new_chat  # ПОЯСНЕНИЕ: обновляется значение переменной command.
        ).pack(pady=(0, 4))  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(pady.

        ctk.CTkButton(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            btn_frame, text="Save Chat", width=100, height=30,  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame, text.
            corner_radius=10, fg_color="#9b59b6", hover_color="#8e44ad",  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
            command=self._save_chat_to_file  # ПОЯСНЕНИЕ: обновляется значение переменной command.
        ).pack()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Progress bar
        self.progress = ctk.CTkProgressBar(self.tab_chat, mode="indeterminate", height=3)  # ПОЯСНЕНИЕ: обновляется значение переменной self.progress.

        # Streaming indicator
        self.streaming_label = ctk.CTkLabel(  # ПОЯСНЕНИЕ: обновляется значение переменной self.streaming_label.
            self.tab_chat, text="",  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_chat, text.
            font=ctk.CTkFont(size=11), text_color="#27ae60"  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Branches panel
        self._create_branches_panel()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_create_branches_panel` — выполняет отдельный шаг бизнес-логики.
    def _create_branches_panel(self):  # ПОЯСНЕНИЕ: объявляется функция _create_branches_panel с параметрами из сигнатуры.
        """Create conversation branches management panel"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        branches_frame = ctk.CTkFrame(self.tab_chat, corner_radius=12)  # ПОЯСНЕНИЕ: обновляется значение переменной branches_frame.
        branches_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))  # ПОЯСНЕНИЕ: обновляется значение переменной branches_frame.grid(row.

        # Header
        branches_header = ctk.CTkFrame(branches_frame, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной branches_header.
        branches_header.pack(fill="x", padx=10, pady=(10, 5))  # ПОЯСНЕНИЕ: обновляется значение переменной branches_header.pack(fill.

        ctk.CTkLabel(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            branches_header, text="Conversation Branches",  # ПОЯСНЕНИЕ: обновляется значение переменной branches_header, text.
            font=ctk.CTkFont(size=14, weight="bold")  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        ).pack(side="left")  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

        self.current_branch_label = ctk.CTkLabel(  # ПОЯСНЕНИЕ: обновляется значение переменной self.current_branch_label.
            branches_header, text="Current: None",  # ПОЯСНЕНИЕ: обновляется значение переменной branches_header, text.
            font=ctk.CTkFont(size=11), text_color="gray"  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.current_branch_label.pack(side="right")  # ПОЯСНЕНИЕ: обновляется значение переменной self.current_branch_label.pack(side.

        # Controls
        branches_controls = ctk.CTkFrame(branches_frame, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной branches_controls.
        branches_controls.pack(fill="x", padx=10, pady=(0, 10))  # ПОЯСНЕНИЕ: обновляется значение переменной branches_controls.pack(fill.

        self.branches_combo = ctk.CTkComboBox(  # ПОЯСНЕНИЕ: обновляется значение переменной self.branches_combo.
            branches_controls, width=250, height=32,  # ПОЯСНЕНИЕ: обновляется значение переменной branches_controls, width.
            values=["No saved branches"], state="readonly"  # ПОЯСНЕНИЕ: обновляется значение переменной values.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.branches_combo.pack(side="left", padx=(0, 10))  # ПОЯСНЕНИЕ: обновляется значение переменной self.branches_combo.pack(side.

        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for text, color, cmd in [  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            ("Save", "#27ae60", self._save_branch),  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            ("Load", "#3498db", self._load_branch),  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            ("Delete", "#e74c3c", self._delete_branch),  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            ("Refresh", "gray30", self._refresh_branches_list)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        ]:  # ПОЯСНЕНИЕ: начинается новый логический блок кода.
            ctk.CTkButton(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                branches_controls, text=text, width=70, height=32,  # ПОЯСНЕНИЕ: обновляется значение переменной branches_controls, text.
                corner_radius=8, fg_color=color,  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
                command=cmd  # ПОЯСНЕНИЕ: обновляется значение переменной command.
            ).pack(side="left", padx=(0, 5))  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

        self._refresh_branches_list()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_create_settings_tab` — выполняет отдельный шаг бизнес-логики.
    def _create_settings_tab(self):  # ПОЯСНЕНИЕ: объявляется функция _create_settings_tab с параметрами из сигнатуры.
        """Create settings tab with API key cards"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        scroll = ctk.CTkScrollableFrame(self.tab_settings, corner_radius=0)  # ПОЯСНЕНИЕ: обновляется значение переменной scroll.
        scroll.pack(fill="both", expand=True)  # ПОЯСНЕНИЕ: обновляется значение переменной scroll.pack(fill.

        ctk.CTkLabel(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            scroll, text="API Keys Configuration",  # ПОЯСНЕНИЕ: обновляется значение переменной scroll, text.
            font=ctk.CTkFont(size=20, weight="bold")  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        ).pack(anchor="w", pady=(0, 15))  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(anchor.

        # API cards
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for key, info in PROVIDER_INFO.items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            card = APIKeyCard(  # ПОЯСНЕНИЕ: обновляется значение переменной card.
                scroll, info["name"], info["color"],  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                info["url"], info["description"],  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                on_model_change=lambda m, k=key: self._on_model_change(k, m)  # ПОЯСНЕНИЕ: обновляется значение переменной on_model_change.
            )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            card.pack(fill="x", pady=8)  # ПОЯСНЕНИЕ: обновляется значение переменной card.pack(fill.
            self.api_cards[key] = card  # ПОЯСНЕНИЕ: обновляется значение переменной self.api_cards[key].
            self._bind_clipboard_shortcuts(card.key_entry, editable=True)  # ПОЯСНЕНИЕ: обновляется значение переменной self._bind_clipboard_shortcuts(card.key_entry, edi.
            self._bind_clipboard_shortcuts(card.model_entry, editable=True)  # ПОЯСНЕНИЕ: обновляется значение переменной self._bind_clipboard_shortcuts(card.model_entry, e.

        # Buttons frame
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame.
        btn_frame.pack(fill="x", pady=20)  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame.pack(fill.

        ctk.CTkButton(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            btn_frame, text="Save Settings", height=40,  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame, text.
            corner_radius=10, fg_color="#27ae60", hover_color="#1e8449",  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
            command=self._save_config  # ПОЯСНЕНИЕ: обновляется значение переменной command.
        ).pack(side="left", padx=(0, 10))  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

        ctk.CTkButton(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            btn_frame, text="Test All Connections", height=40,  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame, text.
            corner_radius=10, fg_color="#3498db", hover_color="#2980b9",  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
            command=self._test_all_connections  # ПОЯСНЕНИЕ: обновляется значение переменной command.
        ).pack(side="left")  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_create_logs_tab` — выполняет отдельный шаг бизнес-логики.
    def _create_logs_tab(self):  # ПОЯСНЕНИЕ: объявляется функция _create_logs_tab с параметрами из сигнатуры.
        """Create logs tab"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.tab_logs.grid_rowconfigure(2, weight=1)  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_logs.grid_rowconfigure(2, weight.
        self.tab_logs.grid_columnconfigure(0, weight=1)  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_logs.grid_columnconfigure(0, weight.

        # Header
        header = ctk.CTkFrame(self.tab_logs, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной header.
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))  # ПОЯСНЕНИЕ: обновляется значение переменной header.grid(row.

        ctk.CTkLabel(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            header, text="Logs & History",  # ПОЯСНЕНИЕ: обновляется значение переменной header, text.
            font=ctk.CTkFont(size=20, weight="bold")  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        ).pack(side="left")  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

        self.logs_stats_label = ctk.CTkLabel(  # ПОЯСНЕНИЕ: обновляется значение переменной self.logs_stats_label.
            header, text="Responses: 0 | Errors: 0",  # ПОЯСНЕНИЕ: обновляется значение переменной header, text.
            font=ctk.CTkFont(size=12), text_color="gray"  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.logs_stats_label.pack(side="right")  # ПОЯСНЕНИЕ: обновляется значение переменной self.logs_stats_label.pack(side.

        # Log type selector
        selector_frame = ctk.CTkFrame(self.tab_logs, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной selector_frame.
        selector_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))  # ПОЯСНЕНИЕ: обновляется значение переменной selector_frame.grid(row.

        self.log_type_var = ctk.StringVar(value="responses")  # ПОЯСНЕНИЕ: обновляется значение переменной self.log_type_var.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for text, value in [("Responses", "responses"), ("Errors", "errors"), ("All", "all")]:  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            ctk.CTkRadioButton(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                selector_frame, text=text,  # ПОЯСНЕНИЕ: обновляется значение переменной selector_frame, text.
                variable=self.log_type_var, value=value,  # ПОЯСНЕНИЕ: обновляется значение переменной variable.
                command=self._refresh_logs_display  # ПОЯСНЕНИЕ: обновляется значение переменной command.
            ).pack(side="left", padx=(0, 20))  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

        # Logs display
        self.logs_display = ctk.CTkTextbox(  # ПОЯСНЕНИЕ: обновляется значение переменной self.logs_display.
            self.tab_logs, corner_radius=12,  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_logs, corner_radius.
            font=ctk.CTkFont(family="Consolas", size=11),  # ПОЯСНЕНИЕ: обновляется значение переменной font.
            state="disabled"  # ПОЯСНЕНИЕ: обновляется значение переменной state.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.logs_display.grid(row=2, column=0, sticky="nsew", pady=(0, 10))  # ПОЯСНЕНИЕ: обновляется значение переменной self.logs_display.grid(row.

        # Setup keyboard shortcuts for logs
        self._setup_logs_bindings()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Buttons
        btn_frame = ctk.CTkFrame(self.tab_logs, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame.
        btn_frame.grid(row=3, column=0, sticky="ew")  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame.grid(row.

        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for text, color, cmd in [  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            ("Refresh", "gray30", self._refresh_logs_display),  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            ("Export Logs", "#27ae60", self._export_logs),  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            ("Clear Logs", "#e74c3c", self._clear_logs)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        ]:  # ПОЯСНЕНИЕ: начинается новый логический блок кода.
            ctk.CTkButton(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                btn_frame, text=text, height=36,  # ПОЯСНЕНИЕ: обновляется значение переменной btn_frame, text.
                corner_radius=8, fg_color=color,  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
                command=cmd  # ПОЯСНЕНИЕ: обновляется значение переменной command.
            ).pack(side="left", padx=(0, 10))  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_create_metrics_tab` — выполняет отдельный шаг бизнес-логики.
    def _create_metrics_tab(self):  # ПОЯСНЕНИЕ: объявляется функция _create_metrics_tab с параметрами из сигнатуры.
        """Create metrics tab with provider statistics"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.tab_metrics.grid_rowconfigure(1, weight=1)  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_metrics.grid_rowconfigure(1, weight.
        self.tab_metrics.grid_columnconfigure(0, weight=1)  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_metrics.grid_columnconfigure(0, weight.

        # Header
        ctk.CTkLabel(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            self.tab_metrics, text="Provider Metrics",  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_metrics, text.
            font=ctk.CTkFont(size=20, weight="bold")  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        ).grid(row=0, column=0, sticky="w", pady=(0, 15))  # ПОЯСНЕНИЕ: обновляется значение переменной ).grid(row.

        # Metrics container
        metrics_frame = ctk.CTkFrame(self.tab_metrics, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной metrics_frame.
        metrics_frame.grid(row=1, column=0, sticky="nsew")  # ПОЯСНЕНИЕ: обновляется значение переменной metrics_frame.grid(row.
        metrics_frame.grid_columnconfigure((0, 1, 2), weight=1)  # ПОЯСНЕНИЕ: обновляется значение переменной metrics_frame.grid_columnconfigure((0, 1, 2), weig.

        # Create metrics cards for each provider
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for i, (key, info) in enumerate(PROVIDER_INFO.items()):  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            row = i // 3  # ПОЯСНЕНИЕ: обновляется значение переменной row.
            col = i % 3  # ПОЯСНЕНИЕ: обновляется значение переменной col.
            card = ProviderMetricsCard(metrics_frame, info["name"], info["color"])  # ПОЯСНЕНИЕ: обновляется значение переменной card.
            card.grid(row=row, column=col, padx=5, pady=5, sticky="ew")  # ПОЯСНЕНИЕ: обновляется значение переменной card.grid(row.
            self.metrics_cards[key] = card  # ПОЯСНЕНИЕ: обновляется значение переменной self.metrics_cards[key].

        # Refresh button
        ctk.CTkButton(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            self.tab_metrics, text="Refresh Metrics", height=36,  # ПОЯСНЕНИЕ: обновляется значение переменной self.tab_metrics, text.
            corner_radius=8, fg_color="#3498db",  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
            command=self._refresh_metrics  # ПОЯСНЕНИЕ: обновляется значение переменной command.
        ).grid(row=2, column=0, sticky="w", pady=(15, 0))  # ПОЯСНЕНИЕ: обновляется значение переменной ).grid(row.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_setup_chat_bindings` — выполняет отдельный шаг бизнес-логики.
    def _setup_chat_bindings(self):  # ПОЯСНЕНИЕ: объявляется функция _setup_chat_bindings с параметрами из сигнатуры.
        """Setup keyboard bindings for chat"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # Universal clipboard shortcuts for chat widgets
        self._bind_clipboard_shortcuts(self.chat_input, editable=True)  # ПОЯСНЕНИЕ: обновляется значение переменной self._bind_clipboard_shortcuts(self.chat_input, ed.
        self._bind_clipboard_shortcuts(self.chat_display, editable=False)  # ПОЯСНЕНИЕ: обновляется значение переменной self._bind_clipboard_shortcuts(self.chat_display, .

    # ЛОГИЧЕСКИЙ БЛОК: функция `_get_text_widget` — выполняет отдельный шаг бизнес-логики.
    def _get_text_widget(self, widget):  # ПОЯСНЕНИЕ: объявляется функция _get_text_widget с параметрами из сигнатуры.
        """Resolve to the underlying tk widget for clipboard operations."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if hasattr(widget, "_entry"):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return widget._entry  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if hasattr(widget, "_textbox"):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return widget._textbox  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        return widget  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    @contextlib.contextmanager  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: функция `_with_widget_enabled` — выполняет отдельный шаг бизнес-логики.
    def _with_widget_enabled(self, widget):  # ПОЯСНЕНИЕ: объявляется функция _with_widget_enabled с параметрами из сигнатуры.
        """Temporarily enable disabled/readonly widgets for clipboard operations."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        original_state = None  # ПОЯСНЕНИЕ: обновляется значение переменной original_state.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            original_state = widget.cget("state")  # ПОЯСНЕНИЕ: обновляется значение переменной original_state.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            original_state = None  # ПОЯСНЕНИЕ: обновляется значение переменной original_state.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if original_state in ("disabled", "readonly"):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                widget.configure(state="normal")  # ПОЯСНЕНИЕ: обновляется значение переменной widget.configure(state.
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                pass  # ПОЯСНЕНИЕ: оставляется пустая заглушка без действий.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            yield  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        finally:  # ПОЯСНЕНИЕ: выполняются действия очистки в finally.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if original_state in ("disabled", "readonly"):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                    widget.configure(state=original_state)  # ПОЯСНЕНИЕ: обновляется значение переменной widget.configure(state.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                    pass  # ПОЯСНЕНИЕ: оставляется пустая заглушка без действий.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_bind_clipboard_shortcuts` — выполняет отдельный шаг бизнес-логики.
    def _bind_clipboard_shortcuts(self, widget, editable=True):  # ПОЯСНЕНИЕ: объявляется функция _bind_clipboard_shortcuts с параметрами из сигнатуры.
        """Universal clipboard binder - returns 'break' ONLY when operation succeeds."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.

        # ЛОГИЧЕСКИЙ БЛОК: функция `_handle_copy` — выполняет отдельный шаг бизнес-логики.
        def _handle_copy(event=None):  # ПОЯСНЕНИЕ: объявляется функция _handle_copy с параметрами из сигнатуры.
            """Описание: функция `_handle_copy`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
            target = self._get_text_widget(event.widget if event else widget)  # ПОЯСНЕНИЕ: обновляется значение переменной target.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if not target:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

            # Check selection exists
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if isinstance(target, tk.Entry) and not target.selection_present():  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                elif isinstance(target, tk.Text) and not target.tag_ranges("sel"):  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
                    return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

            # Perform copy
            with self._with_widget_enabled(target):  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                    target.event_generate("<<Copy>>")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    return "break"  # Break ONLY if successful  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                    return None  # Let default handler work  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # ЛОГИЧЕСКИЙ БЛОК: функция `_handle_cut` — выполняет отдельный шаг бизнес-логики.
        def _handle_cut(event=None):  # ПОЯСНЕНИЕ: объявляется функция _handle_cut с параметрами из сигнатуры.
            """Описание: функция `_handle_cut`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if not editable:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

            target = self._get_text_widget(event.widget if event else widget)  # ПОЯСНЕНИЕ: обновляется значение переменной target.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if not target:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

            # Check selection exists
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if isinstance(target, tk.Entry) and not target.selection_present():  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                elif isinstance(target, tk.Text) and not target.tag_ranges("sel"):  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
                    return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

            # Perform cut
            with self._with_widget_enabled(target):  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                    target.event_generate("<<Cut>>")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    return "break"  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                    return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # ЛОГИЧЕСКИЙ БЛОК: функция `_handle_paste` — выполняет отдельный шаг бизнес-логики.
        def _handle_paste(event=None):  # ПОЯСНЕНИЕ: объявляется функция _handle_paste с параметрами из сигнатуры.
            """Описание: функция `_handle_paste`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if not editable:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

            # Get clipboard content
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                clipboard_text = self.clipboard_get()  # ПОЯСНЕНИЕ: обновляется значение переменной clipboard_text.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if not clipboard_text:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

            target = self._get_text_widget(event.widget if event else widget)  # ПОЯСНЕНИЕ: обновляется значение переменной target.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if not target:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

            # Perform paste
            with self._with_widget_enabled(target):  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                # Try native paste
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                    target.event_generate("<<Paste>>")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    return "break"  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                    pass  # ПОЯСНЕНИЕ: оставляется пустая заглушка без действий.

                # Fallback: manual insert
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                    if isinstance(target, tk.Entry):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                        if target.selection_present():  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                            target.delete("sel.first", "sel.last")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        target.insert(target.index("insert"), clipboard_text)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        return "break"  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
                    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                    elif isinstance(target, tk.Text):  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
                        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                        if target.tag_ranges("sel"):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                            target.delete("sel.first", "sel.last")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        target.insert("insert", clipboard_text)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        return "break"  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                    pass  # ПОЯСНЕНИЕ: оставляется пустая заглушка без действий.

            return None  # Operation failed, allow default  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # ЛОГИЧЕСКИЙ БЛОК: функция `_handle_select_all` — выполняет отдельный шаг бизнес-логики.
        def _handle_select_all(event=None):  # ПОЯСНЕНИЕ: объявляется функция _handle_select_all с параметрами из сигнатуры.
            """Описание: функция `_handle_select_all`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
            target = self._get_text_widget(event.widget if event else widget)  # ПОЯСНЕНИЕ: обновляется значение переменной target.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if not target:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

            with self._with_widget_enabled(target):  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                    if isinstance(target, tk.Entry):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                        target.select_range(0, "end")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                    elif isinstance(target, tk.Text):  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
                        target.tag_add("sel", "1.0", "end-1c")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    target.focus_set()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    return "break"  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                    return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # Bind shortcuts
        widget.bind("<Control-c>", _handle_copy)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        widget.bind("<Control-C>", _handle_copy)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if editable:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            widget.bind("<Control-x>", _handle_cut)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            widget.bind("<Control-X>", _handle_cut)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            widget.bind("<Control-v>", _handle_paste)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            widget.bind("<Control-V>", _handle_paste)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        widget.bind("<Control-a>", _handle_select_all)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        widget.bind("<Control-A>", _handle_select_all)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_setup_logs_bindings` — выполняет отдельный шаг бизнес-логики.
    def _setup_logs_bindings(self):  # ПОЯСНЕНИЕ: объявляется функция _setup_logs_bindings с параметрами из сигнатуры.
        """Setup keyboard bindings for logs"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # Universal clipboard shortcuts for logs
        self._bind_clipboard_shortcuts(self.logs_display, editable=False)  # ПОЯСНЕНИЕ: обновляется значение переменной self._bind_clipboard_shortcuts(self.logs_display, .


    # ==================== UI Queue Handler ====================

    # ЛОГИЧЕСКИЙ БЛОК: функция `_handle_ui_message` — выполняет отдельный шаг бизнес-логики.
    def _handle_ui_message(self, msg: UIMessage):  # ПОЯСНЕНИЕ: объявляется функция _handle_ui_message с параметрами из сигнатуры.
        """Handle messages from worker threads (called on main thread)"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if msg.msg_type == MessageType.RESPONSE:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self._show_response(msg.provider, msg.data, msg.elapsed)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        elif msg.msg_type == MessageType.RESPONSE_CHUNK:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
            self._append_to_chat(msg.data)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        elif msg.msg_type == MessageType.ERROR:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
            self._show_response(msg.provider, f"Error: {msg.data}", msg.elapsed)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        elif msg.msg_type == MessageType.STATUS:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
            self.status_label.configure(text=msg.data)  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_label.configure(text.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        elif msg.msg_type == MessageType.FINISHED:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
            self._finish_query(msg.data["count"], msg.data["time"], msg.data.get("file", ""))  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        elif msg.msg_type == MessageType.CONNECTION_STATUS:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if msg.provider in self.api_cards:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                self.api_cards[msg.provider].set_status(msg.data)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        elif msg.msg_type == MessageType.METRICS_UPDATE:  # ПОЯСНЕНИЕ: проверяется дополнительное условие elif.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if msg.provider in self.metrics_cards:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                self.metrics_cards[msg.provider].update_metrics(msg.data)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ==================== Query Processing ====================

    # ЛОГИЧЕСКИЙ БЛОК: функция `_handle_enter_key` — выполняет отдельный шаг бизнес-логики.
    def _handle_enter_key(self, event):  # ПОЯСНЕНИЕ: объявляется функция _handle_enter_key с параметрами из сигнатуры.
        """Handle Enter key - send query"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self._send_query()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        return "break"  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_handle_shift_enter` — выполняет отдельный шаг бизнес-логики.
    def _handle_shift_enter(self, event):  # ПОЯСНЕНИЕ: объявляется функция _handle_shift_enter с параметрами из сигнатуры.
        """Handle Shift+Enter - insert newline"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.chat_input.insert("insert", "\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        return "break"  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_send_query` — выполняет отдельный шаг бизнес-логики.
    def _send_query(self):  # ПОЯСНЕНИЕ: объявляется функция _send_query с параметрами из сигнатуры.
        """Send query to selected providers"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if self.is_processing:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        question = self.chat_input.get("1.0", "end-1c").strip()  # ПОЯСНЕНИЕ: обновляется значение переменной question.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if not question:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # Get selected providers
        selected = [key for key, switch in self.provider_switches.items() if switch.get()]  # ПОЯСНЕНИЕ: обновляется значение переменной selected.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if not selected:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            messagebox.showwarning("Warning", "Please select at least one AI provider!")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # Update UI
        self.is_processing = True  # ПОЯСНЕНИЕ: обновляется значение переменной self.is_processing.
        self.send_btn.configure(state="disabled")  # ПОЯСНЕНИЕ: обновляется значение переменной self.send_btn.configure(state.
        self.progress.grid(row=3, column=0, sticky="ew", pady=(10, 0))  # ПОЯСНЕНИЕ: обновляется значение переменной self.progress.grid(row.
        self.progress.start()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.status_label.configure(text=f"Querying {len(selected)} AI providers...")  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_label.configure(text.

        # Add user message to chat
        self._add_to_chat(f"You: {question}\n", "user")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self._add_to_chat("-" * 60 + "\n", "divider")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Clear input
        self.chat_input.delete("1.0", "end")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Update provider API keys
        self._update_providers()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Start query thread
        thread = threading.Thread(  # ПОЯСНЕНИЕ: обновляется значение переменной thread.
            target=self._process_query,  # ПОЯСНЕНИЕ: обновляется значение переменной target.
            args=(question, selected),  # ПОЯСНЕНИЕ: обновляется значение переменной args.
            daemon=True  # ПОЯСНЕНИЕ: обновляется значение переменной daemon.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        thread.start()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_process_query` — выполняет отдельный шаг бизнес-логики.
    def _process_query(self, question: str, providers: List[str]):  # ПОЯСНЕНИЕ: объявляется функция _process_query с параметрами из сигнатуры.
        """Process query in parallel (runs in worker thread)"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        responses = {}  # ПОЯСНЕНИЕ: обновляется значение переменной responses.
        total_time = 0  # ПОЯСНЕНИЕ: обновляется значение переменной total_time.

        with ThreadPoolExecutor(max_workers=len(providers)) as executor:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
            futures = {}  # ПОЯСНЕНИЕ: обновляется значение переменной futures.
            # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
            for key in providers:  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if key in self.providers:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    provider = self.providers[key]  # ПОЯСНЕНИЕ: обновляется значение переменной provider.
                    future = executor.submit(provider.query, question)  # ПОЯСНЕНИЕ: обновляется значение переменной future.
                    futures[future] = key  # ПОЯСНЕНИЕ: обновляется значение переменной futures[future].

            # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
            for future in as_completed(futures):  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
                key = futures[future]  # ПОЯСНЕНИЕ: обновляется значение переменной key.
                provider = self.providers[key]  # ПОЯСНЕНИЕ: обновляется значение переменной provider.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                    response, elapsed = future.result()  # ПОЯСНЕНИЕ: обновляется значение переменной response, elapsed.
                    responses[key] = (response, elapsed)  # ПОЯСНЕНИЕ: обновляется значение переменной responses[key].
                    total_time = max(total_time, elapsed)  # ПОЯСНЕНИЕ: обновляется значение переменной total_time.

                    # Log response
                    success = not response.startswith("Error")  # ПОЯСНЕНИЕ: обновляется значение переменной success.
                    self.logger.log_response(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        provider.name, question, response, elapsed,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        success=success, model=provider.model  # ПОЯСНЕНИЕ: обновляется значение переменной success.
                    )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

                    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                    if not success:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                        self.logger.log_error(provider.name, response, f"Query: {question[:100]}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

                    # Send to UI queue (thread-safe)
                    self.ui_queue.put(UIMessage.response(provider.name, response, elapsed))  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                    responses[key] = (f"Error: {str(e)}", 0)  # ПОЯСНЕНИЕ: обновляется значение переменной responses[key].
                    self.logger.log_error(provider.name, str(e), f"Exception: {question[:100]}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    self.ui_queue.put(UIMessage.error(provider.name, str(e)))  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Save to file
        filepath = self._save_responses(question, responses)  # ПОЯСНЕНИЕ: обновляется значение переменной filepath.

        # Signal completion
        self.ui_queue.put(UIMessage.finished(len(responses), total_time, filepath))  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_show_response` — выполняет отдельный шаг бизнес-логики.
    def _show_response(self, name: str, response: str, elapsed: float):  # ПОЯСНЕНИЕ: объявляется функция _show_response с параметрами из сигнатуры.
        """Show response in chat"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # Find provider color
        color = "#3498db"  # ПОЯСНЕНИЕ: обновляется значение переменной color.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for key, info in PROVIDER_INFO.items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if info["name"] == name:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                color = info["color"]  # ПОЯСНЕНИЕ: обновляется значение переменной color.
                break  # ПОЯСНЕНИЕ: цикл прерывается немедленно.

        header = f"\n[{name}] ({elapsed:.1f}s)\n"  # ПОЯСНЕНИЕ: обновляется значение переменной header.
        self._add_to_chat(header, "header")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self._add_to_chat(response + "\n", "response")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self._add_to_chat("-" * 60 + "\n", "divider")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_finish_query` — выполняет отдельный шаг бизнес-логики.
    def _finish_query(self, count: int, total_time: float, filepath: str):  # ПОЯСНЕНИЕ: объявляется функция _finish_query с параметрами из сигнатуры.
        """Finish query processing"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.is_processing = False  # ПОЯСНЕНИЕ: обновляется значение переменной self.is_processing.
        self.send_btn.configure(state="normal")  # ПОЯСНЕНИЕ: обновляется значение переменной self.send_btn.configure(state.
        self.progress.stop()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.progress.grid_forget()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        status = f"Completed: {count} responses in {total_time:.1f}s"  # ПОЯСНЕНИЕ: обновляется значение переменной status.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if filepath:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            status += f" | Saved to {os.path.basename(filepath)}"  # ПОЯСНЕНИЕ: обновляется значение переменной status +.
        self.status_label.configure(text=status)  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_label.configure(text.

        # Update metrics
        self._refresh_metrics()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_add_to_chat` — выполняет отдельный шаг бизнес-логики.
    def _add_to_chat(self, text: str, tag: str = ""):  # ПОЯСНЕНИЕ: объявляется функция _add_to_chat с параметрами из сигнатуры.
        """Add text to chat display"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.chat_display.configure(state="normal")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.
        self.chat_display.insert("end", text)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.chat_display.configure(state="disabled")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.
        self.chat_display.see("end")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_append_to_chat` — выполняет отдельный шаг бизнес-логики.
    def _append_to_chat(self, text: str):  # ПОЯСНЕНИЕ: объявляется функция _append_to_chat с параметрами из сигнатуры.
        """Append text to chat (for streaming)"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.chat_display.configure(state="normal")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.
        self.chat_display.insert("end", text)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.chat_display.configure(state="disabled")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.
        self.chat_display.see("end")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_clear_chat` — выполняет отдельный шаг бизнес-логики.
    def _clear_chat(self):  # ПОЯСНЕНИЕ: объявляется функция _clear_chat с параметрами из сигнатуры.
        """Clear chat display"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.chat_display.configure(state="normal")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.
        self.chat_display.delete("1.0", "end")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.chat_display.configure(state="disabled")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.
        self.status_label.configure(text="Ready")  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_label.configure(text.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_new_chat` — выполняет отдельный шаг бизнес-логики.
    def _new_chat(self):  # ПОЯСНЕНИЕ: объявляется функция _new_chat с параметрами из сигнатуры.
        """Start new chat - clear history for all providers"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for provider in self.providers.values():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            provider.clear_history()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self._clear_chat()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.status_label.configure(text="New chat started - history cleared")  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_label.configure(text.
        self.current_branch_label.configure(text="Current: None")  # ПОЯСНЕНИЕ: обновляется значение переменной self.current_branch_label.configure(text.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_save_chat_to_file` — выполняет отдельный шаг бизнес-логики.
    def _save_chat_to_file(self):  # ПОЯСНЕНИЕ: объявляется функция _save_chat_to_file с параметрами из сигнатуры.
        """Save chat content to a file with directory selection"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # Get chat content
        self.chat_display.configure(state="normal")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.
        content = self.chat_display.get("1.0", "end-1c")  # ПОЯСНЕНИЕ: обновляется значение переменной content.
        self.chat_display.configure(state="disabled")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if not content.strip():  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            messagebox.showwarning("Warning", "Chat is empty. Nothing to save.")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # ПОЯСНЕНИЕ: обновляется значение переменной timestamp.
        default_name = f"chat_log_{timestamp}.txt"  # ПОЯСНЕНИЕ: обновляется значение переменной default_name.

        # Ask user for save location
        filepath = filedialog.asksaveasfilename(  # ПОЯСНЕНИЕ: обновляется значение переменной filepath.
            defaultextension=".txt",  # ПОЯСНЕНИЕ: обновляется значение переменной defaultextension.
            filetypes=[  # ПОЯСНЕНИЕ: обновляется значение переменной filetypes.
                ("Text files", "*.txt"),  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                ("Markdown files", "*.md"),  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                ("All files", "*.*")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            ],  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            initialfile=default_name,  # ПОЯСНЕНИЕ: обновляется значение переменной initialfile.
            title="Save Chat Log"  # ПОЯСНЕНИЕ: обновляется значение переменной title.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if not filepath:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return  # User cancelled  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            with open(filepath, 'w', encoding='utf-8') as f:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                f.write("=" * 70 + "\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write(".
                f.write(f"AI Manager Chat Log\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write(f"Saved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write("=" * 70 + "\n\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write(".
                f.write(content)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write("\n\n" + "=" * 70 + "\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write("\n\n" + ".
                f.write("End of chat log\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write("=" * 70 + "\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write(".

            self.status_label.configure(text=f"Chat saved to {os.path.basename(filepath)}")  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_label.configure(text.
            messagebox.showinfo("Success", f"Chat saved to:\n{filepath}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            messagebox.showerror("Error", f"Failed to save chat:\n{str(e)}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ==================== Clipboard Operations ====================
    # Removed duplicate methods - all handled by universal _bind_clipboard_shortcuts

    # ==================== Config & Providers ====================

    # ЛОГИЧЕСКИЙ БЛОК: функция `_update_providers` — выполняет отдельный шаг бизнес-логики.
    def _update_providers(self):  # ПОЯСНЕНИЕ: объявляется функция _update_providers с параметрами из сигнатуры.
        """Update provider API keys from cards"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for key, card in self.api_cards.items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if key in self.providers:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                self.providers[key].api_key = card.get_key()  # ПОЯСНЕНИЕ: обновляется значение переменной self.providers[key].api_key.
                model = card.get_model()  # ПОЯСНЕНИЕ: обновляется значение переменной model.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if model:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    self.providers[key].set_model(model)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_on_model_change` — выполняет отдельный шаг бизнес-логики.
    def _on_model_change(self, provider_key: str, model: str):  # ПОЯСНЕНИЕ: объявляется функция _on_model_change с параметрами из сигнатуры.
        """Handle model change from UI"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if provider_key in self.providers:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self.providers[provider_key].set_model(model)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_save_config` — выполняет отдельный шаг бизнес-логики.
    def _save_config(self):  # ПОЯСНЕНИЕ: объявляется функция _save_config с параметрами из сигнатуры.
        """Save configuration (keys to secure storage)"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for key, card in self.api_cards.items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            api_key = card.get_key()  # ПОЯСНЕНИЕ: обновляется значение переменной api_key.
            self.key_storage.set_key(key, api_key)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

            # Update provider
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if key in self.providers:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                self.providers[key].api_key = api_key  # ПОЯСНЕНИЕ: обновляется значение переменной self.providers[key].api_key.

        # Save non-sensitive config
        config = {  # ПОЯСНЕНИЕ: обновляется значение переменной config.
            "theme": ctk.get_appearance_mode(),  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "models": {key: card.get_model() for key, card in self.api_cards.items()},  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "enabled_providers": [key for key, switch in self.provider_switches.items() if switch.get()]  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        }  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        with open("config.json", "w", encoding="utf-8") as f:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
            json.dump(config, f, indent=2)  # ПОЯСНЕНИЕ: обновляется значение переменной json.dump(config, f, indent.

        messagebox.showinfo("Success", "Settings saved securely!")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_load_config` — выполняет отдельный шаг бизнес-логики.
    def _load_config(self):  # ПОЯСНЕНИЕ: объявляется функция _load_config с параметрами из сигнатуры.
        """Load configuration"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # Load API keys from secure storage
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for key, card in self.api_cards.items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            api_key = self.key_storage.get_key(key)  # ПОЯСНЕНИЕ: обновляется значение переменной api_key.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if api_key:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                card.set_key(api_key)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if key in self.providers:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    self.providers[key].api_key = api_key  # ПОЯСНЕНИЕ: обновляется значение переменной self.providers[key].api_key.

        # Load non-sensitive config
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if os.path.exists("config.json"):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                with open("config.json", "r", encoding="utf-8") as f:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                    config = json.load(f)  # ПОЯСНЕНИЕ: обновляется значение переменной config.

                # Load models
                models = config.get("models", {})  # ПОЯСНЕНИЕ: обновляется значение переменной models.
                # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
                for key, model in models.items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
                    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                    if key in self.api_cards and model:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                        self.api_cards[key].set_model(model)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                    if key in self.providers and model:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                        self.providers[key].set_model(model)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

                # Load enabled providers
                enabled = config.get("enabled_providers", list(PROVIDER_INFO.keys()))  # ПОЯСНЕНИЕ: обновляется значение переменной enabled.
                # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
                for key, switch in self.provider_switches.items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
                    switch.set(key in enabled)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

            # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
            except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                self.logger.log_error("Config", f"Failed to load config: {e}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_test_all_connections` — выполняет отдельный шаг бизнес-логики.
    def _test_all_connections(self):  # ПОЯСНЕНИЕ: объявляется функция _test_all_connections с параметрами из сигнатуры.
        """Test connections to all providers"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self._update_providers()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: функция `test_provider` — выполняет отдельный шаг бизнес-логики.
        def test_provider(key):  # ПОЯСНЕНИЕ: объявляется функция test_provider с параметрами из сигнатуры.
            """Описание: функция `test_provider`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
            provider = self.providers.get(key)  # ПОЯСНЕНИЕ: обновляется значение переменной provider.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if provider and provider.api_key:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                success = provider.test_connection()  # ПОЯСНЕНИЕ: обновляется значение переменной success.
                self.ui_queue.put(UIMessage.connection_status(key, success))  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                return key, success  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
            return key, False  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        self.status_label.configure(text="Testing connections...")  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_label.configure(text.

        thread = threading.Thread(  # ПОЯСНЕНИЕ: обновляется значение переменной thread.
            target=lambda: [test_provider(k) for k in self.providers.keys()],  # ПОЯСНЕНИЕ: обновляется значение переменной target.
            daemon=True  # ПОЯСНЕНИЕ: обновляется значение переменной daemon.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        thread.start()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ==================== Logs ====================

    # ЛОГИЧЕСКИЙ БЛОК: функция `_refresh_logs_display` — выполняет отдельный шаг бизнес-логики.
    def _refresh_logs_display(self):  # ПОЯСНЕНИЕ: объявляется функция _refresh_logs_display с параметрами из сигнатуры.
        """Refresh logs display"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        log_type = self.log_type_var.get()  # ПОЯСНЕНИЕ: обновляется значение переменной log_type.

        self.logs_display.configure(state="normal")  # ПОЯСНЕНИЕ: обновляется значение переменной self.logs_display.configure(state.
        self.logs_display.delete("1.0", "end")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        responses = self.logger.get_responses_log()  # ПОЯСНЕНИЕ: обновляется значение переменной responses.
        errors = self.logger.get_errors_log()  # ПОЯСНЕНИЕ: обновляется значение переменной errors.

        self.logs_stats_label.configure(text=f"Responses: {len(responses)} | Errors: {len(errors)}")  # ПОЯСНЕНИЕ: обновляется значение переменной self.logs_stats_label.configure(text.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if log_type in ["all", "responses"]:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self.logs_display.insert("end", "=" * 50 + "\n")  # ПОЯСНЕНИЕ: обновляется значение переменной self.logs_display.insert("end", ".
            self.logs_display.insert("end", "RESPONSES LOG\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            self.logs_display.insert("end", "=" * 50 + "\n\n")  # ПОЯСНЕНИЕ: обновляется значение переменной self.logs_display.insert("end", ".

            # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
            for entry in reversed(responses):  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
                self.logs_display.insert("end", f"[{entry['timestamp'][:19]}] {entry['provider']}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                self.logs_display.insert("end", f"Model: {entry.get('model', 'N/A')}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                self.logs_display.insert("end", f"Q: {entry['question'][:100]}...\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                status = "OK" if entry['success'] else "FAIL"  # ПОЯСНЕНИЕ: обновляется значение переменной status.
                self.logs_display.insert("end", f"Status: {status} | Time: {entry['elapsed_time']:.2f}s\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                self.logs_display.insert("end", f"Response: {entry['response'][:200]}...\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                self.logs_display.insert("end", "-" * 40 + "\n\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if log_type in ["all", "errors"]:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self.logs_display.insert("end", "\n" + "=" * 50 + "\n")  # ПОЯСНЕНИЕ: обновляется значение переменной self.logs_display.insert("end", "\n" + ".
            self.logs_display.insert("end", "ERRORS LOG\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            self.logs_display.insert("end", "=" * 50 + "\n\n")  # ПОЯСНЕНИЕ: обновляется значение переменной self.logs_display.insert("end", ".

            # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
            for entry in reversed(errors):  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
                self.logs_display.insert("end", f"[{entry['timestamp'][:19]}] {entry['provider']}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                self.logs_display.insert("end", f"Error: {entry['error']}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                if entry.get('details'):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                    self.logs_display.insert("end", f"Details: {entry['details']}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                self.logs_display.insert("end", "-" * 40 + "\n\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        self.logs_display.configure(state="disabled")  # ПОЯСНЕНИЕ: обновляется значение переменной self.logs_display.configure(state.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_export_logs` — выполняет отдельный шаг бизнес-логики.
    def _export_logs(self):  # ПОЯСНЕНИЕ: объявляется функция _export_logs с параметрами из сигнатуры.
        """Export logs to file"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # ПОЯСНЕНИЕ: обновляется значение переменной timestamp.
        default_name = f"ai_manager_logs_{timestamp}.txt"  # ПОЯСНЕНИЕ: обновляется значение переменной default_name.

        filepath = filedialog.asksaveasfilename(  # ПОЯСНЕНИЕ: обновляется значение переменной filepath.
            defaultextension=".txt",  # ПОЯСНЕНИЕ: обновляется значение переменной defaultextension.
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],  # ПОЯСНЕНИЕ: обновляется значение переменной filetypes.
            initialfile=default_name  # ПОЯСНЕНИЕ: обновляется значение переменной initialfile.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if filepath:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if self.logger.export_logs(filepath):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                messagebox.showinfo("Success", f"Logs exported to {filepath}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            else:  # ПОЯСНЕНИЕ: выполняется альтернативная ветка else.
                messagebox.showerror("Error", "Failed to export logs")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_clear_logs` — выполняет отдельный шаг бизнес-логики.
    def _clear_logs(self):  # ПОЯСНЕНИЕ: объявляется функция _clear_logs с параметрами из сигнатуры.
        """Clear all logs"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if messagebox.askyesno("Confirm", "Clear all logs?"):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self.logger.clear_logs()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            self._refresh_logs_display()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ==================== Metrics ====================

    # ЛОГИЧЕСКИЙ БЛОК: функция `_refresh_metrics` — выполняет отдельный шаг бизнес-логики.
    def _refresh_metrics(self):  # ПОЯСНЕНИЕ: объявляется функция _refresh_metrics с параметрами из сигнатуры.
        """Refresh provider metrics display"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for key, card in self.metrics_cards.items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            metrics = self.logger.get_provider_metrics(PROVIDER_INFO[key]["name"])  # ПОЯСНЕНИЕ: обновляется значение переменной metrics.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if metrics:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                card.update_metrics(metrics)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ==================== Branches ====================

    # ЛОГИЧЕСКИЙ БЛОК: функция `_refresh_branches_list` — выполняет отдельный шаг бизнес-логики.
    def _refresh_branches_list(self):  # ПОЯСНЕНИЕ: объявляется функция _refresh_branches_list с параметрами из сигнатуры.
        """Refresh branches dropdown"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        branches = self.branch_manager.get_branches_list()  # ПОЯСНЕНИЕ: обновляется значение переменной branches.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if branches:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            values = [f"{b['name']} ({b['created_at'][:10]})" for b in branches]  # ПОЯСНЕНИЕ: обновляется значение переменной values.
            self.branches_combo.configure(values=values)  # ПОЯСНЕНИЕ: обновляется значение переменной self.branches_combo.configure(values.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if self.branch_manager.current_branch_id:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
                for i, b in enumerate(branches):  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
                    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                    if b['id'] == self.branch_manager.current_branch_id:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                        self.branches_combo.set(values[i])  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                        self.current_branch_label.configure(text=f"Current: {b['name']}")  # ПОЯСНЕНИЕ: обновляется значение переменной self.current_branch_label.configure(text.
                        break  # ПОЯСНЕНИЕ: цикл прерывается немедленно.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        else:  # ПОЯСНЕНИЕ: выполняется альтернативная ветка else.
            self.branches_combo.configure(values=["No saved branches"])  # ПОЯСНЕНИЕ: обновляется значение переменной self.branches_combo.configure(values.
            self.branches_combo.set("No saved branches")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_save_branch` — выполняет отдельный шаг бизнес-логики.
    def _save_branch(self):  # ПОЯСНЕНИЕ: объявляется функция _save_branch с параметрами из сигнатуры.
        """Save current conversation as branch"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        dialog = ctk.CTkInputDialog(text="Enter branch name:", title="Save Branch")  # ПОЯСНЕНИЕ: обновляется значение переменной dialog.
        name = dialog.get_input()  # ПОЯСНЕНИЕ: обновляется значение переменной name.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if not name:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        providers_history = {key: p.conversation_history.copy() for key, p in self.providers.items()}  # ПОЯСНЕНИЕ: обновляется значение переменной providers_history.

        self.chat_display.configure(state="normal")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.
        chat_content = self.chat_display.get("1.0", "end-1c")  # ПОЯСНЕНИЕ: обновляется значение переменной chat_content.
        self.chat_display.configure(state="disabled")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.

        branch_id = self.branch_manager.create_branch(name, providers_history, chat_content)  # ПОЯСНЕНИЕ: обновляется значение переменной branch_id.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if branch_id:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self._refresh_branches_list()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            self.current_branch_label.configure(text=f"Current: {name}")  # ПОЯСНЕНИЕ: обновляется значение переменной self.current_branch_label.configure(text.
            messagebox.showinfo("Success", f"Branch '{name}' saved!")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        else:  # ПОЯСНЕНИЕ: выполняется альтернативная ветка else.
            messagebox.showerror("Error", "Failed to save branch")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_load_branch` — выполняет отдельный шаг бизнес-логики.
    def _load_branch(self):  # ПОЯСНЕНИЕ: объявляется функция _load_branch с параметрами из сигнатуры.
        """Load selected branch"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        selection = self.branches_combo.get()  # ПОЯСНЕНИЕ: обновляется значение переменной selection.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if selection == "No saved branches":  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            messagebox.showwarning("Warning", "No branches to load")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        branches = self.branch_manager.get_branches_list()  # ПОЯСНЕНИЕ: обновляется значение переменной branches.
        values = [f"{b['name']} ({b['created_at'][:10]})" for b in branches]  # ПОЯСНЕНИЕ: обновляется значение переменной values.

        selected_idx = None  # ПОЯСНЕНИЕ: обновляется значение переменной selected_idx.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for i, v in enumerate(values):  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if v == selection:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                selected_idx = i  # ПОЯСНЕНИЕ: обновляется значение переменной selected_idx.
                break  # ПОЯСНЕНИЕ: цикл прерывается немедленно.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if selected_idx is None:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        branch = branches[selected_idx]  # ПОЯСНЕНИЕ: обновляется значение переменной branch.
        branch_data = self.branch_manager.load_branch(branch['id'])  # ПОЯСНЕНИЕ: обновляется значение переменной branch_data.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if not branch_data:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            messagebox.showerror("Error", "Failed to load branch")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # Restore history
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for key, history in branch_data.get("providers_history", {}).items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if key in self.providers:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                self.providers[key].conversation_history = history.copy()  # ПОЯСНЕНИЕ: обновляется значение переменной self.providers[key].conversation_history.

        # Restore chat
        self.chat_display.configure(state="normal")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.
        self.chat_display.delete("1.0", "end")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.chat_display.insert("1.0", branch_data.get("chat_content", ""))  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.chat_display.configure(state="disabled")  # ПОЯСНЕНИЕ: обновляется значение переменной self.chat_display.configure(state.

        self.current_branch_label.configure(text=f"Current: {branch['name']}")  # ПОЯСНЕНИЕ: обновляется значение переменной self.current_branch_label.configure(text.
        messagebox.showinfo("Success", f"Branch '{branch['name']}' loaded!")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_delete_branch` — выполняет отдельный шаг бизнес-логики.
    def _delete_branch(self):  # ПОЯСНЕНИЕ: объявляется функция _delete_branch с параметрами из сигнатуры.
        """Delete selected branch"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        selection = self.branches_combo.get()  # ПОЯСНЕНИЕ: обновляется значение переменной selection.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if selection == "No saved branches":  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        branches = self.branch_manager.get_branches_list()  # ПОЯСНЕНИЕ: обновляется значение переменной branches.
        values = [f"{b['name']} ({b['created_at'][:10]})" for b in branches]  # ПОЯСНЕНИЕ: обновляется значение переменной values.

        selected_idx = None  # ПОЯСНЕНИЕ: обновляется значение переменной selected_idx.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for i, v in enumerate(values):  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if v == selection:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                selected_idx = i  # ПОЯСНЕНИЕ: обновляется значение переменной selected_idx.
                break  # ПОЯСНЕНИЕ: цикл прерывается немедленно.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if selected_idx is None:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        branch = branches[selected_idx]  # ПОЯСНЕНИЕ: обновляется значение переменной branch.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if not messagebox.askyesno("Confirm", f"Delete branch '{branch['name']}'?"):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if self.branch_manager.delete_branch(branch['id']):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self._refresh_branches_list()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            messagebox.showinfo("Success", f"Branch deleted")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        else:  # ПОЯСНЕНИЕ: выполняется альтернативная ветка else.
            messagebox.showerror("Error", "Failed to delete branch")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ==================== Save Responses ====================

    # ЛОГИЧЕСКИЙ БЛОК: функция `_save_responses` — выполняет отдельный шаг бизнес-логики.
    def _save_responses(self, question: str, responses: Dict[str, Tuple[str, float]]) -> Optional[str]:  # ПОЯСНЕНИЕ: объявляется функция _save_responses с параметрами из сигнатуры.
        """Save responses to file"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # ПОЯСНЕНИЕ: обновляется значение переменной timestamp.
            filename = f"ai_responses_{timestamp}.txt"  # ПОЯСНЕНИЕ: обновляется значение переменной filename.
            filepath = os.path.join(self.output_dir, filename)  # ПОЯСНЕНИЕ: обновляется значение переменной filepath.

            with open(filepath, 'w', encoding='utf-8') as f:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                f.write("=" * 70 + "\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write(".
                f.write(f"AI Manager Response Log\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write("=" * 70 + "\n\n")  # ПОЯСНЕНИЕ: обновляется значение переменной f.write(".
                f.write(f"Question: {question}\n\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                f.write("-" * 70 + "\n\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

                # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
                for name, (response, elapsed) in responses.items():  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
                    provider_name = PROVIDER_INFO.get(name, {}).get("name", name)  # ПОЯСНЕНИЕ: обновляется значение переменной provider_name.
                    f.write(f"[{provider_name}] ({elapsed:.1f}s)\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    f.write("-" * 40 + "\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    f.write(response + "\n\n")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

            return filepath  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            self.logger.log_error("FileSystem", f"Failed to save responses: {e}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
