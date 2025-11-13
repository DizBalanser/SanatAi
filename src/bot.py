import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from db import init_db, save_message, get_last_messages

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /add <text> to store items.")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Please provide text to save. Usage: /add <text>")
        return
    
    text = ' '.join(context.args)
    
    save_message(user_id, text)
    
    await update.message.reply_text("Saved!")


async def list_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    messages = get_last_messages(user_id, limit=5)
    
    if not messages:
        await update.message.reply_text("No messages found. Use /add <text> to store items.")
        return
    
    formatted_list = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(messages)])
    
    await update.message.reply_text(formatted_list)


def main():
    token = os.getenv('TELEGRAM_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_TOKEN not found in .env file!")
        return
    
    init_db()
    logger.info("Database initialized")
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("list", list_messages))
    
    logger.info("Bot started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

