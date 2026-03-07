#!/usr/bin/env python3
"""
🤖 Raghuveer's AI Proposal Bot
Fiverr + Upwork ke liye auto proposals generate karta hai
Claude AI use karta hai

Setup:
1. pip install python-telegram-bot anthropic
2. TELEGRAM_TOKEN aur ANTHROPIC_API_KEY set karo
3. python proposal_bot.py
"""

import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)
import anthropic

# ──────────────────────────────────────────
# CONFIG — Yahan apni keys daalo
# ──────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_KEY")
ALLOWED_USER_ID = 0  # Apna Telegram user ID daalo (security ke liye)

# Raghuveer ka profile — proposal mein use hoga
DEVELOPER_PROFILE = """
Name: Raghuveer Bhati
Skills: React, Node.js, Python, HTML/CSS, Cloudflare Workers, AI/ML tools
Experience: Full Stack Web Developer & Blockchain Tester (Oct 2019 - Present)
Projects:
- Laxmi Library Fee System (React + TailwindCSS + Cloudflare)
- Student Fees Management Dashboard (HTML/JS + Cloudflare Workers)
- AI PDF Editor (Python + Streamlit)
- Veggie Shop E-commerce (EJS + Node.js)
- Free BG Remover (HTML/JS + Python Rembg API)
- Hindi Typing Master (HTML/CSS/JS)
Portfolio: https://raghublock.github.io/portfolio
GitHub: https://github.com/raghublock
Location: Bikaner, India
"""

