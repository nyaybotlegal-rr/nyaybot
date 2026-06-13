import os
import logging
import requests
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

groq_client = Groq(api_key=GROQ_API_KEY)


def search_indian_kanoon(query):
    try:
        search_url = "https://indiankanoon.org/search/?formInput=" + query.replace(" ", "+")
        resp = requests.get(search_url, timeout=10,
                            headers={"User-Agent": "NyayBot/1.0"})
        results = []
        if resp.status_code == 200:
            titles = re.findall(r'<a href="/doc/[^"]+/"[^>]*>([^<]+)</a>', resp.text)
            links = re.findall(r'href="(/doc/[0-9]+/)"', resp.text)
            dates = re.findall(r'(\d{1,2} \w+ \d{4})', resp.text[:5000])
            for i, (title, link) in enumerate(zip(titles[:5], links[:5])):
                results.append({
                    "title": title.strip(),
                    "url": "https://indiankanoon.org" + link,
                    "date": dates[i] if i < len(dates) else "Date N/A",
                })
        return results
    except Exception as e:
        logger.error("Search error: " + str(e))
        return []


def ask_groq(question, context=""):
    system_prompt = (
        "You are NyayBot, an expert Indian legal research assistant. "
        "You help lawyers, law students, and researchers understand Indian court judgments. "
        "RULES: "
        "- Answer only about Indian law and judgments. "
        "- Be precise and use proper legal terminology. "
        "- Always mention relevant Acts/Sections when applicable. "
        "- If you don't know something, say so clearly. "
        "- Keep answers concise but complete (max 300 words). "
        "- For summaries use this format: "
        "Issue: [legal issue] "
        "Held: [court decision] "
        "Key Principle: [important legal principle]"
    )

    if context:
        user_msg = "Context from judgment:\n" + context + "\n\nQuestion: " + question
    else:
        user_msg = question

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        return "AI error: " + str(e) + ". Please try again."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Search Judgments", callback_data="help_search")],
        [InlineKeyboardButton("Ask a Legal Question", callback_data="help_ask")],
        [InlineKeyboardButton("Today's Top Cases", callback_data="today")],
    ]
    text = (
        "Welcome to NyayBot!\n\n"
        "Your free Indian Legal Research Assistant.\n\n"
        "I can help you:\n"
        "- Search Supreme Court and High Court judgments\n"
        "- Answer legal questions using AI\n"
        "- Summarize judgments in simple language\n"
        "- Explain Acts, Sections and legal principles\n\n"
        "Commands:\n"
        "/search <query> - Search judgments\n"
        "/ask <question> - Ask any legal question\n"
        "/today - Recent important cases\n"
        "/help - Show all commands"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text(
            "Usage: /search <your query>\n\n"
            "Examples:\n"
            "/search Section 138 NI Act\n"
            "/search Supreme Court bail 2024\n"
            "/search GST input tax credit"
        )
        return

    msg = await update.message.reply_text("Searching for: " + query + "...")
    results = search_indian_kanoon(query)

    if not results:
        await msg.edit_text("No results found. Try different keywords.")
        return

    text = "Results for: " + query + "\n\n"
    for i, r in enumerate(results, 1):
        text += str(i) + ". " + r["title"][:80] + "\n"
        text += "   " + r["date"] + "\n"
        text += "   " + r["url"] + "\n\n"

    text += "Tap a link to open the full judgment."
    await msg.edit_text(text)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text(
            "Usage: /ask <your legal question>\n\n"
            "Examples:\n"
            "/ask What is the limitation period for cheque bounce cases?\n"
            "/ask Explain Section 34 of Arbitration Act\n"
            "/ask What are grounds for anticipatory bail?"
        )
        return

    msg = await update.message.reply_text("Thinking...")
    answer = ask_groq(question)
    await msg.edit_text("Question: " + question + "\n\nAnswer:\n" + answer + "\n\nNyayBot - Powered by Groq AI")


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Fetching recent Supreme Court cases...")
    results = search_indian_kanoon("Supreme Court 2024")

    today_str = datetime.now().strftime("%d %B %Y")
    text = "Recent Supreme Court Cases\n" + today_str + "\n\n"

    if results:
        for i, r in enumerate(results[:5], 1):
            text += str(i) + ". " + r["title"][:70] + "\n"
            text += "   " + r["url"] + "\n\n"
    else:
        text += "Unable to fetch cases right now. Try /search Supreme Court"

    text += "\nUse /search to find cases on specific topics."
    await msg.edit_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "NyayBot - All Commands\n\n"
        "/search <query>\n"
        "Search Indian court judgments\n"
        "Example: /search Section 138 NI Act\n\n"
        "/ask <question>\n"
        "Ask any Indian legal question\n"
        "Example: /ask What is res judicata?\n\n"
        "/today\n"
        "Recent Supreme Court cases\n\n"
        "Or just type any legal question normally!\n\n"
        "Topics covered:\n"
        "Criminal Law, Civil Law, GST, Arbitration,\n"
        "Insolvency, Constitutional Law, Family Law,\n"
        "Consumer Law, Service Law, Corporate Law"
    )
    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    legal_keywords = [
        "section", "act", "court", "judgment", "case", "law", "bail",
        "ipc", "crpc", "gst", "arbitration", "appeal", "petition",
        "high court", "supreme court", "tribunal", "advocate"
    ]
    is_legal = any(kw in text.lower() for kw in legal_keywords)

    if is_legal or "?" in text or len(text) > 20:
        msg = await update.message.reply_text("Analyzing your question...")
        answer = ask_groq(text)
        await msg.edit_text(answer + "\n\nNyayBot - Powered by Groq AI")
    else:
        await update.message.reply_text(
            "Hi! Ask me any Indian legal question or use:\n"
            "/search - to find judgments\n"
            "/ask - to ask a legal question\n"
            "/help - to see all commands"
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "today":
        await today_command(update, context)
    elif query.data == "help_search":
        await query.message.reply_text(
            "How to search judgments:\n\n"
            "Type /search followed by your topic\n\n"
            "Examples:\n"
            "/search Section 138 NI Act cheque bounce\n"
            "/search Supreme Court GST 2024\n"
            "/search bail conditions high court"
        )
    elif query.data == "help_ask":
        await query.message.reply_text(
            "How to ask legal questions:\n\n"
            "Type /ask followed by your question\n\n"
            "Examples:\n"
            "/ask What is the punishment for Section 420 IPC?\n"
            "/ask Explain the doctrine of promissory estoppel\n"
            "/ask What documents are needed to file a writ petition?"
        )


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("NyayBot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
