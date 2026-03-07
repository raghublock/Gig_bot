#!/usr/bin/env python3
"""
🤖 Raghuveer's AI Job Bot v4.0
FREE - Google Gemini API use karta hai
Features:
- Indeed + LinkedIn job search
- Cover letter generator
- Job match analysis
"""

import os
import logging
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)

# ──────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY     = os.environ.get("GEMINI_KEY")

JOB_ROLES = [
    "React Developer",
    "Node.js Developer",
    "Python Developer",
    "Full Stack Developer",
    "Blockchain Web3 Developer",
    "AI ML Developer"
]

# ──────────────────────────────────────────
# RAGHUVEER KA RESUME
# ──────────────────────────────────────────
RESUME = """
NAME: Raghuveer Bhati
LOCATION: Bikaner, Rajasthan, India
PORTFOLIO: https://raghublock.github.io/portfolio
GITHUB: https://github.com/raghublock
LINKEDIN: https://in.linkedin.com/in/raghuveer-bhati-94a37aa9
TITLE: Full Stack Web Developer | Blockchain Tester | AI Tools Developer

EDUCATION:
- B.Tech in Electronics & Communication Engineering (ECE)
- B.Sc in Biology | B.Ed in Science
- RSCIT Certified (VMOU 2017)

EXPERIENCE:
1. Freelancer – Website Developer (Sep 2024 - Present)
   - AI Background Remover (Python + Rembg)
   - AI PDF Editor with OCR (Python + Streamlit) — aipdfedit.streamlit.app
   - Library Fee Management System (React + TailwindCSS + Cloudflare)
   - Student Fees Dashboard (HTML/JS + Cloudflare Workers)
   - Veggie Shop E-commerce (Node.js + EJS + Render)
   - Hindi & English Typing Masters (HTML/CSS/JS)
   - PDF Compression + Image Master Tool
   - NoteList PWA with Firebase

2. Freelancer – Web3 & Blockchain (Aug 2019 - Present)
   - Ecosystem tester: Aptos, Arbitrum, Sui, Linea
   - IPFS decentralized hosting
   - Smart contract interaction & dApps testing
   - Crypto futures trading & on-chain analysis

3. Accounts Clerk – Army Headquarters (1 year)
   - Financial ledgers & audit management
   - Zero-error fund management

SKILLS:
- Frontend: React.js, Next.js, HTML5, CSS3, TailwindCSS, JavaScript
- Backend: Node.js, Express.js, EJS
- Database: MongoDB, PostgreSQL, Firebase, Cloudflare Workers
- AI/ML: Python, Streamlit, OpenAI API, OCR
- Blockchain: Web3.js, IPFS, Rust (Intermediate)
- Tools: Git, GitHub, Vercel, Render, GitHub Pages

LIVE PROJECTS:
- Library Fee System: raghublock.github.io/library-fee/
- Student Fees: student-fees-management.pages.dev/
- AI PDF Editor: aipdfedit.streamlit.app/
- Veggie Shop: veggie-shop-lgvy.onrender.com/
- BG Remover: raghublock.github.io/free-bg-remover/
- Hindi Typing Master: raghublock.github.io/hindi-typing-master/
- NoteList: raghublock.github.io/notelist/
"""

# ──────────────────────────────────────────
# CONVERSATION STATES
# ──────────────────────────────────────────
GETTING_INPUT, CHOOSING_ROLE = range(2)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# GEMINI AI SETUP
# ──────────────────────────────────────────
def get_gemini():
    genai.configure(api_key=GEMINI_KEY)
    return genai.GenerativeModel("gemini-1.5-flash")  # Free model

def ask_gemini(prompt: str) -> str:
    model = get_gemini()
    response = model.generate_content(prompt)
    return response.text

# ──────────────────────────────────────────
# JOB SEARCH
# ──────────────────────────────────────────

