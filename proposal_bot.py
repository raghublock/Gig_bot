#!/usr/bin/env python3
"""
Raghuveer's Ultimate Bot v6.0
FREE - Google Gemini + CoinGecko API
Features:
- Latest jobs (Indeed + LinkedIn)
- Cover letter generator
- Job match analysis
- Crypto price alerts (BTC, ETH, SOL, APT, ARB, SUI)
- Airdrop alerts
- Testnet launch alerts
- Whale transaction alerts
- New token listing alerts
"""

import os
import logging
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler,
    filters
)

# ──────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

GEMINI_KEYS = [
    os.environ.get("GEMINI_KEY_1"),
    os.environ.get("GEMINI_KEY_2"),
    os.environ.get("GEMINI_KEY_3"),
    os.environ.get("GEMINI_KEY_4"),
]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]
_key_index = [0]

# Alert intervals
ALERT_INTERVAL        = 7200  # Job alerts — har 2 ghante
CRYPTO_ALERT_INTERVAL = 300   # Crypto — har 5 minute

# In-memory user data
user_watchlist   = {}  # {chat_id: ["BTC", "ETH", ...]}
user_price_cache = {}  # {chat_id: {"BTC": 65000, ...}}

# Supported coins
SUPPORTED_COINS = {
    "BTC":   "bitcoin",
    "ETH":   "ethereum",
    "SOL":   "solana",
    "APT":   "aptos",
    "ARB":   "arbitrum",
    "SUI":   "sui",
    "BNB":   "binancecoin",
    "MATIC": "matic-network",
    "DOGE":  "dogecoin",
    "AVAX":  "avalanche-2",
    "LINK":  "chainlink",
    "UNI":   "uniswap",
}

DEFAULT_WATCHLIST = ["BTC", "ETH", "SOL", "APT", "ARB", "SUI"]

# ──────────────────────────────────────────
# JOB ROLES
# ──────────────────────────────────────────
JOB_ROLES = {
    "💻 Web Dev": [
        "React Developer",
        "Node.js Developer",
        "Full Stack Developer",
        "Frontend Developer",
        "JavaScript Developer",
    ],
    "🐍 Python/AI": [
        "Python Developer",
        "AI ML Developer",
        "Streamlit Developer",
        "Python Automation",
        "Data Analyst",
    ],
    "⛓️ Blockchain": [
        "Blockchain Developer",
        "Web3 Developer",
        "Solidity Developer",
        "DeFi Developer",
        "Crypto Tester",
    ],
    "📊 Freelance": [
        "Data Entry",
        "Data Analyst",
        "Web Scraping",
        "Virtual Assistant",
        "Content Writer",
    ],
    "🤝 Sponsorship": [
        "Blockchain Testnet",
        "Web3 Ambassador",
        "Crypto Airdrop Tester",
        "DeFi Beta Tester",
        "Brand Ambassador Tech",
    ]
}

# ──────────────────────────────────────────
# RAGHUVEER KA RESUME
# ──────────────────────────────────────────
RESUME = """
NAME: Raghuveer Bhati
LOCATION: Bikaner, Rajasthan, India
PORTFOLIO: https://raghublock.github.io/portfolio
GITHUB: https://github.com/raghublock

TITLE: Full Stack Web Developer | Blockchain Tester | AI Tools Developer

EDUCATION:
- B.Tech ECE | B.Sc Biology | B.Ed Science | RSCIT Certified

PROJECTS:
1. Library Fee System — React, TailwindCSS, Cloudflare
2. Student Fees Dashboard — HTML, JS, Cloudflare Workers
3. Veggie Shop — Node.js, EJS, Render
4. AI PDF Editor — Python, Streamlit, OCR
5. BG Remover — HTML, JS, Python Rembg API
6. Hindi Typing Master — HTML, CSS, JS
7. NoteList PWA — HTML, CSS, JS, Firebase

SKILLS:
- Frontend: React.js, Next.js, HTML5, CSS3, TailwindCSS, JavaScript
- Backend: Node.js, Express.js, EJS
- DB: MongoDB, PostgreSQL, Firebase, Cloudflare Workers
- AI/ML: Python, Streamlit, OCR, Rembg
- Blockchain: Web3.js, IPFS, Aptos, Arbitrum, Sui, Linea, Rust

EXPERIENCE:
- Freelancer Web Dev (Sep 2024 - Present)
- Web3 & Blockchain Tester (Aug 2019 - Present) — Aptos, Arbitrum, Sui, Linea
- Accounts Clerk, Army HQ (1 year)
"""

