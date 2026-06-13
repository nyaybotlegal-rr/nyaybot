# bot.py — NyayBot: Free Indian Legal AI Telegram Bot
# Uses: Groq (free AI) + Indian Kanoon API + python-telegram-bot

import os
import logging
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from groq import Groq

# ── Setup ──────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY   = os.environ["GROQ_API_KEY"]

groq_client = Groq(api_key=GROQ_API_KEY)

# ── Indian Kanoon Search (Free) ────────────────────────
def search_indian_kanoon(query: str, max_results: int = 5) -> list:
    """Search judgments using Indian Kanoon free API"""
    try:
        url = "https://api.indiankanoon.org/search/"
        params = {"formInput": query, "pagenum": 0}
        headers = {"Authorization": "Token YOUR_INDIANKANOON_TOKEN"}
        # Note: Get free token at https://indiankanoon.org/api/
        # For now we use the public search page as fallback
        
        # Fallback: scrape public search (no token needed)
        search_url = f"https://indiankanoon.org/search/?formInput={query.replace(' ', '+')}"
        resp = requests.get(search_url, timeout=10,
                           headers={"User-Agent": "NyayBot/1.0"})
        
        # Parse basic results from response
        results = []
        if resp.status_code == 200:
            # Extract titles from HTML (basic parsing)
            import re
            titles = re.findall(r'<a href="/doc/[^"]+/"[^>]*>([^<]+)</a>', resp.text)
            links  = re.findall(r'href="(/doc/[0-9]+/)"', resp.text)
            dates  = re.findall(r'(d{1,2} w+ d{4})', resp.text[:5000])
            
            for i, (title, link) in enumerate(zip(titles[:max_results], links[:max_results])):
                results.append({
                    "title": title.strip(),
                    "url": f"https://indiankanoon.org{link}",
                    "date": dates[i] if i < len(dates) else "Date N/A",
                })
        return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

# ── AI Answer with Groq (Free) ─────────────────────────
def ask_groq(question: str, context: str = "") -> str:
    """Get AI answer using free Groq API (Llama 3)"""
    system_prompt = """You are NyayBot, an expert Indian legal research assistant.
You help lawyers, law students, and researchers understand Indian court judgments.

RULES:
- Answer only about Indian law and judgments
- Be precise and use proper legal terminology
- Always mention relevant Acts/Sections when applicable
- If you don't know something, say so clearly
- Keep answers concise but complete (max 300 words)
- For summaries, use this format:
  📋 Issue: [legal issue]
  ⚖️ Held: [court's decision]  
  📌 Key Principle: [important legal principle]
"""
    
    user_msg = f"{question}"
    if context:
        user_msg = f"Context from judgment:
{context}

Question: {question}"
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Free, fast model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI error: {str(e)}. Please try again."