def search_indeed(role: str, location: str) -> list:
    jobs = []
    try:
        query = role.replace(" ", "+")
        loc = location.replace(" ", "+")
        url = f"https://in.indeed.com/jobs?q={query}&l={loc}&sort=date&limit=5"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.find_all("div", class_="job_seen_beacon")[:4]
        for card in cards:
            try:
                title = card.find("h2", class_="jobTitle")
                company = card.find("span", {"data-testid": "company-name"})
                loc_el = card.find("div", {"data-testid": "text-location"})
                link_el = card.find("a", class_="jcs-JobTitle")
                jk = link_el.get("data-jk", "") if link_el else ""
                t = title.get_text(strip=True) if title else ""
                if t:
                    jobs.append({
                        "source": "Indeed 🟡",
                        "title": t,
                        "company": company.get_text(strip=True) if company else "N/A",
                        "location": loc_el.get_text(strip=True) if loc_el else location,
                        "link": f"https://in.indeed.com/viewjob?jk={jk}" if jk else "https://in.indeed.com"
                    })
            except:
                continue
    except Exception as e:
        logger.error(f"Indeed error: {e}")
    return jobs


def search_linkedin(role: str, location: str) -> list:
    jobs = []
    try:
        query = role.replace(" ", "%20")
        loc = location.replace(" ", "%20")
        url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={loc}&sortBy=DD"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        cards = soup.find_all("div", class_="base-card")[:4]
        for card in cards:
            try:
                title = card.find("h3", class_="base-search-card__title")
                company = card.find("h4", class_="base-search-card__subtitle")
                loc_el = card.find("span", class_="job-search-card__location")
                link_el = card.find("a", class_="base-card__full-link")
                t = title.get_text(strip=True) if title else ""
                if t:
                    jobs.append({
                        "source": "LinkedIn 🔵",
                        "title": t,
                        "company": company.get_text(strip=True) if company else "N/A",
                        "location": loc_el.get_text(strip=True) if loc_el else location,
                        "link": link_el.get("href", "https://linkedin.com/jobs") if link_el else "https://linkedin.com/jobs"
                    })
            except:
                continue
    except Exception as e:
        logger.error(f"LinkedIn error: {e}")
    return jobs


def format_jobs(jobs: list) -> str:
    if not jobs:
        return "❌ Koi job nahi mili."
    text = ""
    for i, j in enumerate(jobs, 1):
        text += f"{j['source']} *{i}. {j['title']}*\n"
        text += f"   🏢 {j['company']}\n"
        text += f"   📍 {j['location']}\n"
        text += f"   🔗 [Apply Here]({j['link']})\n\n"
    return text


# ──────────────────────────────────────────
# AI FUNCTIONS (GEMINI - FREE!)
# ──────────────────────────────────────────

def generate_cover_letter(job_desc: str, company: str = "") -> str:
    prompt = f"""
Write a professional cover letter as Raghuveer Bhati.

His resume:
{RESUME}

Job details:
JOB DESCRIPTION: {job_desc}
COMPANY: {company or "the company"}

Requirements:
- 3 paragraphs, 200-250 words total
- Para 1: Why excited about this specific role
- Para 2: 2 specific relevant projects with live links
- Para 3: What he'll bring + call to action
- Include portfolio: https://raghublock.github.io/portfolio
- Professional but genuine tone
- Only output the cover letter, nothing else
"""
    return ask_gemini(prompt)


def analyze_match(job_desc: str) -> str:
    prompt = f"""
Analyze job match for Raghuveer Bhati.

His resume:
{RESUME}

Job description:
{job_desc}

Give exactly this format:
1. Match Score: X%
2. Top 3 matching skills/experience
3. Any skill gaps
4. Should apply? Yes/Maybe/No + one line reason

Be direct and honest. Under 150 words total.
"""
    return ask_gemini(prompt)


# ──────────────────────────────────────────
# BOT HANDLERS
# ──────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🤖 *Raghuveer's AI Job Bot v4.0*
_Powered by Google Gemini — FREE!_

*Commands:*
/jobs — Indeed + LinkedIn jobs dhundo 🔍
/cover — Cover letter banao 📝
/match — Job match % check karo 🎯
/help — Help

