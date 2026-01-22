"""
Secure API Key Storage using system keyring
Falls back to encrypted file storage if keyring unavailable
"""

import json
import os
import logging
import base64
import hashlib
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Try to import keyring
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False
    logger.warning("keyring not available, using fallback storage")


class SecureKeyStorage:
    """Secure storage for API keys using system keyring or encrypted fallback"""

    SERVICE_NAME = "AIManager"
    FALLBACK_FILE = "config_secure.dat"

    def __init__(self, config_dir: str = "."):
        self.config_dir = config_dir
        self.fallback_path = os.path.join(config_dir, self.FALLBACK_FILE)
        self._machine_key = self._get_machine_key()

    def _get_machine_key(self) -> bytes:
        """Get a machine-specific key for fallback encryption"""
        # Use combination of username and machine-specific data
        import platform
        machine_id = f"{platform.node()}-{os.getlogin() if hasattr(os, 'getlogin') else 'user'}"
        return hashlib.sha256(machine_id.encode()).digest()

    def _simple_encrypt(self, data: str) -> str:
        """Simple XOR encryption with machine key (fallback only)"""
        key = self._machine_key
        encrypted = bytearray()
        for i, char in enumerate(data.encode('utf-8')):
            encrypted.append(char ^ key[i % len(key)])
        return base64.b64encode(encrypted).decode('ascii')

    def _simple_decrypt(self, data: str) -> str:
        """Simple XOR decryption with machine key (fallback only)"""
        key = self._machine_key
        encrypted = base64.b64decode(data.encode('ascii'))
        decrypted = bytearray()
        for i, byte in enumerate(encrypted):
            decrypted.append(byte ^ key[i % len(key)])
        return decrypted.decode('utf-8')

    def set_key(self, provider: str, api_key: str) -> bool:
        """Store API key securely"""
        if not api_key:
            return self.delete_key(provider)

        try:
            if KEYRING_AVAILABLE:
                keyring.set_password(self.SERVICE_NAME, provider, api_key)
                logger.info(f"Stored key for {provider} in system keyring")
            else:
                # Fallback to encrypted file
                self._save_to_fallback(provider, api_key)
                logger.info(f"Stored key for {provider} in encrypted file")
            return True
        except Exception as e:
            logger.error(f"Failed to store key for {provider}: {e}")
            return False

    def get_key(self, provider: str) -> Optional[str]:
        """Retrieve API key"""
        try:
            if KEYRING_AVAILABLE:
                key = keyring.get_password(self.SERVICE_NAME, provider)
                if key:
                    return key
            # Try fallback
            return self._load_from_fallback(provider)
        except Exception as e:
            logger.error(f"Failed to retrieve key for {provider}: {e}")
            return None

    def delete_key(self, provider: str) -> bool:
        """Delete stored API key"""
        try:
            if KEYRING_AVAILABLE:
                try:
                    keyring.delete_password(self.SERVICE_NAME, provider)
                except keyring.errors.PasswordDeleteError:
                    pass  # Key didn't exist
            # Also remove from fallback
            self._delete_from_fallback(provider)
            return True
        except Exception as e:
            logger.error(f"Failed to delete key for {provider}: {e}")
            return False

    def _save_to_fallback(self, provider: str, api_key: str):
        """Save to encrypted fallback file"""
        data = self._load_fallback_data()
        data[provider] = self._simple_encrypt(api_key)

        with open(self.fallback_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)

    def _load_from_fallback(self, provider: str) -> Optional[str]:
        """Load from encrypted fallback file"""
        data = self._load_fallback_data()
        encrypted = data.get(provider)
        if encrypted:
            try:
                return self._simple_decrypt(encrypted)
            except Exception:
                return None
        return None

    def _delete_from_fallback(self, provider: str):
        """Delete from fallback file"""
        data = self._load_fallback_data()
        if provider in data:
            del data[provider]
            with open(self.fallback_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)

    def _load_fallback_data(self) -> Dict[str, str]:
        """Load fallback data file"""
        if os.path.exists(self.fallback_path):
            try:
                with open(self.fallback_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def get_all_keys(self) -> Dict[str, str]:
        """Get all stored keys"""
        providers = ["openai", "anthropic", "gemini", "deepseek", "groq", "mistral"]
        keys = {}
        for provider in providers:
            key = self.get_key(provider)
            if key:
                keys[provider] = key
        return keys

    def migrate_from_config(self, config_path: str) -> int:
        """Migrate keys from plain config.json to secure storage"""
        migrated = 0
        if not os.path.exists(config_path):
            return migrated

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            key_mappings = {
                "openai_key": "openai",
                "anthropic_key": "anthropic",
                "gemini_key": "gemini",
                "deepseek_key": "deepseek",
                "groq_key": "groq",
                "mistral_key": "mistral"
            }

            for config_key, provider in key_mappings.items():
                if config_key in config and config[config_key]:
                    if self.set_key(provider, config[config_key]):
                        migrated += 1
                        # Remove from plain config
                        config[config_key] = ""

            # Save config without keys
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Migrated {migrated} keys to secure storage")
        except Exception as e:
            logger.error(f"Migration failed: {e}")

        return migrated


# Singleton instance
_storage_instance: Optional[SecureKeyStorage] = None


def get_key_storage(config_dir: str = ".") -> SecureKeyStorage:
    """Get or create key storage instance"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = SecureKeyStorage(config_dir)
    return _storage_instance
