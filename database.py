import sqlite3
import os
import json
from typing import Dict, Any, List, Optional
from werkzeug.security import generate_password_hash, check_password_hash  # pyrefly: ignore[missing-import]

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.close()
    return conn

def init_db():
    """Initializes database tables for users and interviews."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Interviews Table (stores user's past mock interview sessions and reports)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            candidate_name TEXT,
            interview_type TEXT,
            overall_score INTEGER,
            recommendation TEXT,
            duration TEXT,
            report_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    conn.commit()
    conn.close()

def register_user(full_name: str, email: str, password: str) -> Dict[str, Any]:
    """Registers a new user with secure password hashing."""
    clean_name = full_name.strip()
    clean_email = email.strip().lower()

    if not clean_name:
        return {"success": False, "error": "Full name is required."}
    if not clean_email or "@" not in clean_email:
        return {"success": False, "error": "A valid email address is required."}
    if len(password) < 8:
        return {"success": False, "error": "Password must be at least 8 characters long."}

    password_hash = generate_password_hash(password, method="scrypt")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
            (clean_name, clean_email, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {
            "success": True,
            "user": {
                "id": user_id,
                "full_name": clean_name,
                "email": clean_email
            }
        }
    except sqlite3.IntegrityError:
        return {"success": False, "error": "An account with this email already exists."}
    except Exception as e:
        return {"success": False, "error": f"Database error: {str(e)}"}
    finally:
        conn.close()

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Verifies credentials and returns user dict if valid."""
    clean_email = email.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (clean_email,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        return {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "created_at": user["created_at"]
        }
    return None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves user profile by user ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name, email, created_at FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def save_interview_record(user_id: int, session_id: str, candidate_name: str, 
                          interview_type: str, overall_score: int, 
                          recommendation: str, duration: str, report_dict: Dict[str, Any]) -> bool:
    """Saves or updates an interview completion record for the user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    report_json = json.dumps(report_dict)

    try:
        cursor.execute("""
            INSERT INTO interviews 
            (session_id, user_id, candidate_name, interview_type, overall_score, recommendation, duration, report_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                overall_score=excluded.overall_score,
                recommendation=excluded.recommendation,
                duration=excluded.duration,
                report_data=excluded.report_data
        """, (session_id, user_id, candidate_name, interview_type, overall_score, recommendation, duration, report_json))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB Error] Could not save interview record: {e}")
        return False
    finally:
        conn.close()

def get_user_interviews(user_id: int) -> List[Dict[str, Any]]:
    """Retrieves all past interview records for a given user, newest first."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, session_id, candidate_name, interview_type, overall_score, 
               recommendation, duration, created_at
        FROM interviews
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_interview_report_by_session(session_id: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Retrieves the full report JSON for an interview session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT report_data FROM interviews WHERE session_id = ? AND user_id = ?", (session_id, user_id))
    else:
        cursor.execute("SELECT report_data FROM interviews WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()

    if row and row["report_data"]:
        try:
            return json.loads(row["report_data"])
        except Exception:
            return None
    return None

