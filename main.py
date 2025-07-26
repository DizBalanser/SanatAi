import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv
import openai

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

openai.api_key = OPENAI_API_KEY

@dp.message_handler()
async def handle_message(message: types.Message):
    user_input = message.text
    await message.answer("💬 Думаю над ответом...")

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Ты — SanatAi, ассистент-клон пользователя. Помогаешь, заботишься, отвечаешь от его имени, ведёшь дела."},
            {"role": "user", "content": user_input}
        ]
    )
    answer = response["choices"][0]["message"]["content"]
    await message.answer(answer)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)