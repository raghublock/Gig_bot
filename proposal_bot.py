#!/usr/bin/env python3
"""
🤖 Raghuveer's AI Job Bot v5.0
FREE - Google Gemini API
Features:
- Latest jobs ONLY (24 hours filter)
- Indeed + LinkedIn job search
- Real-time job alerts
- Cover letter generator
- Job match analysis
- All roles including freelance + sponsorship
"""

import os
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler,
    filters, JobQueue
)

# ──────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# 4 Gemini Keys — Auto Rotate
GEMINI_KEYS = [os.environ.get("GEMINI_KEY_1"), os.environ.get("GEMINI_KEY_2"), os.environ.get("GEMINI_KEY_3"), os.environ.get("GEMINI_KEY_4")]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]
_key_index = [0]  # list mein rakha taaki function update kar sake

# Alert interval — har 2 ghante mein check karega
ALERT_INTERVAL = 7200  # seconds

# ──────────────────────────────────────────
# JOB ROLES — Raghuveer ke profile se
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
# RAGHUVEER KA COMPLETE RESUME
# ──────────────────────────────────────────
RESUME = """
NAME: Raghuveer Bhati
LOCATION: Bikaner, Rajasthan, India
PORTFOLIO: https://raghublock.github.io/portfolio
GITHUB: https://github.com/raghublock
LINKEDIN: https://in.linkedin.com/in/raghuveer-bhati-94a37aa9

TITLE: Full Stack Web Developer | Blockchain Tester | AI Tools Developer

EDUCATION:
- B.Tech ECE | B.Sc Biology | B.Ed Science
- RSCIT Certified (VMOU 2017)

PROJECTS (with technologies):
1. Laxmi Library Fee System
   Tech: React.js, TailwindCSS, Cloudflare
   Link: raghublock.github.io/library-fee/

2. Student Fees Management Dashboard
   Tech: HTML, JavaScript, Cloudflare Workers
   Link: student-fees-management.pages.dev/

3. Veggie Shop (E-commerce)
   Tech: HTML, CSS, Node.js, Render
   Link: veggie-shop-lgvy.onrender.com/

4. AI PDF Editor
   Tech: Python, Streamlit, OCR
   Link: aipdfedit.streamlit.app/

5. Free BG Remover
   Tech: HTML, JavaScript, Python API (Rembg)
   Link: raghublock.github.io/free-bg-remover/

6. Image Master Tool
   Tech: HTML, CSS, JavaScript, Canvas API
   Link: raghublock.github.io/image-master-tool/

7. PDF Compressor
   Tech: HTML, CSS, JavaScript
   Link: raghublock.github.io/PDF_Compress/

8. Hindi Typing Master
   Tech: HTML, CSS, JavaScript
   Link: raghublock.github.io/hindi-typing-master/

9. Typing Master Pro
   Tech: HTML, CSS, JavaScript
   Link: raghublock.github.io/typing-master-pro/

10. NoteList PWA
    Tech: HTML, CSS, JavaScript, Firebase
    Link: raghublock.github.io/notelist/

SKILLS:
- Frontend: React.js, Next.js, HTML5, CSS3, TailwindCSS, JavaScript, Canvas API
- Backend: Node.js, Express.js, EJS
- Database: MongoDB, PostgreSQL, Firebase, Cloudflare Workers
- AI/ML: Python, Streamlit, OCR, Rembg API
- Blockchain: Web3.js, IPFS, Aptos, Arbitrum, Sui, Linea, Rust
- Tools: Git, GitHub, Vercel, Render, GitHub Pages, Streamlit Cloud

EXPERIENCE:
- Freelancer Web Developer (Sep 2024 - Present)
- Web3 & Blockchain Tester (Aug 2019 - Present)
- Accounts Clerk, Army Headquarters (1 year)
"""

# ──────────────────────────────────────────
# CONVERSATION STATES
# ──────────────────────────────────────────
GETTING_INPUT, CHOOSING_CATEGORY, CHOOSING_ROLE = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# GEMINI SETUP — 4 Keys Auto Rotate
# ──────────────────────────────────────────
def ask_gemini(prompt: str) -> str:
    # Sab keys try karo ek ek karke
    for attempt in range(len(GEMINI_KEYS)):
        try:
            key = GEMINI_KEYS[_key_index[0] % len(GEMINI_KEYS)]
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-2.0-flash-lite")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                # Quota khatam — next key try karo
                _key_index[0] += 1
                logger.warning(f"Key quota khatam, next key try kar raha hoon...")
                continue
            else:
                raise e
    raise Exception("Sab 4 keys ka quota khatam! Kal dobara try karo.")

