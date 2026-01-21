"""
AI Manager Desktop Application v10.0
Modern Neural Network Manager for Windows

Supported AI:
- OpenAI GPT (GPT-4, GPT-3.5)
- Anthropic Claude (Claude 3)
- Google Gemini
- DeepSeek
- Groq (Llama, Mixtral)
- Mistral AI

Features:
- Modern UI with customtkinter
- Parallel requests to all AI providers
- Save responses to text file
- Dark/Light theme support
- Connection testing & status
- Response logging with download
- Error logging
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
import threading
import os
import sys
import json
import requests
import time
import logging
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import webbrowser
from collections import deque

# App info
APP_VERSION = "10.0"
APP_NAME = "AI Manager"


# ==================== Logging System ====================

class AppLogger:
    """Application logger for responses and errors"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.responses_log: deque = deque(maxlen=1000)  # Last 1000 responses
        self.errors_log: deque = deque(maxlen=500)  # Last 500 errors
        self.session_start = datetime.now()

        # Create log directory
        os.makedirs(log_dir, exist_ok=True)

        # Setup file logging
        self._setup_file_logging()

    def _setup_file_logging(self):
        """Setup file-based logging"""
        log_file = os.path.join(
            self.log_dir,
            f"app_{self.session_start.strftime('%Y%m%d_%H%M%S')}.log"
        )

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def log_response(self, provider: str, question: str, response: str, elapsed: float, success: bool = True):
        """Log AI response"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "question": question[:500],  # Truncate for log
            "response": response,
            "elapsed_time": elapsed,
            "success": success
        }
        self.responses_log.append(entry)

        status = "SUCCESS" if success else "FAILED"
        self.logger.info(f"[{provider}] {status} | {elapsed:.2f}s | Q: {question[:100]}...")

    def log_error(self, provider: str, error: str, details: str = ""):
        """Log error"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "error": error,
            "details": details
        }
        self.errors_log.append(entry)
        self.logger.error(f"[{provider}] {error} | {details}")

    def log_connection_test(self, provider: str, success: bool, message: str = ""):
        """Log connection test"""
        status = "CONNECTED" if success else "FAILED"
        self.logger.info(f"[CONNECTION] {provider}: {status} {message}")

    def get_responses_log(self) -> List[dict]:
        """Get all response logs"""
        return list(self.responses_log)

    def get_errors_log(self) -> List[dict]:
        """Get all error logs"""
        return list(self.errors_log)

    def export_logs(self, filepath: str, log_type: str = "all") -> bool:
        """Export logs to file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write(f"AI MANAGER LOGS EXPORT\n")
                f.write(f"Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")

                if log_type in ["all", "responses"]:
                    f.write("\n" + "=" * 70 + "\n")
                    f.write("RESPONSES LOG\n")
                    f.write("=" * 70 + "\n\n")
                    for entry in self.responses_log:
                        f.write(f"[{entry['timestamp']}] {entry['provider']}\n")
                        f.write(f"Question: {entry['question']}\n")
                        f.write(f"Response ({entry['elapsed_time']:.2f}s):\n")
                        f.write(f"{entry['response']}\n")
                        f.write("-" * 50 + "\n\n")

                if log_type in ["all", "errors"]:
                    f.write("\n" + "=" * 70 + "\n")
                    f.write("ERRORS LOG\n")
                    f.write("=" * 70 + "\n\n")
                    for entry in self.errors_log:
                        f.write(f"[{entry['timestamp']}] {entry['provider']}\n")
                        f.write(f"Error: {entry['error']}\n")
                        if entry['details']:
                            f.write(f"Details: {entry['details']}\n")
                        f.write("-" * 50 + "\n\n")

                f.write("\n" + "=" * 70 + "\n")
                f.write(f"Total responses: {len(self.responses_log)}\n")
                f.write(f"Total errors: {len(self.errors_log)}\n")
                f.write("=" * 70 + "\n")

            return True
        except Exception as e:
            self.logger.error(f"Failed to export logs: {e}")
            return False

    def clear_logs(self):
        """Clear in-memory logs"""
        self.responses_log.clear()
        self.errors_log.clear()


# Global logger instance
app_logger = AppLogger()

# Theme settings
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ==================== AI Providers ====================

class AIProvider:
    """Base class for AI providers"""

    def __init__(self, name: str, api_key: str = "", color: str = "#3498db"):
        self.name = name
        self.api_key = api_key
        self.color = color
        self.is_connected = False
        self.enabled = True

    def test_connection(self) -> bool:
        raise NotImplementedError

    def query(self, question: str) -> Tuple[str, float]:
        """Returns (response, time_taken)"""
        raise NotImplementedError


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider"""

    def __init__(self, api_key: str = ""):
        super().__init__("OpenAI GPT", api_key, "#10a37f")
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

    def query(self, question: str) -> Tuple[str, float]:
        if not self.api_key:
            return "Error: Enter OpenAI API key", 0

        start_time = time.time()
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": question}
                ],
                "max_tokens": 4000,
                "temperature": 0.7
            }
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"], elapsed
            elif response.status_code == 401:
                return "Error: Invalid OpenAI API key", elapsed
            elif response.status_code == 429:
                return "Error: OpenAI rate limit exceeded", elapsed
            else:
                return f"Error OpenAI: {response.status_code}", elapsed
        except requests.exceptions.Timeout:
            return "Error: OpenAI request timeout", time.time() - start_time
        except Exception as e:
            return f"Error OpenAI: {str(e)}", time.time() - start_time


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider"""

    def __init__(self, api_key: str = ""):
        super().__init__("Anthropic Claude", api_key, "#cc785c")
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

    def query(self, question: str) -> Tuple[str, float]:
        if not self.api_key:
            return "Error: Enter Anthropic API key", 0

        start_time = time.time()
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": question}]
            }
            response = requests.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=data,
                timeout=120
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                return response.json()["content"][0]["text"], elapsed
            elif response.status_code == 401:
                return "Error: Invalid Anthropic API key", elapsed
            elif response.status_code == 429:
                return "Error: Anthropic rate limit exceeded", elapsed
            else:
                return f"Error Anthropic: {response.status_code}", elapsed
        except requests.exceptions.Timeout:
            return "Error: Anthropic request timeout", time.time() - start_time
        except Exception as e:
            return f"Error Anthropic: {str(e)}", time.time() - start_time


class GeminiProvider(AIProvider):
    """Google Gemini provider"""

    def __init__(self, api_key: str = ""):
        super().__init__("Gemini", api_key, "#4285f4")
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

    def query(self, question: str) -> Tuple[str, float]:
        if not self.api_key:
            return "Error: Enter Gemini API key", 0

        start_time = time.time()
        try:
            url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "contents": [{"parts": [{"text": question}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4000}
            }
            response = requests.post(url, headers=headers, json=data, timeout=120)
            elapsed = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    return result["candidates"][0]["content"]["parts"][0]["text"], elapsed
                return "Error: Empty response from Gemini", elapsed
            elif response.status_code == 403:
                return "Error: Invalid Gemini API key", elapsed
            elif response.status_code == 429:
                return "Error: Gemini rate limit exceeded", elapsed
            else:
                return f"Error Gemini: {response.status_code}", elapsed
        except requests.exceptions.Timeout:
            return "Error: Gemini request timeout", time.time() - start_time
        except Exception as e:
            return f"Error Gemini: {str(e)}", time.time() - start_time


class DeepSeekProvider(AIProvider):
    """DeepSeek provider"""

    def __init__(self, api_key: str = ""):
        super().__init__("DeepSeek", api_key, "#5436da")
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

    def query(self, question: str) -> Tuple[str, float]:
        if not self.api_key:
            return "Error: Enter DeepSeek API key", 0

        start_time = time.time()
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": question}
                ],
                "max_tokens": 4000,
                "temperature": 0.7
            }
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"], elapsed
            elif response.status_code == 401:
                return "Error: Invalid DeepSeek API key", elapsed
            elif response.status_code == 402:
                return "Error: Insufficient DeepSeek balance", elapsed
            elif response.status_code == 429:
                return "Error: DeepSeek rate limit exceeded", elapsed
            else:
                return f"Error DeepSeek: {response.status_code}", elapsed
        except requests.exceptions.Timeout:
            return "Error: DeepSeek request timeout", time.time() - start_time
        except Exception as e:
            return f"Error DeepSeek: {str(e)}", time.time() - start_time


class GroqProvider(AIProvider):
    """Groq provider"""

    def __init__(self, api_key: str = ""):
        super().__init__("Groq", api_key, "#f55036")
        self.base_url = "https://api.groq.com/openai/v1"
        self.model = "llama-3.3-70b-versatile"

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

    def query(self, question: str) -> Tuple[str, float]:
        if not self.api_key:
            return "Error: Enter Groq API key", 0

        start_time = time.time()
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": question}
                ],
                "max_tokens": 4000,
                "temperature": 0.7
            }
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"], elapsed
            elif response.status_code == 401:
                return "Error: Invalid Groq API key", elapsed
            elif response.status_code == 429:
                return "Error: Groq rate limit exceeded", elapsed
            else:
                return f"Error Groq: {response.status_code}", elapsed
        except requests.exceptions.Timeout:
            return "Error: Groq request timeout", time.time() - start_time
        except Exception as e:
            return f"Error Groq: {str(e)}", time.time() - start_time


class MistralProvider(AIProvider):
    """Mistral AI provider"""

    def __init__(self, api_key: str = ""):
        super().__init__("Mistral AI", api_key, "#ff7000")
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

    def query(self, question: str) -> Tuple[str, float]:
        if not self.api_key:
            return "Error: Enter Mistral AI API key", 0

        start_time = time.time()
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": question}],
                "max_tokens": 4000,
                "temperature": 0.7
            }
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"], elapsed
            elif response.status_code == 401:
                return "Error: Invalid Mistral AI API key", elapsed
            elif response.status_code == 429:
                return "Error: Mistral AI rate limit exceeded", elapsed
            else:
                return f"Error Mistral AI: {response.status_code}", elapsed
        except requests.exceptions.Timeout:
            return "Error: Mistral AI request timeout", time.time() - start_time
        except Exception as e:
            return f"Error Mistral AI: {str(e)}", time.time() - start_time


# ==================== UI Components ====================

class ModernSwitch(ctk.CTkFrame):
    """Modern toggle switch with label"""

    def __init__(self, master, text: str, color: str = "#3498db", command=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.color = color
        self.command = command

        # Status indicator
        self.indicator = ctk.CTkLabel(
            self, text="", width=12, height=12,
            fg_color="gray", corner_radius=6
        )
        self.indicator.pack(side="left", padx=(0, 8))

        # Label
        self.label = ctk.CTkLabel(self, text=text, font=ctk.CTkFont(size=13))
        self.label.pack(side="left", fill="x", expand=True)

        # Switch
        self.switch_var = ctk.BooleanVar(value=True)
        self.switch = ctk.CTkSwitch(
            self, text="", variable=self.switch_var,
            command=self._on_toggle, width=40,
            progress_color=color
        )
        self.switch.pack(side="right")

    def _on_toggle(self):
        if self.command:
            self.command()

    def get(self) -> bool:
        return self.switch_var.get()

    def set(self, value: bool):
        self.switch_var.set(value)

    def set_status(self, connected: bool):
        color = "#2ecc71" if connected else "#e74c3c"
        self.indicator.configure(fg_color=color)


class APIKeyCard(ctk.CTkFrame):
    """Modern card for API key input"""

    def __init__(self, master, name: str, color: str, url: str, description: str, **kwargs):
        super().__init__(master, corner_radius=12, **kwargs)

        self.name = name
        self.url = url
        self.show_key = False

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

        # Key input row
        key_row = ctk.CTkFrame(content, fg_color="transparent")
        key_row.pack(fill="x")

        self.key_entry = ctk.CTkEntry(
            key_row, placeholder_text="Enter API key...",
            show="*", height=36, corner_radius=8
        )
        self.key_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

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

        # Add right-click context menu
        self._create_entry_menu()

    def _toggle_visibility(self):
        self.show_key = not self.show_key
        self.key_entry.configure(show="" if self.show_key else "*")
        self.toggle_btn.configure(text="Hide" if self.show_key else "Show")

    def _paste_key(self):
        """Paste API key from clipboard"""
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                # Clear and paste
                self.key_entry.delete(0, "end")
                self.key_entry.insert(0, clipboard_text.strip())
        except:
            pass

    def _create_entry_menu(self):
        """Create right-click context menu for entry"""
        self.entry_menu = tk.Menu(self, tearoff=0)
        self.entry_menu.add_command(label="Paste", command=self._paste_key)
        self.entry_menu.add_command(label="Clear", command=lambda: self.key_entry.delete(0, "end"))
        self.entry_menu.add_separator()
        self.entry_menu.add_command(label="Select All", command=self._select_all_entry)
        self.entry_menu.add_command(label="Copy", command=self._copy_entry)

        self.key_entry.bind("<Button-3>", self._show_entry_menu)

    def _show_entry_menu(self, event):
        """Show context menu"""
        try:
            self.entry_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.entry_menu.grab_release()

    def _select_all_entry(self):
        """Select all text in entry"""
        self.key_entry.select_range(0, "end")
        self.key_entry.focus()

    def _copy_entry(self):
        """Copy entry content"""
        try:
            content = self.key_entry.get()
            if content:
                self.clipboard_clear()
                self.clipboard_append(content)
        except:
            pass

    def _darken(self, hex_color: str) -> str:
        """Darken a hex color"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        darker = tuple(max(0, int(c * 0.8)) for c in rgb)
        return f"#{darker[0]:02x}{darker[1]:02x}{darker[2]:02x}"

    def get_key(self) -> str:
        return self.key_entry.get()

    def set_key(self, key: str):
        self.key_entry.delete(0, "end")
        self.key_entry.insert(0, key)

    def set_status(self, connected: bool):
        color = "#2ecc71" if connected else "#e74c3c"
        self.status_indicator.configure(fg_color=color)


