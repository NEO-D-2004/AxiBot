import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="storage/axibot.db"):
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    display_name TEXT,
                    personality_summary TEXT DEFAULT 'New viewer, no history yet.',
                    last_seen TIMESTAMP,
                    message_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def get_user(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone()

    def update_user_activity(self, user_id, display_name):
        with sqlite3.connect(self.db_path) as conn:
            # Upsert logic
            conn.execute("""
                INSERT INTO users (user_id, display_name, last_seen, message_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    last_seen = excluded.last_seen,
                    message_count = users.message_count + 1
            """, (user_id, display_name, datetime.now().isoformat()))
            conn.commit()

    def update_personality(self, user_id, summary):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users SET personality_summary = ? WHERE user_id = ?
            """, (summary, user_id))
            conn.commit()

    def get_all_users(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM users")
            return cursor.fetchall()

    def delete_user(self, user_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()

    def update_user_details(self, user_id, display_name, summary, message_count):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users 
                SET display_name = ?, personality_summary = ?, message_count = ?
                WHERE user_id = ?
            """, (display_name, summary, message_count, user_id))
            conn.commit()

    def reset_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DROP TABLE IF EXISTS users")
            conn.commit()
        self._init_db()
