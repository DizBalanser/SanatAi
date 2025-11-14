import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:  # pragma: no cover
    ZoneInfo = None


def _resolve_budapest_tz():
    if ZoneInfo:
        try:
            return ZoneInfo("Europe/Budapest")
        except Exception:
            pass
    # Fallback to the system's local timezone; if unavailable, use UTC.
    system_tz = datetime.now().astimezone().tzinfo
    return system_tz or timezone.utc


BUDAPEST_TZ = _resolve_budapest_tz()


def get_db_connection():
    conn = sqlite3.connect('messages.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

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
            importance INTEGER,
            urgency INTEGER,
            reason TEXT,
            priority_score REAL,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    _ensure_task_columns(cursor)

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


def _normalize_tags(tags: Optional[Iterable[str]]) -> Optional[str]:
    if tags is None:
        return None
    if isinstance(tags, str):
        return tags
    materialized: List[str] = [str(tag).strip() for tag in tags if str(tag).strip()]
    return ','.join(materialized) if materialized else None


def save_task(
    user_id: int,
    title: str,
    description: Optional[str],
    deadline: Optional[str],
    tags: Optional[Iterable[str]],
    estimated_minutes: Optional[int],
    importance: Optional[int] = None,
    urgency: Optional[int] = None,
    reason: Optional[str] = None,
    priority_score: Optional[float] = None,
    status: str = "pending",
) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO tasks (
            user_id,
            title,
            description,
            deadline,
            tags,
            estimated_minutes,
            importance,
            urgency,
            reason,
            priority_score,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            user_id,
            title,
            description,
            deadline,
            _normalize_tags(tags),
            estimated_minutes,
            importance,
            urgency,
            reason,
            priority_score,
            status,
        ),
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id


def update_task_analysis(
    task_id: int,
    importance: int,
    urgency: int,
    reason: str,
    priority_score: float,
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        UPDATE tasks
        SET importance = ?, urgency = ?, reason = ?, priority_score = ?
        WHERE id = ?
        ''',
        (importance, urgency, reason, priority_score, task_id),
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


def get_tasks_by_user(user_id: int, limit: int = 20, offset: int = 0):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, deadline, tags, estimated_minutes, importance, urgency, reason, priority_score, status, created_at
        FROM tasks
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        ''',
        (user_id, limit, offset),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_ideas_by_user(user_id: int, limit: int = 20, offset: int = 0):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, tags, created_at
        FROM ideas
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        ''',
        (user_id, limit, offset),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_notes_by_user(user_id: int, limit: int = 20, offset: int = 0):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, content, tags, created_at
        FROM notes
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        ''',
        (user_id, limit, offset),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_tasks_uncompleted(user_id: int, limit: int = 20, offset: int = 0):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, deadline, tags, estimated_minutes, importance, urgency, reason, priority_score, status, created_at
        FROM tasks
        WHERE user_id = ?
          AND COALESCE(status, 'pending') != 'done'
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        ''',
        (user_id, limit, offset),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_tasks_completed(user_id: int, limit: int = 20, offset: int = 0):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, deadline, tags, estimated_minutes, importance, urgency, reason, priority_score, status, created_at
        FROM tasks
        WHERE user_id = ?
          AND COALESCE(status, 'pending') = 'done'
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        ''',
        (user_id, limit, offset),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_ideas(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, tags, created_at
        FROM ideas
        WHERE user_id = ?
        ORDER BY created_at DESC
        ''',
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_notes(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, content, tags, created_at
        FROM notes
        WHERE user_id = ?
        ORDER BY created_at DESC
        ''',
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_all_tasks(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, deadline, tags, estimated_minutes, importance, urgency, reason, priority_score, status, created_at
        FROM tasks
        WHERE user_id = ?
        ORDER BY created_at DESC
        ''',
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_tasks_by_priority(user_id: int, limit: int = 5):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, deadline, tags, estimated_minutes, importance, urgency, reason, priority_score, status, created_at
        FROM tasks
        WHERE user_id = ?
          AND COALESCE(status, 'pending') != 'done'
        ORDER BY COALESCE(priority_score, 0) DESC, created_at DESC
        LIMIT ?
        ''',
        (user_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_all_tasks(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def delete_tasks_by_ids(user_id: int, task_ids: Iterable[int]):
    ids = list(task_ids)
    if not ids:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f'''
        DELETE FROM tasks
        WHERE user_id = ?
        AND id IN ({','.join(['?'] * len(ids))})
    '''
    cursor.execute(query, (user_id, *ids))
    conn.commit()
    conn.close()


def delete_all_ideas(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM ideas WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def delete_ideas_by_ids(user_id: int, idea_ids: Iterable[int]):
    ids = list(idea_ids)
    if not ids:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f'''
        DELETE FROM ideas
        WHERE user_id = ?
        AND id IN ({','.join(['?'] * len(ids))})
    '''
    cursor.execute(query, (user_id, *ids))
    conn.commit()
    conn.close()


def delete_all_notes(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM notes WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def delete_notes_by_ids(user_id: int, note_ids: Iterable[int]):
    ids = list(note_ids)
    if not ids:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f'''
        DELETE FROM notes
        WHERE user_id = ?
        AND id IN ({','.join(['?'] * len(ids))})
    '''
    cursor.execute(query, (user_id, *ids))
    conn.commit()
    conn.close()


def get_idea_by_id(user_id: int, idea_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, tags, created_at
        FROM ideas
        WHERE id = ? AND user_id = ?
        ''',
        (idea_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_note_by_id(user_id: int, note_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, content, tags, created_at
        FROM notes
        WHERE id = ? AND user_id = ?
        ''',
        (note_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_task_status(user_id: int, task_id: int, status: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        UPDATE tasks
        SET status = ?
        WHERE id = ? AND user_id = ?
        ''',
        (status, task_id, user_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


def get_task_by_id(user_id: int, task_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, deadline, tags, estimated_minutes, importance, urgency, reason, priority_score, status, created_at
        FROM tasks
        WHERE id = ? AND user_id = ?
        ''',
        (task_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def snooze_task_deadline(user_id: int, task_id: int, days: int = 1) -> Optional[str]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT deadline FROM tasks WHERE id = ? AND user_id = ?',
        (task_id, user_id),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    current_deadline = row['deadline']
    today = _budapest_today()

    try:
        base_date = datetime.fromisoformat(current_deadline).date() if current_deadline else today
    except ValueError:
        base_date = today

    new_date = base_date + timedelta(days=days)
    new_deadline = new_date.isoformat()

    cursor.execute(
        'UPDATE tasks SET deadline = ? WHERE id = ? AND user_id = ?',
        (new_deadline, task_id, user_id),
    )
    conn.commit()
    conn.close()
    return new_deadline


def get_tasks_due_today_or_high_priority(user_id: int, limit: int = 5, priority_threshold: float = 4.0):
    today = _budapest_today().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, deadline, tags, estimated_minutes, importance, urgency, reason, priority_score, status, created_at
        FROM tasks
        WHERE user_id = ?
          AND COALESCE(status, 'pending') != 'done'
          AND (
                (deadline = ?)
                OR COALESCE(priority_score, 0) >= ?
              )
        ORDER BY COALESCE(priority_score, 0) DESC, created_at DESC
        LIMIT ?
        ''',
        (user_id, today, priority_threshold, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def search_tasks(user_id: int, query: str, limit: int = 10):
    wildcard = f'%{query}%'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, deadline, tags, importance, urgency, status
        FROM tasks
        WHERE user_id = ?
          AND (
                title LIKE ?
                OR description LIKE ?
                OR tags LIKE ?
              )
        ORDER BY created_at DESC
        LIMIT ?
        ''',
        (user_id, wildcard, wildcard, wildcard, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def search_ideas(user_id: int, query: str, limit: int = 10):
    wildcard = f'%{query}%'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, description, tags
        FROM ideas
        WHERE user_id = ?
          AND (
                title LIKE ?
                OR description LIKE ?
                OR tags LIKE ?
              )
        ORDER BY created_at DESC
        LIMIT ?
        ''',
        (user_id, wildcard, wildcard, wildcard, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def search_notes(user_id: int, query: str, limit: int = 10):
    wildcard = f'%{query}%'
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT id, title, content, tags
        FROM notes
        WHERE user_id = ?
          AND (
                title LIKE ?
                OR content LIKE ?
                OR tags LIKE ?
              )
        ORDER BY created_at DESC
        LIMIT ?
        ''',
        (user_id, wildcard, wildcard, wildcard, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _ensure_task_columns(cursor):
    expected_columns = {
        "importance": "ALTER TABLE tasks ADD COLUMN importance INTEGER",
        "urgency": "ALTER TABLE tasks ADD COLUMN urgency INTEGER",
        "reason": "ALTER TABLE tasks ADD COLUMN reason TEXT",
        "priority_score": "ALTER TABLE tasks ADD COLUMN priority_score REAL",
        "status": "ALTER TABLE tasks ADD COLUMN status TEXT DEFAULT 'pending'"
    }

    cursor.execute("PRAGMA table_info(tasks)")
    existing = {row[1] for row in cursor.fetchall()}

    for column, statement in expected_columns.items():
        if column not in existing:
            cursor.execute(statement)


def _budapest_today():
    return datetime.now(BUDAPEST_TZ).date()

