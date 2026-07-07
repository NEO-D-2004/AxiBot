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
            
            # Check if points column exists in users table, if not add it
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = [info[1] for info in cursor.fetchall()]
            if "points" not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0")
                
            # Create commands table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS commands (
                    command_name TEXT PRIMARY KEY,
                    response_text TEXT,
                    use_count INTEGER DEFAULT 0
                )
            """)

            # Create highlights table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS highlights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    seconds_elapsed INTEGER,
                    user_trigger TEXT,
                    message_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Check if video_id column exists in highlights table, if not add it
            cursor = conn.execute("PRAGMA table_info(highlights)")
            columns = [info[1] for info in cursor.fetchall()]
            if "video_id" not in columns:
                conn.execute("ALTER TABLE highlights ADD COLUMN video_id TEXT")
                
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

    def update_user_details(self, user_id, display_name, summary, message_count, points=0):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE users 
                SET display_name = ?, personality_summary = ?, message_count = ?, points = ?
                WHERE user_id = ?
            """, (display_name, summary, message_count, points, user_id))
            conn.commit()

    def reset_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DROP TABLE IF EXISTS users")
            conn.execute("DROP TABLE IF EXISTS commands")
            conn.execute("DROP TABLE IF EXISTS highlights")
            conn.commit()
        self._init_db()

    def add_points(self, user_id, display_name, amount):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO users (user_id, display_name, last_seen, message_count, points)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    last_seen = excluded.last_seen,
                    points = users.points + excluded.points
            """, (user_id, display_name, datetime.now().isoformat(), amount))
            conn.commit()

    def deduct_points(self, user_id, amount):
        """ Deducts points from user if they have enough. Returns True if success, else False. """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row or row["points"] < amount:
                return False
            
            conn.execute("UPDATE users SET points = points - ? WHERE user_id = ?", (amount, user_id))
            conn.commit()
            return True

    def get_top_users_by_points(self, limit=3):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT display_name, points FROM users ORDER BY points DESC LIMIT ?", (limit,))
            return cursor.fetchall()

    def get_command(self, command_name):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM commands WHERE command_name = ?", (command_name.lower(),))
            return cursor.fetchone()

    def add_command(self, command_name, response_text):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO commands (command_name, response_text, use_count)
                VALUES (?, ?, 0)
                ON CONFLICT(command_name) DO UPDATE SET response_text = excluded.response_text
            """, (command_name.lower(), response_text))
            conn.commit()

    def delete_command(self, command_name):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM commands WHERE command_name = ?", (command_name.lower(),))
            conn.commit()

    def get_all_commands(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM commands ORDER BY command_name")
            return cursor.fetchall()

    def increment_command_use(self, command_name):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE commands SET use_count = use_count + 1 WHERE command_name = ?", (command_name.lower(),))
            conn.commit()

    def add_highlight(self, timestamp, seconds, user, message, video_id=None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO highlights (timestamp, seconds_elapsed, user_trigger, message_text, video_id)
                VALUES (?, ?, ?, ?, ?)
            """, (timestamp, seconds, user, message, video_id))
            conn.commit()

    def get_all_highlights(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM highlights ORDER BY seconds_elapsed DESC")
            return cursor.fetchall()

    def delete_highlight(self, highlight_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM highlights WHERE id = ?", (highlight_id,))
            conn.commit()

    def clear_all_highlights(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM highlights")
            conn.commit()
