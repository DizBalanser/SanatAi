import asyncio
import json
import os
import logging
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

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
    get_idea_by_id,
    get_ideas_by_user,
    get_note_by_id,
    get_notes_by_user,
    get_task_by_id,
    get_tasks_by_user,
    get_tasks_completed,
    get_tasks_uncompleted,
    init_db,
    save_idea,
    save_note,
    save_task,
    search_ideas,
    search_notes,
    search_tasks,
    snooze_task_deadline,
    update_task_analysis,
    update_task_status,
)
from services.suggestions import get_today_tasks, get_top_tasks

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to SanatAi!\n\n"
        "Just send me any text and I'll automatically organize it into tasks, ideas, or notes.\n\n"
        "Try it now: send something like \"Buy groceries tomorrow\" or \"Great app idea: fitness tracker\".\n\n"
        "Type /help to see everything I can do."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📚 <b>SanatAi Bot Commands</b>\n\n"
        "📝 <b>Adding Items</b>\n"
        "Just send any text! I'll automatically classify it as a task, idea, or note.\n\n"
        "📋 <b>Viewing Items</b>\n"
        "/review_tasks [done|active] – View your tasks\n"
        "/review_ideas – View your ideas\n"
        "/review_notes – View your notes\n"
        "/task &lt;id&gt; – View a task in detail\n"
        "/idea &lt;id&gt; – View an idea in detail\n"
        "/note &lt;id&gt; – View a note in detail\n\n"
        "💡 <b>Smart Suggestions</b>\n"
        "/suggest – Top priority tasks\n"
        "/suggest_today – Tasks due today or high priority\n\n"
        "🔍 <b>Search</b>\n"
        "/search &lt;keywords&gt; – Find tasks, ideas, and notes\n\n"
        "🗑️ <b>Deleting Items</b>\n"
        "/clear_task [all|1,2,3] – Delete tasks\n"
        "/clear_idea [all|1,2,3] – Delete ideas\n"
        "/clear_note [all|1,2,3] – Delete notes\n\n"
        "ℹ️ <b>Other</b>\n"
        "/start – Welcome message\n"
        "/help – Show this help message\n\n"
        "💬 <b>Quick Actions on Suggestions</b>\n"
        "Use the inline buttons to Accept (mark as accepted), Snooze (delay by 1 day), or Done (mark completed)."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    await _process_incoming_text(update, text)


async def review_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    filter_token, page = _parse_task_args(context.args)

    text, keyboard, empty_msg = _build_task_list_message(user_id, filter_token, page)
    if not text:
        await update.message.reply_text(empty_msg)
        return

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


async def review_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    page = _parse_page_arg(context.args)
    text, keyboard, empty_msg = _build_idea_list_message(user_id, page)

    if not text:
        await update.message.reply_text(empty_msg)
        return

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


async def review_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    page = _parse_page_arg(context.args)
    text, keyboard, empty_msg = _build_note_list_message(user_id, page)

    if not text:
        await update.message.reply_text(empty_msg)
        return

    await update.message.reply_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = get_top_tasks(user_id, limit=5)
    await _send_task_suggestions(update, tasks, empty_message="No tasks available for suggestions yet.")


async def suggest_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = get_today_tasks(user_id, limit=5)
    await _send_task_suggestions(update, tasks, empty_message="No tasks match today's focus.")


async def view_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_view_command(
        update,
        context,
        fetch_fn=get_task_by_id,
        entity_name="task",
        formatter=_format_task_detail,
    )


async def view_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_view_command(
        update,
        context,
        fetch_fn=get_idea_by_id,
        entity_name="idea",
        formatter=_format_idea_detail,
    )


