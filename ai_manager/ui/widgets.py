# НАЗНАЧЕНИЕ ФАЙЛА: Переиспользуемые UI-виджеты и вспомогательные визуальные компоненты.
"""
Custom UI Widgets for AI Manager
- APIKeyCard: Card for API key input with model entry
- ModernSwitch: Toggle switch for provider selection
- ProviderMetricsCard: Display provider performance metrics
"""

import customtkinter as ctk  # ПОЯСНЕНИЕ: импортируется модуль customtkinter as ctk.
import webbrowser  # ПОЯСНЕНИЕ: импортируется модуль webbrowser.
from typing import Callable, Optional  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.


# ЛОГИЧЕСКИЙ БЛОК: класс `ModernSwitch(ctk.CTkFrame)` — объединяет состояние и поведение подсистемы.
class ModernSwitch(ctk.CTkFrame):  # ПОЯСНЕНИЕ: объявляется класс ModernSwitch.
    """Modern toggle switch with label"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.

    # ЛОГИЧЕСКИЙ БЛОК: функция `__init__` — выполняет отдельный шаг бизнес-логики.
    def __init__(  # ПОЯСНЕНИЕ: объявляется функция __init__ с параметрами из сигнатуры.
        self,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        master,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        text: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        color: str = "#3498db",  # ПОЯСНЕНИЕ: обновляется значение переменной color: str.
        command: Optional[Callable] = None,  # ПОЯСНЕНИЕ: обновляется значение переменной command: Optional[Callable].
        **kwargs  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    ):  # ПОЯСНЕНИЕ: начинается новый логический блок кода.
        """Описание: функция `__init__`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        super().__init__(master, fg_color="transparent", **kwargs)  # ПОЯСНЕНИЕ: обновляется значение переменной super().__init__(master, fg_color.

        self.switch_var = ctk.BooleanVar(value=True)  # ПОЯСНЕНИЕ: обновляется значение переменной self.switch_var.
        self.command = command  # ПОЯСНЕНИЕ: обновляется значение переменной self.command.
        self.color = color  # ПОЯСНЕНИЕ: обновляется значение переменной self.color.

        self.switch = ctk.CTkSwitch(  # ПОЯСНЕНИЕ: обновляется значение переменной self.switch.
            self,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            text=text,  # ПОЯСНЕНИЕ: обновляется значение переменной text.
            variable=self.switch_var,  # ПОЯСНЕНИЕ: обновляется значение переменной variable.
            onvalue=True,  # ПОЯСНЕНИЕ: обновляется значение переменной onvalue.
            offvalue=False,  # ПОЯСНЕНИЕ: обновляется значение переменной offvalue.
            progress_color=color,  # ПОЯСНЕНИЕ: обновляется значение переменной progress_color.
            command=self._on_change  # ПОЯСНЕНИЕ: обновляется значение переменной command.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.switch.pack(anchor="w")  # ПОЯСНЕНИЕ: обновляется значение переменной self.switch.pack(anchor.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_on_change` — выполняет отдельный шаг бизнес-логики.
    def _on_change(self):  # ПОЯСНЕНИЕ: объявляется функция _on_change с параметрами из сигнатуры.
        """Описание: функция `_on_change`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if self.command:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self.command()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get` — выполняет отдельный шаг бизнес-логики.
    def get(self) -> bool:  # ПОЯСНЕНИЕ: объявляется функция get с параметрами из сигнатуры.
        """Описание: функция `get`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return self.switch_var.get()  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `set` — выполняет отдельный шаг бизнес-логики.
    def set(self, value: bool):  # ПОЯСНЕНИЕ: объявляется функция set с параметрами из сигнатуры.
        """Описание: функция `set`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.switch_var.set(value)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.


# ЛОГИЧЕСКИЙ БЛОК: класс `APIKeyCard(ctk.CTkFrame)` — объединяет состояние и поведение подсистемы.
class APIKeyCard(ctk.CTkFrame):  # ПОЯСНЕНИЕ: объявляется класс APIKeyCard.
    """Modern card for API key input with model entry"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.

    # ЛОГИЧЕСКИЙ БЛОК: функция `__init__` — выполняет отдельный шаг бизнес-логики.
    def __init__(  # ПОЯСНЕНИЕ: объявляется функция __init__ с параметрами из сигнатуры.
        self,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        master,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        name: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        color: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        url: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        description: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        on_model_change: Optional[Callable] = None,  # ПОЯСНЕНИЕ: обновляется значение переменной on_model_change: Optional[Callable].
        **kwargs  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    ):  # ПОЯСНЕНИЕ: начинается новый логический блок кода.
        """Описание: функция `__init__`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        super().__init__(master, corner_radius=12, **kwargs)  # ПОЯСНЕНИЕ: обновляется значение переменной super().__init__(master, corner_radius.

        self.name = name  # ПОЯСНЕНИЕ: обновляется значение переменной self.name.
        self.url = url  # ПОЯСНЕНИЕ: обновляется значение переменной self.url.
        self.color = color  # ПОЯСНЕНИЕ: обновляется значение переменной self.color.
        self.show_key = False  # ПОЯСНЕНИЕ: обновляется значение переменной self.show_key.
        self.on_model_change = on_model_change  # ПОЯСНЕНИЕ: обновляется значение переменной self.on_model_change.

        # Header with color accent
        header = ctk.CTkFrame(self, fg_color=color, corner_radius=10, height=4)  # ПОЯСНЕНИЕ: обновляется значение переменной header.
        header.pack(fill="x", padx=10, pady=(10, 0))  # ПОЯСНЕНИЕ: обновляется значение переменной header.pack(fill.

        # Content frame
        content = ctk.CTkFrame(self, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной content.
        content.pack(fill="x", padx=15, pady=10)  # ПОЯСНЕНИЕ: обновляется значение переменной content.pack(fill.

        # Title row
        title_row = ctk.CTkFrame(content, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной title_row.
        title_row.pack(fill="x")  # ПОЯСНЕНИЕ: обновляется значение переменной title_row.pack(fill.

        ctk.CTkLabel(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            title_row, text=name,  # ПОЯСНЕНИЕ: обновляется значение переменной title_row, text.
            font=ctk.CTkFont(size=16, weight="bold")  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        ).pack(side="left")  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

        # Status indicator
        self.status_indicator = ctk.CTkLabel(  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_indicator.
            title_row, text="", width=10, height=10,  # ПОЯСНЕНИЕ: обновляется значение переменной title_row, text.
            fg_color="gray", corner_radius=5  # ПОЯСНЕНИЕ: обновляется значение переменной fg_color.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.status_indicator.pack(side="right", padx=5)  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_indicator.pack(side.

        # Description
        ctk.CTkLabel(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            content, text=description,  # ПОЯСНЕНИЕ: обновляется значение переменной content, text.
            font=ctk.CTkFont(size=11),  # ПОЯСНЕНИЕ: обновляется значение переменной font.
            text_color="gray"  # ПОЯСНЕНИЕ: обновляется значение переменной text_color.
        ).pack(anchor="w", pady=(2, 8))  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(anchor.

        # Model entry
        model_row = ctk.CTkFrame(content, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной model_row.
        model_row.pack(fill="x", pady=(0, 8))  # ПОЯСНЕНИЕ: обновляется значение переменной model_row.pack(fill.

        ctk.CTkLabel(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            model_row, text="Model:",  # ПОЯСНЕНИЕ: обновляется значение переменной model_row, text.
            font=ctk.CTkFont(size=12)  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        ).pack(side="left", padx=(0, 10))  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

        self.model_entry = ctk.CTkEntry(  # ПОЯСНЕНИЕ: обновляется значение переменной self.model_entry.
            model_row, width=240, height=28,  # ПОЯСНЕНИЕ: обновляется значение переменной model_row, width.
            placeholder_text="Enter model name..."  # ПОЯСНЕНИЕ: обновляется значение переменной placeholder_text.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.model_entry.pack(side="left")  # ПОЯСНЕНИЕ: обновляется значение переменной self.model_entry.pack(side.
        self.model_entry.bind("<FocusOut>", self._on_model_change)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.model_entry.bind("<Return>", self._on_model_change)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Key input row
        key_row = ctk.CTkFrame(content, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной key_row.
        key_row.pack(fill="x")  # ПОЯСНЕНИЕ: обновляется значение переменной key_row.pack(fill.

        self.key_entry = ctk.CTkEntry(  # ПОЯСНЕНИЕ: обновляется значение переменной self.key_entry.
            key_row, placeholder_text="Enter API key...",  # ПОЯСНЕНИЕ: обновляется значение переменной key_row, placeholder_text.
            show="*", height=36, corner_radius=8  # ПОЯСНЕНИЕ: обновляется значение переменной show.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))  # ПОЯСНЕНИЕ: обновляется значение переменной self.key_entry.pack(side.

        # Paste button
        ctk.CTkButton(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            key_row, text="Paste", width=60, height=36,  # ПОЯСНЕНИЕ: обновляется значение переменной key_row, text.
            corner_radius=8, fg_color="#2980b9", hover_color="#1f618d",  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
            command=self._request_paste  # ПОЯСНЕНИЕ: обновляется значение переменной command.
        ).pack(side="left", padx=(0, 8))  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

        # Toggle visibility button
        self.toggle_btn = ctk.CTkButton(  # ПОЯСНЕНИЕ: обновляется значение переменной self.toggle_btn.
            key_row, text="Show", width=60, height=36,  # ПОЯСНЕНИЕ: обновляется значение переменной key_row, text.
            corner_radius=8, command=self._toggle_visibility  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.toggle_btn.pack(side="left", padx=(0, 8))  # ПОЯСНЕНИЕ: обновляется значение переменной self.toggle_btn.pack(side.

        # Get key button
        ctk.CTkButton(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            key_row, text="Get Key", width=80, height=36,  # ПОЯСНЕНИЕ: обновляется значение переменной key_row, text.
            corner_radius=8, fg_color=color, hover_color=self._darken(color),  # ПОЯСНЕНИЕ: обновляется значение переменной corner_radius.
            command=lambda: webbrowser.open(url)  # ПОЯСНЕНИЕ: обновляется значение переменной command.
        ).pack(side="left")  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(side.

        # Shortcut bindings handled by app-level clipboard binder

    # ЛОГИЧЕСКИЙ БЛОК: функция `_toggle_visibility` — выполняет отдельный шаг бизнес-логики.
    def _toggle_visibility(self):  # ПОЯСНЕНИЕ: объявляется функция _toggle_visibility с параметрами из сигнатуры.
        """Описание: функция `_toggle_visibility`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.show_key = not self.show_key  # ПОЯСНЕНИЕ: обновляется значение переменной self.show_key.
        self.key_entry.configure(show="" if self.show_key else "*")  # ПОЯСНЕНИЕ: обновляется значение переменной self.key_entry.configure(show.
        self.toggle_btn.configure(text="Hide" if self.show_key else "Show")  # ПОЯСНЕНИЕ: обновляется значение переменной self.toggle_btn.configure(text.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_request_paste` — выполняет отдельный шаг бизнес-логики.
    def _request_paste(self):  # ПОЯСНЕНИЕ: объявляется функция _request_paste с параметрами из сигнатуры.
        """Описание: функция `_request_paste`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            self.key_entry.event_generate("<<Paste>>")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            pass  # ПОЯСНЕНИЕ: оставляется пустая заглушка без действий.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_on_model_change` — выполняет отдельный шаг бизнес-логики.
    def _on_model_change(self, _event=None):  # ПОЯСНЕНИЕ: объявляется функция _on_model_change с параметрами из сигнатуры.
        """Описание: функция `_on_model_change`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if self.on_model_change:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self.on_model_change(self.get_model())  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_darken` — выполняет отдельный шаг бизнес-логики.
    def _darken(self, hex_color: str) -> str:  # ПОЯСНЕНИЕ: объявляется функция _darken с параметрами из сигнатуры.
        """Darken a hex color"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        hex_color = hex_color.lstrip('#')  # ПОЯСНЕНИЕ: обновляется значение переменной hex_color.
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))  # ПОЯСНЕНИЕ: обновляется значение переменной rgb.
        darker = tuple(max(0, int(c * 0.8)) for c in rgb)  # ПОЯСНЕНИЕ: обновляется значение переменной darker.
        return f"#{darker[0]:02x}{darker[1]:02x}{darker[2]:02x}"  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get_key` — выполняет отдельный шаг бизнес-логики.
    def get_key(self) -> str:  # ПОЯСНЕНИЕ: объявляется функция get_key с параметрами из сигнатуры.
        """Описание: функция `get_key`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return self.key_entry.get().strip()  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `set_key` — выполняет отдельный шаг бизнес-логики.
    def set_key(self, key: str):  # ПОЯСНЕНИЕ: объявляется функция set_key с параметрами из сигнатуры.
        """Описание: функция `set_key`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.key_entry.delete(0, "end")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if key:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self.key_entry.insert(0, key)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get_model` — выполняет отдельный шаг бизнес-логики.
    def get_model(self) -> str:  # ПОЯСНЕНИЕ: объявляется функция get_model с параметрами из сигнатуры.
        """Описание: функция `get_model`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if self.model_entry:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            return self.model_entry.get().strip()  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        return ""  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `set_model` — выполняет отдельный шаг бизнес-логики.
    def set_model(self, model: str):  # ПОЯСНЕНИЕ: объявляется функция set_model с параметрами из сигнатуры.
        """Описание: функция `set_model`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
        if self.model_entry:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
            self.model_entry.delete(0, "end")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if model:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                self.model_entry.insert(0, model)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `set_status` — выполняет отдельный шаг бизнес-логики.
    def set_status(self, connected: bool):  # ПОЯСНЕНИЕ: объявляется функция set_status с параметрами из сигнатуры.
        """Описание: функция `set_status`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        color = "#27ae60" if connected else "#e74c3c"  # ПОЯСНЕНИЕ: обновляется значение переменной color.
        self.status_indicator.configure(fg_color=color)  # ПОЯСНЕНИЕ: обновляется значение переменной self.status_indicator.configure(fg_color.


# ЛОГИЧЕСКИЙ БЛОК: класс `ProviderMetricsCard(ctk.CTkFrame)` — объединяет состояние и поведение подсистемы.
class ProviderMetricsCard(ctk.CTkFrame):  # ПОЯСНЕНИЕ: объявляется класс ProviderMetricsCard.
    """Card displaying provider performance metrics"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.

    # ЛОГИЧЕСКИЙ БЛОК: функция `__init__` — выполняет отдельный шаг бизнес-логики.
    def __init__(self, master, provider_name: str, color: str = "#3498db", **kwargs):  # ПОЯСНЕНИЕ: объявляется функция __init__ с параметрами из сигнатуры.
        """Описание: функция `__init__`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        super().__init__(master, corner_radius=10, **kwargs)  # ПОЯСНЕНИЕ: обновляется значение переменной super().__init__(master, corner_radius.

        self.provider_name = provider_name  # ПОЯСНЕНИЕ: обновляется значение переменной self.provider_name.

        # Header
        header = ctk.CTkFrame(self, fg_color=color, corner_radius=8, height=3)  # ПОЯСНЕНИЕ: обновляется значение переменной header.
        header.pack(fill="x", padx=8, pady=(8, 4))  # ПОЯСНЕНИЕ: обновляется значение переменной header.pack(fill.

        # Provider name
        ctk.CTkLabel(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            self, text=provider_name,  # ПОЯСНЕНИЕ: обновляется значение переменной self, text.
            font=ctk.CTkFont(size=13, weight="bold")  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        ).pack(anchor="w", padx=10)  # ПОЯСНЕНИЕ: обновляется значение переменной ).pack(anchor.

        # Metrics frame
        metrics_frame = ctk.CTkFrame(self, fg_color="transparent")  # ПОЯСНЕНИЕ: обновляется значение переменной metrics_frame.
        metrics_frame.pack(fill="x", padx=10, pady=(4, 8))  # ПОЯСНЕНИЕ: обновляется значение переменной metrics_frame.pack(fill.

        # Requests label
        self.requests_label = ctk.CTkLabel(  # ПОЯСНЕНИЕ: обновляется значение переменной self.requests_label.
            metrics_frame, text="Requests: 0",  # ПОЯСНЕНИЕ: обновляется значение переменной metrics_frame, text.
            font=ctk.CTkFont(size=11), text_color="gray"  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.requests_label.pack(anchor="w")  # ПОЯСНЕНИЕ: обновляется значение переменной self.requests_label.pack(anchor.

        # Success rate label
        self.success_label = ctk.CTkLabel(  # ПОЯСНЕНИЕ: обновляется значение переменной self.success_label.
            metrics_frame, text="Success: 0%",  # ПОЯСНЕНИЕ: обновляется значение переменной metrics_frame, text.
            font=ctk.CTkFont(size=11), text_color="gray"  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.success_label.pack(anchor="w")  # ПОЯСНЕНИЕ: обновляется значение переменной self.success_label.pack(anchor.

        # Avg time label
        self.time_label = ctk.CTkLabel(  # ПОЯСНЕНИЕ: обновляется значение переменной self.time_label.
            metrics_frame, text="Avg time: 0s",  # ПОЯСНЕНИЕ: обновляется значение переменной metrics_frame, text.
            font=ctk.CTkFont(size=11), text_color="gray"  # ПОЯСНЕНИЕ: обновляется значение переменной font.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.time_label.pack(anchor="w")  # ПОЯСНЕНИЕ: обновляется значение переменной self.time_label.pack(anchor.

    # ЛОГИЧЕСКИЙ БЛОК: функция `update_metrics` — выполняет отдельный шаг бизнес-логики.
    def update_metrics(self, metrics: dict):  # ПОЯСНЕНИЕ: объявляется функция update_metrics с параметрами из сигнатуры.
        """Update displayed metrics"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.requests_label.configure(text=f"Requests: {metrics.get('total_requests', 0)}")  # ПОЯСНЕНИЕ: обновляется значение переменной self.requests_label.configure(text.

        success_rate = metrics.get('success_rate', 0)  # ПОЯСНЕНИЕ: обновляется значение переменной success_rate.
        success_color = "#27ae60" if success_rate >= 90 else "#f39c12" if success_rate >= 70 else "#e74c3c"  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.success_label.configure(  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            text=f"Success: {success_rate:.1f}%",  # ПОЯСНЕНИЕ: обновляется значение переменной text.
            text_color=success_color  # ПОЯСНЕНИЕ: обновляется значение переменной text_color.
        )  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        avg_time = metrics.get('avg_response_time', 0)  # ПОЯСНЕНИЕ: обновляется значение переменной avg_time.
        self.time_label.configure(text=f"Avg time: {avg_time:.2f}s")  # ПОЯСНЕНИЕ: обновляется значение переменной self.time_label.configure(text.
