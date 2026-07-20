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
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def add_subscriber(email, topics):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO subscribers (email, topics) VALUES (?, ?)",
                 (email, json.dumps(topics)))
    conn.commit()
    conn.close()

def get_active_subscribers():
    conn = get_db()
    subs = conn.execute("SELECT email, topics FROM subscribers WHERE active=1").fetchall()
    conn.close()
    return [{"email": s["email"], "topics": json.loads(s["topics"])} for s in subs]

if __name__ == "__main__":
    init_db()
    add_subscriber("test@example.com", ["adhs", "psychotherapy"])
    print(get_active_subscribers())