async def view_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_view_command(
        update,
        context,
        fetch_fn=get_note_by_id,
        entity_name="note",
        formatter=_format_note_detail,
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args or []).strip()
    message = update.message
    if not message:
        return

    if not query:
        await message.reply_text("Usage: /search <keywords>")
        return

    user_id = update.effective_user.id
    tasks = search_tasks(user_id, query, limit=5)
    ideas = search_ideas(user_id, query, limit=5)
    notes = search_notes(user_id, query, limit=5)

    if not any([tasks, ideas, notes]):
        await message.reply_text(f"No matches found for \"{query}\".")
        return

    esc_query = _escape_markdown(query)
    lines = [f"🔍 *Search results for:* _{esc_query}_", ""]

    if tasks:
        lines.append("📋 *Tasks*")
        for task in tasks:
            title = _escape_markdown(task.get("title") or "Untitled")
            lines.append(f"• {title} (ID: {task['id']})")
        lines.append("")

    if ideas:
        lines.append("💡 *Ideas*")
        for idea in ideas:
            title = _escape_markdown(idea.get("title") or "Untitled")
            lines.append(f"• {title} (ID: {idea['id']})")
        lines.append("")

    if notes:
        lines.append("🗒️ *Notes*")
        for note in notes:
            title = _escape_markdown(note.get("title") or f"Note #{note['id']}")
            lines.append(f"• {title} (ID: {note['id']})")

    text = "\n".join(line for line in lines if line is not None)
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

async def clear_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_clear_command(
        update,
        context,
        entity_name="task",
        fetch_all_fn=get_all_tasks,
        delete_all_fn=delete_all_tasks,
        delete_ids_fn=delete_tasks_by_ids,
        confirm_key="tasks",
    )


async def clear_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_clear_command(
        update,
        context,
        entity_name="idea",
        fetch_all_fn=get_all_ideas,
        delete_all_fn=delete_all_ideas,
        delete_ids_fn=delete_ideas_by_ids,
        confirm_key="ideas",
    )


async def clear_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle_clear_command(
        update,
        context,
        entity_name="note",
        fetch_all_fn=get_all_notes,
        delete_all_fn=delete_all_notes,
        delete_ids_fn=delete_notes_by_ids,
        confirm_key="notes",
    )


async def handle_task_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = (query.data or "").strip()
    await query.answer()

    if "_" not in data:
        await query.message.reply_text("Unknown action.")
        return

    action, task_id_str = data.split("_", 1)
    try:
        task_id = int(task_id_str)
    except ValueError:
        await query.message.reply_text("Invalid task reference.")
        return

    user_id = query.from_user.id

    if action == "accept":
        if update_task_status(user_id, task_id, "accepted"):
            await query.message.reply_text("Accepted! I'll schedule it.")
            await query.edit_message_reply_markup(reply_markup=None)
        else:
            await query.message.reply_text("I couldn't find that task.")

    elif action == "snooze":
        new_deadline = snooze_task_deadline(user_id, task_id, days=1)
        if new_deadline:
            await query.message.reply_text(f"Snoozed until {new_deadline}.")
            await query.edit_message_reply_markup(reply_markup=None)
        else:
            await query.message.reply_text("Snooze failed. Task not found.")

    elif action == "done":
        if update_task_status(user_id, task_id, "done"):
            await query.message.reply_text("Great! Task completed. 🎉")
            await query.edit_message_reply_markup(reply_markup=None)
        else:
            await query.message.reply_text("I couldn't find that task.")
    else:
        await query.message.reply_text("Unsupported action.")


async def handle_clear_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    await query.answer()

    if data == "cancel_clear":
        await query.edit_message_text("Deletion cancelled.")
        return

    try:
        _, entity_key, user_id_str = data.split(":")
    except ValueError:
        await query.message.reply_text("Invalid confirmation data.")
        return

    if str(query.from_user.id) != user_id_str:
        await query.message.reply_text("You can't confirm this action.")
        return

    delete_map = {
        "tasks": (delete_all_tasks, "tasks"),
        "ideas": (delete_all_ideas, "ideas"),
        "notes": (delete_all_notes, "notes"),
    }
    entry = delete_map.get(entity_key)
    if not entry:
        await query.message.reply_text("Unknown entity.")
        return

    delete_fn, label = entry
    delete_fn(query.from_user.id)
    await query.edit_message_text(f"All {label} deleted.")