# ──────────────────────────────────────────
# CONVERSATION STATES
# ──────────────────────────────────────────
GETTING_INPUT, CHOOSING_CATEGORY, CHOOSING_ROLE, CRYPTO_INPUT = range(4)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# GEMINI — 4 Keys Auto Rotate
# ──────────────────────────────────────────
def ask_gemini(prompt: str) -> str:
    for attempt in range(len(GEMINI_KEYS)):
        try:
            key = GEMINI_KEYS[_key_index[0] % len(GEMINI_KEYS)]
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-2.0-flash-lite")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                _key_index[0] += 1
                logger.warning("Key quota khatam, next key try kar raha hoon...")
                continue
            else:
                raise e
    raise Exception("Sab 4 keys ka quota khatam! Kal dobara try karo.")

# ──────────────────────────────────────────
# JOB SEARCH FUNCTIONS
# ──────────────────────────────────────────
def search_indeed_latest(role: str, location: str) -> list:
    jobs = []
    try:
        query = role.replace(" ", "+")
        loc = location.replace(" ", "+")
        url = "https://in.indeed.com/jobs?q={}&l={}&sort=date&fromage=1&limit=5".format(query, loc)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.find_all("div", class_="job_seen_beacon")[:4]
        for card in cards:
            try:
                title = card.find("h2", class_="jobTitle")
                company = card.find("span", {"data-testid": "company-name"})
                loc_el = card.find("div", {"data-testid": "text-location"})
                date_el = card.find("span", {"data-testid": "myJobsStateDate"})
                link_el = card.find("a", class_="jcs-JobTitle")
                jk = link_el.get("data-jk", "") if link_el else ""
                t = title.get_text(strip=True) if title else ""
                if t:
                    jobs.append({
                        "source": "Indeed",
                        "title": t,
                        "company": company.get_text(strip=True) if company else "N/A",
                        "location": loc_el.get_text(strip=True) if loc_el else location,
                        "posted": date_el.get_text(strip=True) if date_el else "Today",
                        "link": "https://in.indeed.com/viewjob?jk={}".format(jk) if jk else "https://in.indeed.com"
                    })
            except Exception:
                continue
    except Exception as e:
        logger.error("Indeed error: {}".format(e))
    return jobs


def search_linkedin_latest(role: str, location: str) -> list:
    jobs = []
    try:
        query = role.replace(" ", "%20")
        loc = location.replace(" ", "%20")
        url = "https://www.linkedin.com/jobs/search/?keywords={}&location={}&sortBy=DD&f_TPR=r86400".format(query, loc)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.find_all("div", class_="base-card")[:4]
        for card in cards:
            try:
                title = card.find("h3", class_="base-search-card__title")
                company = card.find("h4", class_="base-search-card__subtitle")
                loc_el = card.find("span", class_="job-search-card__location")
                date_el = card.find("time")
                link_el = card.find("a", class_="base-card__full-link")
                t = title.get_text(strip=True) if title else ""
                if t:
                    jobs.append({
                        "source": "LinkedIn",
                        "title": t,
                        "company": company.get_text(strip=True) if company else "N/A",
                        "location": loc_el.get_text(strip=True) if loc_el else location,
                        "posted": date_el.get("datetime", "Today") if date_el else "Today",
                        "link": link_el.get("href", "https://linkedin.com/jobs") if link_el else "https://linkedin.com/jobs"
                    })
            except Exception:
                continue
    except Exception as e:
        logger.error("LinkedIn error: {}".format(e))
    return jobs


def format_jobs(jobs: list) -> str:
    if not jobs:
        return "Abhi koi latest job nahi mili."
    text = ""
    for i, j in enumerate(jobs, 1):
        emoji = "🟡" if j["source"] == "Indeed" else "🔵"
        text += "{} *{}. {}*\n".format(emoji, i, j["title"])
        text += "   {} {}\n".format("🏢", j["company"])
        text += "   {} {}\n".format("📍", j["location"])
        text += "   {} {}\n".format("🕐", j["posted"])
        text += "   [Apply Here]({})\n\n".format(j["link"])
    return text

