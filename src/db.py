import sqlite3
from datetime import datetime


def get_db_connection():
    conn = sqlite3.connect('messages.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def save_message(user_id, text):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO messages (user_id, text) VALUES (?, ?)',
        (user_id, text)
    )
    
    conn.commit()
    conn.close()


def get_last_messages(user_id, limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT text FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?',
        (user_id, limit)
    )
    
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in reversed(rows)]