async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    await query.answer()

    try:
        _, list_type, filter_token, page_str = data.split(":")
        page = max(1, int(page_str))
    except ValueError:
        await query.message.reply_text("Invalid pagination request.")
        return

    user_id = query.from_user.id

    if list_type == "tasks":
        text, keyboard, empty_msg = _build_task_list_message(user_id, filter_token, page)
    elif list_type == "ideas":
        text, keyboard, empty_msg = _build_idea_list_message(user_id, page)
    else:
        text, keyboard, empty_msg = _build_note_list_message(user_id, page)

    if not text:
        await query.answer(empty_msg or "No entries for this page.")
        return

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


async def _send_task_suggestions(update: Update, tasks: List[dict], empty_message: str):
    message = update.effective_message
    if not message:
        return

    if not tasks:
        await message.reply_text(empty_message)
        return

    for task in tasks:
        text = _format_task_message(task)
        keyboard = _build_task_keyboard(task["id"])
        await message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)


def _format_task_message(task: dict) -> str:
    title = task.get("title") or "Untitled task"
    importance = task.get("importance") if task.get("importance") is not None else "?"
    urgency = task.get("urgency") if task.get("urgency") is not None else "?"
    reason = task.get("reason") or "No reason yet."
    deadline = task.get("deadline")

    lines = [
        f"🔥 Task: {title}",
        f"⭐ Importance: {importance}",
        f"⏳ Urgency: {urgency}",
    ]
    if deadline:
        lines.append(f"📅 Deadline: {deadline}")
    lines.append(f"Reason: {reason}")
    return "\n".join(lines)


def _build_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton("Accept", callback_data=f"accept_{task_id}"),
            InlineKeyboardButton("Snooze", callback_data=f"snooze_{task_id}"),
            InlineKeyboardButton("Done", callback_data=f"done_{task_id}"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


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


def _safe_positive_int(value: Any, default: int = 1) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


async def _analyze_task_async(title: str, details: str, deadline: Optional[str]) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, analyze_task, title, details, deadline)


async def _handle_clear_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    entity_name: str,
    fetch_all_fn,
    delete_all_fn,
    delete_ids_fn,
    confirm_key: str,
):
    user_id = update.effective_user.id
    args = context.args or []
    args_text = " ".join(args).strip()

    if not args_text:
        await update.message.reply_text(f"Usage: /clear_{entity_name} all | 1 | 1,2,3")
        return

    if args and args[0].lower() == "all":
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Yes, delete all",
                        callback_data=f"confirm_clear:{confirm_key}:{user_id}",
                    ),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_clear"),
                ]
            ]
        )
        await update.message.reply_text(
            f"⚠️ Are you sure you want to delete ALL {entity_name}s? This cannot be undone!",
            reply_markup=keyboard,
        )
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


def _escape_markdown(text: Optional[str]) -> str:
    if text is None:
        return ""
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)


async def _handle_view_command(update: Update, context: ContextTypes.DEFAULT_TYPE, fetch_fn, entity_name: str, formatter):
    if not context.args:
        await update.message.reply_text(f"Usage: /{entity_name} <id>")
        return

    try:
        item_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a numeric ID.")
        return

    user_id = update.effective_user.id
    record = fetch_fn(user_id, item_id)
    if not record:
        await update.message.reply_text(f"{entity_name.capitalize()} not found.")
        return

    text = formatter(record)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


def _format_task_detail(task: dict) -> str:
    title = _escape_markdown(task.get("title") or "Untitled task")
    description = _escape_markdown(task.get("description") or "")
    tags = task.get("tags") or ""
    tags_text = _escape_markdown(tags) if tags else "-"
    reason = _escape_markdown(task.get("reason") or "")
    status = _escape_markdown(task.get("status") or "pending")
    deadline = _escape_markdown(task.get("deadline")) if task.get("deadline") else None
    lines = [
        f"📌 *Task #{task['id']}: {title}*",
        f"Status: {status}",
    ]
    if deadline:
        lines.append(f"📅 Deadline: {deadline}")
    if task.get("estimated_minutes"):
        lines.append(f"⏱️ Estimated: {task['estimated_minutes']} min")
    lines.append(f"⭐ Importance: {task.get('importance') or '?'}")
    lines.append(f"⏳ Urgency: {task.get('urgency') or '?'}")
    if reason:
        lines.append(f"📝 Reason: {reason}")
    if description:
        lines.append(f"\nDescription:\n{description}")
    lines.append(f"\nTags: {tags_text}")
    return "\n".join(lines)


