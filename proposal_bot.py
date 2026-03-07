#!/usr/bin/env python3
"""
🤖 Raghuveer's AI Job Application Bot
- Upwork/Fiverr proposals generate karta hai
- Job links se cover letters banata hai
- Resume se tailored applications
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)
import anthropic

# ──────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_KEY")

# ──────────────────────────────────────────
# RAGHUVEER KA POORA RESUME DATA
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
- B.Sc in Biology
- B.Ed in Science
- RSCIT Certified (VMOU 2017)

EXPERIENCE:
1. Freelancer – Website Developer (Sep 2024 - Present), Bikaner
   - Built AI-powered Background Remover (Python + Rembg API)
   - Built AI PDF Editor with OCR (Python + Streamlit) — aipdfedit.streamlit.app
   - Built Library Fee Management System (React + TailwindCSS + Cloudflare)
   - Built Student Fees Management Dashboard (HTML/JS + Cloudflare Workers)
   - Built Veggie Shop E-commerce (Node.js + EJS + Render)
   - Built Hindi & English Typing Master apps (HTML/CSS/JS)
   - Built PDF Compression tool and Image Master Tool
   - Built NoteList PWA with Firebase (offline support)

2. Freelancer – Web3 & Blockchain (Aug 2019 - Present), Bikaner
   - Early ecosystem tester: Aptos, Arbitrum, Sui, Linea testnets
   - IPFS decentralized hosting experience
   - Web3 domain management (Unstoppable Domains)
   - Smart contract interaction & dApps testing
   - Cryptocurrency futures trading & on-chain analysis

3. Accounts Clerk – Army Headquarters (1 year)
   - Managed financial ledgers & audit board proceedings
   - Zero-error fund management
   - Handled sensitive government financial data

TECHNICAL SKILLS:
- Frontend: React.js, Next.js, HTML5, CSS3, TailwindCSS, JavaScript (Advanced)
- Backend: Node.js, Express.js, EJS
- Database: MongoDB, PostgreSQL, Firebase, Cloudflare Workers
- AI/ML: Python, Streamlit, OpenAI API, OCR, Rembg
- Blockchain: Web3.js, IPFS, testnet operations, Rust (Intermediate)
- Tools: Git/GitHub, Vercel, Render, GitHub Pages, VS Code

LIVE PROJECTS:
1. Laxmi Library Fee System — raghublock.github.io/library-fee/
2. Student Fees Management — student-fees-management.pages.dev/
3. AI PDF Editor — aipdfedit.streamlit.app/
4. Veggie Shop — veggie-shop-lgvy.onrender.com/
5. Free BG Remover — raghublock.github.io/free-bg-remover/
6. Hindi Typing Master — raghublock.github.io/hindi-typing-master/
7. NoteList App — raghublock.github.io/notelist/

STRENGTHS:
- Army background: disciplined, zero-error mindset
- Self-taught across Web Dev, Web3, and AI
- 5+ years blockchain experience
- Builds real tools used by real local businesses
"""

