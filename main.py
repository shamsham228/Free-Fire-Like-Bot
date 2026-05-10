import os
import telebot
import requests
import time
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, jsonify
import logging
import sys
from config import *

# ╔══════════════════════════════════════════════════════════════════╗
# ║  CREATOR: TARIKUL ISLAM
# ║  TELEGRAM: https://t.me/paglu_dev
# ║  PERSONAL TELEGRAM: https://t.me/itzpaglu
# ║  FIXED VERSION: 2025
# ╚══════════════════════════════════════════════════════════════════╝

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === CONFIG ===
if not BOT_TOKEN:
    logger.error(ERRORS["no_token"])
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
like_tracker = {}  # in-memory cache

# Flask app for webhook
app = Flask(__name__)

# === DATA RESET ===

def reset_limits():
    """Daily reset of usage tracker (in-memory only)."""
    while True:
        try:
            # Calculate time until next 00:00 UTC
            now_utc = datetime.utcnow()
            next_reset = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            sleep_seconds = (next_reset - now_utc).total_seconds()

            logger.info(f"Next reset in {sleep_seconds/3600:.2f} hours")
            time.sleep(sleep_seconds)
            like_tracker.clear()
            logger.info("✅ Daily limits reset at 00:00 UTC")
        except Exception as e:
            logger.error(f"Error in reset_limits thread: {e}")

# === UTILS ===

def is_user_in_channel(user_id):
    """Check if user is member of all required channels"""
    try:
        for channel in REQUIRED_CHANNELS:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        logger.error(f"Join check failed for user {user_id}: {e}")
        return False

def call_api(region, uid):
    """Call Free Fire Like API"""
    url = f"{API_BASE_URL}/like?uid={uid}&server_name={region.upper()}"
    try:
        logger.info(f"Calling API: {url}")
        response = requests.get(url, timeout=API_TIMEOUT)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            logger.warning(f"Rate limited: {response.text}")
            return response.json()
        elif response.status_code == 400:
            logger.warning(f"Bad request: {response.text}")
            return response.json()
        else:
            logger.error(f"API returned {response.status_code}: {response.text}")
            return {"error": f"API Error {response.status_code}"}
    except requests.exceptions.Timeout:
        return {"error": "API Timeout. Please try again."}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to API. Please try again later."}
    except Exception as e:
        logger.error(f"API call error: {e}")
        return {"error": str(e)}

def get_user_limit(user_id):
    """Get daily limit for user"""
    if user_id == OWNER_ID:
        return OWNER_DAILY_REQUESTS
    return USER_DAILY_REQUESTS

# Start background thread
threading.Thread(target=reset_limits, daemon=True).start()

# === FLASK ROUTES ===

