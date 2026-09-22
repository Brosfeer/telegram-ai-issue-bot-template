import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from issue_bot.config import settings as config

logger = logging.getLogger(__name__)

class Database:
    """Manages SQLite database with WAL mode, access control, and batch buffers."""

    @staticmethod
    def get_connection() -> sqlite3.Connection:
        config.init_directories()
        conn = sqlite3.connect(str(config.DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @classmethod
    def init_db(cls) -> None:
        """Initialize database tables with schema migrations."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            
            # Batches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Items table (screenshots, text notes, documents)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER,
                    user_id INTEGER NOT NULL,
                    item_type TEXT NOT NULL,
                    file_id TEXT,
                    file_unique_id TEXT,
                    local_path TEXT,
                    caption TEXT,
                    media_group_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE CASCADE
                )
            """)

            # Issues table (tracked created GitHub issues)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER,
                    user_id INTEGER NOT NULL,
                    issue_number INTEGER NOT NULL,
                    issue_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    labels TEXT,
                    created_by_ai INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(batch_id) REFERENCES batches(id) ON DELETE SET NULL
                )
            """)

            # Authorized users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS authorized_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    role TEXT NOT NULL DEFAULT 'qa',
                    authorized_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Access requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS access_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    last_requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Seed Admin User if not already present
            cursor.execute("""
                INSERT OR IGNORE INTO authorized_users (user_id, username, first_name, role, authorized_by)
                VALUES (?, ?, ?, 'admin', ?)
            """, (config.ADMIN_USER_ID, "admin", "Admin", config.ADMIN_USER_ID))

            conn.commit()
            logger.info("Database initialized successfully with access control tables.")

    @classmethod
    def get_or_create_open_batch(cls, user_id: int) -> Dict[str, Any]:
        """Fetch current open batch for user, or create a new one."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM batches WHERE user_id = ? AND status = 'open' ORDER BY id DESC LIMIT 1",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)

            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "INSERT INTO batches (user_id, status, created_at, updated_at) VALUES (?, 'open', ?, ?)",
                (user_id, now, now)
            )
            conn.commit()
            batch_id = cursor.lastrowid
            cursor.execute("SELECT * FROM batches WHERE id = ?", (batch_id,))
            return dict(cursor.fetchone())

    @classmethod
    def get_open_batch(cls, user_id: int) -> Optional[Dict[str, Any]]:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM batches WHERE user_id = ? AND status = 'open' ORDER BY id DESC LIMIT 1",
                (user_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @classmethod
    def lock_batch_for_processing(cls, batch_id: int) -> bool:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "UPDATE batches SET status = 'processing', updated_at = ? WHERE id = ? AND status = 'open'",
                (now, batch_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    @classmethod
    def unlock_batch(cls, batch_id: int) -> None:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "UPDATE batches SET status = 'open', updated_at = ? WHERE id = ? AND status = 'processing'",
                (now, batch_id)
            )
            conn.commit()

    @classmethod
    def close_batch(cls, batch_id: int) -> None:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                "UPDATE batches SET status = 'closed', updated_at = ? WHERE id = ?",
                (now, batch_id)
            )
            conn.commit()

    @classmethod
    def clear_batch(cls, user_id: int) -> int:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            batch = cls.get_open_batch(user_id)
            if not batch:
                return 0
            batch_id = batch["id"]
            cursor.execute("DELETE FROM items WHERE batch_id = ?", (batch_id,))
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("UPDATE batches SET status = 'cleared', updated_at = ? WHERE id = ?", (now, batch_id))
            conn.commit()
            return batch_id

    @classmethod
    def add_item_to_batch(
        cls,
        batch_id: int,
        user_id: int,
        item_type: str,
        file_id: Optional[str] = None,
        file_unique_id: Optional[str] = None,
        local_path: Optional[str] = None,
        caption: Optional[str] = None,
        media_group_id: Optional[str] = None
    ) -> int:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            if file_unique_id:
                cursor.execute(
                    "SELECT id FROM items WHERE batch_id = ? AND file_unique_id = ?",
                    (batch_id, file_unique_id)
                )
                if cursor.fetchone():
                    return 0

            cursor.execute("""
                INSERT INTO items (
                    batch_id, user_id, item_type, file_id, file_unique_id, local_path, caption, media_group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (batch_id, user_id, item_type, file_id, file_unique_id, local_path, caption, media_group_id))
            conn.commit()
            return cursor.lastrowid

    @classmethod
    def update_item_caption(cls, item_id: int, caption: str) -> bool:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE items SET caption = ? WHERE id = ?", (caption, item_id))
            conn.commit()
            return cursor.rowcount > 0

    @classmethod
    def get_batch_items(cls, batch_id: int) -> List[Dict[str, Any]]:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM items WHERE batch_id = ? ORDER BY id ASC", (batch_id,))
            return [dict(r) for r in cursor.fetchall()]

    @classmethod
    def get_last_batch_item(cls, batch_id: int, item_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            if item_type:
                cursor.execute(
                    "SELECT * FROM items WHERE batch_id = ? AND item_type = ? ORDER BY id DESC LIMIT 1",
                    (batch_id, item_type)
                )
            else:
                cursor.execute(
                    "SELECT * FROM items WHERE batch_id = ? ORDER BY id DESC LIMIT 1",
                    (batch_id,)
                )
            row = cursor.fetchone()
            return dict(row) if row else None

    @classmethod
    def find_item_by_file_unique_id(cls, batch_id: int, file_unique_id: str) -> Optional[Dict[str, Any]]:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM items WHERE batch_id = ? AND file_unique_id = ? ORDER BY id DESC LIMIT 1",
                (batch_id, file_unique_id)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @classmethod
    def record_issue(
        cls,
        batch_id: Optional[int],
        user_id: int,
        issue_number: int,
        issue_url: str,
        title: str,
        labels: Optional[str] = None,
        created_by_ai: bool = False
    ) -> int:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO issues (
                    batch_id, user_id, issue_number, issue_url, title, labels, created_by_ai
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (batch_id, user_id, issue_number, issue_url, title, labels, 1 if created_by_ai else 0))
            conn.commit()
            return cursor.lastrowid

    @classmethod
    def get_recent_issues(cls, limit: int = 5) -> List[Dict[str, Any]]:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM issues ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    # Access control
    @classmethod
    def is_user_authorized(cls, user_id: int) -> bool:
        if user_id == config.ADMIN_USER_ID or user_id in config.ALLOWED_USER_IDS:
            return True
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM authorized_users WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None

    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        if config.ADMIN_USER_ID > 0 and user_id == config.ADMIN_USER_ID:
            return True
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM authorized_users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return bool(row and row["role"] == "admin")

    @classmethod
    def get_authorized_users(cls) -> List[Dict[str, Any]]:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM authorized_users ORDER BY id ASC")
            return [dict(r) for r in cursor.fetchall()]

    @classmethod
    def authorize_user(
        cls,
        user_id: int,
        username: Optional[str],
        first_name: Optional[str],
        role: str = "qa",
        authorized_by: Optional[int] = None
    ) -> bool:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO authorized_users (user_id, username, first_name, role, authorized_by)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    role = excluded.role
            """, (user_id, username, first_name, role, authorized_by))
            cursor.execute("DELETE FROM access_requests WHERE user_id = ?", (user_id,))
            conn.commit()
            return True

    @classmethod
    def revoke_user(cls, user_id: int) -> bool:
        if user_id == config.ADMIN_USER_ID:
            return False
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM authorized_users WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    @classmethod
    def record_access_request(cls, user_id: int, username: Optional[str], first_name: Optional[str]) -> bool:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("SELECT last_requested_at FROM access_requests WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE access_requests
                    SET username = ?, first_name = ?, last_requested_at = ?, status = 'pending'
                    WHERE user_id = ?
                """, (username, first_name, now, user_id))
            else:
                cursor.execute("""
                    INSERT INTO access_requests (user_id, username, first_name, status, last_requested_at)
                    VALUES (?, ?, ?, 'pending', ?)
                """, (user_id, username, first_name, now))
            conn.commit()
            return True

    @classmethod
    def get_pending_requests(cls) -> List[Dict[str, Any]]:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM access_requests WHERE status = 'pending' ORDER BY id ASC")
            return [dict(r) for r in cursor.fetchall()]

    @classmethod
    def resolve_access_request(cls, user_id: int, status: str = "approved") -> None:
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE access_requests SET status = ? WHERE user_id = ?", (status, user_id))
            conn.commit()
