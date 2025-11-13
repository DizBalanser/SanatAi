import sqlite3
from typing import Iterable, List, Optional


def get_db_connection():
    conn = sqlite3.connect('messages.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            deadline TEXT,
            tags TEXT,
            estimated_minutes INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS ideas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            tags TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS notes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            content TEXT NOT NULL,
            tags TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )

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


def _normalize_tags(tags: Optional[Iterable[str]]) -> Optional[str]:
    if tags is None:
        return None
    if isinstance(tags, str):
        return tags
    materialized: List[str] = [str(tag).strip() for tag in tags if str(tag).strip()]
    return ','.join(materialized) if materialized else None


def save_task(user_id: int, title: str, description: Optional[str], deadline: Optional[str],
              tags: Optional[Iterable[str]], estimated_minutes: Optional[int]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO tasks (user_id, title, description, deadline, tags, estimated_minutes)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (user_id, title, description, deadline, _normalize_tags(tags), estimated_minutes),
    )
    conn.commit()
    conn.close()


def save_idea(user_id: int, title: str, description: Optional[str], tags: Optional[Iterable[str]]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO ideas (user_id, title, description, tags)
        VALUES (?, ?, ?, ?)
        ''',
        (user_id, title, description, _normalize_tags(tags)),
    )
    conn.commit()
    conn.close()


def save_note(user_id: int, title: Optional[str], content: str, tags: Optional[Iterable[str]]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO notes (user_id, title, content, tags)
        VALUES (?, ?, ?, ?)
        ''',
        (user_id, title, content, _normalize_tags(tags)),
    )
    conn.commit()
    conn.close()


def get_tasks_by_user(user_id: int, limit: int = 20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, deadline, tags, estimated_minutes, created_at
        FROM tasks
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        ''',
        (user_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_ideas_by_user(user_id: int, limit: int = 20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, tags, created_at
        FROM ideas
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        ''',
        (user_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_notes_by_user(user_id: int, limit: int = 20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, content, tags, created_at
        FROM notes
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        ''',
        (user_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

