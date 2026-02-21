"""
crypto.py – Encrypt / decrypt sensitive fields (passwords, usernames)
Uses Fernet symmetric encryption from the cryptography library.

Key is stored in .env or auto-generated on first run and saved to key.secret
"""

import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet

KEY_FILE = Path(os.environ.get("KEY_FILE", "key.secret"))


def _load_or_create_key() -> bytes:
    """Load the encryption key from disk, or generate + save a new one."""
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes().strip()

    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)   # owner read-only
    return key


_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_load_or_create_key())
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a string and return a base64-safe token string."""
    if not plaintext:
        return plaintext
    token = _get_fernet().encrypt(plaintext.encode())
    return token.decode()


def decrypt(token: str) -> str:
    """Decrypt a Fernet token string back to plaintext."""
    if not token:
        return token
    plaintext = _get_fernet().decrypt(token.encode())
    return plaintext.decode()


def rotate_key(new_key: bytes, db_session) -> None:
    """
    Re-encrypt all stored credentials with a new key.
    Call this if you need to rotate the encryption key.
    """
    from database import MonitoredServer
    old_fernet = _get_fernet()
    new_fernet = Fernet(new_key)

    servers = db_session.query(MonitoredServer).all()
    for srv in servers:
        if srv.username:
            plain = old_fernet.decrypt(srv.username.encode()).decode()
            srv.username = new_fernet.encrypt(plain.encode()).decode()
        if srv.password:
            plain = old_fernet.decrypt(srv.password.encode()).decode()
            srv.password = new_fernet.encrypt(plain.encode()).decode()

    db_session.commit()

    global _fernet
    KEY_FILE.write_bytes(new_key)
    _fernet = new_fernet