# ──────────────────────────────────────────
# JOB SEARCH — LATEST ONLY
# ──────────────────────────────────────────

def search_indeed_latest(role: str, location: str) -> list:
    """Indeed se SIRF latest jobs (last 24 hours)"""
    jobs = []
    try:
        query = role.replace(" ", "+")
        loc = location.replace(" ", "+")
        # fromage=1 = last 24 hours only
        url = f"https://in.indeed.com/jobs?q={query}&l={loc}&sort=date&fromage=1&limit=5"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
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
                posted = date_el.get_text(strip=True) if date_el else "Today"

                if t:
                    jobs.append({
                        "source": "Indeed 🟡",
                        "title": t,
                        "company": company.get_text(strip=True) if company else "N/A",
                        "location": loc_el.get_text(strip=True) if loc_el else location,
                        "posted": posted,
                        "link": f"https://in.indeed.com/viewjob?jk={jk}" if jk else "https://in.indeed.com"
                    })
            except:
                continue
    except Exception as e:
        logger.error(f"Indeed error: {e}")
    return jobs


def search_linkedin_latest(role: str, location: str) -> list:
    """LinkedIn se SIRF latest jobs (last 24 hours)"""
    jobs = []
    try:
        query = role.replace(" ", "%20")
        loc = location.replace(" ", "%20")
        # f_TPR=r86400 = last 24 hours
        url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={loc}&sortBy=DD&f_TPR=r86400"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
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
                posted = date_el.get("datetime", "Today") if date_el else "Today"

                if t:
                    jobs.append({
                        "source": "LinkedIn 🔵",
                        "title": t,
                        "company": company.get_text(strip=True) if company else "N/A",
                        "location": loc_el.get_text(strip=True) if loc_el else location,
                        "posted": posted,
                        "link": link_el.get("href", "https://linkedin.com/jobs") if link_el else "https://linkedin.com/jobs"
                    })
            except:
                continue
    except Exception as e:
        logger.error(f"LinkedIn error: {e}")
    return jobs


def format_jobs(jobs: list) -> str:
    if not jobs:
        return "❌ Abhi koi latest job nahi mili."
    text = ""
    for i, j in enumerate(jobs, 1):
        text += f"{j['source']} *{i}. {j['title']}*\n"
        text += f"   🏢 {j['company']}\n"
        text += f"   📍 {j['location']}\n"
        text += f"   🕐 {j['posted']}\n"
        text += f"   🔗 [Apply Here]({j['link']})\n\n"
    return text


# ──────────────────────────────────────────
# AUTO ALERT — Har 2 ghante mein
# ──────────────────────────────────────────
async def auto_job_alert(context):
    """Automatic job alert — har 2 ghante mein latest jobs bhejta hai"""
    chat_id = context.job.chat_id

    all_jobs = []
    # Top roles check karo
    alert_roles = [
        "Full Stack Developer",
        "React Developer",
        "Python Developer",
        "Blockchain Developer",
        "Data Analyst"
    ]

    for role in alert_roles[:3]:
        all_jobs.extend(search_indeed_latest(role, "remote")[:1])
        all_jobs.extend(search_linkedin_latest(role, "India")[:1])

    # Duplicates hatao
    seen, unique = set(), []
    for j in all_jobs:
        key = j["title"] + j["company"]
        if key not in seen:
            seen.add(key)
            unique.append(j)

    if unique:
        now = datetime.now().strftime("%d %b %Y, %I:%M %p")
        msg = f"🔔 *LATEST JOB ALERT!*\n_{now}_\n\n"
        msg += format_jobs(unique[:5])
        msg += "💡 _/cover type karo cover letter ke liye!_"

        await context.bot.send_message(
            chat_id=chat_id,
            text=msg,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )


# ──────────────────────────────────────────
# AI FUNCTIONS
# ──────────────────────────────────────────

def generate_cover_letter(job_desc: str, company: str = "") -> str:
    return ask_gemini(f"""
Write a professional cover letter as Raghuveer Bhati.

Resume: {RESUME}

JOB: {job_desc}
COMPANY: {company or "the company"}

3 paragraphs, 200-250 words:
- Para 1: Why excited about this specific role
- Para 2: 2 specific relevant projects with tech stack and live links
- Para 3: What he'll bring + call to action
- Include portfolio: https://raghublock.github.io/portfolio
- Professional but genuine tone
Only output the cover letter.
""")


