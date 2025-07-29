import os
import json
import asyncio
import html
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv
import openai
from gmail_utils import fetch_and_cache_unread_emails

# === Environment Setup === #
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# === Bot Initialization === #
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

# === Constants === #
SYSTEM_PROMPT = """
You are SanatAi — a high-IQ (IQ 180) personal coach and intelligent mirror of Sanatbek Zhamurzaev.
You remember recent conversation and saved facts. Use that context to reply concisely, supportively, and insightfully.
"""
HISTORY_LIMIT = 30
MEMORY_FILE = "memory.json"

# === Load Memory & History === #
try:
    with open("history.json", "r", encoding="utf-8") as f:
        dialog_history = json.load(f)
except FileNotFoundError:
    dialog_history = []

try:
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        memory = json.load(f)
except FileNotFoundError:
    memory = {}

# === Utility Functions === #
def save_memory():
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

def save_history():
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(dialog_history, f, ensure_ascii=False, indent=2)

def build_messages(user_prompt: str):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if memory:
        mem_text = "\n".join(f"{k}: {v}" for k, v in memory.items())
        messages.append({"role": "system", "content": f"Memory:\n{mem_text}"})
    for entry in dialog_history[-HISTORY_LIMIT:]:
        messages.append({"role": "user", "content": entry['user']})
        messages.append({"role": "assistant", "content": entry['ai']})
    messages.append({"role": "user", "content": user_prompt})
    return messages

async def ask_openai(prompt: str) -> str:
    try:
        messages = build_messages(prompt)
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            timeout=20
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error: {e}"

async def extract_memory_entries(user_prompt: str) -> dict:
    extraction_prompt = (
        "Identify personal facts or preferences in the text to store as JSON key:value. "
        "If none, return {}. Text:\n" + user_prompt
    )
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": extraction_prompt}
            ],
            timeout=20
        )
        return json.loads(resp.choices[0].message.content)
    except Exception:
        return {}

async def summarize_email_with_gpt(subject, sender, body):
    try:
        messages = [
            {"role": "system", "content": "You summarize emails in 2-3 concise and clear sentences. Focus on what's most important for the user to know."},
            {"role": "user", "content": f"Email subject: {subject}\nFrom: {sender}\n\n{body}"}
        ]
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=messages,
            timeout=20
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "(summary failed)"

# === Bot Commands === #
@dp.message_handler(commands=["summary_inbox"])
async def cmd_summary_inbox(message: types.Message):
    await message.reply("📥 Checking unread emails and summarizing...")
    try:
        emails = fetch_and_cache_unread_emails()
        if not emails:
            return await message.reply("📜 No unread emails.")

        reply_lines = []
        for i, email in enumerate(emails):
            summary = await summarize_email_with_gpt(email["subject"], email["from"], email["body"])
            reply_lines.append(f"<b>{i+1}. {html.escape(summary)}</b>\nFrom: {html.escape(email['from'])}")

        await message.reply("\n\n".join(reply_lines), parse_mode="HTML")

    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@dp.message_handler(commands=['read'])
async def cmd_read_email(message: types.Message):
    try:
        index = int(message.get_args().strip()) - 1
        with open("email_cache.json", "r", encoding="utf-8") as f:
            emails = json.load(f)
        if 0 <= index < len(emails):
            e = emails[index]
            safe_subject = html.escape(e['subject'])
            safe_from = html.escape(e['from'])
            safe_body = html.escape(e['body'])[:2000]
            preview = f"<b>{safe_subject}</b>\nFrom: {safe_from}\n\n{safe_body}"
            await message.reply(preview, parse_mode="HTML")
        else:
            await message.reply("📜 Email number out of range.")
    except Exception:
        await message.reply("⚠️ Usage: /read <email_number>")

@dp.message_handler(commands=['history'])
async def cmd_history(message: types.Message):
    if not dialog_history:
        return await message.reply("No conversation history yet.")
    lines = []
    for idx, entry in enumerate(dialog_history[-HISTORY_LIMIT:], 1):
        lines.append(f"{idx}. You: {html.escape(entry['user'])}")
        lines.append(f"   SanatAi: {html.escape(entry['ai'])}")
    await message.reply("\n".join(lines))

@dp.message_handler(commands=['reset'])
async def cmd_reset(message: types.Message):
    global dialog_history
    dialog_history = []
    save_history()
    await message.reply("Conversation history cleared.")

@dp.message_handler(commands=['remember'])
async def cmd_remember(message: types.Message):
    text = message.get_args()
    if ' is ' in text:
        key, val = text.split(' is ', 1)
        memory[key.strip()] = val.strip()
        save_memory()
        await message.reply(f"Got it! I'll remember: {html.escape(key.strip())} is {html.escape(val.strip())}")
    else:
        await message.reply("Use: /remember <fact> is <value>")

@dp.message_handler(commands=['forget'])
async def cmd_forget(message: types.Message):
    key = message.get_args().strip()
    if key in memory:
        memory.pop(key)
        save_memory()
        await message.reply(f"Forgot '{html.escape(key)}'.")
    else:
        await message.reply(f"No memory for '{html.escape(key)}' found.")

@dp.message_handler(commands=['summarize'])
async def cmd_summarize(message: types.Message):
    recent = "\n".join(e['user'] for e in dialog_history[-HISTORY_LIMIT:])
    summary = await ask_openai(f"Summarize in 2-3 sentences to make a notes:\n{recent}")
    await message.reply(f"Summary:\n{html.escape(summary)}")

@dp.message_handler(commands=['memory'])
async def cmd_memory(message: types.Message):
    if not memory:
        await message.reply("🧠 I don't remember anything yet.")
        return
    lines = ["🧠 <b>Current memory:</b>"]
    for key, value in memory.items():
        lines.append(f"• <b>{html.escape(key)}</b>: {html.escape(value)}")
    await message.reply("\n".join(lines), parse_mode="HTML")

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handle_message(message: types.Message):
    user_input = message.text.strip()
    await message.chat.do("typing")
    reply = await ask_openai(user_input)
    dialog_history.append({'user': user_input, 'ai': reply})
    if len(dialog_history) > HISTORY_LIMIT:
        dialog_history.pop(0)
    save_history()
    new_mem = await extract_memory_entries(user_input)
    for k,v in new_mem.items():
        memory[k] = v
    if new_mem:
        save_memory()
    await message.reply(html.escape(reply))

# === Start Bot === #
if __name__ == "__main__":
    print("[SanatAi] Starting bot...")
    executor.start_polling(dp, skip_updates=True)
