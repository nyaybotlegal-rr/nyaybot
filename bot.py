import os
import logging
import requests
import re
import asyncio
import threading
import feedparser
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from bs4 import BeautifulSoup
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

# ── Court Sources ──────────────────────────────────────
COURT_SOURCES = {
    "supreme_court": {
        "name": "Supreme Court of India",
        "url": "https://main.sci.gov.in/judgments",
        "search_url": "https://indiankanoon.org/search/?formInput=",
        "direct_url": "https://main.sci.gov.in",
        "emoji": "🏛️",
    },
    "delhi_hc": {
        "name": "Delhi High Court",
        "url": "https://dhcapplication.nic.in/",
        "search_url": "https://indiankanoon.org/search/?formInput=court%3A%22Delhi+High+Court%22+",
        "direct_url": "https://dhcapplication.nic.in",
        "emoji": "⚖️",
    },
    "bombay_hc": {
        "name": "Bombay High Court",
        "url": "https://bombayhighcourt.nic.in",
        "search_url": "https://indiankanoon.org/search/?formInput=court%3A%22Bombay+High+Court%22+",
        "direct_url": "https://bombayhighcourt.nic.in",
        "emoji": "⚖️",
    },
    "madras_hc": {
        "name": "Madras High Court",
        "url": "https://hcmadras.tn.nic.in",
        "search_url": "https://indiankanoon.org/search/?formInput=court%3A%22Madras+High+Court%22+",
        "direct_url": "https://hcmadras.tn.nic.in",
        "emoji": "⚖️",
    },
    "calcutta_hc": {
        "name": "Calcutta High Court",
        "url": "https://calcuttahighcourt.gov.in",
        "search_url": "https://indiankanoon.org/search/?formInput=court%3A%22Calcutta+High+Court%22+",
        "direct_url": "https://calcuttahighcourt.gov.in",
        "emoji": "⚖️",
    },
    "allahabad_hc": {
        "name": "Allahabad High Court",
        "url": "https://allahabadhighcourt.in",
        "search_url": "https://indiankanoon.org/search/?formInput=court%3A%22Allahabad+High+Court%22+",
        "direct_url": "https://allahabadhighcourt.in",
        "emoji": "⚖️",
    },
    "karnataka_hc": {
        "name": "Karnataka High Court",
        "url": "https://hckinfo.kerala.gov.in",
        "search_url": "https://indiankanoon.org/search/?formInput=court%3A%22Karnataka+High+Court%22+",
        "direct_url": "https://karnatakajudiciary.kar.nic.in",
        "emoji": "⚖️",
    },
    "gujarat_hc": {
        "name": "Gujarat High Court",
        "url": "https://gujarathighcourt.nic.in",
        "search_url": "https://indiankanoon.org/search/?formInput=court%3A%22Gujarat+High+Court%22+",
        "direct_url": "https://gujarathighcourt.nic.in",
        "emoji": "⚖️",
    },
    "nclt": {
        "name": "NCLT",
        "url": "https://nclt.gov.in",
        "search_url": "https://indiankanoon.org/search/?formInput=court%3A%22NCLT%22+",
        "direct_url": "https://nclt.gov.in",
        "emoji": "🏢",
    },
    "nclat": {
        "name": "NCLAT",
        "url": "https://nclat.nic.in",
        "search_url": "https://indiankanoon.org/search/?formInput=court%3A%22NCLAT%22+",
        "direct_url": "https://nclat.nic.in",
        "emoji": "🏢",
    },
    "ncdrc": {
        "name": "NCDRC (Consumer Court)",
        "url": "https://ncdrc.nic.in",
        "search_url": "https://indiankanoon.org/search/?formInput=court%3A%22NCDRC%22+",
        "direct_url": "https://ncdrc.nic.in",
        "emoji": "🛒",
    },
}

# ── Health Server ──────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"NyayBot is running!")

    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info("Health server on port " + str(port))
    server.serve_forever()