@app.route('/')
def home():
    return jsonify({
        'status': 'Bot is running',
        'bot': 'Free Fire Likes Bot',
        'health': 'OK',
        'version': '2.0 FIXED'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return '', 500

# === TELEGRAM COMMANDS ===

@bot.message_handler(commands=['start'])
def start_command(message):
    """Start command"""
    user_id = message.from_user.id
    
    if not is_user_in_channel(user_id):
        markup = InlineKeyboardMarkup()
        for channel in REQUIRED_CHANNELS:
            markup.add(InlineKeyboardButton(
                f"🔗 Join {channel}", 
                url=f"https://t.me/{channel.strip('@')}"
            ))
        bot.reply_to(
            message, 
            "📢 *Channel Membership Required*\n\nTo use this bot, you must join all our channels first",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return
    
    if user_id not in like_tracker:
        like_tracker[user_id] = {
            "used": 0,
            "last_used": datetime.now() - timedelta(days=1),
            "total_likes_sent": 0
        }
    
    bot.reply_to(
        message,
        "✅ *You're verified!*\n\n"
        "Use `/like region uid` to send likes\n\n"
        "Example: `/like IND 123456789`\n\n"
        "Type `/help` for more info",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    """Help command"""
    user_id = message.from_user.id

    if user_id == OWNER_ID:
        help_text = (
            "📖 *Bot Commands:*\n\n"
            "🧑‍💻 `/like <region> <uid>` - Send likes to Free Fire UID\n"
            "🔰 `/start` - Start or verify\n"
            "🆘 `/help` - Show this help menu\n"
            "📊 `/stats` - Your statistics\n\n"
            "👑 *Owner Commands:*\n"
            "📈 `/remain` - Show all users' usage & stats\n"
            "🔄 `/update_tokens` - Force token update\n\n"
            f"📞 *Support:* {OWNER_USERNAME}\n"
            f"⚡ *Version:* 2.0 FIXED"
        )
        bot.reply_to(message, help_text, parse_mode="Markdown")
        return

    if not is_user_in_channel(user_id):
        markup = InlineKeyboardMarkup()
        for channel in REQUIRED_CHANNELS:
            markup.add(InlineKeyboardButton(
                f"🔗 Join {channel}",
                url=f"https://t.me/{channel.strip('@')}"
            ))
        bot.reply_to(
            message,
            "❌ You must join all our channels to use this command.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    help_text = (
        "📖 *Bot Commands:*\n\n"
        "🧑‍💻 `/like <region> <uid>` - Send likes\n"
        "  Example: `/like IND 123456789`\n\n"
        "📊 `/stats` - Your statistics\n"
        "🔰 `/start` - Start/verify\n"
        "🆘 `/help` - This menu\n\n"
        f"📞 *Support:* {OWNER_USERNAME}\n\n"
        "⚠️ *Note:* Level 1-2 accounts limited to 20 likes/day"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show user statistics"""
    user_id = message.from_user.id
    
    if user_id not in like_tracker:
        bot.reply_to(message, "📊 No statistics yet. Use `/like` to start!", parse_mode="Markdown")
        return
    
    stats = like_tracker[user_id]
    stats_text = (
        f"📊 *Your Statistics*\n\n"
        f"👤 User ID: `{user_id}`\n"
        f"📈 Total Likes Sent: `{stats.get('total_likes_sent', 0)}`\n"
        f"🔄 Requests Today: `{stats.get('used', 0)}`\n"
        f"📅 Last Used: `{stats.get('last_used')}`"
    )
    bot.reply_to(message, stats_text, parse_mode="Markdown")

@bot.message_handler(commands=['like'])
def handle_like(message):
    """Handle like command"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    args = message.text.split()

    # Only allow in groups (except owner in private)
    if message.chat.type == "private" and message.from_user.id != OWNER_ID:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔗 Join Official Group", url=GROUP_JOIN_LINK))
        bot.reply_to(
            message,
            "❌ Sorry! This command is not allowed in private chats.\n\nJoin our official group:",
            reply_markup=markup
        )
        return

    # Check membership
    if not is_user_in_channel(user_id):
        markup = InlineKeyboardMarkup()
        for channel in REQUIRED_CHANNELS:
            markup.add(InlineKeyboardButton(
                f"🔗 Join {channel}",
                url=f"https://t.me/{channel.strip('@')}"
            ))
        bot.reply_to(message, ERRORS["not_member"], reply_markup=markup, parse_mode="Markdown")
        return

    # Check format
    if len(args) != 3:
        bot.reply_to(
            message,
            ERRORS["invalid_format"],
            parse_mode="Markdown"
        )
        return

    region, uid = args[1].upper(), args[2]
    
    # Validate input
    if not region.isalpha() or not uid.isdigit():
        bot.reply_to(message, ERRORS["invalid_input"], parse_mode="Markdown")
        return
    
    # Validate region
    if region not in SUPPORTED_REGIONS:
        bot.reply_to(
            message,
            f"⚠️ Invalid region. Supported: {', '.join(SUPPORTED_REGIONS)}",
            parse_mode="Markdown"
        )
        return

    # Process like in thread
    threading.Thread(target=process_like, args=(message, region, uid)).start()

def process_like(message, region, uid):
    """Process like request"""
    user_id = message.from_user.id
    now_utc = datetime.utcnow()
    
    # Initialize tracker
    if user_id not in like_tracker:
        like_tracker[user_id] = {
            "used": 0,
            "last_used": now_utc - timedelta(days=1),
            "total_likes_sent": 0
        }
    
    usage = like_tracker[user_id]

    # Check if it's a new day (reset limit)
    last_used_date = usage["last_used"].date()
    current_date = now_utc.date()
    if current_date > last_used_date:
        usage["used"] = 0

    max_limit = get_user_limit(user_id)
    
    # Check daily limit
    if usage["used"] >= max_limit:
        bot.reply_to(
            message,
            f"⚠️ You have exceeded your daily request limit ({max_limit}/day)!\n\n"
            "Come back tomorrow for more likes.",
            parse_mode="Markdown"
        )
        return

    # Send processing message
    processing_msg = bot.reply_to(message, "⏳ Please wait... Sending likes...")
    
    try:
        # Call API
        response = call_api(region, uid)
        
        # Check for errors
        if "error" in response:
            error_msg = response.get("error", "Unknown error")
            bot.edit_message_text(
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                text=f"⚠️ Error: {error_msg}"
            )
            logger.error(f"API Error: {error_msg}")
            return
        
        # Check status
        status = response.get("status", 0)
        if status == 0:
            # API error
            message_text = response.get("message", "Unknown error")
            bot.edit_message_text(
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                text=f"❌ {message_text}"
            )
            return
        elif status == 2:
            # No likes added
            bot.edit_message_text(
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                text=ERRORS["no_likes"]
            )
            return
        
        # Success (status == 1)
        player_name = response.get("PlayerNickname", "Unknown")
        player_uid = response.get("UID", uid)
        player_level = response.get("PlayerLevel", 0)
        likes_before = response.get("LikesbeforeCommand", 0)
        likes_given = response.get("LikesGivenByAPI", 0)
        likes_after = response.get("LikesafterCommand", 0)
        
        daily_limit_info = response.get("daily_limit_info", {})
        
        # Update tracker
        usage["used"] += 1
        usage["last_used"] = now_utc
        usage["total_likes_sent"] = usage.get("total_likes_sent", 0) + likes_given
        
        # Build response
        response_text = (
            f"✅ *Request Processed Successfully*\n\n"
            f"👤 *Name:* `{player_name}`\n"
            f"🆔 *UID:* `{player_uid}`\n"
            f"⭐ *Level:* `{player_level}`\n"
            f"🌍 *Region:* `{region}`\n\n"
            f"📊 *Like Statistics:*\n"
            f"🤡 *Before:* `{likes_before}`\n"
            f"📈 *Added:* `{likes_given}`\n"
            f"🗿 *After:* `{likes_after}`\n\n"
            f"📅 *Daily Limit:*\n"
            f"✅ Sent: `{daily_limit_info.get('likes_sent_today', 0)}/{daily_limit_info.get('max_daily_likes', '?')}`\n"
            f"⏳ Remaining: `{daily_limit_info.get('remaining', '?')}`\n\n"
            f"🔐 *Requests Today:* `{usage['used']}/{max_limit}`\n"
            f"👑 *Credit:* @itzpaglu"
        )
        
        bot.edit_message_text(
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id,
            text=response_text,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Like sent successfully. User: {user_id}, UID: {player_uid}, Likes: {likes_given}")
        
    except Exception as e:
        logger.error(f"Error in process_like: {e}", exc_info=True)
        try:
            bot.edit_message_text(
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id,
                text=ERRORS["processing_error"]
            )
        except:
            bot.reply_to(message, ERRORS["processing_error"])

@bot.message_handler(commands=["remain"])
def owner_commands(message):
    """Owner only commands"""
    if message.from_user.id != OWNER_ID:
        return

    args = message.text.split()
    cmd = args[0].lower()

    if cmd == "/remain":
        lines = ["📊 *Daily Request Usage:*\n"]
        
        if not like_tracker:
            lines.append("❌ No users have used the bot yet.")
        else:
            for user_id, usage in like_tracker.items():
                limit = get_user_limit(user_id)
                used = usage.get("used", 0)
                total_likes = usage.get("total_likes_sent", 0)
                limit_str = "∞ Unlimited" if limit > 1000 else f"{used}/{limit}"
                
                lines.append(
                    f"👤 `{user_id}` → Requests: {limit_str} | Total Likes: {total_likes}"
                )
        
        bot.reply_to(message, "\n".join(lines), parse_mode="Markdown")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def reply_all(message):
    """Handle unknown messages"""
    if message.text.startswith('/'):
        known_commands = ['/start', '/like', '/help', '/remain', '/stats']
        command = message.text.split()[0].lower()
        if command not in known_commands:
            bot.reply_to(
                message,
                "❓ Unknown command. Type `/help` for available commands.",
                parse_mode="Markdown"
            )

# Start polling or webhook
if __name__ == '__main__':
    logger.info("Starting bot...")
    
    if WEBHOOK_URL:
        logger.info(f"Using Webhook mode: {WEBHOOK_URL}")
        # For production use webhook
        bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        app.run(host="0.0.0.0", port=PORT, debug=False)
    else:
        logger.info("Using Polling mode (development)")
        # For development use polling
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