def _format_idea_detail(idea: dict) -> str:
    title = _escape_markdown(idea.get("title") or "Untitled idea")
    description = _escape_markdown(idea.get("description") or "")
    tags = idea.get("tags") or ""
    tags_text = _escape_markdown(tags) if tags else "-"
    lines = [
        f"💡 *Idea #{idea['id']}: {title}*",
    ]
    if description:
        lines.append(f"\nDetails:\n{description}")
    lines.append(f"\nTags: {tags_text}")
    return "\n".join(lines)


def _format_note_detail(note: dict) -> str:
    title = _escape_markdown(note.get("title") or f"Note #{note['id']}")
    content = _escape_markdown(note.get("content") or "")
    tags = note.get("tags") or ""
    tags_text = _escape_markdown(tags) if tags else "-"
    lines = [
        f"🗒️ *Note #{note['id']}: {title}*",
        f"\nContent:\n{content}",
        f"\nTags: {tags_text}",
    ]
    return "\n".join(lines)


def _parse_task_args(args: List[str]) -> Tuple[str, int]:
    filter_token = "all"
    page = 1
    remaining = list(args or [])

    if remaining:
        first = remaining[0].lower()
        if first in {"done", "active", "all"}:
            filter_token = first
            remaining = remaining[1:]

    if remaining:
        page = _safe_positive_int(remaining[0], default=1) or 1

    return filter_token, max(1, page)


def _parse_page_arg(args: List[str]) -> int:
    if not args:
        return 1
    return max(1, _safe_positive_int(args[0], default=1) or 1)


def _build_task_list_message(user_id: int, filter_token: str, page: int, limit: int = 10):
    offset = (page - 1) * limit
    filter_token = filter_token or "all"

    if filter_token == "done":
        tasks = get_tasks_completed(user_id, limit=limit, offset=offset)
        header = "✅ Completed Tasks"
        empty_msg = "No completed tasks yet."
    elif filter_token == "active":
        tasks = get_tasks_uncompleted(user_id, limit=limit, offset=offset)
        header = "⏳ Active Tasks (Not Completed)"
        empty_msg = "🎉 No active tasks! All done!"
    else:
        tasks = get_tasks_by_user(user_id, limit=limit, offset=offset)
        header = "📋 All Tasks"
        empty_msg = "You have no tasks yet. Send me something todo!"

    if not tasks:
        msg = empty_msg if offset == 0 else "No tasks on this page."
        return None, None, msg

    lines: List[str] = [f"{header} — page {page}", ""]
    for idx, task in enumerate(tasks, start=offset + 1):
        lines.extend(_format_task_entry(task, idx))
        lines.append("")

    text = "\n".join(line for line in lines if line is not None).strip()
    keyboard = _build_pagination_keyboard("tasks", filter_token, page, len(tasks) == limit)
    return text, keyboard, None


def _build_idea_list_message(user_id: int, page: int, limit: int = 10):
    offset = (page - 1) * limit
    ideas = get_ideas_by_user(user_id, limit=limit, offset=offset)
    if not ideas:
        msg = "No ideas saved yet. Share your spark and I'll keep it." if offset == 0 else "No ideas on this page."
        return None, None, msg

    lines: List[str] = [f"💡 Ideas — page {page}", ""]
    for idx, idea in enumerate(ideas, start=offset + 1):
        lines.extend(_format_idea_entry(idea, idx))
        lines.append("")

    text = "\n".join(line for line in lines if line is not None).strip()
    keyboard = _build_pagination_keyboard("ideas", "all", page, len(ideas) == limit)
    return text, keyboard, None


