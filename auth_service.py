"""
Campus Resource Booking System - Authentication Service
=======================================================

Functional Module: User Management & Authentication
Non-Functional Requirements Addressed:
- Security: Salted SHA-256 cryptographic password hashing, strict email/password pattern validation.
- Reliability: Robust database transaction management and duplicate constraint handling.
- Maintainability: Modular validation logic, clear separation of auth state.
- Performance: Single indexed lookups for credential verification.
"""

import hashlib
import secrets
import re
import sqlite3
from datetime import datetime
from typing import Optional, Tuple
from database import db
from models import User


class AuthService:
    """Manages user authentication, registration, password hashing, and active session."""

    def __init__(self):
        self.current_user: Optional[User] = None

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hashes a password with a cryptographic hex salt using SHA-256."""
        if salt is None:
            salt = secrets.token_hex(16)
        salted_pwd = (password + salt).encode("utf-8")
        pwd_hash = hashlib.sha256(salted_pwd).hexdigest()
        return pwd_hash, salt

    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """Validates username formatting (alphanumeric + underscore, 3-20 chars)."""
        username = username.strip()
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
            return False, "Username must be 3-20 characters long and contain only letters, numbers, or underscores."
        return True, ""

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Validates email format."""
        email = email.strip()
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(pattern, email):
            return False, "Invalid email address format (e.g., student@campus.edu)."
        return True, ""

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """
        Validates password strength:
        - At least 6 characters
        - Contains at least 1 digit
        - Contains at least 1 letter
        """
        if len(password) < 6:
            return False, "Password must be at least 6 characters long."
        if not re.search(r"\d", password):
            return False, "Password must contain at least one numeric digit."
        if not re.search(r"[a-zA-Z]", password):
            return False, "Password must contain at least one letter."
        return True, ""

    def register_user(
        self, username: str, password: str, full_name: str, email: str, role: str = "Student"
    ) -> Tuple[bool, str]:
        """Registers a new user into the database."""
        # Validation
        u_valid, u_msg = self.validate_username(username)
        if not u_valid:
            return False, u_msg

        e_valid, e_msg = self.validate_email(email)
        if not e_valid:
            return False, e_msg

        p_valid, p_msg = self.validate_password(password)
        if not p_valid:
            return False, p_msg

        if not full_name.strip():
            return False, "Full name cannot be empty."

        role = role.strip().capitalize()
        if role not in ["Student", "Admin"]:
            return False, "Invalid role specified. Allowed roles: Student, Admin."

        pwd_hash, salt = self.hash_password(password)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, password_hash, salt, full_name, email, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (username.strip(), pwd_hash, salt, full_name.strip(), email.strip().lower(), role, now))
                conn.commit()
                return True, f"User '{username}' registered successfully as {role}."
        except sqlite3.IntegrityError as e:
            err_msg = str(e).lower()
            if "users.username" in err_msg or "unique constraint failed: users.username" in err_msg:
                return False, f"Username '{username}' is already taken. Please choose another."
            elif "users.email" in err_msg or "unique constraint failed: users.email" in err_msg:
                return False, f"Email '{email}' is already registered in the system."
            return False, f"Registration failed due to a constraint violation: {e}"
        except sqlite3.Error as e:
            return False, f"Database error during registration: {e}"

    def login(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Authenticates user credentials and sets active session."""
        username = username.strip()
        if not username or not password:
            return False, "Username and password cannot be empty.", None

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, username, password_hash, salt, full_name, email, role, created_at
                    FROM users WHERE username = ?;
                """, (username,))
                row = cursor.fetchone()

                if not row:
                    return False, "Invalid username or password.", None

                stored_hash = row["password_hash"]
                stored_salt = row["salt"]

                computed_hash, _ = self.hash_password(password, stored_salt)

                if computed_hash == stored_hash:
                    user = User(
                        user_id=row["user_id"],
                        username=row["username"],
                        full_name=row["full_name"],
                        email=row["email"],
                        role=row["role"],
                        created_at=row["created_at"]
                    )
                    self.current_user = user
                    return True, f"Welcome back, {user.full_name} ({user.role})!", user
                else:
                    return False, "Invalid username or password.", None

        except sqlite3.Error as e:
            return False, f"Database error during login: {e}", None

    def logout(self) -> None:
        """Clears the active session."""
        self.current_user = None

    def get_current_user(self) -> Optional[User]:
        """Returns the currently logged-in user."""
        return self.current_user

    def is_logged_in(self) -> bool:
        """Returns True if a user session is active."""
        return self.current_user is not None

    def require_role(self, allowed_roles: list) -> bool:
        """Checks if current user has one of the allowed roles."""
        if not self.is_logged_in():
            return False
        return self.current_user.role in allowed_roles
