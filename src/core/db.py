import sqlite3
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH

DB_PATH_DIR = os.path.dirname(DB_PATH)
if DB_PATH_DIR and not os.path.exists(DB_PATH_DIR):
    os.makedirs(DB_PATH_DIR)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS subscribers (
        email TEXT PRIMARY KEY,
        topics TEXT NOT NULL, -- JSON string
        profession TEXT DEFAULT '',
        day TEXT DEFAULT 'friday', -- monday, wednesday, friday
        time TEXT DEFAULT 'morning', -- morning, midday
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def add_subscriber(email, topics, profession='', day='friday', time='morning'):
    conn = get_db()
    conn.execute('''INSERT OR REPLACE INTO subscribers 
                    (email, topics, profession, day, time) VALUES (?, ?, ?, ?, ?)''',
                 (email, json.dumps(topics), profession, day, time))
    conn.commit()
    conn.close()

def get_subscriber(email):
    conn = get_db()
    row = conn.execute("SELECT * FROM subscribers WHERE email=? AND active=1", (email,)).fetchone()
    conn.close()
    if row:
        return {
            "email": row["email"],
            "topics": json.loads(row["topics"]),
            "profession": row["profession"],
            "day": row["day"],
            "time": row["time"],
            "active": bool(row["active"]),
            "created_at": row["created_at"]
        }
    return None

def get_active_subscribers():
    conn = get_db()
    subs = conn.execute("SELECT * FROM subscribers WHERE active=1").fetchall()
    conn.close()
    return [{
        "email": s["email"],
        "topics": json.loads(s["topics"]),
        "profession": s["profession"],
        "day": s["day"],
        "time": s["time"]
    } for s in subs]

# Whitelist allowed columns to prevent SQL injection via column names
ALLOWED_COLUMNS = {"topics", "profession", "day", "time", "active"}

def update_subscriber(email, updates):
    conn = get_db()
    fields = []
    values = []
    for key, value in updates.items():
        # CRITICAL: Reject any column not in whitelist
        if key not in ALLOWED_COLUMNS:
            raise ValueError(f"Column '{key}' not allowed for updates")
        if key == "topics":
            value = json.dumps(value)
        fields.append(f"{key}=?")
        values.append(value)
    values.append(email)
    conn.execute(f"UPDATE subscribers SET {', '.join(fields)} WHERE email=?", values)
    conn.commit()
    conn.close()

def remove_subscriber(email):
    conn = get_db()
    conn.execute("UPDATE subscribers SET active=0 WHERE email=?", (email,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    add_subscriber("test@example.com", ["adhs", "psychotherapy"], profession="hr", day="friday", time="morning")
    print(get_active_subscribers())