def analyze_match(job_desc: str) -> str:
    return ask_gemini(f"""
Analyze job match for Raghuveer Bhati.
Resume: {RESUME}
Job: {job_desc}

Give exactly:
1. Match Score: X%
2. Top 3 matching skills
3. Skill gaps (if any)
4. Apply? Yes/Maybe/No + reason

Under 150 words. Be direct.
""")


# ──────────────────────────────────────────
# BOT HANDLERS
# ──────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🤖 *Raghuveer's AI Job Bot v5.0*
_Powered by Google Gemini — FREE!_

*Commands:*
/jobs — Latest jobs dhundo 🔍
/alert — Auto job alerts ON karo 🔔
/cover — Cover letter banao 📝
/match — Job match % check karo 🎯
/stop — Alerts band karo
/help — Help

*Best Workflow:*
1️⃣ /alert → Auto alerts ON karo
2️⃣ Naukri aate hi notification milegi!
3️⃣ /cover → Cover letter ready
4️⃣ Apply karo! ✅
""", parse_mode="Markdown")


async def alert_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Auto alert shuru karo"""
    chat_id = update.effective_chat.id

    # Pehle check karo already running hai ya nahi
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    if current_jobs:
        await update.message.reply_text(
            "✅ *Alerts already ON hain!*\n\nHar 2 ghante mein latest jobs milenge.\n/stop se band karo.",
            parse_mode="Markdown"
        )
        return

    # Alert shuru karo
    context.job_queue.run_repeating(
        auto_job_alert,
        interval=ALERT_INTERVAL,
        first=10,  # 10 seconds mein pehla alert
        chat_id=chat_id,
        name=str(chat_id)
    )

    await update.message.reply_text("""
🔔 *Job Alerts ON ho gaye!*

✅ Har *2 ghante* mein latest jobs milenge
✅ Indeed + LinkedIn dono check karega
✅ Roles: Full Stack, React, Python, Blockchain, Data

_Pehla alert 10 seconds mein aa raha hai..._

/stop se alerts band kar sakte ho.
""", parse_mode="Markdown")


async def stop_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alerts band karo"""
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))

    if jobs:
        for job in jobs:
            job.schedule_removal()
        await update.message.reply_text("🔕 *Alerts band ho gaye!*\n\n/alert se dobara start kar sakte ho.", parse_mode="Markdown")
    else:
        await update.message.reply_text("ℹ️ Koi alert nahi chal raha.\n\n/alert se start karo.", parse_mode="Markdown")


async def jobs_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual job search"""
    keyboard = []
    for category in JOB_ROLES.keys():
        keyboard.append([InlineKeyboardButton(category, callback_data=f"cat_{category}")])

    await update.message.reply_text(
        "🔍 *Category choose karo:*\n_(Sirf aaj ki latest jobs milegi!)_",
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
        short = role.split()[0] + " " + role.split()[1] if len(role.split()) > 1 else role
        row.append(InlineKeyboardButton(short, callback_data=f"role_{role}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔍 Sab Roles", callback_data=f"role_all_{category}")])

    await query.edit_message_text(
        f"✅ *{category}*\n\nKaunsi role?",
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
        role_display = f"Sab {category} Roles"
    else:
        context.user_data["search_roles"] = [data]
        role_display = data

    keyboard = [[
        InlineKeyboardButton("🌍 Remote", callback_data="loc_remote"),
        InlineKeyboardButton("🇮🇳 India", callback_data="loc_india"),
        InlineKeyboardButton("🌐 Dono", callback_data="loc_both"),
    ]]

    await query.edit_message_text(
        f"✅ *{role_display}*\n\n📍 Location?",
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
        f"🔍 *Latest jobs dhundh raha hoon...*\n_Sirf aaj ki jobs — {now}_\n_20-30 seconds..._",
        parse_mode="Markdown"
    )

    try:
        all_jobs = []
        locations = []
        if location == "remote":
            locations = ["remote"]
        elif location == "india":
            locations = ["India"]
        else:
            locations = ["remote", "India"]

        for r in roles[:3]:
            for loc in locations:
                all_jobs.extend(search_indeed_latest(r, loc)[:2])
                all_jobs.extend(search_linkedin_latest(r, loc)[:2])

        # Duplicates hatao
        seen, unique = set(), []
        for j in all_jobs:
            key = j["title"] + j["company"]
            if key not in seen:
                seen.add(key)
                unique.append(j)

        unique = unique[:10]

        if unique:
            msg = f"🎯 *{len(unique)} Latest Jobs Mili!*\n_Aaj ki — {now}_\n\n"
            msg += format_jobs(unique)
            msg += "💡 _Job copy karo → /cover se cover letter banao!_"
        else:
            msg = f"""❌ *Abhi koi new job nahi mili.*
_(Last 24 hours mein)_

Manually dekho:
🔵 [LinkedIn Latest](https://www.linkedin.com/jobs/search/?keywords=full+stack+developer&location=India&sortBy=DD&f_TPR=r86400)
🟡 [Indeed Latest](https://in.indeed.com/jobs?q=react+developer&l=remote&sort=date&fromage=1)

Ya /alert se auto notifications ON karo! 🔔"""

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

        keyboard = [[
            InlineKeyboardButton("🔄 Dobara Search", callback_data="restart"),
            InlineKeyboardButton("📝 Cover Letter", callback_data="goto_cover"),
            InlineKeyboardButton("🔔 Auto Alert", callback_data="goto_alert"),
        ]]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Kya karna chahte ho?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Error aaya. /jobs dobara try karo."
        )
        logger.error(f"Search error: {e}")

    return ConversationHandler.END


