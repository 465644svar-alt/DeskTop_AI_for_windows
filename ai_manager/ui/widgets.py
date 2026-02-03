"""
Custom UI Widgets for AI Manager
- APIKeyCard: Card for API key input with model selection
- ModernSwitch: Toggle switch for provider selection
- ProviderMetricsCard: Display provider performance metrics
"""

import customtkinter as ctk
import tkinter as tk
import webbrowser
from typing import Callable, List, Optional


class ModernSwitch(ctk.CTkFrame):
    """Modern toggle switch with label"""

    def __init__(
        self,
        master,
        text: str,
        color: str = "#3498db",
        command: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.switch_var = ctk.BooleanVar(value=True)
        self.command = command
        self.color = color

        self.switch = ctk.CTkSwitch(
            self,
            text=text,
            variable=self.switch_var,
            onvalue=True,
            offvalue=False,
            progress_color=color,
            command=self._on_change
        )
        self.switch.pack(anchor="w")

    def _on_change(self):
        if self.command:
            self.command()

    def get(self) -> bool:
        return self.switch_var.get()

    def set(self, value: bool):
        self.switch_var.set(value)


class APIKeyCard(ctk.CTkFrame):
    """Modern card for API key input with model selection"""

    def __init__(
        self,
        master,
        name: str,
        color: str,
        url: str,
        description: str,
        models: List[str] = None,
        on_model_change: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(master, corner_radius=12, **kwargs)

        self.name = name
        self.url = url
        self.color = color
        self.show_key = False
        self.models = models or []
        self.on_model_change = on_model_change

        # Header with color accent
        header = ctk.CTkFrame(self, fg_color=color, corner_radius=10, height=4)
        header.pack(fill="x", padx=10, pady=(10, 0))

        # Content frame
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=10)

        # Title row
        title_row = ctk.CTkFrame(content, fg_color="transparent")
        title_row.pack(fill="x")

        ctk.CTkLabel(
            title_row, text=name,
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")

        # Status indicator
        self.status_indicator = ctk.CTkLabel(
            title_row, text="", width=10, height=10,
            fg_color="gray", corner_radius=5
        )
        self.status_indicator.pack(side="right", padx=5)

        # Description
        ctk.CTkLabel(
            content, text=description,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(anchor="w", pady=(2, 8))

        # Model selector (if models available)
        if self.models:
            model_row = ctk.CTkFrame(content, fg_color="transparent")
            model_row.pack(fill="x", pady=(0, 8))

            ctk.CTkLabel(
                model_row, text="Model:",
                font=ctk.CTkFont(size=12)
            ).pack(side="left", padx=(0, 10))

            self.model_combo = ctk.CTkComboBox(
                model_row,
                values=self.models,
                width=200,
                height=28,
                command=self._on_model_select
            )
            self.model_combo.pack(side="left")
            self.model_combo.set(self.models[0])
        else:
            self.model_combo = None

        # Key input row
        key_row = ctk.CTkFrame(content, fg_color="transparent")
        key_row.pack(fill="x")

        self.key_entry = ctk.CTkEntry(
            key_row, placeholder_text="Enter API key...",
            show="*", height=36, corner_radius=8
        )
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._entry_widget = self.key_entry._entry if hasattr(self.key_entry, "_entry") else self.key_entry

        # Paste button
        ctk.CTkButton(
            key_row, text="Paste", width=60, height=36,
            corner_radius=8, fg_color="#2980b9", hover_color="#1f618d",
            command=self._paste_key
        ).pack(side="left", padx=(0, 8))

        # Toggle visibility button
        self.toggle_btn = ctk.CTkButton(
            key_row, text="Show", width=60, height=36,
            corner_radius=8, command=self._toggle_visibility
        )
        self.toggle_btn.pack(side="left", padx=(0, 8))

        # Get key button
        ctk.CTkButton(
            key_row, text="Get Key", width=80, height=36,
            corner_radius=8, fg_color=color, hover_color=self._darken(color),
            command=lambda: webbrowser.open(url)
        ).pack(side="left")

        # Add keyboard shortcuts and context menu
        self._setup_key_entry_bindings()

    def _setup_key_entry_bindings(self):
        """Setup keyboard shortcuts and context menu for key entry"""
        # Context menu
        self.entry_menu = tk.Menu(self, tearoff=0)
        self.entry_menu.add_command(label="Cut", command=self._cut_entry, accelerator="Ctrl+X")
        self.entry_menu.add_command(label="Copy", command=self._copy_entry, accelerator="Ctrl+C")
        self.entry_menu.add_command(label="Paste", command=self._paste_key, accelerator="Ctrl+V")
        self.entry_menu.add_separator()
        self.entry_menu.add_command(label="Select All", command=self._select_all_entry, accelerator="Ctrl+A")
        self.entry_menu.add_command(label="Clear", command=lambda: self.key_entry.delete(0, "end"))

        # Right-click menu
        self._entry_widget.bind("<Button-3>", self._show_entry_menu)

        # Keyboard shortcuts
        self._entry_widget.bind("<Control-a>", lambda e: self._select_all_entry() or "break")
        self._entry_widget.bind("<Control-A>", lambda e: self._select_all_entry() or "break")
        self._entry_widget.bind("<Control-c>", lambda e: self._copy_entry() or "break")
        self._entry_widget.bind("<Control-C>", lambda e: self._copy_entry() or "break")
        self._entry_widget.bind("<Control-v>", lambda e: self._paste_key() or "break")
        self._entry_widget.bind("<Control-V>", lambda e: self._paste_key() or "break")
        self._entry_widget.bind("<Control-x>", lambda e: self._cut_entry() or "break")
        self._entry_widget.bind("<Control-X>", lambda e: self._cut_entry() or "break")

    def _show_entry_menu(self, event):
        try:
            self.entry_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.entry_menu.grab_release()

    def _select_all_entry(self):
        if hasattr(self._entry_widget, "selection_range"):
            self._entry_widget.selection_range(0, "end")
        self._entry_widget.focus_set()

    def _copy_entry(self):
        try:
            if self._entry_widget.selection_present():
                selected = self._entry_widget.selection_get()
            else:
                selected = self.key_entry.get()
            if selected:
                self.clipboard_clear()
                self.clipboard_append(selected)
        except Exception:
            pass

    def _cut_entry(self):
        try:
            if self._entry_widget.selection_present():
                selected = self._entry_widget.selection_get()
                if selected:
                    self.clipboard_clear()
                    self.clipboard_append(selected)
                    self._entry_widget.delete("sel.first", "sel.last")
        except Exception:
            pass

    def _toggle_visibility(self):
        self.show_key = not self.show_key
        self.key_entry.configure(show="" if self.show_key else "*")
        self.toggle_btn.configure(text="Hide" if self.show_key else "Show")

    def _paste_key(self):
        try:
            text = self.clipboard_get()
            if text:
                # Clear current content and insert
                self.key_entry.delete(0, "end")
                self.key_entry.insert(0, text.strip())
        except Exception:
            pass

    def _on_model_select(self, model: str):
        if self.on_model_change:
            self.on_model_change(model)

    def _darken(self, hex_color: str) -> str:
        """Darken a hex color"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        darker = tuple(max(0, int(c * 0.8)) for c in rgb)
        return f"#{darker[0]:02x}{darker[1]:02x}{darker[2]:02x}"

    def get_key(self) -> str:
        return self.key_entry.get().strip()

    def set_key(self, key: str):
        self.key_entry.delete(0, "end")
        if key:
            self.key_entry.insert(0, key)

    def get_model(self) -> str:
        if self.model_combo:
            return self.model_combo.get()
        return ""

    def set_model(self, model: str):
        if self.model_combo and model in self.models:
            self.model_combo.set(model)

    def set_status(self, connected: bool):
        color = "#27ae60" if connected else "#e74c3c"
        self.status_indicator.configure(fg_color=color)


class ProviderMetricsCard(ctk.CTkFrame):
    """Card displaying provider performance metrics"""

    def __init__(self, master, provider_name: str, color: str = "#3498db", **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)

        self.provider_name = provider_name

        # Header
        header = ctk.CTkFrame(self, fg_color=color, corner_radius=8, height=3)
        header.pack(fill="x", padx=8, pady=(8, 4))

        # Provider name
        ctk.CTkLabel(
            self, text=provider_name,
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=10)

        # Metrics frame
        metrics_frame = ctk.CTkFrame(self, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=10, pady=(4, 8))

        # Requests label
        self.requests_label = ctk.CTkLabel(
            metrics_frame, text="Requests: 0",
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.requests_label.pack(anchor="w")

        # Success rate label
        self.success_label = ctk.CTkLabel(
            metrics_frame, text="Success: 0%",
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.success_label.pack(anchor="w")

        # Avg time label
        self.time_label = ctk.CTkLabel(
            metrics_frame, text="Avg time: 0s",
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.time_label.pack(anchor="w")

    def update_metrics(self, metrics: dict):
        """Update displayed metrics"""
        self.requests_label.configure(text=f"Requests: {metrics.get('total_requests', 0)}")

        success_rate = metrics.get('success_rate', 0)
        success_color = "#27ae60" if success_rate >= 90 else "#f39c12" if success_rate >= 70 else "#e74c3c"
        self.success_label.configure(
            text=f"Success: {success_rate:.1f}%",
            text_color=success_color
        )

        avg_time = metrics.get('avg_response_time', 0)
        self.time_label.configure(text=f"Avg time: {avg_time:.2f}s")
