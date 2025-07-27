import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv
import openai

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)

openai.api_key = OPENAI_API_KEY

SYSTEM_PROMPT = """
You are SanatAi — a high-IQ (IQ 180) personal coach and intelligent mirror of Sanatbek Zhamurzaev. 
You are trained on his thoughts, values, goals, and communication style. You act as his digital twin: 
supporting, analyzing, planning, reflecting, and responding as he would — but with greater clarity, 
emotional intelligence, and wisdom. Your mission is to help Sanatbek continuously grow — intellectually, 
emotionally, professionally, and physically — and to handle messages, decisions, and thoughts with deep
care and strategic insight. Be practical, grounded, direct, supportive, and visionary. Default to thinking 
ahead, suggesting improvements, and taking initiative when appropriate
"""

async def ask_openai(user_prompt: str) -> str:
    print(f"[Prompt] {user_prompt}")  # Debug print
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Или "gpt-3.5-turbo" если хочешь дешевле
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            timeout=15  # 
        )
        answer = response["choices"][0]["message"]["content"]
        print(f"[Answer] {answer}")  #  Debug print
        return answer
    except Exception as e:
        print(f"[OpenAI Error] {e}")
        return "⚠️ Sorry, I had trouble processing your request. Please try again."

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handle_message(message: types.Message):
    chat_type = message.chat.type
    user_input = message.text

    if chat_type in ["group", "supergroup"]:
        me = await bot.get_me()
        bot_mention = f"@{me.username.lower()}"

        if bot_mention in user_input.lower():
            clean_input = user_input.replace(bot_mention, "").strip()
            await message.chat.do("typing")
            reply = await ask_openai(clean_input)
            await message.reply(reply)
    else:
        await message.chat.do("typing")
        reply = await ask_openai(user_input)
        await message.reply(reply)

if __name__ == "__main__":
    print("[SanatAi] Bot is starting...")
    executor.start_polling(dp, skip_updates=True)