async def cover_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "cover"
    await update.message.reply_text(
        "📝 *Cover Letter Banao*\n\nJob description paste karo:\n_(Pehli line mein company name — optional)_",
        parse_mode="Markdown"
    )
    return GETTING_INPUT


async def match_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "match"
    await update.message.reply_text(
        "🎯 *Job Match Check*\n\nJob description paste karo:",
        parse_mode="Markdown"
    )
    return GETTING_INPUT


async def input_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    job_desc = update.message.text

    loading = await update.message.reply_text(
        "⏳ *Gemini AI kaam kar raha hai... 10-15 sec*",
        parse_mode="Markdown"
    )

    try:
        if mode == "cover":
            lines = job_desc.split('\n')
            company = lines[0] if len(lines) > 1 else ""
            desc = '\n'.join(lines[1:]) if len(lines) > 1 else job_desc
            result = generate_cover_letter(desc, company)
            header = "✅ *COVER LETTER READY!*\n━━━━━━━━━━━━\n\n"
            footer = "\n\n━━━━━━━━━━━━\n📋 _Copy karo aur apply karo!_"
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
            InlineKeyboardButton("🔄 Dobara", callback_data=f"regen_{mode}"),
            InlineKeyboardButton("🔍 Jobs Dhundo", callback_data="restart"),
        ]]
        await update.message.reply_text(
            "Kya karna chahte ho?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        await loading.edit_text(f"❌ Error: {str(e)}\n\nDobara try karo.")
        logger.error(f"Error: {e}")

    return ConversationHandler.END


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "restart":
        await query.edit_message_text("/jobs type karo!")
    elif query.data == "goto_cover":
        await query.edit_message_text("/cover type karo!")
    elif query.data == "goto_alert":
        await query.edit_message_text("/alert type karo auto notifications ke liye! 🔔")
    elif query.data.startswith("regen_"):
        mode = query.data.split("_", 1)[1]
        context.user_data["mode"] = mode
        await query.edit_message_text("Job description dobara paste karo:")
        return GETTING_INPUT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancel.\n\n/jobs, /cover, /match, /alert type karo.")
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🤖 *Commands:*

*/jobs* — Latest jobs dhundo (aaj ki)
*/alert* — Auto alerts ON karo (har 2 ghante)
*/stop* — Alerts band karo
*/cover* — Cover letter banao
*/match* — Job match % check karo
*/cancel* — Cancel

*Job Categories:*
💻 Web Dev — React, Node, Full Stack
🐍 Python/AI — Python, Data Analyst
⛓️ Blockchain — Web3, DeFi, Crypto
📊 Freelance — Data Entry, VA
🤝 Sponsorship — Testnet, Ambassador

*Best Workflow:*
1️⃣ /alert → Auto notifications ON
2️⃣ Job aate hi Telegram pe milega!
3️⃣ /cover → Cover letter ready
4️⃣ Apply! ✅

_FREE — Powered by Google Gemini 🆓_
""", parse_mode="Markdown")


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

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("alert", alert_start))
    app.add_handler(CommandHandler("stop", stop_alerts))
    app.add_handler(job_conv)
    app.add_handler(content_conv)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Raghuveer's Job Bot v5.0 chal raha hai!")
    print("FREE - Gemini | Latest Jobs | Auto Alerts!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