# ──────────────────────────────────────────
# CONVERSATION STATES
# ──────────────────────────────────────────
CHOOSING_TYPE, GETTING_INPUT, GETTING_BUDGET = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# AI FUNCTIONS
# ──────────────────────────────────────────
def generate_proposal(platform: str, job_desc: str, budget: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    if platform == "fiverr":
        instruction = """
Write a SHORT Fiverr proposal (150-180 words):
- First line: directly address client's problem
- Middle: mention 1-2 RELEVANT projects from resume with live links
- End: clear call to action
- Friendly, confident tone
"""
    else:
        instruction = """
Write a professional Upwork proposal (220-260 words):
- Start by repeating client's specific need
- Mention relevant experience + project links
- Give a brief 3-step plan
- Mention timeline
- End with ONE specific question about their project
"""

    prompt = f"""
You are writing as Raghuveer Bhati. His resume:
{RESUME}

Write a {platform.upper()} proposal for this job:
JOB: {job_desc}
BUDGET: {budget}

{instruction}

Include portfolio: https://raghublock.github.io/portfolio
Sound human and specific. Only output proposal text.
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def generate_cover_letter(job_desc: str, company: str = "") -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    prompt = f"""
You are writing as Raghuveer Bhati. His resume:
{RESUME}

Write a cover letter for:
JOB: {job_desc}
COMPANY: {company if company else "the company"}

Requirements:
- 3 paragraphs, 200-250 words total
- Para 1: Why excited about THIS role specifically
- Para 2: 2 specific relevant projects with results
- Para 3: What you'll bring + call to action
- Include portfolio link naturally
- Professional but genuine tone

Only output the cover letter.
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def analyze_job_match(job_desc: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    prompt = f"""
Based on Raghuveer Bhati's resume:
{RESUME}

Analyze this job and give:
1. Match Score (0-100%)
2. Top 3 matching skills
3. Any gaps
4. Apply? Yes/Maybe/No + reason

JOB: {job_desc}

Be direct. Under 150 words.
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


# ──────────────────────────────────────────
# BOT HANDLERS
# ──────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = """
🤖 *Raghuveer's AI Job Bot*

Main tumhare liye:
✅ Fiverr proposals likhta hoon
✅ Upwork proposals likhta hoon
✅ Cover letters banata hoon
✅ Job match analyze karta hoon

*Commands:*
/proposal — Fiverr/Upwork proposal
/cover — Cover letter banao
/match — Job match check karo
/help — Sab commands
"""
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def proposal_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("🟢 Fiverr", callback_data="prop_fiverr"),
        InlineKeyboardButton("🔵 Upwork", callback_data="prop_upwork"),
    ]]
    await update.message.reply_text(
        "📋 *Kahan ke liye proposal chahiye?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return CHOOSING_TYPE


async def cover_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "cover"
    await update.message.reply_text(
        "📝 *Cover Letter*\n\nJob description paste karo:\n_(Pehli line mein company name likho — optional)_",
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


async def type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "prop_fiverr":
        context.user_data["mode"] = "fiverr"
        platform = "Fiverr 🟢"
    else:
        context.user_data["mode"] = "upwork"
        platform = "Upwork 🔵"

    await query.edit_message_text(
        f"✅ *{platform}*\n\n📝 Job description paste karo:",
        parse_mode="Markdown"
    )
    return GETTING_INPUT


async def input_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode", "upwork")
    context.user_data["job_desc"] = update.message.text

    if mode in ["fiverr", "upwork"]:
        await update.message.reply_text(
            "💰 *Client ka budget?*\n_Example: $50, $200, Not specified_",
            parse_mode="Markdown"
        )
        return GETTING_BUDGET
    else:
        await process_generation(update, context)
        return ConversationHandler.END


async def budget_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["budget"] = update.message.text
    await process_generation(update, context)
    return ConversationHandler.END


async def process_generation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    job_desc = context.user_data.get("job_desc", "")
    budget = context.user_data.get("budget", "Not specified")

    loading = await update.message.reply_text(
        "⏳ *AI kaam kar raha hai... 10-15 sec*",
        parse_mode="Markdown"
    )

    try:
        if mode in ["fiverr", "upwork"]:
            result = generate_proposal(mode, job_desc, budget)
            header = f"✅ *{mode.upper()} PROPOSAL READY!*\n━━━━━━━━━━━━\n\n"
            footer = "\n\n━━━━━━━━━━━━\n📋 _Copy karo aur paste karo!_"

        elif mode == "cover":
            lines = job_desc.split('\n')
            company = lines[0] if len(lines) > 1 else ""
            desc = '\n'.join(lines[1:]) if len(lines) > 1 else job_desc
            result = generate_cover_letter(desc, company)
            header = "✅ *COVER LETTER READY!*\n━━━━━━━━━━━━\n\n"
            footer = "\n\n━━━━━━━━━━━━\n📋 _Copy karo aur apply karo!_"

        else:  # match
            result = analyze_job_match(job_desc)
            header = "🎯 *JOB MATCH ANALYSIS*\n━━━━━━━━━━━━\n\n"
            footer = "\n\n━━━━━━━━━━━━"

        await loading.delete()

        full_msg = header + result + footer
        # Telegram 4096 char limit handle karo
        if len(full_msg) > 4096:
            await update.message.reply_text(header + result[:2000] + "...", parse_mode="Markdown")
            await update.message.reply_text("..." + result[2000:] + footer, parse_mode="Markdown")
        else:
            await update.message.reply_text(full_msg, parse_mode="Markdown")

        keyboard = [[
            InlineKeyboardButton("🔄 Dobara", callback_data=f"regen_{mode}"),
            InlineKeyboardButton("🏠 Menu", callback_data="menu"),
        ]]
        await update.message.reply_text(
            "Kya karna chahte ho?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        await loading.edit_text(f"❌ Error aaya: {str(e)}\n\nDobara try karo.")
        logger.error(f"Error: {e}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "menu":
        await query.edit_message_text(
            "/proposal — Proposal\n/cover — Cover letter\n/match — Job match"
        )
    elif query.data.startswith("regen_"):
        mode = query.data.split("_", 1)[1]
        context.user_data["mode"] = mode
        await query.edit_message_text("Job description dobara paste karo:")
        return GETTING_INPUT


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancel.\n\n/proposal, /cover ya /match type karo.")
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🤖 *Commands:*

*/proposal* — Fiverr ya Upwork proposal
*/cover* — Cover letter banao
*/match* — Job kitna match karta hai
*/cancel* — Cancel karo

*Cover letter tip:*
Pehli line mein company name likho, phir job description paste karo!
""", parse_mode="Markdown")


# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN or not ANTHROPIC_KEY:
        raise ValueError("TELEGRAM_TOKEN aur ANTHROPIC_KEY Railway Variables mein set karo!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("proposal", proposal_start),
            CommandHandler("cover", cover_start),
            CommandHandler("match", match_start),
        ],
        states={
            CHOOSING_TYPE: [CallbackQueryHandler(type_chosen)],
            GETTING_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_received)],
            GETTING_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, budget_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Raghuveer's Job Bot chal raha hai!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
