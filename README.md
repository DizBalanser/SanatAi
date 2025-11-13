# SanatAi
AI Task Manager - Telegram Bot

A simple Telegram bot that allows users to store and retrieve messages using SQLite database.

## Features

- `/start` - Welcome message
- `/add <text>` - Save a message to the database
- `/list` - Show the last 5 saved messages

## Setup

1. **Create Telegram Bot via @BotFather**
   - Open Telegram → search @BotFather
   - Send `/newbot`
   - Choose name + username
   - Copy the HTTP API token

2. **Create .env file**
   - Create a `.env` file in the project root
   - Add your token: `TELEGRAM_TOKEN=your_token_here`

3. **Activate virtual environment**
   ```powershell
   venv\Scripts\Activate.ps1
   ```

4. **Install dependencies** (if not already installed)
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the bot**
   ```bash
   python src/bot.py
   ```

## Project Structure

```
SanatAi/
├── src/
│   ├── bot.py      # Main bot logic
│   └── db.py       # Database functions
├── venv/           # Virtual environment
├── .env            # Environment variables (create this)
├── messages.db     # SQLite database (created automatically)
└── requirements.txt
```
