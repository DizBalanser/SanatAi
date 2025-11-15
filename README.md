# SanatAi
AI-Powered Task Manager - Telegram Bot

An intelligent Telegram bot that automatically classifies and organizes your messages into tasks, ideas, and notes using OpenAI. Features AI-powered task prioritization and smart suggestions.

## Features

### 🤖 AI-Powered Classification
- **Automatic Classification**: Just send any text and the bot automatically classifies it as a task, idea, or note
- **Smart Task Analysis**: AI analyzes tasks and assigns importance/urgency scores
- **Priority Scoring**: Tasks are automatically prioritized based on AI analysis

### 📋 Task Management
- **View Tasks**: See all tasks, filter by status (done/active), or view all
- **Task Filtering**: 
  - `/review_tasks` - Show all tasks
  - `/review_tasks done` - Show only completed tasks
  - `/review_tasks active` - Show only active (not completed) tasks
- **Task Details**: View full details of any task with `/task <id>`
- **Task Actions**: Use inline buttons to Accept, Snooze, or mark tasks as Done
- **Smart Suggestions**: Get prioritized task suggestions with `/suggest` or `/suggest_today`

### 💡 Ideas & Notes
- **Ideas**: Store and review your ideas with `/review_ideas`
- **Notes**: Save and view notes with `/review_notes`
- **View Details**: See full details with `/idea <id>` or `/note <id>`

### 🔍 Search
- Search across all tasks, ideas, and notes with `/search <keywords>`

### 🗑️ Management
- Delete items individually or in bulk
- Confirmation dialogs for dangerous operations
- Pagination for long lists

## Commands

### Basic Commands
- `/start` - Welcome message and introduction
- `/help` - Show all available commands

### Viewing Items
- `/review_tasks` or `/tasks` or `/t` - View all tasks
- `/review_tasks done` - View completed tasks only
- `/review_tasks active` - View active (not completed) tasks only
- `/review_ideas` or `/ideas` or `/i` - View your ideas
- `/review_notes` or `/notes` or `/n` - View your notes
- `/task <id>` - View task details
- `/idea <id>` - View idea details
- `/note <id>` - View note details

### Smart Features
- `/suggest` - Get top priority task suggestions
- `/suggest_today` - Get tasks due today or high priority
- `/search <keywords>` - Search across all items

### Deleting Items
- `/clear_task [all|1,2,3]` - Delete tasks (use `all` to delete all, or numbers to delete specific ones)
- `/clear_idea [all|1,2,3]` - Delete ideas
- `/clear_note [all|1,2,3]` - Delete notes

### Quick Actions
When viewing suggested tasks, use inline buttons:
- **Accept** - Mark task as accepted
- **Snooze** - Delay task deadline by 1 day
- **Done** - Mark task as completed

## Setup

### 1. Create Telegram Bot via @BotFather
- Open Telegram → search `@BotFather`
- Send `/newbot`
- Choose a name and username for your bot
- Copy the HTTP API token

### 2. Get OpenAI API Key
- Go to [OpenAI Platform](https://platform.openai.com/)
- Create an account or sign in
- Navigate to API Keys section
- Create a new API key

### 3. Create .env file
Create a `.env` file in the project root with your tokens:

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 4. Activate Virtual Environment

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 5. Install Dependencies
```bash
pip install -r requirements.txt
```

### 6. Run the Bot
```bash
python src/bot.py
```

## Usage Examples

### Adding Items
Just send any text message:
```
Buy groceries tomorrow
→ Classified as: Task with deadline 2025-11-15

Great app idea: fitness tracker
→ Classified as: Idea

Meeting notes: discussed project timeline
→ Classified as: Note
```

### Viewing Tasks
```
/review_tasks          → Shows all tasks with status labels
/review_tasks done     → Shows only completed tasks (✅ Done)
/review_tasks active   → Shows only active tasks (⏳ Not Completed)
```

### Task Actions
When you use `/suggest`, you'll see tasks with inline buttons:
- Click **Accept** to mark as accepted
- Click **Snooze** to delay by 1 day
- Click **Done** to mark as completed

## Project Structure

```
SanatAi/
├── src/
│   ├── bot.py              # Main bot logic and handlers
│   ├── db.py               # Database operations
│   ├── ai/
│   │   ├── classifier.py   # AI message classification
│   │   └── task_analysis.py # AI task prioritization
│   └── services/
│       └── suggestions.py  # Task suggestion logic
├── venv/                   # Virtual environment
├── .env                    # Environment variables (create this)
├── messages.db             # SQLite database (created automatically)
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Dependencies

- `python-telegram-bot==20.7` - Telegram bot framework
- `python-dotenv` - Environment variable management
- `openai>=1.51.0` - OpenAI API client for AI features

## How It Works

1. **Message Classification**: When you send a message, it's sent to OpenAI which classifies it as task, idea, or note
2. **Task Analysis**: If classified as a task, the AI analyzes it and assigns:
   - Importance score (1-5)
   - Urgency score (1-5)
   - Priority score (calculated from importance and urgency)
3. **Storage**: Items are stored in SQLite database with all extracted information
4. **Smart Suggestions**: The bot suggests tasks based on priority scores and deadlines

## Notes

- The database file `messages.db` is created automatically on first run
- All data is stored locally in SQLite
- The bot uses OpenAI API for classification and analysis (requires API key)
- Task status labels: **✅ Done** for completed tasks, **⏳ Not Completed** for active tasks

## License

See LICENSE file for details.
