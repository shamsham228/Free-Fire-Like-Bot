import os
import telebot
import requests
import time
import threading
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import logging
import sys

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== CONFIGURATION =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", 5000))

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found in environment variables!")
    sys.exit(1)

REQUIRED_CHANNELS = ["@liketutorial228"]
GROUP_JOIN_LINK = "https://t.me/liketutorial228group"
OWNER_ID = 6602027873
OWNER_USERNAME = "@Jingen_333"
API_BASE_URL = "https://free-fire-like-api-chi-neon.vercel.app"  # Use the working API

# ===== BOT & APP INITIALIZATION =====
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
app = Flask(__name__)
like_tracker = {}

# ===== FUNCTIONS =====

def reset_limits():
    """Reset daily limits at 00:00 UTC"""
    while True:
        try:
            now_utc = datetime.utcnow()
            next_reset = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            sleep_seconds = (next_reset - now_utc).total_seconds()
            
            logger.info(f"⏰ Next limit reset in {sleep_seconds/3600:.1f} hours")
            time.sleep(sleep_seconds)
            
            like_tracker.clear()
            logger.info("✅ Daily limits reset!")
        except Exception as e:
            logger.error(f"❌ Reset error: {e}")
            time.sleep(3600)

def is_user_in_channel(user_id):
    """Check if user is member of all required channels"""
    try:
        for channel in REQUIRED_CHANNELS:
            try:
                member = bot.get_chat_member(channel, user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    return False
            except Exception as e:
                logger.warning(f"⚠️ Cannot check {channel}: {e}")
                return False
        return True
    except Exception as e:
        logger.error(f"❌ Channel check error: {e}")
        return False

def call_api(uid, region):
    """Call the API to send like"""
    url = f"{API_BASE_URL}/like?uid={uid}&server_name={region.upper()}"
    try:
        logger.info(f"🔗 Calling API: {url}")
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ API Response: {data}")
            return data
        else:
            logger.error(f"❌ API Error {response.status_code}")
            return {"error": f"API Error {response.status_code}", "status": 0}
    except requests.timeout:
        return {"error": "API Request Timeout", "status": 0}
    except Exception as e:
        logger.error(f"❌ API call error: {e}")
        return {"error": str(e), "status": 0}

def get_user_limit(user_id):
    """Get daily like limit for user"""
    if user_id == OWNER_ID:
        return 999999
    return 10  # Regular users: 10 likes per day

def format_response(data):
    """Format API response for Telegram"""
    try:
        if "error" in data:
            return f"❌ *Error*\n{data['error']}"
        
        if data.get("status") != 1:
            return "❌ *Failed to send like*\nTry again later"
        
        player_name = data.get("PlayerNickname", "Unknown")
        player_uid = data.get("UID", "N/A")
        likes_before = data.get("LikesbeforeCommand", 0)
        likes_given = data.get("LikesGivenByAPI", 0)
        likes_after = data.get("LikesafterCommand", 0)
        region = data.get("Region", "IND")
        level = data.get("PlayerLevel", 0)
        
        return (
            f"✅ *Success*\n\n"
            f"👤 *Name:* `{player_name}`\n"
            f"🆔 *UID:* `{player_uid}`\n"
            f"🏆 *Level:* `{level}`\n"
            f"🌍 *Region:* `{region}`\n"
            f"❤️ *Before:* `{likes_before}`\n"
            f"➕ *Added:* `{likes_given}`\n"
            f"❤️‍🔥 *Total:* `{likes_after}`"
        )
    except Exception as e:
        logger.error(f"Format error: {e}")
        return "⚠️ Error formatting response"

# ===== TELEGRAM COMMANDS =====

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    logger.info(f"👤 User started: {username} ({user_id})")
    
    if not is_user_in_channel(user_id):
        markup = InlineKeyboardMarkup()
        for channel in REQUIRED_CHANNELS:
            channel_name = channel.lstrip('@')
            markup.add(InlineKeyboardButton(f"🔗 Join {channel}", url=f"https://t.me/{channel_name}"))
        
        bot.reply_to(
            message,
            "📢 *Channel Verification Required*\n\n"
            "To use this bot, you must join our channel first.",
            reply_markup=markup
        )
        return
    
    if user_id not in like_tracker:
        like_tracker[user_id] = {"used": 0, "last_used": datetime.utcnow() - timedelta(days=1)}
    
    bot.reply_to(
        message,
        "✅ *Verified!*\n\n"
        "Use `/like <region> <uid>` to send likes\n\n"
        "Example: `/like IND 123456789`\n\n"
        "Supported Regions: IND, BD, BR, US, GLOBAL"
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.from_user.id
    
    if not is_user_in_channel(user_id):
        markup = InlineKeyboardMarkup()
        for channel in REQUIRED_CHANNELS:
            channel_name = channel.lstrip('@')
            markup.add(InlineKeyboardButton(f"🔗 Join {channel}", url=f"https://t.me/{channel_name}"))
        
        bot.reply_to(message, "❌ Join our channel first", reply_markup=markup)
        return
    
    help_text = (
        "📖 *Available Commands:*\n\n"
        "🎯 `/like <region> <uid>` - Send like to player\n"
        "📊 `/remain` - Check remaining likes\n"
        "🆘 `/help` - Show this message\n\n"
        "**Regions:** IND, BD, BR, US, GLOBAL\n\n"
        f"👑 *Owner:* {OWNER_USERNAME}"
    )
    
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['like'])
def handle_like(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    # Check if user is in group (for non-owner)
    if message.chat.type == "private" and user_id != OWNER_ID:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔗 Join Group", url=GROUP_JOIN_LINK))
        bot.reply_to(
            message,
            "❌ This command only works in groups\n\nJoin our group:",
            reply_markup=markup
        )
        return
    
    # Check channel membership
    if not is_user_in_channel(user_id):
        markup = InlineKeyboardMarkup()
        for channel in REQUIRED_CHANNELS:
            channel_name = channel.lstrip('@')
            markup.add(InlineKeyboardButton(f"🔗 Join {channel}", url=f"https://t.me/{channel_name}"))
        
        bot.reply_to(message, "❌ Join our channel first", reply_markup=markup)
        return
    
    # Validate format
    if len(args) != 3:
        bot.reply_to(
            message,
            "❌ *Invalid Format*\n\n"
            "Use: `/like <region> <uid>`\n"
            "Example: `/like IND 123456789`"
        )
        return
    
    region, uid = args[1].upper(), args[2]
    
    if not region.isalpha() or not uid.isdigit():
        bot.reply_to(message, "⚠️ *Invalid Input*\nRegion must be letters, UID must be numbers")
        return
    
    # Process in background
    threading.Thread(target=process_like, args=(message, user_id, region, uid)).start()

def process_like(message, user_id, region, uid):
    """Process like request"""
    try:
        now_utc = datetime.utcnow()
        
        # Initialize user tracker
        if user_id not in like_tracker:
            like_tracker[user_id] = {"used": 0, "last_used": now_utc - timedelta(days=1)}
        
        usage = like_tracker[user_id]
        
        # Reset if new day
        if usage["last_used"].date() < now_utc.date():
            usage["used"] = 0
        
        # Check limit
        max_limit = get_user_limit(user_id)
        if usage["used"] >= max_limit:
            bot.reply_to(
                message,
                f"⚠️ *Daily Limit Exceeded*\n\n"
                f"Your limit: {max_limit} likes/day\n"
                f"Come back tomorrow!"
            )
            return
        
        # Show processing message
        processing_msg = bot.send_message(
            message.chat.id,
            "⏳ *Processing...*\nSending like to your account...",
            reply_to_message_id=message.message_id
        )
        
        # Call API
        logger.info(f"📤 Processing: UID={uid}, Region={region}, User={user_id}")
        response = call_api(uid, region)
        
        # Update tracker
        usage["used"] += 1
        usage["last_used"] = now_utc
        like_tracker[user_id] = usage
        
        # Format and send response
        response_text = format_response(response)
        remaining = max_limit - usage["used"]
        
        if response.get("status") == 1:
            response_text += f"\n\n🔐 *Remaining:* `{remaining}/{max_limit}`"
        
        bot.edit_message_text(
            response_text,
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id
        )
        
    except Exception as e:
        logger.error(f"❌ Process error: {e}")
        bot.reply_to(message, f"❌ *Error*\n{str(e)[:100]}")

@bot.message_handler(commands=['remain'])
def show_remain(message):
    """Show remaining likes (Owner only)"""
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        bot.reply_to(message, "❌ *Owner Only Command*")
        return
    
    lines = ["📊 *Daily Usage Stats:*\n"]
    
    if not like_tracker:
        lines.append("❌ No users yet")
    else:
        for uid, usage in like_tracker.items():
            limit = get_user_limit(uid)
            used = usage.get("used", 0)
            limit_str = "∞" if limit > 1000 else str(limit)
            remaining = limit - used if limit <= 1000 else "∞"
            
            lines.append(f"`{uid}` → {used}/{limit_str} (Remaining: {remaining})")
    
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Ignore other messages"""
    pass

# ===== FLASK ROUTES =====

@app.route('/')
def index():
    return {
        'status': '✅ Bot Running',
        'bot_name': 'Free Fire Likes Bot',
        'health': 'OK'
    }

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

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

# ===== MAIN =====

if __name__ == '__main__':
    logger.info("🚀 Starting Free Fire Likes Bot...")
    
    # Start limit reset thread
    threading.Thread(target=reset_limits, daemon=True).start()
    
    # Start polling
    logger.info("🔔 Bot is listening for messages...")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        sys.exit(1)
