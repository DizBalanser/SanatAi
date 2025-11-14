from typing import List

from db import get_tasks_by_priority


def get_top_tasks(user_id: int, limit: int = 5) -> List[dict]:
    """
    Fetch tasks sorted by priority_score (DESC) and return the top entries.
    """
    limit = max(1, min(limit, 5))
    tasks = get_tasks_by_priority(user_id, limit=limit)
    return tasks