*Best Workflow:*
1️⃣ /jobs → jobs dhundo
2️⃣ Job description copy karo
3️⃣ /cover → cover letter ready
4️⃣ Apply karo! ✅
""", parse_mode="Markdown")


async def jobs_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    row = []
    for i, role in enumerate(JOB_ROLES):
        row.append(InlineKeyboardButton(role.split()[0], callback_data=f"role_{role}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔍 Sab Roles", callback_data="role_all")])

    await update.message.reply_text(
        "🔍 *Kaunsi role ke liye jobs dhundhein?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CHOOSING_ROLE


async def role_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role = query.data.replace("role_", "")
    context.user_data["search_role"] = role

    keyboard = [[
        InlineKeyboardButton("🌍 Remote", callback_data="loc_remote"),
        InlineKeyboardButton("🇮🇳 India", callback_data="loc_india"),
        InlineKeyboardButton("🌐 Dono", callback_data="loc_both"),
    ]]
    role_display = "Sab Roles" if role == "all" else role
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
    role = context.user_data.get("search_role", "Full Stack Developer")

    await query.edit_message_text(
        "🔍 *Jobs dhundh raha hoon...*\n_Indeed + LinkedIn — 20-30 sec_",
        parse_mode="Markdown"
    )

    try:
        all_jobs = []
        roles = JOB_ROLES[:3] if role == "all" else [role]
        locations = []
        if location == "remote":
            locations = ["remote"]
        elif location == "india":
            locations = ["India"]
        else:
            locations = ["remote", "India"]

        for r in roles[:2]:
            for loc in locations:
                all_jobs.extend(search_indeed(r, loc)[:2])
                all_jobs.extend(search_linkedin(r, loc)[:2])

        # Duplicates hatao
        seen, unique = set(), []
        for j in all_jobs:
            key = j["title"] + j["company"]
            if key not in seen:
                seen.add(key)
                unique.append(j)

        unique = unique[:8]

        if unique:
            msg = f"🎯 *{len(unique)} Jobs Mili!*\n\n"
            msg += format_jobs(unique)
            msg += "💡 _Job copy karo → /cover se cover letter banao!_"
        else:
            msg = """❌ *Jobs nahi mili — manually dekho:*

🔵 [LinkedIn Jobs](https://www.linkedin.com/jobs/search/?keywords=full+stack+developer&location=India)
🟡 [Indeed India](https://in.indeed.com/jobs?q=react+developer&l=remote)

Job description copy karo → /cover type karo! ✅"""

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

        keyboard = [[
            InlineKeyboardButton("🔄 Dobara Search", callback_data="restart"),
            InlineKeyboardButton("📝 Cover Letter", callback_data="goto_cover"),
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
        await query.edit_message_text("/jobs type karo dobara search ke liye!")
    elif query.data == "goto_cover":
        await query.edit_message_text("/cover type karo cover letter ke liye!")
    elif query.data.startswith("regen_"):
        mode = query.data.split("_", 1)[1]
        context.user_data["mode"] = mode
        await query.edit_message_text("Job description dobara paste karo:")
        return GETTING_INPUT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancel.\n\n/jobs, /cover, /match type karo.")
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🤖 *Commands:*

*/jobs* — Indeed + LinkedIn jobs dhundo
*/cover* — Cover letter banao
*/match* — Job match % check karo
*/cancel* — Cancel

*Workflow:*
1️⃣ /jobs → role + location choose karo
2️⃣ Job description copy karo
3️⃣ /cover → paste karo → letter ready!
4️⃣ Apply karo ✅

_Powered by Google Gemini — FREE! 🆓_
""", parse_mode="Markdown")


# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN or not GEMINI_KEY:
        raise ValueError("TELEGRAM_TOKEN aur GEMINI_KEY Railway Variables mein set karo!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    job_conv = ConversationHandler(
        entry_points=[CommandHandler("jobs", jobs_start)],
        states={
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
    app.add_handler(job_conv)
    app.add_handler(content_conv)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Raghuveer's Job Bot v4.0 chal raha hai!")
    print("FREE - Powered by Google Gemini!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