# ── Search Functions ───────────────────────────────────
def search_indian_kanoon(query, court_filter=""):
    """Search Indian Kanoon with optional court filter"""
    try:
        if court_filter:
            full_query = court_filter + query
        else:
            full_query = query
        search_url = "https://indiankanoon.org/search/?formInput=" + full_query.replace(" ", "+")
        resp = requests.get(search_url, timeout=10,
                            headers={"User-Agent": "NyayBot/1.0 Legal Research"})
        results = []
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            result_divs = soup.find_all("div", class_="result")
            if not result_divs:
                titles = re.findall(r'<a href="/doc/[^"]+/"[^>]*>([^<]+)</a>', resp.text)
                links = re.findall(r'href="(/doc/[0-9]+/)"', resp.text)
                dates = re.findall(r'(\d{1,2} \w+ \d{4})', resp.text[:5000])
                for i, (title, link) in enumerate(zip(titles[:5], links[:5])):
                    results.append({
                        "title": title.strip(),
                        "url": "https://indiankanoon.org" + link,
                        "date": dates[i] if i < len(dates) else "Date N/A",
                        "court": "Indian Court",
                        "snippet": "",
                    })
            else:
                for div in result_divs[:5]:
                    title_tag = div.find("a")
                    title = title_tag.get_text(strip=True) if title_tag else "Unknown"
                    link = "https://indiankanoon.org" + title_tag["href"] if title_tag else ""
                    date_tag = div.find("span", class_="docsource_main")
                    date = date_tag.get_text(strip=True) if date_tag else "Date N/A"
                    snippet_tag = div.find("p")
                    snippet = snippet_tag.get_text(strip=True)[:150] if snippet_tag else ""
                    results.append({
                        "title": title,
                        "url": link,
                        "date": date,
                        "court": date,
                        "snippet": snippet,
                    })
        return results
    except Exception as e:
        logger.error("Search error: " + str(e))
        return []


def fetch_sci_recent():
    """Fetch recent Supreme Court judgments via Indian Kanoon"""
    try:
        results = search_indian_kanoon("Supreme Court of India", "")
        return results
    except Exception as e:
        logger.error("SCI fetch error: " + str(e))
        return []


def fetch_rss_news():
    """Fetch latest legal news from free RSS feeds"""
    feeds = [
        ("Bar & Bench", "https://www.barandbench.com/feed"),
        ("LiveLaw", "https://www.livelaw.in/feed"),
        ("SCC Online", "https://www.scconline.com/blog/feed/"),
    ]
    news_items = []
    for source, feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                news_items.append({
                    "source": source,
                    "title": entry.get("title", "No title")[:100],
                    "url": entry.get("link", ""),
                    "date": entry.get("published", "")[:16],
                })
        except Exception as e:
            logger.error("RSS error " + source + ": " + str(e))
    return news_items[:8]


# ── Groq AI ────────────────────────────────────────────
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
        "- For summaries use: Issue / Held / Key Principle format."
    )
    if context:
        user_msg = "Context:\n" + context + "\n\nQuestion: " + question
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