# ==================== Main Application ====================

class AIManagerApp(ctk.CTk):
    """Main application window"""

    PROVIDER_INFO = [
        ("OpenAI GPT", "openai", "#10a37f", "https://platform.openai.com/api-keys",
         "GPT-4o, GPT-4, GPT-3.5 Turbo"),
        ("Anthropic Claude", "anthropic", "#cc785c", "https://console.anthropic.com/",
         "Claude 3.5 Sonnet, Claude 3 Haiku"),
        ("Gemini", "gemini", "#4285f4", "https://aistudio.google.com/apikey",
         "Gemini 1.5 Flash, Gemini 1.5 Pro"),
        ("DeepSeek", "deepseek", "#5436da", "https://platform.deepseek.com/",
         "DeepSeek Chat, DeepSeek Coder"),
        ("Groq", "groq", "#f55036", "https://console.groq.com/keys",
         "Llama 3.3, Mixtral (Ultra fast!)"),
        ("Mistral AI", "mistral", "#ff7000", "https://console.mistral.ai/api-keys/",
         "Mistral Small, Mistral Large")
    ]

    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # Config
        self.config_file = "config.json"
        self.config = self._load_config()
        self.output_dir = self.config.get("output_dir", os.path.expanduser("~/Documents"))

        # Initialize providers
        self.providers: Dict[str, AIProvider] = {}
        self._init_providers()

        # UI variables
        self.api_cards: Dict[str, APIKeyCard] = {}
        self.provider_switches: Dict[str, ModernSwitch] = {}
        self.is_processing = False

        # Create UI
        self._create_ui()

        # Load config to UI
        self._load_config_to_ui()

        # Check connections in background
        self.after(500, self._check_connections_background)

    def _load_config(self) -> dict:
        """Load configuration"""
        default_config = {
            "api_keys": {
                "openai": "", "anthropic": "", "gemini": "",
                "deepseek": "", "groq": "", "mistral": ""
            },
            "output_dir": os.path.expanduser("~/Documents"),
            "theme": "dark"
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
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

    def _save_config(self):
        """Save configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _init_providers(self):
        """Initialize AI providers"""
        self.providers = {
            "OpenAI GPT": OpenAIProvider(self.config["api_keys"].get("openai", "")),
            "Anthropic Claude": AnthropicProvider(self.config["api_keys"].get("anthropic", "")),
            "Gemini": GeminiProvider(self.config["api_keys"].get("gemini", "")),
            "DeepSeek": DeepSeekProvider(self.config["api_keys"].get("deepseek", "")),
            "Groq": GroqProvider(self.config["api_keys"].get("groq", "")),
            "Mistral AI": MistralProvider(self.config["api_keys"].get("mistral", ""))
        }

    def _create_ui(self):
        """Create main UI"""
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left sidebar
        self._create_sidebar()

        # Main content
        self._create_main_content()

    def _create_sidebar(self):
        """Create left sidebar"""
        sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Logo/Title
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            logo_frame, text=APP_NAME,
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame, text=f"v{APP_VERSION}",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        ).pack(anchor="w")

        # Divider
        ctk.CTkFrame(sidebar, height=2, fg_color="gray30").pack(fill="x", padx=20, pady=10)

        # AI Selection section
        ctk.CTkLabel(
            sidebar, text="Active AI Providers",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=(10, 15))

        # Provider switches
        switches_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        switches_frame.pack(fill="x", padx=20)

        for name, key, color, url, desc in self.PROVIDER_INFO:
            switch = ModernSwitch(switches_frame, text=name, color=color)
            switch.pack(fill="x", pady=4)
            self.provider_switches[name] = switch

        # Select/Deselect all buttons
        btn_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkButton(
            btn_frame, text="Select All", height=32,
            corner_radius=8, fg_color="gray30",
            command=self._select_all_providers
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(
            btn_frame, text="Deselect All", height=32,
            corner_radius=8, fg_color="gray30",
            command=self._deselect_all_providers
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Connection test buttons
        test_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        test_frame.pack(fill="x", padx=20, pady=(10, 0))

        ctk.CTkButton(
            test_frame, text="Test Connections",
            height=36, corner_radius=8,
            fg_color="#27ae60", hover_color="#1e8449",
            command=self._test_all_connections
        ).pack(fill="x", pady=(0, 5))

        ctk.CTkButton(
            test_frame, text="Send Test Query",
            height=36, corner_radius=8,
            fg_color="#3498db", hover_color="#2980b9",
            command=self._send_test_query
        ).pack(fill="x")

        # Connection status display
        self.connection_status_label = ctk.CTkLabel(
            sidebar, text="Status: Not tested",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.connection_status_label.pack(anchor="w", padx=20, pady=(5, 0))

        # Divider
        ctk.CTkFrame(sidebar, height=2, fg_color="gray30").pack(fill="x", padx=20, pady=10)

        # Output directory
        ctk.CTkLabel(
            sidebar, text="Output Directory",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=(10, 10))

        dir_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        dir_frame.pack(fill="x", padx=20)

        self.output_dir_label = ctk.CTkLabel(
            dir_frame, text=self._truncate_path(self.output_dir),
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w"
        )
        self.output_dir_label.pack(fill="x")

        ctk.CTkButton(
            dir_frame, text="Change Directory",
            height=32, corner_radius=8, fg_color="gray30",
            command=self._select_output_dir
        ).pack(fill="x", pady=(8, 0))

        # Theme toggle at bottom
        theme_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        theme_frame.pack(side="bottom", fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            theme_frame, text="Dark Mode",
            font=ctk.CTkFont(size=12)
        ).pack(side="left")

        self.theme_switch = ctk.CTkSwitch(
            theme_frame, text="",
            command=self._toggle_theme
        )
        self.theme_switch.pack(side="right")
        self.theme_switch.select()

    def _create_main_content(self):
        """Create main content area"""
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # Tabs
        self.tabview = ctk.CTkTabview(main, corner_radius=12)
        self.tabview.grid(row=0, column=0, sticky="nsew", rowspan=2)

        # Create tabs
        self.tab_chat = self.tabview.add("Chat")
        self.tab_settings = self.tabview.add("API Settings")
        self.tab_logs = self.tabview.add("Logs")

        self._create_chat_tab()
        self._create_settings_tab()
        self._create_logs_tab()

    def _create_chat_tab(self):
        """Create chat tab"""
        self.tab_chat.grid_rowconfigure(1, weight=1)
        self.tab_chat.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self.tab_chat, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            header, text="Ask AI",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left")

        # Status label
        self.status_label = ctk.CTkLabel(
            header, text="Ready",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(side="right")

        # Chat display
        self.chat_display = ctk.CTkTextbox(
            self.tab_chat, corner_radius=12,
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled"
        )
        self.chat_display.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        # Input area
        input_frame = ctk.CTkFrame(self.tab_chat, fg_color="transparent")
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)

        self.chat_input = ctk.CTkTextbox(
            input_frame, height=100, corner_radius=12,
            font=ctk.CTkFont(size=13)
        )
        self.chat_input.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        # Keyboard shortcuts
        self.chat_input.bind("<Control-Return>", lambda e: self._send_query())
        # Note: Ctrl+V works by default in CTkTextbox

        # Context menu for input
        self._create_context_menu()

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
            btn_frame, text="Paste", width=100, height=30,
            corner_radius=10, fg_color="#2980b9", hover_color="#1f618d",
            command=self._paste_from_clipboard
        ).pack(pady=(0, 4))

        ctk.CTkButton(
            btn_frame, text="Clear", width=100, height=30,
            corner_radius=10, fg_color="gray30",
            command=self._clear_chat
        ).pack()

        # Progress bar
        self.progress = ctk.CTkProgressBar(self.tab_chat, mode="indeterminate", height=3)

    def _create_settings_tab(self):
        """Create settings tab"""
        # Scrollable frame for API cards
        scroll = ctk.CTkScrollableFrame(self.tab_settings, corner_radius=0)
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(
            scroll, text="API Keys Configuration",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w", pady=(0, 15))

        # API cards grid
        cards_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        cards_frame.pack(fill="x")

        for i, (name, key, color, url, desc) in enumerate(self.PROVIDER_INFO):
            card = APIKeyCard(cards_frame, name, color, url, desc)
            card.pack(fill="x", pady=8)
            self.api_cards[key] = card

        # Save button
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            btn_frame, text="Save Settings", height=45,
            corner_radius=10, font=ctk.CTkFont(size=14, weight="bold"),
            command=self._save_settings
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Test Connections", height=45,
            corner_radius=10, fg_color="gray30",
            command=self._check_all_connections
        ).pack(side="left")

    def _create_logs_tab(self):
        """Create logs tab"""
        self.tab_logs.grid_rowconfigure(1, weight=1)
        self.tab_logs.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            header, text="Logs & History",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(side="left")

        # Stats label
        self.logs_stats_label = ctk.CTkLabel(
            header, text="Responses: 0 | Errors: 0",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.logs_stats_label.pack(side="right")

        # Log type selector
        selector_frame = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        selector_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.log_type_var = ctk.StringVar(value="responses")

        ctk.CTkRadioButton(
            selector_frame, text="Responses",
            variable=self.log_type_var, value="responses",
            command=self._refresh_logs_display
        ).pack(side="left", padx=(0, 20))

        ctk.CTkRadioButton(
            selector_frame, text="Errors",
            variable=self.log_type_var, value="errors",
            command=self._refresh_logs_display
        ).pack(side="left", padx=(0, 20))

        ctk.CTkRadioButton(
            selector_frame, text="All",
            variable=self.log_type_var, value="all",
            command=self._refresh_logs_display
        ).pack(side="left")

        # Logs display
        self.logs_display = ctk.CTkTextbox(
            self.tab_logs, corner_radius=12,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled"
        )
        self.logs_display.grid(row=2, column=0, sticky="nsew", pady=(0, 10))

        # Buttons
        btn_frame = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew")

        ctk.CTkButton(
            btn_frame, text="Refresh", height=36,
            corner_radius=8, fg_color="gray30",
            command=self._refresh_logs_display
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Export Logs", height=36,
            corner_radius=8, fg_color="#27ae60", hover_color="#1e8449",
            command=self._export_logs
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Export Responses", height=36,
            corner_radius=8, fg_color="#3498db", hover_color="#2980b9",
            command=lambda: self._export_logs("responses")
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Export Errors", height=36,
            corner_radius=8, fg_color="#e74c3c", hover_color="#c0392b",
            command=lambda: self._export_logs("errors")
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Clear Logs", height=36,
            corner_radius=8, fg_color="gray30",
            command=self._clear_logs
        ).pack(side="right")

    def _refresh_logs_display(self):
        """Refresh logs display"""
        log_type = self.log_type_var.get()

        self.logs_display.configure(state="normal")
        self.logs_display.delete("1.0", "end")

        responses = app_logger.get_responses_log()
        errors = app_logger.get_errors_log()

        # Update stats
        self.logs_stats_label.configure(
            text=f"Responses: {len(responses)} | Errors: {len(errors)}"
        )

        if log_type in ["all", "responses"]:
            self.logs_display.insert("end", "=" * 50 + "\n")
            self.logs_display.insert("end", "RESPONSES LOG\n")
            self.logs_display.insert("end", "=" * 50 + "\n\n")

            for entry in reversed(responses):  # Newest first
                self.logs_display.insert("end", f"[{entry['timestamp'][:19]}] {entry['provider']}\n")
                self.logs_display.insert("end", f"Q: {entry['question'][:100]}...\n")
                status = "OK" if entry['success'] else "FAIL"
                self.logs_display.insert("end", f"Status: {status} | Time: {entry['elapsed_time']:.2f}s\n")
                self.logs_display.insert("end", f"Response: {entry['response'][:200]}...\n")
                self.logs_display.insert("end", "-" * 40 + "\n\n")

        if log_type in ["all", "errors"]:
            self.logs_display.insert("end", "\n" + "=" * 50 + "\n")
            self.logs_display.insert("end", "ERRORS LOG\n")
            self.logs_display.insert("end", "=" * 50 + "\n\n")

            for entry in reversed(errors):  # Newest first
                self.logs_display.insert("end", f"[{entry['timestamp'][:19]}] {entry['provider']}\n")
                self.logs_display.insert("end", f"Error: {entry['error']}\n")
                if entry['details']:
                    self.logs_display.insert("end", f"Details: {entry['details']}\n")
                self.logs_display.insert("end", "-" * 40 + "\n\n")

        self.logs_display.configure(state="disabled")

    def _export_logs(self, log_type: str = "all"):
        """Export logs to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"ai_manager_logs_{log_type}_{timestamp}.txt"

        filepath = filedialog.asksaveasfilename(
            title="Export Logs",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if filepath:
            if app_logger.export_logs(filepath, log_type):
                messagebox.showinfo("Success", f"Logs exported to:\n{filepath}")
                self.status_label.configure(text=f"Logs exported")
            else:
                messagebox.showerror("Error", "Failed to export logs")

    def _clear_logs(self):
        """Clear in-memory logs"""
        if messagebox.askyesno("Confirm", "Clear all in-memory logs?"):
            app_logger.clear_logs()
            self._refresh_logs_display()
            self.status_label.configure(text="Logs cleared")

    def _test_all_connections(self):
        """Test all connections with detailed status"""
        self.connection_status_label.configure(text="Testing connections...")

        thread = threading.Thread(target=self._test_connections_thread, daemon=True)
        thread.start()

    def _test_connections_thread(self):
        """Thread for testing connections"""
        self._update_providers()

        results = {}
        connected = 0
        total = 0

        key_map = {
            "openai": "OpenAI GPT",
            "anthropic": "Anthropic Claude",
            "gemini": "Gemini",
            "deepseek": "DeepSeek",
            "groq": "Groq",
            "mistral": "Mistral AI"
        }

        for key, name in key_map.items():
            if name in self.providers and self.provider_switches[name].get():
                total += 1
                status = self.providers[name].test_connection()
                results[name] = status

                if status:
                    connected += 1

                # Log the test
                app_logger.log_connection_test(name, status)

                # Update UI
                self.after(0, lambda n=name, s=status: self._update_connection_status(n, s))
                self.after(0, lambda k=key, s=status: self._update_card_status(k, s))

        # Update status label
        status_text = f"Connected: {connected}/{total}"
        self.after(0, lambda: self.connection_status_label.configure(
            text=status_text,
            text_color="#2ecc71" if connected == total else "#e74c3c"
        ))

    def _send_test_query(self):
        """Send a simple test query to all selected providers"""
        selected = [name for name, switch in self.provider_switches.items() if switch.get()]

        if not selected:
            messagebox.showwarning("Warning", "Please select at least one AI provider!")
            return

        # Simple test question
        test_question = "Hello! Please respond with 'OK' if you can receive this message."

        self.connection_status_label.configure(text="Sending test query...")
        self._add_to_chat(f"[TEST] Sending test query to {len(selected)} providers...\n", "system")

        self._update_providers()

        thread = threading.Thread(
            target=self._process_test_query,
            args=(test_question, selected),
            daemon=True
        )
        thread.start()

    def _process_test_query(self, question: str, providers: List[str]):
        """Process test query"""
        results = {}

        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            futures = {}
            for name in providers:
                if name in self.providers:
                    future = executor.submit(self.providers[name].query, question)
                    futures[future] = name

            for future in as_completed(futures):
                name = futures[future]
                try:
                    response, elapsed = future.result()
                    success = not response.startswith("Error")
                    results[name] = (success, elapsed)

                    # Log response
                    app_logger.log_response(name, question, response, elapsed, success)

                    # Show result
                    status = "OK" if success else "FAIL"
                    self.after(0, lambda n=name, s=status, t=elapsed:
                        self._add_to_chat(f"[TEST] {n}: {s} ({t:.2f}s)\n", "response"))

                except Exception as e:
                    results[name] = (False, 0)
                    app_logger.log_error(name, str(e), "Test query failed")
                    self.after(0, lambda n=name, e=str(e):
                        self._add_to_chat(f"[TEST] {n}: ERROR - {e}\n", "error"))

        # Summary
        success_count = sum(1 for v in results.values() if v[0])
        total = len(results)

        self.after(0, lambda: self._add_to_chat(
            f"\n[TEST COMPLETE] {success_count}/{total} providers responded successfully\n\n",
            "system"
        ))
        self.after(0, lambda: self.connection_status_label.configure(
            text=f"Test: {success_count}/{total} OK",
            text_color="#2ecc71" if success_count == total else "#e74c3c"
        ))

    # ==================== Actions ====================

    def _select_all_providers(self):
        for switch in self.provider_switches.values():
            switch.set(True)

    def _deselect_all_providers(self):
        for switch in self.provider_switches.values():
            switch.set(False)

    def _select_output_dir(self):
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir
        )
        if directory:
            self.output_dir = directory
            self.config["output_dir"] = directory
            self._save_config()
            self.output_dir_label.configure(text=self._truncate_path(directory))

    def _truncate_path(self, path: str, max_len: int = 35) -> str:
        if len(path) <= max_len:
            return path
        return "..." + path[-(max_len - 3):]

    def _toggle_theme(self):
        mode = "dark" if self.theme_switch.get() else "light"
        ctk.set_appearance_mode(mode)
        self.config["theme"] = mode
        self._save_config()

    def _load_config_to_ui(self):
        """Load config to UI"""
        for key, card in self.api_cards.items():
            card.set_key(self.config["api_keys"].get(key, ""))

        # Theme
        if self.config.get("theme") == "light":
            self.theme_switch.deselect()
            ctk.set_appearance_mode("light")

    def _save_settings(self):
        """Save API settings"""
        for key, card in self.api_cards.items():
            self.config["api_keys"][key] = card.get_key()

        self._update_providers()
        self._save_config()

        messagebox.showinfo("Success", "Settings saved successfully!")
        self._check_all_connections()

    def _update_providers(self):
        """Update provider API keys"""
        key_map = {
            "OpenAI GPT": "openai",
            "Anthropic Claude": "anthropic",
            "Gemini": "gemini",
            "DeepSeek": "deepseek",
            "Groq": "groq",
            "Mistral AI": "mistral"
        }
        for name, key in key_map.items():
            if name in self.providers:
                self.providers[name].api_key = self.config["api_keys"].get(key, "")

    def _check_connections_background(self):
        """Check connections in background"""
        thread = threading.Thread(target=self._check_all_connections_thread, daemon=True)
        thread.start()

    def _check_all_connections(self):
        """Check all connections"""
        thread = threading.Thread(target=self._check_all_connections_thread, daemon=True)
        thread.start()

    def _check_all_connections_thread(self):
        """Thread for checking connections"""
        self._update_providers()

        key_map = {
            "openai": "OpenAI GPT",
            "anthropic": "Anthropic Claude",
            "gemini": "Gemini",
            "deepseek": "DeepSeek",
            "groq": "Groq",
            "mistral": "Mistral AI"
        }

        for key, name in key_map.items():
            if name in self.providers:
                status = self.providers[name].test_connection()

                # Update UI
                self.after(0, lambda n=name, s=status: self._update_connection_status(n, s))
                self.after(0, lambda k=key, s=status: self._update_card_status(k, s))

    def _update_connection_status(self, name: str, status: bool):
        if name in self.provider_switches:
            self.provider_switches[name].set_status(status)

    def _update_card_status(self, key: str, status: bool):
        if key in self.api_cards:
            self.api_cards[key].set_status(status)

    def _send_query(self):
        """Send query to selected providers"""
        if self.is_processing:
            return

        question = self.chat_input.get("1.0", "end-1c").strip()
        if not question:
            return

        # Get selected providers
        selected = [name for name, switch in self.provider_switches.items() if switch.get()]
        if not selected:
            messagebox.showwarning("Warning", "Please select at least one AI provider!")
            return

        # Update UI
        self.is_processing = True
        self.send_btn.configure(state="disabled")
        self.progress.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self.progress.start()
        self.status_label.configure(text=f"Querying {len(selected)} AI providers...")

        # Add user message to chat
        self._add_to_chat(f"You: {question}\n", "user")
        self._add_to_chat("-" * 60 + "\n", "divider")

        # Clear input
        self.chat_input.delete("1.0", "end")

        # Update providers
        self._update_providers()

        # Start query thread
        thread = threading.Thread(
            target=self._process_query,
            args=(question, selected),
            daemon=True
        )
        thread.start()

    def _process_query(self, question: str, providers: List[str]):
        """Process query in parallel"""
        responses = {}
        total_time = 0

        # Use ThreadPoolExecutor for parallel requests
        with ThreadPoolExecutor(max_workers=len(providers)) as executor:
            futures = {}
            for name in providers:
                if name in self.providers:
                    future = executor.submit(self.providers[name].query, question)
                    futures[future] = name

            for future in as_completed(futures):
                name = futures[future]
                try:
                    response, elapsed = future.result()
                    responses[name] = (response, elapsed)
                    total_time = max(total_time, elapsed)

                    # Log response
                    success = not response.startswith("Error")
                    app_logger.log_response(name, question, response, elapsed, success)

                    if not success:
                        app_logger.log_error(name, response, f"Query: {question[:100]}")

                    # Update UI immediately
                    self.after(0, lambda n=name, r=response, t=elapsed: self._show_response(n, r, t))
                except Exception as e:
                    responses[name] = (f"Error: {str(e)}", 0)
                    # Log error
                    app_logger.log_error(name, str(e), f"Exception during query: {question[:100]}")
                    self.after(0, lambda n=name, e=str(e): self._show_response(n, f"Error: {e}", 0))

        # Save to file
        filepath = self._save_responses(question, responses)

        # Finish
        self.after(0, lambda: self._finish_query(len(responses), total_time, filepath))

    def _show_response(self, name: str, response: str, elapsed: float):
        """Show response in chat"""
        color = self.providers[name].color if name in self.providers else "#3498db"
        header = f"\n[{name}] ({elapsed:.1f}s)\n"
        self._add_to_chat(header, "header")
        self._add_to_chat(response + "\n", "response")
        self._add_to_chat("-" * 60 + "\n", "divider")

    def _finish_query(self, count: int, total_time: float, filepath: str):
        """Finish query processing"""
        self.is_processing = False
        self.send_btn.configure(state="normal")
        self.progress.stop()
        self.progress.grid_forget()
        self.status_label.configure(text=f"Completed: {count} responses in {total_time:.1f}s")

        if filepath:
            self._add_to_chat(f"\nSaved to: {filepath}\n\n", "info")

    def _add_to_chat(self, text: str, tag: str = None):
        """Add text to chat display"""
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text)
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def _clear_chat(self):
        """Clear chat display"""
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        self.status_label.configure(text="Ready")

    def _paste_from_clipboard(self):
        """Paste text from clipboard to input field"""
        try:
            # Get clipboard content
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                # Delete selected text if any
                try:
                    self.chat_input.delete("sel.first", "sel.last")
                except:
                    pass
                # Insert at cursor position (INSERT = current cursor position)
                self.chat_input.insert("insert", clipboard_text)
                self.chat_input.see("insert")
                self.status_label.configure(text=f"Pasted {len(clipboard_text)} characters")
        except tk.TclError:
            # Clipboard is empty or contains non-text data
            self.status_label.configure(text="Clipboard is empty or contains non-text")
        except Exception as e:
            self.status_label.configure(text=f"Paste error: {str(e)[:30]}")

    def _copy_to_clipboard(self, text: str):
        """Copy text to clipboard"""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.status_label.configure(text="Copied to clipboard")
        except Exception:
            pass

    def _create_context_menu(self):
        """Create right-click context menu for text widgets"""
        import tkinter as tk

        # Context menu for input
        self.input_menu = tk.Menu(self, tearoff=0)
        self.input_menu.add_command(label="Paste", command=self._paste_from_clipboard, accelerator="Ctrl+V")
        self.input_menu.add_command(label="Cut", command=self._cut_input)
        self.input_menu.add_command(label="Copy", command=self._copy_input)
        self.input_menu.add_separator()
        self.input_menu.add_command(label="Select All", command=self._select_all_input, accelerator="Ctrl+A")
        self.input_menu.add_command(label="Clear", command=lambda: self.chat_input.delete("1.0", "end"))

        # Context menu for chat display
        self.chat_menu = tk.Menu(self, tearoff=0)
        self.chat_menu.add_command(label="Copy", command=self._copy_chat_selection)
        self.chat_menu.add_command(label="Copy All", command=self._copy_all_chat)
        self.chat_menu.add_separator()
        self.chat_menu.add_command(label="Select All", command=self._select_all_chat)
        self.chat_menu.add_command(label="Clear Chat", command=self._clear_chat)

        # Bind right-click
        self.chat_input.bind("<Button-3>", self._show_input_menu)
        self.chat_display.bind("<Button-3>", self._show_chat_menu)

        # Bind Ctrl+A for select all
        self.chat_input.bind("<Control-a>", lambda e: self._select_all_input())
        self.chat_input.bind("<Control-A>", lambda e: self._select_all_input())

    def _show_input_menu(self, event):
        """Show context menu for input"""
        try:
            self.input_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.input_menu.grab_release()

    def _show_chat_menu(self, event):
        """Show context menu for chat"""
        try:
            self.chat_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.chat_menu.grab_release()

    def _cut_input(self):
        """Cut selected text from input"""
        try:
            selected = self.chat_input.get("sel.first", "sel.last")
            if selected:
                self._copy_to_clipboard(selected)
                self.chat_input.delete("sel.first", "sel.last")
        except Exception:
            pass

    def _copy_input(self):
        """Copy selected text from input"""
        try:
            selected = self.chat_input.get("sel.first", "sel.last")
            if selected:
                self._copy_to_clipboard(selected)
        except Exception:
            pass

    def _select_all_input(self):
        """Select all text in input"""
        self.chat_input.tag_add("sel", "1.0", "end-1c")
        return "break"

    def _copy_chat_selection(self):
        """Copy selected text from chat"""
        try:
            self.chat_display.configure(state="normal")
            selected = self.chat_display.get("sel.first", "sel.last")
            self.chat_display.configure(state="disabled")
            if selected:
                self._copy_to_clipboard(selected)
        except Exception:
            pass

    def _copy_all_chat(self):
        """Copy all chat content"""
        self.chat_display.configure(state="normal")
        content = self.chat_display.get("1.0", "end-1c")
        self.chat_display.configure(state="disabled")
        if content.strip():
            self._copy_to_clipboard(content)

    def _select_all_chat(self):
        """Select all text in chat"""
        self.chat_display.configure(state="normal")
        self.chat_display.tag_add("sel", "1.0", "end-1c")
        self.chat_display.configure(state="disabled")

    def _save_responses(self, question: str, responses: Dict[str, Tuple[str, float]]) -> Optional[str]:
        """Save responses to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ai_responses_{timestamp}.txt"
            filepath = os.path.join(self.output_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write(f"AI MANAGER RESPONSES\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 70 + "\n\n")

                f.write("QUESTION:\n")
                f.write("-" * 70 + "\n")
                f.write(question + "\n")
                f.write("-" * 70 + "\n\n")

                for name, (response, elapsed) in responses.items():
                    f.write(f"\n{'='*70}\n")
                    f.write(f"[{name}] - Response time: {elapsed:.2f}s\n")
                    f.write(f"{'='*70}\n\n")
                    f.write(response + "\n")

                f.write("\n" + "=" * 70 + "\n")
                f.write(f"Total providers: {len(responses)}\n")
                f.write("=" * 70 + "\n")

            return filepath
        except Exception as e:
            print(f"Error saving file: {e}")
            return None


def main():
    """Entry point"""
    # Windows DPI awareness
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

    app = AIManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
