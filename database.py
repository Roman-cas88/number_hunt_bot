import sqlite3
from config import DB_PATH
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                score INTEGER DEFAULT 0,
                last_found_number INTEGER DEFAULT 0,
                total_found INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS game_state (
                id INTEGER PRIMARY KEY CHECK (id=1),
                current_number INTEGER DEFAULT 1,
                is_running INTEGER DEFAULT 0,
                is_voting INTEGER DEFAULT 0,
                admin_decision_needed INTEGER DEFAULT 0
            );
            INSERT OR IGNORE INTO game_state (id, current_number, is_running, is_voting, admin_decision_needed)
            VALUES (1, 1, 0, 0, 0);

            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                number INTEGER,
                photo_file_id TEXT,
                status TEXT CHECK(status IN ('pending','accepted','rejected')),
                message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER,
                voter_id INTEGER,
                vote TEXT CHECK(vote IN ('approve','reject')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(submission_id, voter_id)
            );
        """)
        self.conn.commit()

    # ---------- Игроки ----------
    def add_player(self, user_id, username, first_name):
        self.cursor.execute("""
            INSERT OR IGNORE INTO players (user_id, username, first_name, is_active)
            VALUES (?, ?, ?, 1)
        """, (user_id, username, first_name))
        self.conn.commit()

    def set_player_active(self, user_id, active=True):
        self.cursor.execute("UPDATE players SET is_active = ? WHERE user_id = ?", (1 if active else 0, user_id))
        self.conn.commit()

    def get_active_players(self):
        self.cursor.execute("SELECT user_id FROM players WHERE is_active = 1")
        return [row[0] for row in self.cursor.fetchall()]

    def get_player_score(self, user_id):
        self.cursor.execute("SELECT score, total_found, last_found_number FROM players WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def get_rating(self):
        self.cursor.execute("SELECT user_id, username, first_name, score FROM players WHERE is_active = 1 ORDER BY score DESC")
        return self.cursor.fetchall()

    def update_player_score(self, user_id, number):
        self.cursor.execute("""
            UPDATE players 
            SET score = score + 1, 
                total_found = total_found + 1, 
                last_found_number = ?
            WHERE user_id = ?
        """, (number, user_id))
        self.conn.commit()

    # ---------- Состояние игры ----------
    def get_game_state(self):
        self.cursor.execute("SELECT current_number, is_running, is_voting, admin_decision_needed FROM game_state WHERE id=1")
        return self.cursor.fetchone()

    def set_game_running(self, running):
        self.cursor.execute("UPDATE game_state SET is_running = ? WHERE id=1", (1 if running else 0,))
        self.conn.commit()

    def set_current_number(self, number):
        self.cursor.execute("UPDATE game_state SET current_number = ? WHERE id=1", (number,))
        self.conn.commit()

    def set_voting(self, voting):
        self.cursor.execute("UPDATE game_state SET is_voting = ? WHERE id=1", (1 if voting else 0,))
        self.conn.commit()

    def set_admin_decision_needed(self, needed):
        self.cursor.execute("UPDATE game_state SET admin_decision_needed = ? WHERE id=1", (1 if needed else 0,))
        self.conn.commit()

    def reset_game(self):
        self.cursor.execute("""
            UPDATE game_state 
            SET current_number = 1, is_running = 1, is_voting = 0, admin_decision_needed = 0 
            WHERE id=1
        """)
        self.conn.commit()

    # ---------- Подачи (submissions) ----------
    def create_submission(self, user_id, number, photo_file_id, message_id):
        self.cursor.execute("""
            INSERT INTO submissions (user_id, number, photo_file_id, status, message_id)
            VALUES (?, ?, ?, 'pending', ?)
        """, (user_id, number, photo_file_id, message_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_pending_submission(self):
        self.cursor.execute("SELECT id, user_id, number, photo_file_id, message_id FROM submissions WHERE status='pending' LIMIT 1")
        return self.cursor.fetchone()

    def update_submission_status(self, submission_id, status):
        self.cursor.execute("UPDATE submissions SET status = ? WHERE id = ?", (status, submission_id))
        self.conn.commit()

    def get_submission_author(self, submission_id):
        self.cursor.execute("SELECT user_id FROM submissions WHERE id = ?", (submission_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    # ---------- Голоса ----------
    def add_vote(self, submission_id, voter_id, vote):
        try:
            self.cursor.execute("INSERT INTO votes (submission_id, voter_id, vote) VALUES (?, ?, ?)",
                                (submission_id, voter_id, vote))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_votes_for_submission(self, submission_id):
        self.cursor.execute("SELECT voter_id, vote FROM votes WHERE submission_id = ?", (submission_id,))
        return self.cursor.fetchall()

    def count_approves(self, submission_id):
        self.cursor.execute("SELECT COUNT(*) FROM votes WHERE submission_id = ? AND vote='approve'", (submission_id,))
        return self.cursor.fetchone()[0]

    def count_rejects(self, submission_id):
        self.cursor.execute("SELECT COUNT(*) FROM votes WHERE submission_id = ? AND vote='reject'", (submission_id,))
        return self.cursor.fetchone()[0]

    def get_voters_for_submission(self, submission_id):
        self.cursor.execute("SELECT voter_id FROM votes WHERE submission_id = ?", (submission_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def delete_votes_for_submission(self, submission_id):
        self.cursor.execute("DELETE FROM votes WHERE submission_id = ?", (submission_id,))
        self.conn.commit()

    def get_old_pending_submissions(self, seconds_ago):
        self.cursor.execute("""
            SELECT id, user_id, number, message_id, created_at 
            FROM submissions 
            WHERE status='pending' AND julianday('now') - julianday(created_at) > ? / 86400.0
        """, (seconds_ago,))
        return self.cursor.fetchall()