# ──────────────────────────────────────────
# CRYPTO FUNCTIONS
# ──────────────────────────────────────────
def get_crypto_prices(coins: list) -> dict:
    try:
        ids = ",".join([SUPPORTED_COINS.get(c.upper(), c.lower()) for c in coins])
        url = "https://api.coingecko.com/api/v3/simple/price?ids={}&vs_currencies=usd,inr&include_24hr_change=true".format(ids)
        res = requests.get(url, timeout=10)
        data = res.json()
        result = {}
        for coin in coins:
            coin_id = SUPPORTED_COINS.get(coin.upper(), coin.lower())
            if coin_id in data:
                result[coin.upper()] = {
                    "usd": data[coin_id].get("usd", 0),
                    "inr": data[coin_id].get("inr", 0),
                    "change_24h": data[coin_id].get("usd_24h_change", 0)
                }
        return result
    except Exception as e:
        logger.error("Price fetch error: {}".format(e))
        return {}


def format_price_msg(prices: dict) -> str:
    if not prices:
        return "Price fetch nahi hua. Dobara try karo."
    msg = ""
    for coin, data in prices.items():
        change = data.get("change_24h", 0)
        arrow = "📈" if change >= 0 else "📉"
        sign = "+" if change >= 0 else ""
        msg += "{} *{}*\n".format(arrow, coin)
        msg += "   USD: ${:,.2f}\n".format(data["usd"])
        msg += "   INR: Rs.{:,.0f}\n".format(data["inr"])
        msg += "   24h: `{}{}%`\n\n".format(sign, round(change, 2))
    return msg


def get_new_airdrops() -> list:
    try:
        url = "https://airdrops.io/latest/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.find_all("div", class_="airdrop-item")[:5]
        airdrops = []
        for card in cards:
            try:
                name = card.find("h3") or card.find("h2")
                link = card.find("a")
                if name:
                    airdrops.append({
                        "name": name.get_text(strip=True),
                        "reward": "Check site",
                        "link": "https://airdrops.io" + link.get("href", "") if link else "https://airdrops.io"
                    })
            except Exception:
                continue
        if airdrops:
            return airdrops
    except Exception as e:
        logger.error("Airdrop error: {}".format(e))

    return [
        {"name": "airdrops.io — Latest Drops", "reward": "Multiple active", "link": "https://airdrops.io"},
        {"name": "DeFiLlama Airdrops", "reward": "Latest drops", "link": "https://defillama.com/airdrops"},
        {"name": "CoinMarketCap Airdrops", "reward": "Ongoing campaigns", "link": "https://coinmarketcap.com/airdrop/"},
        {"name": "Galxe Campaigns", "reward": "Active quests", "link": "https://galxe.com"},
        {"name": "Layer3 Tasks", "reward": "Earn crypto", "link": "https://layer3.xyz"},
    ]


def get_new_testnets() -> list:
    try:
        url = "https://cryptorank.io/testnets"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.find_all("tr")[:6]
        testnets = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 2:
                name = cols[0].get_text(strip=True)
                status = cols[1].get_text(strip=True)
                if name:
                    testnets.append({"name": name, "status": status, "link": "https://cryptorank.io/testnets"})
        if testnets:
            return testnets
    except Exception as e:
        logger.error("Testnet error: {}".format(e))

    return [
        {"name": "CryptoRank Testnets", "status": "Active", "link": "https://cryptorank.io/testnets"},
        {"name": "Galxe Quests", "status": "Multiple active", "link": "https://galxe.com"},
        {"name": "Layer3 Tasks", "status": "Active", "link": "https://layer3.xyz"},
        {"name": "Intract Campaigns", "status": "Active", "link": "https://intract.io"},
    ]


def get_whale_alerts() -> list:
    try:
        url = "https://whale-alert.io/recent-transactions"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.find_all("tr")[:6]
        whales = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                c = cols[0].get_text(strip=True)
                a = cols[1].get_text(strip=True)
                v = cols[2].get_text(strip=True)
                if c:
                    whales.append({"coin": c, "amount": a, "usd": v})
        if whales:
            return whales
    except Exception as e:
        logger.error("Whale error: {}".format(e))

    return [
        {"coin": "Visit whale-alert.io", "amount": "Real-time data", "usd": "Free tier available"},
        {"coin": "Telegram: @whale_alert_io", "amount": "Live alerts", "usd": "Subscribe for free"},
    ]


