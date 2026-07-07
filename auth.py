"""
auth.py
=======
Simple, dependency-free authentication using PBKDF2-HMAC-SHA256 password
hashing with a per-user random salt. No plaintext passwords ever touch disk.
"""

import hashlib
import os
import re
import sqlite3
from datetime import datetime

from db import get_app_conn

PBKDF2_ITERATIONS = 260_000


def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return dk.hex()


def _is_valid_email(email: str) -> bool:
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


def _is_valid_username(username: str) -> bool:
    return re.match(r"^[A-Za-z0-9_]{3,20}$", username) is not None


def register_user(username: str, email: str, password: str, confirm_password: str):
    """Returns (success: bool, message: str)."""
    username = username.strip()
    email = email.strip().lower()

    if not username or not email or not password:
        return False, "All fields are required."
    if not _is_valid_username(username):
        return False, "Username must be 3-20 characters: letters, numbers, underscore only."
    if not _is_valid_email(email):
        return False, "Please enter a valid email address."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if password != confirm_password:
        return False, "Passwords do not match."

    salt = os.urandom(16)
    password_hash = _hash_password(password, salt)

    try:
        with get_app_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, salt, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, email, password_hash, salt.hex(), datetime.utcnow().isoformat()),
            )
        return True, "Account created successfully! Please log in."
    except sqlite3.IntegrityError:
        return False, "That username or email is already registered."


def authenticate_user(username_or_email: str, password: str):
    """Returns user dict on success, or None on failure."""
    identifier = username_or_email.strip().lower()

    with get_app_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE lower(username) = ? OR lower(email) = ?",
            (identifier, identifier),
        )
        row = cur.fetchone()

    if row is None:
        return None

    salt = bytes.fromhex(row["salt"])
    expected_hash = _hash_password(password, salt)

    if expected_hash != row["password_hash"]:
        return None

    return {"user_id": row["user_id"], "username": row["username"], "email": row["email"]}