# ── Telegram Handlers ──────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏛️ Supreme Court", callback_data="court_supreme_court"),
         InlineKeyboardButton("⚖️ High Courts", callback_data="show_hc_menu")],
        [InlineKeyboardButton("🏢 NCLT/NCLAT", callback_data="court_nclt"),
         InlineKeyboardButton("🛒 Consumer Court", callback_data="court_ncdrc")],
        [InlineKeyboardButton("📰 Legal News", callback_data="news"),
         InlineKeyboardButton("📋 Today's Cases", callback_data="today")],
        [InlineKeyboardButton("❓ Ask Legal Question", callback_data="help_ask")],
    ]
    text = (
        "Welcome to NyayBot!\n\n"
        "Your free Indian Legal Research Assistant.\n\n"
        "I cover these courts:\n"
        "🏛️ Supreme Court of India\n"
        "⚖️ Delhi, Bombay, Madras, Calcutta,\n"
        "   Allahabad, Karnataka, Gujarat HCs\n"
        "🏢 NCLT / NCLAT\n"
        "🛒 NCDRC (Consumer Court)\n\n"
        "Commands:\n"
        "/search <query> - Search all courts\n"
        "/court - Search specific court\n"
        "/ask <question> - AI legal answer\n"
        "/today - Recent SC judgments\n"
        "/news - Latest legal news\n"
        "/courts - List all courts\n"
        "/help - All commands"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def courts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available courts with direct links"""
    keyboard = []
    row = []
    for key, court in COURT_SOURCES.items():
        row.append(InlineKeyboardButton(
            court["emoji"] + " " + court["name"],
            callback_data="court_" + key
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    text = (
        "Available Court Sources:\n\n"
        "Tap any court to search its judgments.\n"
        "Or use: /court <court name> <query>\n\n"
        "Example:\n"
        "/court delhi high court GST\n"
        "/court supreme court bail"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def court_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search a specific court"""
    args = " ".join(context.args).lower()
    if not args:
        await update.message.reply_text(
            "Usage: /court <court name> <query>\n\n"
            "Examples:\n"
            "/court supreme court bail conditions\n"
            "/court delhi high court GST\n"
            "/court bombay high court cheque bounce\n"
            "/court nclt insolvency\n\n"
            "Or use /courts to pick from a menu."
        )
        return

    matched_court = None
    query = args

    court_keywords = {
        "supreme_court": ["supreme court", "sci", "sc"],
        "delhi_hc": ["delhi", "delhi high court", "dhc"],
        "bombay_hc": ["bombay", "bombay high court", "bhc", "mumbai"],
        "madras_hc": ["madras", "madras high court", "chennai"],
        "calcutta_hc": ["calcutta", "calcutta high court", "kolkata"],
        "allahabad_hc": ["allahabad", "allahabad high court"],
        "karnataka_hc": ["karnataka", "karnataka high court", "bangalore"],
        "gujarat_hc": ["gujarat", "gujarat high court", "ahmedabad"],
        "nclt": ["nclt", "national company law tribunal"],
        "nclat": ["nclat", "national company law appellate"],
        "ncdrc": ["ncdrc", "consumer court", "consumer forum", "national consumer"],
    }

    for court_key, keywords in court_keywords.items():
        for kw in keywords:
            if args.startswith(kw):
                matched_court = court_key
                query = args[len(kw):].strip()
                break
        if matched_court:
            break

    if not matched_court:
        await update.message.reply_text(
            "Court not recognized. Try:\n"
            "/court supreme court <topic>\n"
            "/court delhi high court <topic>\n"
            "/court nclt <topic>\n\n"
            "Or use /courts to see all options."
        )
        return

    if not query:
        query = "recent judgments 2024"

    court = COURT_SOURCES[matched_court]
    msg = await update.message.reply_text(
        "Searching " + court["name"] + " for: " + query + "..."
    )

    court_filter = "court%3A%22" + court["name"].replace(" ", "+") + "%22+"
    results = search_indian_kanoon(query, court_filter)

    if not results:
        results = search_indian_kanoon(court["name"] + " " + query)

    if not results:
        await msg.edit_text(
            "No results found for " + court["name"] + ".\n"
            "Try: /search " + query + " (searches all courts)\n"
            "Or visit: " + court["direct_url"]
        )
        return

    text = court["emoji"] + " " + court["name"] + "\n"
    text += "Search: " + query + "\n\n"
    for i, r in enumerate(results, 1):
        text += str(i) + ". " + r["title"][:70] + "\n"
        text += "   " + r["date"] + "\n"
        text += "   " + r["url"] + "\n\n"
    text += "Visit court directly: " + court["direct_url"]
    await msg.edit_text(text)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search across all courts"""
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text(
            "Usage: /search <query>\n\n"
            "Examples:\n"
            "/search Section 138 NI Act\n"
            "/search GST input tax credit\n"
            "/search arbitration award enforcement\n"
            "/search insolvency resolution plan\n"
            "/search bail anticipatory 2024\n\n"
            "To search a specific court use:\n"
            "/court <court name> <query>"
        )
        return

    msg = await update.message.reply_text("Searching all courts for: " + query + "...")
    results = search_indian_kanoon(query)

    if not results:
        await msg.edit_text(
            "No results found for: " + query + "\n"
            "Try different keywords or use /court to search specific courts."
        )
        return

    text = "Search Results: " + query + "\n\n"
    for i, r in enumerate(results, 1):
        text += str(i) + ". " + r["title"][:70] + "\n"
        text += "   " + r["date"] + "\n"
        text += "   " + r["url"] + "\n\n"
    text += "Tip: Use /court to filter by specific court."
    await msg.edit_text(text)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text(
            "Usage: /ask <your legal question>\n\n"
            "Examples:\n"
            "/ask What is Section 138 NI Act?\n"
            "/ask Explain IBC Section 7 application\n"
            "/ask What is the test for anticipatory bail?\n"
            "/ask Difference between void and voidable contract"
        )
        return
    msg = await update.message.reply_text("Thinking...")
    answer = ask_groq(question)
    await msg.edit_text(
        "Question: " + question + "\n\n"
        "Answer:\n" + answer + "\n\n"
        "NyayBot - Powered by Groq AI"
    )


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent SC judgments"""
    msg = await update.message.reply_text("Fetching recent Supreme Court judgments...")
    results = fetch_sci_recent()
    today_str = datetime.now().strftime("%d %B %Y")
    text = "🏛️ Recent Supreme Court Judgments\n" + today_str + "\n\n"
    if results:
        for i, r in enumerate(results[:5], 1):
            text += str(i) + ". " + r["title"][:70] + "\n"
            text += "   " + r["url"] + "\n\n"
    else:
        text += "Could not fetch. Try: /search Supreme Court 2024"
    text += "\nSearch specific courts: /courts"
    await msg.edit_text(text)


async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch latest legal news from RSS feeds"""
    msg = await update.message.reply_text("Fetching latest legal news...")
    news = fetch_rss_news()
    if not news:
        await msg.edit_text(
            "Could not fetch news right now. Try these sites:\n"
            "- barandbench.com\n"
            "- livelaw.in\n"
            "- scconline.com"
        )
        return
    text = "📰 Latest Legal News\n\n"
    current_source = ""
    for item in news:
        if item["source"] != current_source:
            current_source = item["source"]
            text += "\n" + current_source + ":\n"
        text += "• " + item["title"] + "\n"
        text += "  " + item["url"] + "\n\n"
    await msg.edit_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "NyayBot - All Commands\n\n"
        "/search <query>\n"
        "Search across all Indian courts\n"
        "Example: /search GST appeal 2024\n\n"
        "/court <court> <query>\n"
        "Search a specific court\n"
        "Example: /court delhi high court bail\n\n"
        "/courts\n"
        "Show all available courts\n\n"
        "/ask <question>\n"
        "AI answer to any legal question\n"
        "Example: /ask What is res judicata?\n\n"
        "/today\n"
        "Recent Supreme Court judgments\n\n"
        "/news\n"
        "Latest legal news (Bar & Bench, LiveLaw)\n\n"
        "/help\n"
        "Show this help message\n\n"
        "Courts Covered:\n"
        "Supreme Court, Delhi HC, Bombay HC,\n"
        "Madras HC, Calcutta HC, Allahabad HC,\n"
        "Karnataka HC, Gujarat HC,\n"
        "NCLT, NCLAT, NCDRC"
    )
    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    legal_keywords = [
        "section", "act", "court", "judgment", "case", "law", "bail",
        "ipc", "crpc", "gst", "arbitration", "appeal", "petition",
        "high court", "supreme court", "tribunal", "advocate", "ibc",
        "nclt", "nclat", "consumer", "cheque", "writ", "habeas",
        "mandamus", "certiorari", "injunction", "stay", "contempt"
    ]
    is_legal = any(kw in text.lower() for kw in legal_keywords)
    if is_legal or "?" in text or len(text) > 20:
        msg = await update.message.reply_text("Analyzing your question...")
        answer = ask_groq(text)
        await msg.edit_text(answer + "\n\nNyayBot - Powered by Groq AI")
    else:
        await update.message.reply_text(
            "Hi! Ask me any Indian legal question.\n\n"
            "/search - Find judgments\n"
            "/court - Search specific court\n"
            "/ask - Legal AI answer\n"
            "/news - Legal news\n"
            "/help - All commands"
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "today":
        await today_command(update, context)

    elif data == "news":
        await news_command(update, context)

    elif data == "help_ask":
        await query.message.reply_text(
            "How to ask legal questions:\n\n"
            "Type /ask followed by your question\n\n"
            "Examples:\n"
            "/ask What is the punishment for Section 420 IPC?\n"
            "/ask Explain the doctrine of promissory estoppel\n"
            "/ask What are the grounds for writ of mandamus?\n"
            "/ask Difference between NCLT and NCLAT"
        )

    elif data == "show_hc_menu":
        hc_keyboard = [
            [InlineKeyboardButton("Delhi HC", callback_data="court_delhi_hc"),
             InlineKeyboardButton("Bombay HC", callback_data="court_bombay_hc")],
            [InlineKeyboardButton("Madras HC", callback_data="court_madras_hc"),
             InlineKeyboardButton("Calcutta HC", callback_data="court_calcutta_hc")],
            [InlineKeyboardButton("Allahabad HC", callback_data="court_allahabad_hc"),
             InlineKeyboardButton("Karnataka HC", callback_data="court_karnataka_hc")],
            [InlineKeyboardButton("Gujarat HC", callback_data="court_gujarat_hc")],
        ]
        await query.message.reply_text(
            "Select a High Court:",
            reply_markup=InlineKeyboardMarkup(hc_keyboard)
        )

    elif data.startswith("court_"):
        court_key = data[6:]
        if court_key in COURT_SOURCES:
            court = COURT_SOURCES[court_key]
            results = search_indian_kanoon(
                "recent 2024",
                "court%3A%22" + court["name"].replace(" ", "+") + "%22+"
            )
            if not results:
                results = search_indian_kanoon(court["name"] + " 2024")

            text = court["emoji"] + " " + court["name"] + "\nRecent Judgments\n\n"
            if results:
                for i, r in enumerate(results[:4], 1):
                    text += str(i) + ". " + r["title"][:65] + "\n"
                    text += "   " + r["url"] + "\n\n"
            else:
                text += "Visit directly: " + court["direct_url"] + "\n"
            text += "\nSearch this court: /court " + court["name"].lower() + " <topic>"
            await query.message.reply_text(text)


# ── Main ───────────────────────────────────────────────
async def run_bot():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("court", court_command))
    app.add_handler(CommandHandler("courts", courts_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("NyayBot is running with multi-court support...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    await asyncio.Event().wait()


if __name__ == "__main__":
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    asyncio.run(run_bot())