def get_new_listings() -> list:
    try:
        url = "https://api.coingecko.com/api/v3/coins/list/new"
        res = requests.get(url, timeout=10)
        data = res.json()
        listings = []
        for coin in data[:8]:
            listings.append({
                "name": coin.get("name", "N/A"),
                "symbol": coin.get("symbol", "N/A").upper(),
                "id": coin.get("id", "")
            })
        return listings
    except Exception as e:
        logger.error("Listings error: {}".format(e))
        return []

# ──────────────────────────────────────────
# AUTO ALERTS
# ──────────────────────────────────────────
async def auto_job_alert(context):
    chat_id = context.job.chat_id
    all_jobs = []
    alert_roles = ["Full Stack Developer", "React Developer", "Python Developer", "Blockchain Developer", "Data Analyst"]
    for role in alert_roles[:3]:
        all_jobs.extend(search_indeed_latest(role, "remote")[:1])
        all_jobs.extend(search_linkedin_latest(role, "India")[:1])

    seen, unique = set(), []
    for j in all_jobs:
        key = j["title"] + j["company"]
        if key not in seen:
            seen.add(key)
            unique.append(j)

    if unique:
        now = datetime.now().strftime("%d %b %Y, %I:%M %p")
        msg = "🔔 *LATEST JOB ALERT!*\n_{}_\n\n".format(now)
        msg += format_jobs(unique[:5])
        msg += "/cover se cover letter banao!"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown", disable_web_page_preview=True)


async def auto_crypto_alert(context):
    chat_id = context.job.chat_id
    watchlist = user_watchlist.get(chat_id, DEFAULT_WATCHLIST)
    if not watchlist:
        return

    prices = get_crypto_prices(watchlist)
    old_prices = user_price_cache.get(chat_id, {})
    alerts = []

    for coin, data in prices.items():
        current = data["usd"]
        old = old_prices.get(coin, current)
        if old > 0:
            change_pct = ((current - old) / old) * 100
            if abs(change_pct) >= 5:
                direction = "UPAR 🚀" if change_pct > 0 else "NEECHE 💥"
                sign = "+" if change_pct > 0 else ""
                alerts.append("*{}* {} {}{}%\nUSD: ${:,.2f}".format(coin, direction, sign, round(change_pct, 1), current))

    user_price_cache[chat_id] = {c: d["usd"] for c, d in prices.items()}

    if alerts:
        now = datetime.now().strftime("%d %b, %I:%M %p")
        msg = "🔔 *CRYPTO PRICE ALERT!*\n_{}_\n\n".format(now)
        msg += "\n\n".join(alerts)
        msg += "\n\n/crypto se full dashboard dekho"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")


# ──────────────────────────────────────────
# AI FUNCTIONS
# ──────────────────────────────────────────
def generate_cover_letter(job_desc: str, company: str = "") -> str:
    return ask_gemini(
        "Write a professional cover letter as Raghuveer Bhati.\n\n"
        "Resume:\n{}\n\nJob: {}\nCompany: {}\n\n"
        "3 paragraphs, 200-250 words. Include relevant projects with links. "
        "Portfolio: https://raghublock.github.io/portfolio\n"
        "Only output the cover letter.".format(RESUME, job_desc, company or "the company")
    )


def analyze_match(job_desc: str) -> str:
    return ask_gemini(
        "Analyze job match for Raghuveer Bhati.\nResume:\n{}\n\nJob:\n{}\n\n"
        "Give: 1. Match Score (%) 2. Top 3 matching skills 3. Gaps 4. Apply? Yes/Maybe/No + reason\n"
        "Under 150 words. Be direct.".format(RESUME, job_desc)
    )


# ──────────────────────────────────────────
# BOT COMMAND HANDLERS
# ──────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Raghuveer's Ultimate Bot v6.0*\n_Jobs + Crypto + Web3 — FREE!_\n\n"
        "*💼 Job Commands:*\n"
        "/jobs — Latest jobs dhundo\n"
        "/alert — Auto job alerts ON\n"
        "/cover — Cover letter banao\n"
        "/match — Job match check\n\n"
        "*💰 Crypto Commands:*\n"
        "/crypto — Full crypto dashboard\n"
        "/watchlist — Apne coins set karo\n\n"
        "/stop — Sab alerts band karo\n"
        "/help — Full help",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coins_str = ", ".join(SUPPORTED_COINS.keys())
    await update.message.reply_text(
        "🤖 *Ultimate Bot v6.0 — Commands:*\n\n"
        "*💼 JOB HUNTING:*\n"
        "/jobs — Latest jobs (Indeed + LinkedIn)\n"
        "/alert — Auto job alerts (har 2 ghante)\n"
        "/cover — AI cover letter banao\n"
        "/match — Job match % check karo\n\n"
        "*💰 CRYPTO & WEB3:*\n"
        "/crypto — Full crypto dashboard\n"
        "/watchlist — Apne coins set karo\n\n"
        "Supported coins: {}\n\n"
        "*Other:*\n"
        "/stop — Sab alerts band karo\n"
        "/cancel — Current step cancel\n\n"
        "_FREE — Gemini AI + CoinGecko_".format(coins_str),
        parse_mode="Markdown"
    )


