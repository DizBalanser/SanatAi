import asyncio
import json
import os
import logging
from typing import Any, Dict, Iterable, List, Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ai.classifier import classify_message
from ai.task_analysis import analyze_task
from db import (
    delete_all_ideas,
    delete_all_notes,
    delete_all_tasks,
    delete_ideas_by_ids,
    delete_notes_by_ids,
    delete_tasks_by_ids,
    get_all_ideas,
    get_all_notes,
    get_all_tasks,
    get_ideas_by_user,
    get_notes_by_user,
    get_tasks_by_user,
    init_db,
    save_idea,
    save_note,
    save_task,
    update_task_analysis,
)
from services.suggestions import get_top_tasks

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey! Send any text and I'll classify it into tasks, ideas, or notes automatically.\n"
        "Commands: /review_tasks /review_ideas /review_notes /suggest /clear_task /clear_idea /clear_note"
    )


async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    await _process_incoming_text(update, text)


async def review_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = get_tasks_by_user(user_id, limit=10)

    if not tasks:
        await update.message.reply_text("You have no tasks yet. Send me something todo!")
        return

    lines: List[str] = ["Your tasks:"]
    for idx, task in enumerate(tasks, start=1):
        deadline = task.get("deadline") or "no deadline"
        est = task.get("estimated_minutes")
        est_part = f" - {est} min" if est else ""
        lines.append(f"{idx}) [{task.get('title')}] (deadline: {deadline}){est_part}")

    await update.message.reply_text("\n".join(lines))


async def review_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ideas = get_ideas_by_user(user_id, limit=10)

    if not ideas:
        await update.message.reply_text("No ideas saved yet. Share your spark and I'll keep it.")
        return

    lines: List[str] = ["Your ideas:"]
    for idx, idea in enumerate(ideas, start=1):
        desc = (idea.get("description") or "")[:50]
        suffix = f" - {desc}..." if desc else ""
        lines.append(f"{idx}) {idea.get('title')}{suffix}")

    await update.message.reply_text("\n".join(lines))


async def review_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    notes = get_notes_by_user(user_id, limit=10)

    if not notes:
        await update.message.reply_text("You do not have notes yet. Send any thought to get started.")
        return

    lines: List[str] = ["Your notes:"]
    for idx, note in enumerate(notes, start=1):
        title = note.get("title") or f"Note #{note.get('id')}"
        snippet = (note.get("content") or "")[:60]
        suffix = f" - {snippet}..." if snippet else ""
        lines.append(f"{idx}) {title}{suffix}")

    await update.message.reply_text("\n".join(lines))


async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = get_top_tasks(user_id, limit=5)

    if not tasks:
        await update.message.reply_text("No tasks available for suggestions yet.")
        return

    lines = ["🔥 Your top tasks:"]
    for idx, task in enumerate(tasks, start=1):
        title = task.get("title") or f"Task #{task.get('id')}"
        importance = task.get("importance") or "?"
        urgency = task.get("urgency") or "?"
        lines.append(f"{idx}. {title} (⭐{importance}/⏳{urgency})")

    await update.message.reply_text("\n".join(lines))

async def clear_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_clear_command(
        update,
        entity_name="task",
        fetch_all_fn=get_all_tasks,
        delete_all_fn=delete_all_tasks,
        delete_ids_fn=delete_tasks_by_ids,
    )


async def clear_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_clear_command(
        update,
        entity_name="idea",
        fetch_all_fn=get_all_ideas,
        delete_all_fn=delete_all_ideas,
        delete_ids_fn=delete_ideas_by_ids,
    )


async def clear_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_clear_command(
        update,
        entity_name="note",
        fetch_all_fn=get_all_notes,
        delete_all_fn=delete_all_notes,
        delete_ids_fn=delete_notes_by_ids,
    )


async def _process_incoming_text(update: Update, text: str):
    user_id = update.effective_user.id

    if not text:
        await update.message.reply_text("I need some text to classify. Try typing a note or todo!")
        return

    try:
        classification = classify_message(text)
    except Exception as exc:
        logger.error("Classification error: %s", exc, exc_info=True)
        await _fallback_note(update, user_id, text, reason="AI failed to respond.")
        return

    entry_type = (classification or {}).get("type")
    logger.info("Classification result: %s", classification)

    if entry_type == "task" and classification.get("task"):
        await _save_task(update, user_id, classification["task"], text)
        return

    if entry_type == "idea" and classification.get("idea"):
        await _save_idea(update, user_id, classification["idea"], text)
        return

    if entry_type == "note" and classification.get("note"):
        await _save_note(update, user_id, classification["note"], text)
        return

    await _fallback_note(update, user_id, text, reason="AI returned an unexpected response.")


