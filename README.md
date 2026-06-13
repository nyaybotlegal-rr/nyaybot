# ⚖️ NyayBot — Indian Legal AI Telegram Bot

> Free AI-powered Telegram bot for Indian legal research. Search judgments, ask legal questions, get AI answers — all at zero cost.

---

## What is NyayBot?

NyayBot is a Telegram bot that helps advocates, law students, and legal researchers with:

- 🔍 **Search** — Find judgments from Supreme Court and High Courts via Indian Kanoon
- 🧠 **AI Q&A** — Ask any Indian legal question and get AI-powered answers (Groq + Llama 3.1)
- 📋 **Daily Cases** — Fetch recent Supreme Court judgments
- 💬 **Natural Chat** — Just type any legal question normally

---

## Tech Stack (All Free)

| Tool | Purpose | Cost |
|------|---------|------|
| Telegram Bot API | User interface | Free |
| Groq (Llama 3.1) | AI legal answers | Free (14,400 req/day) |
| Indian Kanoon | Judgment search | Free (public) |
| python-telegram-bot | Bot framework | Free (open source) |
| Render.com | 24/7 hosting | Free tier |
| GitHub | Code repository | Free |
| Cron-job.org | Keepalive ping | Free |

---

## Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Welcome message and menu | `/start` |
| `/search <query>` | Search Indian court judgments | `/search Section 138 NI Act` |
| `/ask <question>` | Ask any legal question | `/ask What is anticipatory bail?` |
| `/today` | Recent Supreme Court cases | `/today` |
| `/help` | Show all commands | `/help` |

You can also just type any legal question directly — the bot detects legal keywords automatically.

---

## Project Structure

```
nyaybot/
├── bot.py            # Main application (all-in-one)
├── requirements.txt  # Python dependencies
├── Procfile          # Render start command
└── README.md         # This file
```

---

## How It Works

```
User (Telegram)
      |
      v
Telegram Bot API
      |
      v
Render.com (bot.py — Python 3.14)
      |                    |
      v                    v
Indian Kanoon          Groq AI API
(Search judgments)     (Legal Q&A)
      |                    |
      +--------------------+
                |
                v
        Reply sent to User
```

**Keepalive system:**
```
Cron-job.org (every 5 min)
      |
      v  HTTP GET ping
Render Health Server (port 8080)
      |
      v  200 OK
Render stays awake 24/7
```

---

## Setup Guide (Step by Step)

### Step 1 — Create Telegram Bot
1. Open Telegram → search **@BotFather**
2. Send `/newbot`
3. Give it a name and username (must end in `_bot`)
4. Save the **token** given (looks like `7123456789:AAFxyz...`)

### Step 2 — Get Groq API Key
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up free with Google
3. Click **API Keys** → **Create API Key**
4. Save the key (starts with `gsk_...`) — shown only once!

### Step 3 — Create GitHub Repository
1. Go to [github.com](https://github.com) → sign in
2. Click **+** → **New repository** → name it `nyaybot`
3. Set to **Public** → tick **Add README** → Create

### Step 4 — Upload Files to GitHub
Upload these 3 files to your repository:

**requirements.txt**
```
python-telegram-bot==21.5
groq==0.7.0
requests==2.31.0
httpx==0.27.0
```

**Procfile** (no extension, capital P)
```
web: python bot.py
```

**bot.py** — copy from source file

### Step 5 — Deploy on Render
1. Go to [render.com](https://render.com) → sign in with GitHub
2. Click **New +** → **Web Service**
3. Connect your `nyaybot` GitHub repository
4. Fill in:
   - Name: `nyaybot`
   - Region: `Singapore`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`
   - Plan: **Free**
5. Add Environment Variables:
   - `TELEGRAM_TOKEN` = your bot token
   - `GROQ_API_KEY` = your Groq key
6. Click **Create Web Service**

### Step 6 — Setup Keepalive (Cron-job.org)
1. Go to [cron-job.org](https://cron-job.org) → sign up free
2. Click **Create Cronjob**
3. URL: your Render URL (e.g., `https://nyaybot.onrender.com`)
4. Schedule: Every **5 minutes**
5. Save

### Step 7 — Test Your Bot
1. Open Telegram → search your bot username
2. Press **Start**
3. Try: `/ask What is Section 138 NI Act?`

If it replies — your bot is live! 🎉

---

## Environment Variables

| Variable | Description | Where to get |
|----------|-------------|--------------|
| `TELEGRAM_TOKEN` | Bot authentication token | @BotFather on Telegram |
| `GROQ_API_KEY` | Groq AI API key | console.groq.com |

---

## Maintenance

This bot is designed to be **zero maintenance**:

- Render auto-restarts if the bot crashes
- Cron-job.org keeps it awake 24/7
- GitHub → Render auto-deployment on every commit
- No database, no server management needed

To update the bot: edit `bot.py` on GitHub → Render auto-deploys in 2-3 minutes.

---

## Limitations (Free Tier)

| Limitation | Details |
|-----------|---------|
| Groq API | 14,400 requests/day (enough for ~500 users) |
| Render | May be slow on first wake (rare with keepalive) |
| Indian Kanoon | Public search only (no full-text PDF access) |
| Storage | No database — stateless only |

---

## Future Enhancements

- [ ] Daily 8 AM judgment digest to subscribers
- [ ] Topic-based alerts (GST, Arbitration, IBC etc.)
- [ ] Full PDF text extraction and summarization
- [ ] Add to Telegram groups for law firms
- [ ] User subscription management
- [ ] High Court coverage expansion

---

## License

MIT License — free to use, modify, and distribute.

---

*Built with ❤️ for Indian Legal Professionals*
*Powered by Groq AI + Indian Kanoon + Telegram*