async def alert_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if context.job_queue.get_jobs_by_name(str(chat_id)):
        await update.message.reply_text("✅ *Job alerts already ON hain!*\n\n/stop se band karo.", parse_mode="Markdown")
        return
    context.job_queue.run_repeating(
        auto_job_alert, interval=ALERT_INTERVAL, first=10,
        chat_id=chat_id, name=str(chat_id)
    )
    await update.message.reply_text(
        "🔔 *Job Alerts ON!*\n\nHar 2 ghante mein latest jobs milenge.\nPehla alert 10 seconds mein aa raha hai!\n\n/stop se band karo.",
        parse_mode="Markdown"
    )


async def stop_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    removed = 0
    for job in context.job_queue.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()
        removed += 1
    for job in context.job_queue.get_jobs_by_name("crypto_{}".format(chat_id)):
        job.schedule_removal()
        removed += 1
    if removed:
        await update.message.reply_text("🔕 *Sab alerts band ho gaye!*\n\n/alert ya /crypto se dobara ON karo.", parse_mode="Markdown")
    else:
        await update.message.reply_text("Koi alert nahi chal raha tha.", parse_mode="Markdown")


# ── JOB SEARCH HANDLERS ──
async def jobs_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(cat, callback_data="cat_{}".format(cat))] for cat in JOB_ROLES.keys()]
    await update.message.reply_text(
        "🔍 *Category choose karo:*\n_Sirf aaj ki latest jobs!_",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CHOOSING_CATEGORY


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.replace("cat_", "")
    context.user_data["category"] = category
    roles = JOB_ROLES.get(category, [])
    keyboard = []
    row = []
    for role in roles:
        short = " ".join(role.split()[:2])
        row.append(InlineKeyboardButton(short, callback_data="role_{}".format(role)))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔍 Sab Roles", callback_data="role_all_{}".format(category))])
    await query.edit_message_text(
        "✅ *{}*\n\nKaunsi role?".format(category),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CHOOSING_ROLE


async def role_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.replace("role_", "")
    if data.startswith("all_"):
        category = data.replace("all_", "")
        context.user_data["search_roles"] = JOB_ROLES.get(category, [])
        role_display = "Sab {} Roles".format(category)
    else:
        context.user_data["search_roles"] = [data]
        role_display = data
    keyboard = [[
        InlineKeyboardButton("🌍 Remote", callback_data="loc_remote"),
        InlineKeyboardButton("🇮🇳 India", callback_data="loc_india"),
        InlineKeyboardButton("🌐 Dono", callback_data="loc_both"),
    ]]
    await query.edit_message_text(
        "✅ *{}*\n\nLocation?".format(role_display),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CHOOSING_ROLE


async def location_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    location = query.data.replace("loc_", "")
    roles = context.user_data.get("search_roles", ["Full Stack Developer"])
    now = datetime.now().strftime("%d %b, %I:%M %p")
    await query.edit_message_text(
        "🔍 *Jobs dhundh raha hoon...*\nSirf aaj ki — {}\n20-30 seconds...".format(now),
        parse_mode="Markdown"
    )
    try:
        all_jobs = []
        locations = ["remote"] if location == "remote" else ["India"] if location == "india" else ["remote", "India"]
        for r in roles[:2]:
            for loc in locations:
                all_jobs.extend(search_indeed_latest(r, loc)[:2])
                all_jobs.extend(search_linkedin_latest(r, loc)[:2])
        seen, unique = set(), []
        for j in all_jobs:
            key = j["title"] + j["company"]
            if key not in seen:
                seen.add(key)
                unique.append(j)
        unique = unique[:8]
        if unique:
            msg = "🎯 *{} Latest Jobs Mili!*\n_{}_\n\n".format(len(unique), now)
            msg += format_jobs(unique)
            msg += "/cover se cover letter banao!"
        else:
            msg = (
                "Abhi koi new job nahi mili (last 24 hours).\n\n"
                "Manually dekho:\n"
                "🔵 [LinkedIn](https://www.linkedin.com/jobs/search/?keywords=full+stack+developer&location=India&sortBy=DD&f_TPR=r86400)\n"
                "🟡 [Indeed](https://in.indeed.com/jobs?q=react+developer&l=remote&sort=date&fromage=1)\n\n"
                "Ya /alert se auto notifications ON karo!"
            )
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=msg,
            parse_mode="Markdown", disable_web_page_preview=True
        )
        keyboard = [[
            InlineKeyboardButton("🔄 Dobara Search", callback_data="restart"),
            InlineKeyboardButton("📝 Cover Letter", callback_data="goto_cover"),
        ]]
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Kya karna chahte ho?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Error aaya. /jobs dobara try karo.")
        logger.error("Search error: {}".format(e))
    return ConversationHandler.END


# ── COVER LETTER & MATCH ──
async def cover_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "cover"
    await update.message.reply_text(
        "📝 *Cover Letter Banao*\n\nJob description paste karo:\n_Pehli line mein company name — optional_",
        parse_mode="Markdown"
    )
    return GETTING_INPUT


async def match_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "match"
    await update.message.reply_text("🎯 *Job Match Check*\n\nJob description paste karo:", parse_mode="Markdown")
    return GETTING_INPUT


async def input_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    job_desc = update.message.text
    loading = await update.message.reply_text("⏳ *AI kaam kar raha hai... 10-15 sec*", parse_mode="Markdown")
    try:
        if mode == "cover":
            lines = job_desc.split("\n")
            company = lines[0] if len(lines) > 1 else ""
            desc = "\n".join(lines[1:]) if len(lines) > 1 else job_desc
            result = generate_cover_letter(desc, company)
            header = "✅ *COVER LETTER READY!*\n━━━━━━━━━━━━\n\n"
            footer = "\n\n━━━━━━━━━━━━\n_Copy karo aur apply karo!_"
        else:
            result = analyze_match(job_desc)
            header = "🎯 *JOB MATCH ANALYSIS*\n━━━━━━━━━━━━\n\n"
            footer = "\n\n━━━━━━━━━━━━"
        await loading.delete()
        full_msg = header + result + footer
        if len(full_msg) > 4096:
            await update.message.reply_text(header + result[:2000] + "...", parse_mode="Markdown")
            await update.message.reply_text("..." + result[2000:] + footer, parse_mode="Markdown")
        else:
            await update.message.reply_text(full_msg, parse_mode="Markdown")
        keyboard = [[
            InlineKeyboardButton("🔄 Dobara", callback_data="regen_{}".format(mode)),
            InlineKeyboardButton("🔍 Jobs Dhundo", callback_data="restart"),
        ]]
        await update.message.reply_text("Kya karna chahte ho?", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await loading.edit_text("Error: {}\n\nDobara try karo.".format(str(e)))
        logger.error("Error: {}".format(e))
    return ConversationHandler.END


# ── CRYPTO HANDLERS ──
async def crypto_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💰 Live Prices", callback_data="crypto_prices"),
         InlineKeyboardButton("📊 My Watchlist", callback_data="crypto_watchlist")],
        [InlineKeyboardButton("🪂 Airdrops", callback_data="crypto_airdrops"),
         InlineKeyboardButton("🧪 Testnets", callback_data="crypto_testnets")],
        [InlineKeyboardButton("🐳 Whale Alerts", callback_data="crypto_whales"),
         InlineKeyboardButton("🆕 New Listings", callback_data="crypto_listings")],
        [InlineKeyboardButton("🔔 Price Alert ON", callback_data="crypto_alert_on"),
         InlineKeyboardButton("🔕 Alert OFF", callback_data="crypto_alert_off")],
    ]
    await update.message.reply_text(
        "💰 *Crypto & Web3 Dashboard*\n\nKya dekhna hai?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def crypto_set_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coins_list = ", ".join(SUPPORTED_COINS.keys())
    await update.message.reply_text(
        "📊 *Watchlist Set Karo*\n\nCoins type karo space se alag:\nExample: BTC ETH SOL APT ARB SUI\n\nAvailable: {}".format(coins_list),
        parse_mode="Markdown"
    )
    return CRYPTO_INPUT


async def crypto_watchlist_saved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    coins = [c.upper().strip() for c in update.message.text.split()]
    valid = [c for c in coins if c in SUPPORTED_COINS]
    invalid = [c for c in coins if c not in SUPPORTED_COINS]
    if valid:
        user_watchlist[chat_id] = valid
        msg = "✅ *Watchlist saved!*\n\nTracking: {}".format(", ".join(valid))
        if invalid:
            msg += "\nNot found: {}".format(", ".join(invalid))
        msg += "\n\n/crypto se Price Alert ON karo!"
    else:
        msg = "Koi valid coin nahi!\n\nAvailable: {}".format(", ".join(SUPPORTED_COINS.keys()))
    await update.message.reply_text(msg, parse_mode="Markdown")
    return ConversationHandler.END


async def crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    now = datetime.now().strftime("%d %b, %I:%M %p")

    back_keyboard = [[
        InlineKeyboardButton("🔄 Refresh", callback_data=query.data),
        InlineKeyboardButton("🏠 Menu", callback_data="crypto_menu_back")
    ]]

    if query.data == "crypto_prices":
        await query.edit_message_text("⏳ Prices fetch ho rahi hain...", parse_mode="Markdown")
        watchlist = user_watchlist.get(chat_id, DEFAULT_WATCHLIST)
        prices = get_crypto_prices(watchlist)
        msg = "💰 *LIVE CRYPTO PRICES*\n_{}_\n\n".format(now)
        msg += format_price_msg(prices)
        msg += "_Source: CoinGecko_"
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(back_keyboard))

    elif query.data == "crypto_watchlist":
        watchlist = user_watchlist.get(chat_id, [])
        if watchlist:
            msg = "📊 *Tumhara Watchlist:*\n{}\n\n/watchlist se change karo".format(", ".join(watchlist))
        else:
            msg = "📊 Watchlist empty hai!\n\n/watchlist se coins add karo\nExample: BTC ETH SOL APT"
        await query.edit_message_text(msg, parse_mode="Markdown")

    elif query.data == "crypto_airdrops":
        await query.edit_message_text("⏳ Latest airdrops dhundh raha hoon...", parse_mode="Markdown")
        airdrops = get_new_airdrops()
        msg = "🪂 *LATEST AIRDROPS*\n_{}_\n\n".format(now)
        for i, a in enumerate(airdrops, 1):
            msg += "*{}. {}*\n".format(i, a["name"])
            msg += "   Reward: {}\n".format(a["reward"])
            msg += "   [Claim Here]({})\n\n".format(a["link"])
        await query.edit_message_text(msg, parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(back_keyboard),
                                       disable_web_page_preview=True)

    elif query.data == "crypto_testnets":
        await query.edit_message_text("⏳ Latest testnets dhundh raha hoon...", parse_mode="Markdown")
        testnets = get_new_testnets()
        msg = "🧪 *ACTIVE TESTNETS*\n_{}_\n\n".format(now)
        for i, t in enumerate(testnets, 1):
            msg += "*{}. {}*\n".format(i, t["name"])
            msg += "   Status: {}\n".format(t["status"])
            msg += "   [Join Here]({})\n\n".format(t["link"])
        msg += "Testnet = Free tokens + future airdrop chance!"
        await query.edit_message_text(msg, parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(back_keyboard),
                                       disable_web_page_preview=True)

    elif query.data == "crypto_whales":
        await query.edit_message_text("⏳ Whale transactions check kar raha hoon...", parse_mode="Markdown")
        whales = get_whale_alerts()
        msg = "🐳 *WHALE ALERT*\n_{}_\n\n".format(now)
        for w in whales:
            msg += "*{}*\n".format(w["coin"])
            msg += "   Amount: {}\n".format(w["amount"])
            msg += "   Value: {}\n\n".format(w["usd"])
        msg += "[Real-time: whale-alert.io](https://whale-alert.io)"
        await query.edit_message_text(msg, parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(back_keyboard),
                                       disable_web_page_preview=True)

    elif query.data == "crypto_listings":
        await query.edit_message_text("⏳ New listings dhundh raha hoon...", parse_mode="Markdown")
        listings = get_new_listings()
        msg = "🆕 *NEW TOKEN LISTINGS*\n_{}_\n\n".format(now)
        for i, l in enumerate(listings, 1):
            msg += "*{}. {}* ({})\n".format(i, l["name"], l["symbol"])
            msg += "   [CoinGecko](https://coingecko.com/en/coins/{})\n\n".format(l["id"])
        if not listings:
            msg += "Abhi koi new listing nahi mili."
        await query.edit_message_text(msg, parse_mode="Markdown",
                                       reply_markup=InlineKeyboardMarkup(back_keyboard),
                                       disable_web_page_preview=True)

    elif query.data == "crypto_alert_on":
        watchlist = user_watchlist.get(chat_id, DEFAULT_WATCHLIST)
        for job in context.job_queue.get_jobs_by_name("crypto_{}".format(chat_id)):
            job.schedule_removal()
        context.job_queue.run_repeating(
            auto_crypto_alert, interval=CRYPTO_ALERT_INTERVAL, first=10,
            chat_id=chat_id, name="crypto_{}".format(chat_id)
        )
        msg = "🔔 *Crypto Alerts ON!*\n\nTracking: {}\nHar 5 min check karega\n5% change pe alert aayega!\n\n/watchlist se coins change karo".format(", ".join(watchlist))
        await query.edit_message_text(msg, parse_mode="Markdown")

    elif query.data == "crypto_alert_off":
        jobs = context.job_queue.get_jobs_by_name("crypto_{}".format(chat_id))
        if jobs:
            for job in jobs:
                job.schedule_removal()
            await query.edit_message_text("🔕 *Crypto alerts band!*\n\n/crypto se dobara ON karo.", parse_mode="Markdown")
        else:
            await query.edit_message_text("Koi crypto alert nahi chal raha tha.", parse_mode="Markdown")

    elif query.data == "crypto_menu_back":
        keyboard = [
            [InlineKeyboardButton("💰 Live Prices", callback_data="crypto_prices"),
             InlineKeyboardButton("📊 My Watchlist", callback_data="crypto_watchlist")],
            [InlineKeyboardButton("🪂 Airdrops", callback_data="crypto_airdrops"),
             InlineKeyboardButton("🧪 Testnets", callback_data="crypto_testnets")],
            [InlineKeyboardButton("🐳 Whale Alerts", callback_data="crypto_whales"),
             InlineKeyboardButton("🆕 New Listings", callback_data="crypto_listings")],
            [InlineKeyboardButton("🔔 Price Alert ON", callback_data="crypto_alert_on"),
             InlineKeyboardButton("🔕 Alert OFF", callback_data="crypto_alert_off")],
        ]
        await query.edit_message_text(
            "💰 *Crypto & Web3 Dashboard*\n\nKya dekhna hai?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "restart":
        await query.edit_message_text("/jobs type karo!")
    elif query.data == "goto_cover":
        await query.edit_message_text("/cover type karo cover letter ke liye!")
    elif query.data.startswith("regen_"):
        mode = query.data.split("_", 1)[1]
        context.user_data["mode"] = mode
        await query.edit_message_text("Job description dobara paste karo:")
        return GETTING_INPUT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/jobs, /cover, /match, /crypto type karo.")
    return ConversationHandler.END


# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN Railway Variables mein set karo!")
    if not GEMINI_KEYS:
        raise ValueError("Kam se kam ek GEMINI_KEY_1 Railway Variables mein set karo!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    job_conv = ConversationHandler(
        entry_points=[CommandHandler("jobs", jobs_start)],
        states={
            CHOOSING_CATEGORY: [CallbackQueryHandler(category_chosen, pattern="^cat_")],
            CHOOSING_ROLE: [
                CallbackQueryHandler(role_chosen, pattern="^role_"),
                CallbackQueryHandler(location_chosen, pattern="^loc_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    content_conv = ConversationHandler(
        entry_points=[
            CommandHandler("cover", cover_start),
            CommandHandler("match", match_start),
        ],
        states={
            GETTING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    crypto_conv = ConversationHandler(
        entry_points=[CommandHandler("watchlist", crypto_set_watchlist)],
        states={
            CRYPTO_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, crypto_watchlist_saved)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("alert", alert_start))
    app.add_handler(CommandHandler("stop", stop_alerts))
    app.add_handler(CommandHandler("crypto", crypto_menu))
    app.add_handler(job_conv)
    app.add_handler(content_conv)
    app.add_handler(crypto_conv)
    app.add_handler(CallbackQueryHandler(crypto_callback, pattern="^crypto_"))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Raghuveer's Ultimate Bot v6.0 chal raha hai!")
    print("Jobs + Crypto + Web3 — FREE!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