def _build_note_list_message(user_id: int, page: int, limit: int = 10):
    offset = (page - 1) * limit
    notes = get_notes_by_user(user_id, limit=limit, offset=offset)
    if not notes:
        msg = "You do not have notes yet. Send any thought to get started." if offset == 0 else "No notes on this page."
        return None, None, msg

    lines: List[str] = [f"🗒️ Notes — page {page}", ""]
    for idx, note in enumerate(notes, start=offset + 1):
        lines.extend(_format_note_entry(note, idx))
        lines.append("")

    text = "\n".join(line for line in lines if line is not None).strip()
    keyboard = _build_pagination_keyboard("notes", "all", page, len(notes) == limit)
    return text, keyboard, None


def _format_task_entry(task: dict, idx: int) -> List[str]:
    title = _escape_markdown(task.get("title") or "Untitled task")
    status = (task.get("status") or "pending").lower()
    deadline = task.get("deadline")
    est = task.get("estimated_minutes")
    importance = task.get("importance")
    urgency = task.get("urgency")
    reason = task.get("reason")

    lines = [f"📌 *{idx}. {title}*"]
    lines.append(f"   Status: {'✅ Done' if status == 'done' else '⏳ Not Completed'}")
    if deadline:
        lines.append(f"   📅 Due: {deadline}")
    if est:
        lines.append(f"   ⏱️ Est: {est} min")
    if importance or urgency:
        lines.append(f"   ⭐ {importance or '?'} / ⏳ {urgency or '?'}")
    if reason:
        lines.append(f"   📝 {_escape_markdown(reason)}")
    return lines


def _format_idea_entry(idea: dict, idx: int) -> List[str]:
    title = _escape_markdown(idea.get("title") or "Untitled idea")
    description = idea.get("description")
    preview = _escape_markdown((description or "")[:80]) if description else ""

    lines = [f"💡 *{idx}. {title}*"]
    if preview:
        lines.append(f"   📝 {preview}")
    return lines


def _format_note_entry(note: dict, idx: int) -> List[str]:
    title = _escape_markdown(note.get("title") or f"Note #{note.get('id')}")
    content = note.get("content") or ""
    preview = _escape_markdown(content[:100]) if content else ""

    lines = [f"🗒️ *{idx}. {title}*"]
    if preview:
        lines.append(f"   📝 {preview}")
    return lines


def _build_pagination_keyboard(list_type: str, filter_token: str, page: int, has_next: bool):
    buttons = []
    if page > 1:
        buttons.append(
            InlineKeyboardButton(
                "⬅ Prev",
                callback_data=f"page:{list_type}:{filter_token}:{page - 1}",
            )
        )
    if has_next:
        buttons.append(
            InlineKeyboardButton(
                "Next ➡",
                callback_data=f"page:{list_type}:{filter_token}:{page + 1}",
            )
        )

    if not buttons:
        return None
    return InlineKeyboardMarkup([buttons])


def main():
    token = os.getenv('TELEGRAM_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_TOKEN not found in .env file!")
        return
    
    init_db()
    logger.info("Database initialized")
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler(["review_tasks", "tasks", "t"], review_tasks))
    application.add_handler(CommandHandler(["review_ideas", "ideas", "i"], review_ideas))
    application.add_handler(CommandHandler(["review_notes", "notes", "n"], review_notes))
    application.add_handler(CommandHandler("suggest", suggest))
    application.add_handler(CommandHandler("suggest_today", suggest_today))
    application.add_handler(CommandHandler("task", view_task))
    application.add_handler(CommandHandler("idea", view_idea))
    application.add_handler(CommandHandler("note", view_note))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("clear_task", clear_task))
    application.add_handler(CommandHandler("clear_idea", clear_idea))
    application.add_handler(CommandHandler("clear_note", clear_note))
    application.add_handler(CallbackQueryHandler(handle_pagination, pattern=r"^page:(tasks|ideas|notes):"))
    application.add_handler(CallbackQueryHandler(handle_clear_confirmation, pattern=r"^(confirm_clear:[^:]+:\d+|cancel_clear)$"))
    application.add_handler(CallbackQueryHandler(handle_task_action, pattern=r"^(accept|snooze|done)_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text))
    
    logger.info("Bot started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
