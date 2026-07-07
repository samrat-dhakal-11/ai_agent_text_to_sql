"""
db.py
=====
All database plumbing for the app.

Two SQLite files are used:
  - app_data.db   -> users, chat sessions, chat messages (the "app" side)
  - students.db   -> the domain data the chatbot is allowed to query (the "agent" side)

Keeping them separate means the chatbot's SQL tool can never accidentally
touch user passwords or chat history, even if a query goes wrong.
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

APP_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_data.db")
STUDENT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.db")


@contextmanager
def get_app_conn():
    conn = sqlite3.connect(APP_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ----------------------------------------------------------------------
# APP DATABASE  (users / sessions / messages)
# ----------------------------------------------------------------------
def init_app_database():
    with get_app_conn() as conn:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt          TEXT NOT NULL,
                created_at    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                title        TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   INTEGER NOT NULL,
                role         TEXT NOT NULL,          -- 'user' | 'assistant' | 'system'
                content      TEXT NOT NULL,
                blocked      INTEGER NOT NULL DEFAULT 0,  -- 1 if a guardrail blocked it
                created_at   TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
            );
            """
        )


# ----------------------------------------------------------------------
# STUDENT / DOMAIN DATABASE  (what the chatbot is allowed to query)
# ----------------------------------------------------------------------
def init_student_database(force_reset: bool = False):
    """Create a richer academic dataset than the original demo:
    Departments, Instructors, Students, Courses, Enrollments, Attendance."""
    conn = sqlite3.connect(STUDENT_DB)
    cursor = conn.cursor()

    if force_reset:
        cursor.executescript(
            """
            DROP TABLE IF EXISTS Attendance;
            DROP TABLE IF EXISTS Enrollments;
            DROP TABLE IF EXISTS Students;
            DROP TABLE IF EXISTS Courses;
            DROP TABLE IF EXISTS Instructors;
            DROP TABLE IF EXISTS Departments;
            """
        )

    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS Departments (
            department_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            building TEXT
        );

        CREATE TABLE IF NOT EXISTS Instructors (
            instructor_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department_id INTEGER,
            hire_year INTEGER,
            FOREIGN KEY (department_id) REFERENCES Departments(department_id)
        );

        CREATE TABLE IF NOT EXISTS Students (
            student_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            department_id INTEGER,
            enrollment_year INTEGER,
            gpa REAL,
            FOREIGN KEY (department_id) REFERENCES Departments(department_id)
        );

        CREATE TABLE IF NOT EXISTS Courses (
            course_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department_id INTEGER,
            credits INTEGER,
            instructor_id INTEGER,
            FOREIGN KEY (department_id) REFERENCES Departments(department_id),
            FOREIGN KEY (instructor_id) REFERENCES Instructors(instructor_id)
        );

        CREATE TABLE IF NOT EXISTS Enrollments (
            enrollment_id INTEGER PRIMARY KEY,
            student_id INTEGER,
            course_id INTEGER,
            grade TEXT,
            semester TEXT,
            FOREIGN KEY (student_id) REFERENCES Students(student_id),
            FOREIGN KEY (course_id) REFERENCES Courses(course_id)
        );

        CREATE TABLE IF NOT EXISTS Attendance (
            attendance_id INTEGER PRIMARY KEY,
            student_id INTEGER,
            course_id INTEGER,
            date TEXT,
            status TEXT,   -- Present / Absent / Late
            FOREIGN KEY (student_id) REFERENCES Students(student_id),
            FOREIGN KEY (course_id) REFERENCES Courses(course_id)
        );
        """
    )

    # Only seed if empty, so re-running the app doesn't duplicate rows
    cursor.execute("SELECT COUNT(*) FROM Departments;")
    if cursor.fetchone()[0] == 0:
        cursor.executescript(
            """
            INSERT INTO Departments VALUES
                (1, 'Computer Science', 'Turing Hall'),
                (2, 'Mathematics', 'Euler Hall'),
                (3, 'Physics', 'Newton Hall');

            INSERT INTO Instructors VALUES
                (1, 'Dr. Alice Frost', 1, 2012),
                (2, 'Dr. Ben Osei', 2, 2015),
                (3, 'Dr. Carla Nunez', 1, 2018),
                (4, 'Dr. David Kim', 3, 2010);

            INSERT INTO Students VALUES
                (1, 'Emma Wilson', 20, 'F', 1, 2023, 3.8),
                (2, 'Liam Garcia', 21, 'M', 1, 2022, 3.4),
                (3, 'Olivia Martinez', 19, 'F', 2, 2024, 3.9),
                (4, 'Noah Chen', 22, 'M', 1, 2021, 3.1),
                (5, 'Ava Patel', 20, 'F', 3, 2023, 3.6),
                (6, 'Ethan Rossi', 23, 'M', 2, 2020, 2.9),
                (7, 'Sophia Kim', 21, 'F', 1, 2022, 3.95),
                (8, 'Mason Ali', 19, 'M', 3, 2024, 3.3);

            INSERT INTO Courses VALUES
                (1, 'Python Programming', 1, 3, 1),
                (2, 'Data Structures', 1, 4, 3),
                (3, 'Calculus I', 2, 4, 2),
                (4, 'Linear Algebra', 2, 3, 2),
                (5, 'Classical Mechanics', 3, 4, 4),
                (6, 'Quantum Physics', 3, 4, 4);

            INSERT INTO Enrollments VALUES
                (1, 1, 1, 'A', 'Fall2025'),
                (2, 2, 1, 'B+', 'Fall2025'),
                (3, 3, 3, 'A', 'Fall2025'),
                (4, 4, 2, 'A-', 'Fall2025'),
                (5, 5, 5, 'B', 'Fall2025'),
                (6, 6, 4, 'C+', 'Fall2025'),
                (7, 7, 2, 'A', 'Fall2025'),
                (8, 8, 6, 'B-', 'Fall2025'),
                (9, 1, 2, 'B+', 'Spring2026'),
                (10, 3, 4, 'A-', 'Spring2026');

            INSERT INTO Attendance VALUES
                (1, 1, 1, '2026-01-10', 'Present'),
                (2, 2, 1, '2026-01-10', 'Absent'),
                (3, 3, 3, '2026-01-10', 'Present'),
                (4, 4, 2, '2026-01-10', 'Late'),
                (5, 5, 5, '2026-01-11', 'Present'),
                (6, 6, 4, '2026-01-11', 'Present'),
                (7, 7, 2, '2026-01-11', 'Absent'),
                (8, 8, 6, '2026-01-11', 'Present');
            """
        )

    conn.commit()
    conn.close()


def ensure_databases():
    """Call once at app startup."""
    init_app_database()
    if not os.path.exists(STUDENT_DB):
        init_student_database(force_reset=True)
    else:
        init_student_database(force_reset=False)


# ----------------------------------------------------------------------
# CHAT SESSION / MESSAGE HELPERS
# ----------------------------------------------------------------------
def create_session(user_id: int, title: str) -> int:
    with get_app_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO chat_sessions (user_id, title, created_at) VALUES (?, ?, ?)",
            (user_id, title, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def get_sessions(user_id: int):
    with get_app_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT session_id, title, created_at FROM chat_sessions "
            "WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def rename_session(session_id: int, title: str):
    with get_app_conn() as conn:
        conn.execute(
            "UPDATE chat_sessions SET title = ? WHERE session_id = ?", (title, session_id)
        )


def delete_session(session_id: int):
    with get_app_conn() as conn:
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))


def save_message(session_id: int, role: str, content: str, blocked: bool = False):
    with get_app_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, blocked, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, int(blocked), datetime.utcnow().isoformat()),
        )


def get_messages(session_id: int):
    with get_app_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT role, content, blocked, created_at FROM chat_messages "
            "WHERE session_id = ? ORDER BY message_id ASC",
            (session_id,),
        )
        return [dict(row) for row in cur.fetchall()]