"""
Campus Resource Booking System - Database Layer
==============================================

Non-Functional Requirements Implemented in Architecture:
1. SECURITY:
   - Uses SQLite parameterized queries (?, ?) to prevent SQL Injection attacks.
   - Restricts raw direct string interpolation in queries.
   - Enforces relational constraints (FOREIGN KEYS) to preserve data integrity.
2. RELIABILITY:
   - Exception handling on all database connections and cursor transactions.
   - Automatic rollback on transactional errors and explicit commit on success.
   - Always safely closes resources via context management or try/finally blocks.
3. PERFORMANCE:
   - SQLite B-Tree indexing on primary lookup columns: username, email, booking dates, resource category.
   - Efficient JOIN queries to reduce redundant roundtrips.
4. MAINTAINABILITY:
   - Centralized database configuration and schema initialization.
   - Clean, modular database interface with decoupled service layers.
"""

import sqlite3
import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campus_booking.db")


class Database:
    """Handles low-level SQLite database operations, schema creation, and seeding."""

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a connection with foreign keys and row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """Creates tables and indices if they do not already exist."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Users Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        full_name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        role TEXT NOT NULL CHECK(role IN ('Admin', 'Student')),
                        created_at TEXT NOT NULL
                    );
                """)

                # Resources Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS resources (
                        resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        category TEXT NOT NULL,
                        capacity INTEGER NOT NULL CHECK(capacity >= 0),
                        location TEXT NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('Available', 'Under Maintenance', 'Decommissioned')),
                        description TEXT DEFAULT ''
                    );
                """)

                # Bookings Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bookings (
                        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        resource_id INTEGER NOT NULL,
                        booking_date TEXT NOT NULL,
                        time_slot TEXT NOT NULL,
                        purpose TEXT NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED')),
                        admin_remarks TEXT DEFAULT '',
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                        FOREIGN KEY (resource_id) REFERENCES resources (resource_id) ON DELETE RESTRICT
                    );
                """)

                # Performance Indices
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_category ON resources(category);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_date_slot ON bookings(resource_id, booking_date, time_slot);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);")

                conn.commit()
                self._seed_default_data(conn)
        except sqlite3.Error as e:
            print(f"[Database Error during initialization]: {e}")
            raise

    def _seed_default_data(self, conn: sqlite3.Connection) -> None:
        """Seeds initial admin account and default campus facilities if database is fresh."""
        import hashlib
        import secrets

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users;")
        user_count = cursor.fetchone()["count"]

        if user_count == 0:
            # Seed Default Admin: admin / Admin@123
            salt = secrets.token_hex(16)
            admin_pwd = "Admin@123"
            pwd_hash = hashlib.sha256((admin_pwd + salt).encode("utf-8")).hexdigest()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                INSERT INTO users (username, password_hash, salt, full_name, email, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, ("admin", pwd_hash, salt, "System Administrator", "admin@campus.edu", "Admin", now))

            # Seed Default Student: student1 / Student@123
            salt_s = secrets.token_hex(16)
            student_pwd = "Student@123"
            pwd_hash_s = hashlib.sha256((student_pwd + salt_s).encode("utf-8")).hexdigest()
            cursor.execute("""
                INSERT INTO users (username, password_hash, salt, full_name, email, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, ("student1", pwd_hash_s, salt_s, "Alex Johnson", "alex.j@campus.edu", "Student", now))

            # Seed Default Resources
            default_resources = [
                ("Main Auditorium", "Auditorium", 500, "Central Block - Ground Floor", "Available", "Equipped with surround sound, 4K projection, and stage lighting."),
                ("Robotics & AI Research Lab", "Lab", 40, "Engineering Wing - Room 302", "Available", "High-performance workstations, 3D printers, and sensor kits."),
                ("Advanced Physics Lab", "Lab", 30, "Science Block - Room 104", "Available", "Equipped for optics, mechanics, and electronics experiments."),
                ("Seminar Hall A", "Auditorium", 120, "Academic Complex - 2nd Floor", "Available", "Tiered seating with dual HD displays and conference mics."),
                ("High-End 4K Projector Kit #1", "Equipment", 1, "Media Equipment Center", "Available", "Portable 4K laser projector with HDMI/Wireless transmitters."),
                ("Smart Classroom 101", "Classroom", 60, "Commerce Block - 1st Floor", "Available", "Interactive smartboard, hybrid streaming cameras, and audio."),
                ("Indoor Sports Arena", "Sports Facility", 100, "Campus Sports Complex", "Available", "Wooden court suitable for badminton, basketball, and table tennis."),
                ("Conference Room Executive", "Auditorium", 25, "Administration Block - 3rd Floor", "Under Maintenance", "Scheduled maintenance for ventilation system.")
            ]

            cursor.executemany("""
                INSERT INTO resources (name, category, capacity, location, status, description)
                VALUES (?, ?, ?, ?, ?, ?);
            """, default_resources)

            conn.commit()


# Singleton database instance
db = Database()