# ── Telegram Handlers ──────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Search Judgments", callback_data="help_search")],
        [InlineKeyboardButton("❓ Ask a Legal Question", callback_data="help_ask")],
        [InlineKeyboardButton("📋 Today's Top Cases", callback_data="today")],
    ]
    await update.message.reply_text(
        "⚖️ *Welcome to NyayBot!*

"
        "Your free Indian Legal Research Assistant.

"
        "I can help you:
"
        "• 🔍 Search Supreme Court & High Court judgments
"
        "• ❓ Answer legal questions using AI
"
        "• 📋 Summarize judgments in simple language
"
        "• 📚 Explain Acts, Sections & legal principles

"
        "*Commands:*
"
        "/search \<query\> — Search judgments
"
        "/ask \<question\> — Ask any legal question
"
        "/today — Today's important cases
"
        "/help — Show all commands",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text(
            "Usage: /search <your query>

"
            "Examples:
"
            "• /search Section 138 NI Act
"
            "• /search Supreme Court bail 2024
"
            "• /search GST input tax credit"
        )
        return
    
    msg = await update.message.reply_text(f"🔍 Searching for: *{query}*...", parse_mode="Markdown")
    results = search_indian_kanoon(query)
    
    if not results:
        await msg.edit_text("❌ No results found. Try different keywords.")
        return
    
    text = f"🔍 *Results for: {query}*

"
    for i, r in enumerate(results, 1):
        text += f"{i}\. [{r['title'][:60]}]({r['url']})
"
        text += f"   📅 {r['date']}

"
    
    text += "💡 Tap a case title to open it\. Then ask me: /ask explain this case"
    
    await msg.edit_text(text, parse_mode="MarkdownV2", disable_web_page_preview=True)

async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text(
            "Usage: /ask <your legal question>

"
            "Examples:
"
            "• /ask What is the limitation period for cheque bounce cases?
"
            "• /ask Explain Section 34 of Arbitration Act
"
            "• /ask What are grounds for anticipatory bail?"
        )
        return
    
    msg = await update.message.reply_text("🧠 Thinking...")
    answer = ask_groq(question)
    
    await msg.edit_text(
        f"❓ *Question:* {question}

"
        f"⚖️ *Answer:*
{answer}

"
        f"_Powered by Groq AI • NyayBot_",
        parse_mode="Markdown",
    )

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📋 Fetching today's important cases...")
    
    # Search for recent Supreme Court judgments
    results = search_indian_kanoon("Supreme Court 2024")
    
    text = f"📋 *Recent Supreme Court Cases*
_{datetime.now().strftime('%d %B %Y')}_

"
    
    if results:
        for i, r in enumerate(results[:5], 1):
            text += f"{i}\. [{r['title'][:55]}]({r['url']})

"
    else:
        text += "Unable to fetch today's cases\. Try /search Supreme Court"
    
    text += "
💡 Use /search to find cases on specific topics"
    await msg.edit_text(text, parse_mode="MarkdownV2", disable_web_page_preview=True)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚖️ *NyayBot — All Commands*

"
        "🔍 */search* \<query\>
"
        "Search Indian court judgments
"
        "_Example: /search Section 138 NI Act_

"
        "❓ */ask* \<question\>
"
        "Ask any Indian legal question
"
        "_Example: /ask What is res judicata?_

"
        "📋 */today*
"
        "Recent Supreme Court cases

"
        "💬 *Just type normally* to chat about law\!

"
        "📚 *Topics I cover:*
"
        "Criminal Law • Civil Law • GST • Arbitration
"
        "Insolvency • Constitutional Law • Family Law
"
        "Consumer Law • Service Law • Corporate Law",
        parse_mode="MarkdownV2",
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text messages as legal questions"""
    text = update.message.text
    
    # Check if it looks like a legal question
    legal_keywords = ["section", "act", "court", "judgment", "case", "law", "bail",
                      "ipc", "crpc", "gst", "arbitration", "appeal", "petition",
                      "high court", "supreme court", "tribunal", "advocate"]
    
    is_legal = any(kw in text.lower() for kw in legal_keywords)
    
    if is_legal or "?" in text or len(text) > 20:
        msg = await update.message.reply_text("🧠 Analyzing your question...")
        answer = ask_groq(text)
        await msg.edit_text(
            f"⚖️ {answer}

_NyayBot • Powered by Groq AI_",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "Hi! Ask me any Indian legal question or use:
"
            "/search — to find judgments
"
            "/ask — to ask a legal question
"
            "/help — to see all commands"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "today":
        await today_command(update, context)
    elif query.data == "help_search":
        await query.message.reply_text(
            "🔍 *How to search judgments:*

"
            "Type: /search followed by your topic

"
            "Examples:
"
            "• /search Section 138 NI Act cheque bounce
"
            "• /search Supreme Court GST 2024
"
            "• /search bail conditions high court",
            parse_mode="Markdown",
        )
    elif query.data == "help_ask":
        await query.message.reply_text(
            "❓ *How to ask legal questions:*

"
            "Type: /ask followed by your question

"
            "Examples:
"
            "• /ask What is the punishment for Section 420 IPC?
"
            "• /ask Explain the doctrine of promissory estoppel
"
            "• /ask What documents are needed to file a writ petition?",
            parse_mode="Markdown",
        )

# ── Main ───────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("ask",    ask_command))
    app.add_handler(CommandHandler("today",  today_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ NyayBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
