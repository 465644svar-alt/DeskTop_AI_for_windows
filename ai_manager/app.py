"""
AI Manager Desktop Application v11.0
Main Application Module with thread-safe UI and modular architecture
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
import threading
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import __version__, __app_name__
from .services import UIQueue, UIMessage, MessageType, get_logger, get_branch_manager
from .providers import (
    PROVIDER_REGISTRY, PROVIDER_INFO, create_provider,
    OpenAIProvider, AnthropicProvider, GeminiProvider,
    DeepSeekProvider, GroqProvider, MistralProvider
)
from .utils import SecureKeyStorage, get_key_storage
from .ui.widgets import APIKeyCard, ModernSwitch, ProviderMetricsCard

# Theme settings
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AIManagerApp(ctk.CTk):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # App state
        self.is_processing = False
        self.output_dir = "responses"
        os.makedirs(self.output_dir, exist_ok=True)

        # Services
        self.logger = get_logger()
        self.branch_manager = get_branch_manager()
        self.key_storage = get_key_storage()

        # Thread-safe UI queue
        self.ui_queue = UIQueue(poll_interval=50)

        # Initialize providers
        self.providers: Dict[str, any] = {}
        self._init_providers()

        # UI state
        self.provider_switches: Dict[str, ModernSwitch] = {}
        self.api_cards: Dict[str, APIKeyCard] = {}
        self.metrics_cards: Dict[str, ProviderMetricsCard] = {}

        # Window setup
        self.title(f"{__app_name__} v{__version__}")
        self.geometry("1200x800")
        self.minsize(900, 600)

        # Build UI
        self._create_ui()

        # Load saved config
        self._load_config()

        # Start UI queue polling
        self.ui_queue.start_polling(self, self._handle_ui_message)

        # Migrate keys from old config if needed
        self._migrate_keys()

    def _init_providers(self):
        """Initialize all AI providers"""
        for key in PROVIDER_REGISTRY:
            self.providers[key] = create_provider(key)

    def _migrate_keys(self):
        """Migrate API keys from plain config to secure storage"""
        config_path = "config.json"
        if os.path.exists(config_path):
            migrated = self.key_storage.migrate_from_config(config_path)
            if migrated > 0:
                self.logger.logger.info(f"Migrated {migrated} API keys to secure storage")

    def _create_ui(self):
        """Create main UI"""
        # Main container
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=15)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Create tabs
        self.tab_chat = self.tabview.add("Chat")
        self.tab_settings = self.tabview.add("Settings")
        self.tab_logs = self.tabview.add("Logs")
        self.tab_metrics = self.tabview.add("Metrics")

        self._create_chat_tab()
        self._create_settings_tab()
        self._create_logs_tab()
        self._create_metrics_tab()

    def _create_chat_tab(self):
        """Create chat tab with provider selection"""
        self.tab_chat.grid_rowconfigure(1, weight=1)
        self.tab_chat.grid_columnconfigure(0, weight=1)

        # Header with provider toggles
        header = ctk.CTkFrame(self.tab_chat, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            header, text="Ask AI",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left")

        # Status frame with label and model info
        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right")

        self.model_label = ctk.CTkLabel(
            status_frame, text="",
            font=ctk.CTkFont(size=10), text_color="#3498db"
        )
        self.model_label.pack(side="top")

        self.status_label = ctk.CTkLabel(
            status_frame, text="Ready",
            font=ctk.CTkFont(size=12), text_color="gray"
        )
        self.status_label.pack(side="top")

        # Provider toggles
        toggles_frame = ctk.CTkFrame(self.tab_chat, fg_color="transparent")
        toggles_frame.grid(row=0, column=0, sticky="e", pady=(0, 10), padx=(0, 100))

        for key, info in PROVIDER_INFO.items():
            switch = ModernSwitch(
                toggles_frame, info["name"], info["color"]
            )
            switch.pack(side="left", padx=5)
            self.provider_switches[key] = switch

        # Chat display
        self.chat_display = ctk.CTkTextbox(
            self.tab_chat, corner_radius=12,
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled"
        )
        self.chat_display.grid(row=1, column=0, sticky="nsew", pady=(0, 5))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self.tab_chat, height=4, corner_radius=2,
            progress_color="#3498db"
        )
        self.progress_bar.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.progress_bar.set(0)

        # Input area
        input_frame = ctk.CTkFrame(self.tab_chat, fg_color="transparent")
        input_frame.grid(row=3, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.chat_input = ctk.CTkTextbox(
            input_frame, height=100, corner_radius=12,
            font=ctk.CTkFont(size=13)
        )
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        # Keyboard shortcuts for chat input
        self.chat_input.bind("<Return>", self._handle_enter_key)
        self.chat_input.bind("<Shift-Return>", self._handle_shift_enter)
        self._setup_chat_bindings()

        # Buttons
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1)

        self.send_btn = ctk.CTkButton(
            btn_frame, text="Send", width=100, height=40,
            corner_radius=10, font=ctk.CTkFont(size=14, weight="bold"),
            command=self._send_query
        )
        self.send_btn.pack(pady=(0, 4))

        ctk.CTkButton(
            btn_frame, text="Clear", width=100, height=30,
            corner_radius=10, fg_color="gray30",
            command=self._clear_chat
        ).pack(pady=(0, 4))

        ctk.CTkButton(
            btn_frame, text="New Chat", width=100, height=30,
            corner_radius=10, fg_color="#e74c3c", hover_color="#c0392b",
            command=self._new_chat
        ).pack(pady=(0, 4))

        ctk.CTkButton(
            btn_frame, text="Save Chat", width=100, height=30,
            corner_radius=10, fg_color="#9b59b6", hover_color="#8e44ad",
            command=self._save_chat_to_file
        ).pack()

        # Test buttons row
        test_frame = ctk.CTkFrame(self.tab_chat, fg_color="transparent")
        test_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))

        ctk.CTkButton(
            test_frame, text="Test Connection", height=32,
            corner_radius=8, fg_color="#3498db", hover_color="#2980b9",
            command=self._test_all_connections
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            test_frame, text="Send Test Query", height=32,
            corner_radius=8, fg_color="#9b59b6", hover_color="#8e44ad",
            command=self._send_test_query
        ).pack(side="left", padx=(0, 10))

        # Theme toggle
        self.theme_btn = ctk.CTkButton(
            test_frame, text="Light Theme", height=32, width=100,
            corner_radius=8, fg_color="#34495e", hover_color="#2c3e50",
            command=self._toggle_theme
        )
        self.theme_btn.pack(side="right")

        # Branches panel
        self._create_branches_panel()

    def _create_branches_panel(self):
        """Create conversation branches management panel"""
        branches_frame = ctk.CTkFrame(self.tab_chat, corner_radius=12)
        branches_frame.grid(row=5, column=0, sticky="ew", pady=(10, 0))

        # Header
        branches_header = ctk.CTkFrame(branches_frame, fg_color="transparent")
        branches_header.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            branches_header, text="Conversation Branches",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        self.current_branch_label = ctk.CTkLabel(
            branches_header, text="Current: None",
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.current_branch_label.pack(side="right")

        # Controls
        branches_controls = ctk.CTkFrame(branches_frame, fg_color="transparent")
        branches_controls.pack(fill="x", padx=10, pady=(0, 10))

        self.branches_combo = ctk.CTkComboBox(
            branches_controls, width=250, height=32,
            values=["No saved branches"], state="readonly"
        )
        self.branches_combo.pack(side="left", padx=(0, 10))

        for text, color, cmd in [
            ("Save", "#27ae60", self._save_branch),
            ("Load", "#3498db", self._load_branch),
            ("Delete", "#e74c3c", self._delete_branch),
            ("Refresh", "gray30", self._refresh_branches_list)
        ]:
            ctk.CTkButton(
                branches_controls, text=text, width=70, height=32,
                corner_radius=8, fg_color=color,
                command=cmd
            ).pack(side="left", padx=(0, 5))

        self._refresh_branches_list()

    def _create_settings_tab(self):
        """Create settings tab with API key cards"""
        scroll = ctk.CTkScrollableFrame(self.tab_settings, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(
            scroll, text="API Keys Configuration",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w", pady=(0, 15))

        # API cards
        for key, info in PROVIDER_INFO.items():
            provider = self.providers.get(key)
            models = provider.AVAILABLE_MODELS if provider else []

            card = APIKeyCard(
                scroll, info["name"], info["color"],
                info["url"], info["description"],
                models=models,
                on_model_change=lambda m, k=key: self._on_model_change(k, m)
            )
            card.pack(fill="x", pady=8)
            self.api_cards[key] = card

        # Buttons frame
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            btn_frame, text="Save Settings", height=40,
            corner_radius=10, fg_color="#27ae60", hover_color="#1e8449",
            command=self._save_config
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Validate Keys", height=40,
            corner_radius=10, fg_color="#f39c12", hover_color="#d68910",
            command=self._validate_api_keys
        ).pack(side="left")

    def _create_logs_tab(self):
        """Create logs tab"""
        self.tab_logs.grid_rowconfigure(2, weight=1)
        self.tab_logs.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            header, text="Logs & History",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left")

        self.logs_stats_label = ctk.CTkLabel(
            header, text="Responses: 0 | Errors: 0",
            font=ctk.CTkFont(size=12), text_color="gray"
        )
        self.logs_stats_label.pack(side="right")

        # Log type selector
        selector_frame = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        selector_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.log_type_var = ctk.StringVar(value="responses")
        for text, value in [("Responses", "responses"), ("Errors", "errors"), ("All", "all")]:
            ctk.CTkRadioButton(
                selector_frame, text=text,
                variable=self.log_type_var, value=value,
                command=self._refresh_logs_display
            ).pack(side="left", padx=(0, 20))

        # Logs display
        self.logs_display = ctk.CTkTextbox(
            self.tab_logs, corner_radius=12,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled"
        )
        self.logs_display.grid(row=2, column=0, sticky="nsew", pady=(0, 10))

        # Setup keyboard shortcuts for logs
        self._setup_logs_bindings()

        # Buttons
        btn_frame = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew")

        for text, color, cmd in [
            ("Refresh", "gray30", self._refresh_logs_display),
            ("Export Logs", "#27ae60", self._export_logs),
            ("Clear Logs", "#e74c3c", self._clear_logs)
        ]:
            ctk.CTkButton(
                btn_frame, text=text, height=36,
                corner_radius=8, fg_color=color,
                command=cmd
            ).pack(side="left", padx=(0, 10))

    def _create_metrics_tab(self):
        """Create metrics tab with provider statistics"""
        self.tab_metrics.grid_rowconfigure(1, weight=1)
        self.tab_metrics.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(
            self.tab_metrics, text="Provider Metrics",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 15))

        # Metrics container
        metrics_frame = ctk.CTkFrame(self.tab_metrics, fg_color="transparent")
        metrics_frame.grid(row=1, column=0, sticky="nsew")
        metrics_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Create metrics cards for each provider
        for i, (key, info) in enumerate(PROVIDER_INFO.items()):
            row = i // 3
            col = i % 3
            card = ProviderMetricsCard(metrics_frame, info["name"], info["color"])
            card.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            self.metrics_cards[key] = card

        # Refresh button
        ctk.CTkButton(
            self.tab_metrics, text="Refresh Metrics", height=36,
            corner_radius=8, fg_color="#3498db",
            command=self._refresh_metrics
        ).grid(row=2, column=0, sticky="w", pady=(15, 0))

    def _setup_chat_bindings(self):
        """Setup keyboard bindings for chat"""
        # Context menus
        self.input_menu = tk.Menu(self, tearoff=0)
        self.input_menu.add_command(label="Cut", command=self._cut_input, accelerator="Ctrl+X")
        self.input_menu.add_command(label="Copy", command=self._copy_input, accelerator="Ctrl+C")
        self.input_menu.add_command(label="Paste", command=self._paste_input, accelerator="Ctrl+V")
        self.input_menu.add_separator()
        self.input_menu.add_command(label="Select All", command=self._select_all_input, accelerator="Ctrl+A")

        self.chat_menu = tk.Menu(self, tearoff=0)
        self.chat_menu.add_command(label="Copy", command=self._copy_chat)
        self.chat_menu.add_command(label="Select All", command=self._select_all_chat)

        self.chat_input.bind("<Button-3>", lambda e: self._show_menu(e, self.input_menu))
        self.chat_display.bind("<Button-3>", lambda e: self._show_menu(e, self.chat_menu))

        # Bind clipboard shortcuts to all text widgets
        self._bind_clipboard_shortcuts(self.chat_input, editable=True)
        self._bind_clipboard_shortcuts(self.chat_display, editable=False)

    def _bind_clipboard_shortcuts(self, widget, editable=True):
        """Bind clipboard shortcuts to a text widget"""
        # Ctrl+A - Select All
        def select_all(e):
            widget.tag_add("sel", "1.0", "end-1c")
            return "break"
        widget.bind("<Control-a>", select_all)
        widget.bind("<Control-A>", select_all)

        # Ctrl+C - Copy
        def copy_text(e):
            try:
                text_widget = widget._textbox if hasattr(widget, '_textbox') else widget
                text_widget.event_generate("<<Copy>>")
            except:
                try:
                    sel = widget.get("sel.first", "sel.last")
                    if sel:
                        self.clipboard_clear()
                        self.clipboard_append(sel)
                except:
                    pass
            return "break"
        widget.bind("<Control-c>", copy_text)
        widget.bind("<Control-C>", copy_text)

        if editable:
            # Ctrl+V - Paste
            def paste_text(e):
                try:
                    text_widget = widget._textbox if hasattr(widget, '_textbox') else widget
                    text_widget.event_generate("<<Paste>>")
                except:
                    try:
                        text = self.clipboard_get()
                        widget.insert("insert", text)
                    except:
                        pass
                return "break"
            widget.bind("<Control-v>", paste_text)
            widget.bind("<Control-V>", paste_text)

            # Ctrl+X - Cut
            def cut_text(e):
                try:
                    text_widget = widget._textbox if hasattr(widget, '_textbox') else widget
                    text_widget.event_generate("<<Cut>>")
                except:
                    try:
                        sel = widget.get("sel.first", "sel.last")
                        if sel:
                            self.clipboard_clear()
                            self.clipboard_append(sel)
                            widget.delete("sel.first", "sel.last")
                    except:
                        pass
                return "break"
            widget.bind("<Control-x>", cut_text)
            widget.bind("<Control-X>", cut_text)

    def _setup_logs_bindings(self):
        """Setup keyboard bindings for logs"""
        self.logs_menu = tk.Menu(self, tearoff=0)
        self.logs_menu.add_command(label="Copy", command=self._copy_logs)
        self.logs_menu.add_command(label="Select All", command=self._select_all_logs)

        self.logs_display.bind("<Button-3>", lambda e: self._show_menu(e, self.logs_menu))
        self._bind_clipboard_shortcuts(self.logs_display, editable=False)

    def _show_menu(self, event, menu):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ==================== UI Queue Handler ====================

    def _handle_ui_message(self, msg: UIMessage):
        """Handle messages from worker threads (called on main thread)"""
        if msg.msg_type == MessageType.RESPONSE:
            self._show_response(msg.provider, msg.data, msg.elapsed)

        elif msg.msg_type == MessageType.RESPONSE_CHUNK:
            self._append_to_chat(msg.data)

        elif msg.msg_type == MessageType.ERROR:
            self._show_response(msg.provider, f"Error: {msg.data}", msg.elapsed)

        elif msg.msg_type == MessageType.STATUS:
            self.status_label.configure(text=msg.data)

        elif msg.msg_type == MessageType.FINISHED:
            self._finish_query(msg.data["count"], msg.data["time"], msg.data.get("file", ""))

        elif msg.msg_type == MessageType.CONNECTION_STATUS:
            if msg.provider in self.api_cards:
                self.api_cards[msg.provider].set_status(msg.data)

        elif msg.msg_type == MessageType.METRICS_UPDATE:
            if msg.provider in self.metrics_cards:
                self.metrics_cards[msg.provider].update_metrics(msg.data)

    # ==================== Query Processing ====================

    def _handle_enter_key(self, event):
        """Handle Enter key - send query"""
        self._send_query()
        return "break"

    def _handle_shift_enter(self, event):
        """Handle Shift+Enter - insert newline"""
        self.chat_input.insert("insert", "\n")
        return "break"

    def _send_query(self):
        """Send query to selected providers"""
        if self.is_processing:
            return

        question = self.chat_input.get("1.0", "end-1c").strip()
        if not question:
            return

        # Get selected providers
        selected = [key for key, switch in self.provider_switches.items() if switch.get()]
        if not selected:
            messagebox.showwarning("Warning", "Please select at least one AI provider!")
            return

        # Update UI
        self.is_processing = True
        self.send_btn.configure(state="disabled")
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

        # Show selected models
        model_info = []
        for key in selected:
            if key in self.api_cards:
                model = self.api_cards[key].get_model()
                model_info.append(f"{PROVIDER_INFO[key]['name'][:3]}:{model[:15]}")
        self.model_label.configure(text=" | ".join(model_info[:3]))
        self.status_label.configure(text=f"Querying {len(selected)} AI providers...")

        # Add user message to chat
        self._add_to_chat(f"You: {question}\n", "user")
        self._add_to_chat("-" * 60 + "\n", "divider")

        # Clear input
        self.chat_input.delete("1.0", "end")

        # Update provider API keys
        self._update_providers()

        # Start query thread
        thread = threading.Thread(
            target=self._process_query,
            args=(question, selected),
            daemon=True
        )
        thread.start()

    def _process_query(self, question: str, providers: List[str]):
        """Process query in parallel (runs in worker thread)"""
        responses = {}
        total_time = 0

        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            futures = {}
            for key in providers:
                if key in self.providers:
                    provider = self.providers[key]
                    future = executor.submit(provider.query, question)
                    futures[future] = key

            for future in as_completed(futures):
                key = futures[future]
                provider = self.providers[key]
                try:
                    response, elapsed = future.result()
                    responses[key] = (response, elapsed)
                    total_time = max(total_time, elapsed)

                    # Log response
                    success = not response.startswith("Error")
                    self.logger.log_response(
                        provider.name, question, response, elapsed,
                        success=success, model=provider.model
                    )

                    if not success:
                        self.logger.log_error(provider.name, response, f"Query: {question[:100]}")

                    # Send to UI queue (thread-safe)
                    self.ui_queue.put(UIMessage.response(provider.name, response, elapsed))

                except Exception as e:
                    responses[key] = (f"Error: {str(e)}", 0)
                    self.logger.log_error(provider.name, str(e), f"Exception: {question[:100]}")
                    self.ui_queue.put(UIMessage.error(provider.name, str(e)))

        # Save to file
        filepath = self._save_responses(question, responses)

        # Signal completion
        self.ui_queue.put(UIMessage.finished(len(responses), total_time, filepath))

    def _show_response(self, name: str, response: str, elapsed: float):
        """Show response in chat"""
        # Find provider color
        color = "#3498db"
        for key, info in PROVIDER_INFO.items():
            if info["name"] == name:
                color = info["color"]
                break

        header = f"\n[{name}] ({elapsed:.1f}s)\n"
        self._add_to_chat(header, "header")
        self._add_to_chat(response + "\n", "response")
        self._add_to_chat("-" * 60 + "\n", "divider")

    def _finish_query(self, count: int, total_time: float, filepath: str):
        """Finish query processing"""
        self.is_processing = False
        self.send_btn.configure(state="normal")
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(1)  # Show completed

        status = f"Completed: {count} responses in {total_time:.1f}s"
        if filepath:
            status += f" | Saved to {os.path.basename(filepath)}"
        self.status_label.configure(text=status)

        # Clear model label after completion
        self.after(3000, lambda: self.model_label.configure(text=""))
        self.after(3000, lambda: self.progress_bar.set(0))

        # Update metrics
        self._refresh_metrics()

    def _add_to_chat(self, text: str, tag: str = ""):
        """Add text to chat display"""
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text)
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def _append_to_chat(self, text: str):
        """Append text to chat (for streaming)"""
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text)
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def _clear_chat(self):
        """Clear chat display"""
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        self.status_label.configure(text="Ready")

    def _new_chat(self):
        """Start new chat - clear history for all providers"""
        for provider in self.providers.values():
            provider.clear_history()
        self._clear_chat()
        self.status_label.configure(text="New chat started - history cleared")
        self.current_branch_label.configure(text="Current: None")

    def _toggle_theme(self):
        """Toggle between dark and light themes"""
        current = ctk.get_appearance_mode()
        if current == "Dark":
            ctk.set_appearance_mode("light")
            self.theme_btn.configure(text="Dark Theme")
        else:
            ctk.set_appearance_mode("dark")
            self.theme_btn.configure(text="Light Theme")

    def _save_chat_to_file(self):
        """Save chat content to a file with directory selection"""
        # Get chat content
        self.chat_display.configure(state="normal")
        content = self.chat_display.get("1.0", "end-1c")
        self.chat_display.configure(state="disabled")

        if not content.strip():
            messagebox.showwarning("Warning", "Chat is empty. Nothing to save.")
            return

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"chat_log_{timestamp}.txt"

        # Ask user for save location
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("Markdown files", "*.md"),
                ("All files", "*.*")
            ],
            initialfile=default_name,
            title="Save Chat Log"
        )

        if not filepath:
            return  # User cancelled

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write(f"AI Manager Chat Log\n")
                f.write(f"Saved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")
                f.write(content)
                f.write("\n\n" + "=" * 70 + "\n")
                f.write("End of chat log\n")
                f.write("=" * 70 + "\n")

            self.status_label.configure(text=f"Chat saved to {os.path.basename(filepath)}")
            messagebox.showinfo("Success", f"Chat saved to:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save chat:\n{str(e)}")

    # ==================== Clipboard Operations ====================

    def _copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)

    def _cut_input(self):
        try:
            selected = self.chat_input.get("sel.first", "sel.last")
            if selected:
                self._copy_to_clipboard(selected)
                self.chat_input.delete("sel.first", "sel.last")
        except Exception:
            pass

    def _copy_input(self):
        try:
            selected = self.chat_input.get("sel.first", "sel.last")
            if selected:
                self._copy_to_clipboard(selected)
        except Exception:
            pass

    def _paste_input(self):
        try:
            text = self.clipboard_get()
            if text:
                self.chat_input.insert("insert", text)
        except Exception:
            pass

    def _select_all_input(self):
        self.chat_input.tag_add("sel", "1.0", "end-1c")

    def _copy_chat(self):
        try:
            self.chat_display.configure(state="normal")
            selected = self.chat_display.get("sel.first", "sel.last")
            self.chat_display.configure(state="disabled")
            if selected:
                self._copy_to_clipboard(selected)
        except Exception:
            # Copy all if no selection
            self.chat_display.configure(state="normal")
            content = self.chat_display.get("1.0", "end-1c")
            self.chat_display.configure(state="disabled")
            if content.strip():
                self._copy_to_clipboard(content)

    def _select_all_chat(self):
        self.chat_display.configure(state="normal")
        self.chat_display.tag_add("sel", "1.0", "end-1c")
        self.chat_display.configure(state="disabled")

    def _copy_logs(self):
        try:
            self.logs_display.configure(state="normal")
            selected = self.logs_display.get("sel.first", "sel.last")
            self.logs_display.configure(state="disabled")
            if selected:
                self._copy_to_clipboard(selected)
        except Exception:
            pass

    def _select_all_logs(self):
        self.logs_display.configure(state="normal")
        self.logs_display.tag_add("sel", "1.0", "end-1c")
        self.logs_display.configure(state="disabled")

    # ==================== Config & Providers ====================

    def _update_providers(self):
        """Update provider API keys from cards"""
        for key, card in self.api_cards.items():
            if key in self.providers:
                self.providers[key].api_key = card.get_key()
                model = card.get_model()
                if model:
                    self.providers[key].set_model(model)

    def _on_model_change(self, provider_key: str, model: str):
        """Handle model change from UI"""
        if provider_key in self.providers:
            self.providers[provider_key].set_model(model)

    def _save_config(self):
        """Save configuration (keys to secure storage)"""
        for key, card in self.api_cards.items():
            api_key = card.get_key()
            self.key_storage.set_key(key, api_key)

            # Update provider
            if key in self.providers:
                self.providers[key].api_key = api_key

        # Save non-sensitive config
        config = {
            "theme": ctk.get_appearance_mode(),
            "models": {key: card.get_model() for key, card in self.api_cards.items()},
            "enabled_providers": [key for key, switch in self.provider_switches.items() if switch.get()]
        }

        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        messagebox.showinfo("Success", "Settings saved securely!")

    def _load_config(self):
        """Load configuration"""
        # Load API keys from secure storage
        for key, card in self.api_cards.items():
            api_key = self.key_storage.get_key(key)
            if api_key:
                card.set_key(api_key)
                if key in self.providers:
                    self.providers[key].api_key = api_key

        # Load non-sensitive config
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)

                # Load models
                models = config.get("models", {})
                for key, model in models.items():
                    if key in self.api_cards and model:
                        self.api_cards[key].set_model(model)
                    if key in self.providers and model:
                        self.providers[key].set_model(model)

                # Load enabled providers
                enabled = config.get("enabled_providers", list(PROVIDER_INFO.keys()))
                for key, switch in self.provider_switches.items():
                    switch.set(key in enabled)

            except Exception as e:
                self.logger.log_error("Config", f"Failed to load config: {e}")

    def _validate_api_keys(self):
        """Validate API key formats without making API calls"""
        results = []

        for key, info in PROVIDER_INFO.items():
            if key in self.api_cards:
                api_key = self.api_cards[key].get_key()
                provider_name = info["name"]

                if not api_key:
                    results.append((provider_name, "EMPTY", "No key entered", "#95a5a6"))
                elif len(api_key) < 20:
                    results.append((provider_name, "INVALID", "Key too short", "#e74c3c"))
                elif key == "openai" and not api_key.startswith("sk-"):
                    results.append((provider_name, "WARN", "Should start with 'sk-'", "#f39c12"))
                elif key == "anthropic" and not api_key.startswith("sk-ant-"):
                    results.append((provider_name, "WARN", "Should start with 'sk-ant-'", "#f39c12"))
                else:
                    results.append((provider_name, "OK", f"Format valid ({len(api_key)} chars)", "#27ae60"))

        # Show in popup
        result_text = "API Key Validation Results:\n\n"
        for name, status, msg, _ in results:
            result_text += f"[{status:^7}] {name}: {msg}\n"

        messagebox.showinfo("Key Validation", result_text)

        # Update status indicators
        for key, info in PROVIDER_INFO.items():
            if key in self.api_cards:
                for name, status, _, color in results:
                    if name == info["name"]:
                        self.api_cards[key].status_indicator.configure(
                            fg_color=color if status == "OK" else "#e74c3c" if status in ["INVALID", "EMPTY"] else "#f39c12"
                        )

    def _test_all_connections(self):
        """Test connections to all providers"""
        self._update_providers()

        # Show in chat that testing has started
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", "\n" + "=" * 50 + "\n")
        self.chat_display.insert("end", "Testing All Connections...\n")
        self.chat_display.insert("end", "=" * 50 + "\n\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

        def test_all():
            results = []
            for key, info in PROVIDER_INFO.items():
                provider = self.providers.get(key)
                provider_name = info["name"]

                if provider and provider.api_key:
                    self.ui_queue.put(UIMessage.status(f"Testing {provider_name}..."))
                    try:
                        success = provider.test_connection()
                        status = "OK" if success else "FAILED"
                        results.append((provider_name, success, None))
                    except Exception as e:
                        results.append((provider_name, False, str(e)))
                        status = "ERROR"
                    self.ui_queue.put(UIMessage.connection_status(key, success if 'success' in dir() else False))
                else:
                    results.append((provider_name, None, "No API key"))

            # Send results to UI
            self.ui_queue.put(UIMessage.status("Connection tests completed"))

            # Format results for display
            result_text = ""
            ok_count = 0
            fail_count = 0
            skip_count = 0

            for name, success, error in results:
                if success is None:
                    result_text += f"  [ SKIP ] {name} - {error}\n"
                    skip_count += 1
                elif success:
                    result_text += f"  [  OK  ] {name}\n"
                    ok_count += 1
                else:
                    result_text += f"  [ FAIL ] {name}"
                    if error:
                        result_text += f" - {error}"
                    result_text += "\n"
                    fail_count += 1

            summary = f"\nResults: {ok_count} OK, {fail_count} Failed, {skip_count} Skipped\n"

            # Update chat display with results (via queue for thread safety)
            def show_results():
                self.chat_display.configure(state="normal")
                self.chat_display.insert("end", result_text)
                self.chat_display.insert("end", summary)
                self.chat_display.insert("end", "=" * 50 + "\n\n")
                self.chat_display.configure(state="disabled")
                self.chat_display.see("end")

            self.after(0, show_results)

        self.status_label.configure(text="Testing connections...")

        thread = threading.Thread(target=test_all, daemon=True)
        thread.start()

    def _send_test_query(self):
        """Send a test query to all providers with API keys"""
        self._update_providers()

        test_question = "Hello! Please respond with a short greeting in one sentence."

        # Get providers with API keys
        providers_to_test = []
        for key, info in PROVIDER_INFO.items():
            provider = self.providers.get(key)
            if provider and provider.api_key:
                providers_to_test.append((key, info["name"], provider))

        if not providers_to_test:
            messagebox.showwarning("Warning", "No providers have API keys configured!")
            return

        # Show in chat
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", "\n" + "=" * 50 + "\n")
        self.chat_display.insert("end", f"Test Query: \"{test_question}\"\n")
        self.chat_display.insert("end", f"Sending to {len(providers_to_test)} providers...\n")
        self.chat_display.insert("end", "=" * 50 + "\n\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

        def process_test():
            import time
            results = []

            for key, name, provider in providers_to_test:
                self.ui_queue.put(UIMessage.status(f"Testing {name}..."))

                try:
                    response, elapsed = provider.query(test_question)
                    results.append((name, True, response[:200], elapsed))
                except Exception as e:
                    results.append((name, False, str(e)[:100], 0.0))

            # Show results
            def show_results():
                self.chat_display.configure(state="normal")

                for name, success, text, elapsed in results:
                    status = "OK" if success else "FAIL"
                    self.chat_display.insert("end", f"[{status}] {name} ({elapsed:.2f}s):\n")
                    self.chat_display.insert("end", f"  {text}\n\n")

                self.chat_display.insert("end", "=" * 50 + "\n\n")
                self.chat_display.configure(state="disabled")
                self.chat_display.see("end")

            self.after(0, show_results)
            self.ui_queue.put(UIMessage.status("Test queries completed"))

        self.status_label.configure(text="Sending test queries...")
        thread = threading.Thread(target=process_test, daemon=True)
        thread.start()

    # ==================== Logs ====================

    def _refresh_logs_display(self):
        """Refresh logs display"""
        log_type = self.log_type_var.get()

        self.logs_display.configure(state="normal")
        self.logs_display.delete("1.0", "end")

        responses = self.logger.get_responses_log()
        errors = self.logger.get_errors_log()

        self.logs_stats_label.configure(text=f"Responses: {len(responses)} | Errors: {len(errors)}")

        if log_type in ["all", "responses"]:
            self.logs_display.insert("end", "=" * 50 + "\n")
            self.logs_display.insert("end", "RESPONSES LOG\n")
            self.logs_display.insert("end", "=" * 50 + "\n\n")

            for entry in reversed(responses):
                self.logs_display.insert("end", f"[{entry['timestamp'][:19]}] {entry['provider']}\n")
                self.logs_display.insert("end", f"Model: {entry.get('model', 'N/A')}\n")
                self.logs_display.insert("end", f"Q: {entry['question'][:100]}...\n")
                status = "OK" if entry['success'] else "FAIL"
                self.logs_display.insert("end", f"Status: {status} | Time: {entry['elapsed_time']:.2f}s\n")
                self.logs_display.insert("end", f"Response: {entry['response'][:200]}...\n")
                self.logs_display.insert("end", "-" * 40 + "\n\n")

        if log_type in ["all", "errors"]:
            self.logs_display.insert("end", "\n" + "=" * 50 + "\n")
            self.logs_display.insert("end", "ERRORS LOG\n")
            self.logs_display.insert("end", "=" * 50 + "\n\n")

            for entry in reversed(errors):
                self.logs_display.insert("end", f"[{entry['timestamp'][:19]}] {entry['provider']}\n")
                self.logs_display.insert("end", f"Error: {entry['error']}\n")
                if entry.get('details'):
                    self.logs_display.insert("end", f"Details: {entry['details']}\n")
                self.logs_display.insert("end", "-" * 40 + "\n\n")

        self.logs_display.configure(state="disabled")

    def _export_logs(self):
        """Export logs to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"ai_manager_logs_{timestamp}.txt"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=default_name
        )

        if filepath:
            if self.logger.export_logs(filepath):
                messagebox.showinfo("Success", f"Logs exported to {filepath}")
            else:
                messagebox.showerror("Error", "Failed to export logs")

    def _clear_logs(self):
        """Clear all logs"""
        if messagebox.askyesno("Confirm", "Clear all logs?"):
            self.logger.clear_logs()
            self._refresh_logs_display()

    # ==================== Metrics ====================

    def _refresh_metrics(self):
        """Refresh provider metrics display"""
        for key, card in self.metrics_cards.items():
            metrics = self.logger.get_provider_metrics(PROVIDER_INFO[key]["name"])
            if metrics:
                card.update_metrics(metrics)

    # ==================== Branches ====================

    def _refresh_branches_list(self):
        """Refresh branches dropdown"""
        branches = self.branch_manager.get_branches_list()
        if branches:
            values = [f"{b['name']} ({b['created_at'][:10]})" for b in branches]
            self.branches_combo.configure(values=values)
            if self.branch_manager.current_branch_id:
                for i, b in enumerate(branches):
                    if b['id'] == self.branch_manager.current_branch_id:
                        self.branches_combo.set(values[i])
                        self.current_branch_label.configure(text=f"Current: {b['name']}")
                        break
        else:
            self.branches_combo.configure(values=["No saved branches"])
            self.branches_combo.set("No saved branches")

    def _save_branch(self):
        """Save current conversation as branch"""
        dialog = ctk.CTkInputDialog(text="Enter branch name:", title="Save Branch")
        name = dialog.get_input()
        if not name:
            return

        providers_history = {key: p.conversation_history.copy() for key, p in self.providers.items()}

        self.chat_display.configure(state="normal")
        chat_content = self.chat_display.get("1.0", "end-1c")
        self.chat_display.configure(state="disabled")

        branch_id = self.branch_manager.create_branch(name, providers_history, chat_content)
        if branch_id:
            self._refresh_branches_list()
            self.current_branch_label.configure(text=f"Current: {name}")
            messagebox.showinfo("Success", f"Branch '{name}' saved!")
        else:
            messagebox.showerror("Error", "Failed to save branch")

    def _load_branch(self):
        """Load selected branch"""
        selection = self.branches_combo.get()
        if selection == "No saved branches":
            messagebox.showwarning("Warning", "No branches to load")
            return

        branches = self.branch_manager.get_branches_list()
        values = [f"{b['name']} ({b['created_at'][:10]})" for b in branches]

        selected_idx = None
        for i, v in enumerate(values):
            if v == selection:
                selected_idx = i
                break

        if selected_idx is None:
            return

        branch = branches[selected_idx]
        branch_data = self.branch_manager.load_branch(branch['id'])
        if not branch_data:
            messagebox.showerror("Error", "Failed to load branch")
            return

        # Restore history
        for key, history in branch_data.get("providers_history", {}).items():
            if key in self.providers:
                self.providers[key].conversation_history = history.copy()

        # Restore chat
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.insert("1.0", branch_data.get("chat_content", ""))
        self.chat_display.configure(state="disabled")

        self.current_branch_label.configure(text=f"Current: {branch['name']}")
        messagebox.showinfo("Success", f"Branch '{branch['name']}' loaded!")

    def _delete_branch(self):
        """Delete selected branch"""
        selection = self.branches_combo.get()
        if selection == "No saved branches":
            return

        branches = self.branch_manager.get_branches_list()
        values = [f"{b['name']} ({b['created_at'][:10]})" for b in branches]

        selected_idx = None
        for i, v in enumerate(values):
            if v == selection:
                selected_idx = i
                break

        if selected_idx is None:
            return

        branch = branches[selected_idx]
        if not messagebox.askyesno("Confirm", f"Delete branch '{branch['name']}'?"):
            return

        if self.branch_manager.delete_branch(branch['id']):
            self._refresh_branches_list()
            messagebox.showinfo("Success", f"Branch deleted")
        else:
            messagebox.showerror("Error", "Failed to delete branch")

    # ==================== Save Responses ====================

    def _save_responses(self, question: str, responses: Dict[str, Tuple[str, float]]) -> Optional[str]:
        """Save responses to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ai_responses_{timestamp}.txt"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write(f"AI Manager Response Log\n")
                f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Question: {question}\n\n")
                f.write("-" * 70 + "\n\n")

                for name, (response, elapsed) in responses.items():
                    provider_name = PROVIDER_INFO.get(name, {}).get("name", name)
                    f.write(f"[{provider_name}] ({elapsed:.1f}s)\n")
                    f.write("-" * 40 + "\n")
                    f.write(response + "\n\n")

            return filepath
        except Exception as e:
            self.logger.log_error("FileSystem", f"Failed to save responses: {e}")
            return None
