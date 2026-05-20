"""
DPDP Act-compliant encryption for all PII fields stored in the database.

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
The master key is stored in the OS keychain via the `keyring` library.
If the keychain is unavailable, a restricted key file is used as fallback.
"""

import logging
from pathlib import Path

from cryptography.fernet import Fernet

from ca_reminder.config import KEY_FILE, KEYRING_KEY_ACCOUNT, KEYRING_SERVICE

logger = logging.getLogger(__name__)

try:
    import keyring
    _KEYRING_AVAILABLE = True
except ImportError:
    _KEYRING_AVAILABLE = False
    logger.warning("keyring library not available — using key-file fallback.")


class EncryptionManager:
    """
    Manages the Fernet encryption key lifecycle.

    Priority order for key storage:
      1. OS keychain  (most secure — key never touches the filesystem)
      2. Access-restricted file  (fallback for headless / server installs)
    """

    def __init__(self) -> None:
        self._fernet: Fernet = Fernet(self._load_or_create_key())

    # ── Key management ────────────────────────────────────────────────────────

    def _load_or_create_key(self) -> bytes:
        if _KEYRING_AVAILABLE:
            try:
                stored = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY_ACCOUNT)
                if stored:
                    return stored.encode()
                key = Fernet.generate_key()
                keyring.set_password(KEYRING_SERVICE, KEYRING_KEY_ACCOUNT, key.decode())
                logger.info("New encryption key generated and stored in OS keychain.")
                return key
            except Exception as exc:
                logger.warning("Keyring error (%s) — falling back to key file.", exc)

        return self._load_or_create_key_file()

    def _load_or_create_key_file(self) -> bytes:
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if KEY_FILE.exists():
            return KEY_FILE.read_bytes().strip()
        key = Fernet.generate_key()
        KEY_FILE.write_bytes(key)
        try:
            KEY_FILE.chmod(0o600)   # owner read/write only
        except Exception:
            pass
        logger.info("New encryption key generated and stored in key file: %s", KEY_FILE)
        return key

    # ── Public API ────────────────────────────────────────────────────────────

    def encrypt(self, plaintext: str) -> str:
        """Return a URL-safe Fernet token for *plaintext*. Empty strings pass through."""
        if not plaintext:
            return ""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str:
        """Decrypt a Fernet token. Returns empty string on empty input, logs on error."""
        if not token:
            return ""
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except Exception as exc:
            logger.error("Decryption failed: %s", exc)
            return "[DECRYPTION ERROR]"