# ──────────────────────────────────────────
# CONVERSATION STATES
# ──────────────────────────────────────────
CHOOSING_PLATFORM, GETTING_JOB_DESC, GETTING_BUDGET = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# AI PROPOSAL GENERATOR
# ──────────────────────────────────────────
def generate_proposal(platform: str, job_desc: str, budget: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    if platform == "fiverr":
        style = """
        - Short aur punchy (150-200 words max)
        - Pehli line client ki problem solve karne wali ho
        - 3 bullet points mein kya deliver karoge
        - Call to action at end
        - Friendly tone
        """
    else:  # upwork
        style = """
        - Professional aur detailed (200-300 words)
        - Pehle client ki requirement repeat karo (shows you read it)
        - Relevant experience mention karo
        - Timeline aur deliverables clear karo
        - Budget ke baare mein confident raho
        - End mein question poochho (engagement badhata hai)
        """

    prompt = f"""
Tu Raghuveer Bhati hai, ek experienced Full Stack Developer from Bikaner, India.

Tera profile:
{DEVELOPER_PROFILE}

Ab tu ek {platform.upper()} proposal likhega is job ke liye:

JOB DESCRIPTION:
{job_desc}

CLIENT KA BUDGET: {budget}

Proposal writing style:
{style}

IMPORTANT:
- English mein likho (professional)
- Generic mat likho — job description ke specific points address karo
- Apne REAL projects mention karo jo relevant hain
- Portfolio link zaroor daalo
- Natural aur human-like lagni chahiye proposal

Sirf proposal text do, koi explanation nahi.
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text

# ──────────────────────────────────────────
# BOT HANDLERS
# ──────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot start command"""
    user_id = update.effective_user.id

    # Security check
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return ConversationHandler.END

    welcome = """
🤖 *Raghuveer's AI Proposal Bot*

Namaste! Main tumhare liye Fiverr aur Upwork proposals automatically generate karta hoon.

*Commands:*
/proposal — Naya proposal banao
/help — Help dekho
/cancel — Koi bhi step cancel karo

Ab `/proposal` type karo aur shuru karte hain! 🚀
"""
    await update.message.reply_text(welcome, parse_mode="Markdown")


async def proposal_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proposal generation shuru karo"""
    keyboard = [
        [
            InlineKeyboardButton("🟢 Fiverr", callback_data="fiverr"),
            InlineKeyboardButton("🔵 Upwork", callback_data="upwork"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📋 *Platform select karo:*\n\nKahan ke liye proposal chahiye?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return CHOOSING_PLATFORM


async def platform_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Platform select ho gaya"""
    query = update.callback_query
    await query.answer()

    platform = query.data
    context.user_data["platform"] = platform

    platform_name = "Fiverr 🟢" if platform == "fiverr" else "Upwork 🔵"

    await query.edit_message_text(
        f"✅ Platform: *{platform_name}*\n\n"
        f"📝 *Job description paste karo:*\n\n"
        f"_Client ne jo likha hai woh copy-paste karo yahan_",
        parse_mode="Markdown"
    )
    return GETTING_JOB_DESC


async def job_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Job description mili"""
    context.user_data["job_desc"] = update.message.text

    await update.message.reply_text(
        "💰 *Client ka budget kya hai?*\n\n"
        "_Example: $50, $200, Not specified, etc._",
        parse_mode="Markdown"
    )
    return GETTING_BUDGET


async def budget_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Budget mila — ab proposal generate karo"""
    budget = update.message.text
    platform = context.user_data["platform"]
    job_desc = context.user_data["job_desc"]

    # Loading message
    loading_msg = await update.message.reply_text(
        "⏳ *AI proposal generate kar raha hai...*\n\n"
        "_10-15 seconds lagenge_",
        parse_mode="Markdown"
    )

    try:
        proposal = generate_proposal(platform, job_desc, budget)

        # Loading message delete karo
        await loading_msg.delete()

        platform_name = "FIVERR" if platform == "fiverr" else "UPWORK"

        # Proposal send karo
        result_msg = f"""
✅ *{platform_name} PROPOSAL READY!*
━━━━━━━━━━━━━━━━━━━━

{proposal}

━━━━━━━━━━━━━━━━━━━━
📋 _Copy karo aur paste karo!_
"""
        await update.message.reply_text(result_msg, parse_mode="Markdown")

        # Follow-up options
        keyboard = [
            [
                InlineKeyboardButton("🔄 Dobara Generate", callback_data=f"regen_{platform}"),
                InlineKeyboardButton("📝 Naya Proposal", callback_data="new"),
            ]
        ]
        await update.message.reply_text(
            "Kya karna chahte ho?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        await loading_msg.edit_text(
            f"❌ Error aaya: {str(e)}\n\nDobara try karo /proposal"
        )
        logger.error(f"Proposal generation error: {e}")

    return ConversationHandler.END


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline button clicks handle karo"""
    query = update.callback_query
    await query.answer()

    if query.data == "new":
        await query.edit_message_text("Theek hai! `/proposal` type karo naye proposal ke liye.")

    elif query.data.startswith("regen_"):
        platform = query.data.split("_")[1]
        context.user_data["platform"] = platform
        await query.edit_message_text(
            "📝 Job description dobara paste karo:",
        )
        return GETTING_JOB_DESC


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    await update.message.reply_text(
        "❌ Cancel ho gaya.\n\nNaya proposal ke liye /proposal type karo."
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help message"""
    help_text = """
🤖 *Proposal Bot Help*

*Kaise use karein:*
1. `/proposal` type karo
2. Platform choose karo (Fiverr ya Upwork)
3. Job description paste karo
4. Budget batao
5. ✅ Proposal copy karo!

*Tips:*
• Poori job description copy karo — AI better proposal banega
• Budget "Not specified" bhi likh sakte ho
• Ek job ke liye multiple proposals generate kar sakte ho

*Commands:*
/proposal — Naya proposal
/help — Yeh message
/cancel — Current step cancel

_Made by Raghuveer Bhati 🚀_
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


# ──────────────────────────────────────────
# MAIN — BOT CHALAAO
# ──────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("proposal", proposal_start)],
        states={
            CHOOSING_PLATFORM: [CallbackQueryHandler(platform_chosen)],
            GETTING_JOB_DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, job_desc_received)],
            GETTING_BUDGET:    [MessageHandler(filters.TEXT & ~filters.COMMAND, budget_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Raghuveer's Proposal Bot chal raha hai...")
    print("Telegram pe /start type karo!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()