async def _save_task(update: Update, user_id: int, payload: dict, original_text: str):
    title = payload.get("title") or _clip_text(original_text)
    description = payload.get("details") or payload.get("description")
    deadline = payload.get("deadline")
    tags = _prepare_tags(payload.get("tags"))
    estimated_minutes = _to_int(payload.get("estimated_minutes"))

    task_id = save_task(user_id, title, description, deadline, tags, estimated_minutes)

    try:
        analysis = await _analyze_task_async(title, description or original_text, deadline)
    except Exception as exc:
        logger.warning("Task analysis failed, using fallback: %s", exc)
        analysis = {"importance": 3, "urgency": 3, "reason": "ai_fallback"}
    importance = analysis["importance"]
    urgency = analysis["urgency"]
    reason = analysis["reason"]
    priority_score = round(importance * 0.6 + urgency * 0.4, 2)
    update_task_analysis(task_id, importance, urgency, reason, priority_score)

    deadline_part = f" (deadline: {deadline})" if deadline else ""
    est_part = f" [{estimated_minutes} min]" if estimated_minutes else ""
    await update.message.reply_text(
        f"Saved as task: {title}{deadline_part}{est_part} (⭐{importance}/⏳{urgency})"
    )


async def _save_idea(update: Update, user_id: int, payload: dict, original_text: str):
    title = payload.get("title") or _clip_text(original_text)
    description = payload.get("details") or payload.get("description")
    tags = _prepare_tags(payload.get("tags"))

    save_idea(user_id, title, description, tags)
    await update.message.reply_text(f"Saved as idea: {title}")


async def _save_note(update: Update, user_id: int, payload: dict, original_text: str):
    title = payload.get("title")
    content = payload.get("content") or original_text
    tags = _prepare_tags(payload.get("tags"))

    save_note(user_id, title, content, tags)
    label = title or _clip_text(content)
    await update.message.reply_text(f"Saved as note: {label}")


async def _fallback_note(update: Update, user_id: int, text: str, reason: str):
    logger.warning("Falling back to note storage: %s", reason)
    save_note(user_id, None, text, None)
    await update.message.reply_text("AI failed to classify, so I saved it as a note.")


def _prepare_tags(tags: Optional[Any]) -> Optional[List[str]]:
    if tags is None:
        return None
    if isinstance(tags, str):
        try:
            # try to parse a JSON-style string list first
            maybe_json = tags.strip()
            if maybe_json.startswith("["):
                parsed = json.loads(maybe_json)
                if isinstance(parsed, list):
                    return _prepare_tags(parsed)
        except Exception:
            pass
        return [tag.strip() for tag in tags.split(",") if tag.strip()]
    if isinstance(tags, Iterable):
        cleaned = []
        for tag in tags:
            if tag is None:
                continue
            cleaned_tag = str(tag).strip()
            if cleaned_tag:
                cleaned.append(cleaned_tag)
        return cleaned or None
    cleaned_value = str(tags).strip()
    return [cleaned_value] if cleaned_value else None


def _clip_text(text: str, max_len: int = 60) -> str:
    text = text.strip()
    return text if len(text) <= max_len else f"{text[: max_len - 3].rstrip()}..."


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def _analyze_task_async(title: str, details: str, deadline: Optional[str]) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, analyze_task, title, details, deadline)


async def _handle_clear_command(
    update: Update,
    entity_name: str,
    fetch_all_fn,
    delete_all_fn,
    delete_ids_fn,
):
    user_id = update.effective_user.id
    args = update.message.text.split(maxsplit=1)
    args_text = args[1].strip() if len(args) > 1 else ""

    if not args_text:
        await update.message.reply_text(f"Usage: /clear_{entity_name} all | 1 | 1,2,3")
        return

    if args_text.lower() == "all":
        delete_all_fn(user_id)
        await update.message.reply_text(f"Deleted all {entity_name}s.")
        return

    try:
        indices = _parse_indices(args_text)
    except ValueError:
        await update.message.reply_text("Invalid indexes format. Use numbers like 1 or 1,2,3.")
        return

    entities = fetch_all_fn(user_id)
    if not entities:
        await update.message.reply_text(f"No {entity_name}s found.")
        return

    max_index = len(entities)
    invalid = [i for i in indices if i < 1 or i > max_index]
    if invalid:
        await update.message.reply_text(f"Invalid {entity_name} indexes: {invalid}")
        return

    ids_to_delete = [entities[i - 1]["id"] for i in indices]
    delete_ids_fn(user_id, ids_to_delete)

    if len(indices) == 1:
        await update.message.reply_text(f"Deleted: {indices[0]} {entity_name}.")
    else:
        joined = ",".join(str(i) for i in indices)
        await update.message.reply_text(f"Deleted {entity_name}s: {joined}")


def _parse_indices(text: str) -> List[int]:
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        raise ValueError("No indexes provided.")
    return [int(part) for part in parts]


def main():
    token = os.getenv('TELEGRAM_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_TOKEN not found in .env file!")
        return
    
    init_db()
    logger.info("Database initialized")
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("review_tasks", review_tasks))
    application.add_handler(CommandHandler("review_ideas", review_ideas))
    application.add_handler(CommandHandler("review_notes", review_notes))
    application.add_handler(CommandHandler("suggest", suggest))
    application.add_handler(CommandHandler("clear_task", clear_task))
    application.add_handler(CommandHandler("clear_idea", clear_idea))
    application.add_handler(CommandHandler("clear_note", clear_note))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text))
    
    logger.info("Bot started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
