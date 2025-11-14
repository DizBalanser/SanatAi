from typing import List

from db import get_tasks_by_priority, get_tasks_due_today_or_high_priority


def get_top_tasks(user_id: int, limit: int = 5) -> List[dict]:
    """
    Fetch tasks sorted by priority_score (DESC) and return the top entries.
    """
    limit = max(1, min(limit, 5))
    tasks = get_tasks_by_priority(user_id, limit=limit)
    return tasks


def get_today_tasks(user_id: int, limit: int = 5, priority_threshold: float = 4.0) -> List[dict]:
    """
    Fetch tasks that are due today or exceed the priority threshold.
    """
    limit = max(1, min(limit, 5))
    tasks = get_tasks_due_today_or_high_priority(user_id, limit=limit, priority_threshold=priority_threshold)
    return tasks
