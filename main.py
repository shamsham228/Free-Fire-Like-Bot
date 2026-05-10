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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not found!")
    sys.exit(1)

REQUIRED_CHANNELS = ["@liketutorial228"]
GROUP_JOIN_LINK = "https://t.me/liketutorial228group"
OWNER_ID = 6602027873
OWNER_USERNAME = "@Jingen_333"
API_BASE_URL = "https://free-fire-like-api-mocha.vercel.app"

bot = telebot.TeleBot(BOT_TOKEN)
like_tracker = {}

app = Flask(__name__)

def reset_limits():
    while True:
        try:
            now_utc = datetime.utcnow()
            next_reset = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            sleep_seconds = (next_reset - now_utc).total_seconds()
            time.sleep(sleep_seconds)
            like_tracker.clear()
            logger.info("✅ Daily limits reset at 00:00 UTC")
        except Exception as e:
            logger.error(f"Error in reset_limits: {e}")

def is_user_in_channel(user_id):
    try:
        for channel in REQUIRED_CHANNELS:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        logger.error(f"Join check failed: {e}")
        return False

def call_api(region, uid):
    url = f"{API_BASE_URL}/like?uid={uid}&server_name={region.upper()}"
    try:
        response = requests.get(url, timeout=20)
        if response.status_code == 200:
            return response.json()
        return {"error": f"API Error {response.status_code}"}
    except Exception as e:
        logger.error(f"API call error: {e}")
        return {"error": str(e)}

def get_user_limit(user_id):
    if user_id == OWNER_ID:
        return 999999999
    return 1

threading.Thread(target=reset_limits, daemon=True).start()

@app.route('/')
def home():
    return jsonify({
        'status': 'Bot is running',
        'bot': 'Free Fire Likes Bot',
        'health': 'OK'
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

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    if not is_user_in_channel(user_id):
        markup = InlineKeyboardMarkup()
        for channel in REQUIRED_CHANNELS:
            markup.add(InlineKeyboardButton(f"🔗 Join {channel}", url=f"https://t.me/{channel.strip('@')}"))
        bot.reply_to(message, "📢 Channel Membership Required\nTo use this bot, you must join all our channels first", reply_markup=markup, parse_mode="Markdown")
        return
    if user_id not in like_tracker:
        like_tracker[user_id] = {"used": 0, "last_used": datetime.now() - timedelta(days=1)}
    bot.reply_to(message, "✅ You're verified! Use /like to send likes.\nHelp: /like [region] [uid]", parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.from_user.id
    if user_id == OWNER_ID:
        help_text = f"📖 *Bot Commands:*\n\n🧑‍💻 `/like <region> <uid>` - Send likes\n🔰 `/start` - Start\n🆘 `/help` - Help\n\n👑 *Owner:*\n📈 `/remain` - Stats\n\n📞 {OWNER_USERNAME}"
        bot.reply_to(message, help_text, parse_mode="Markdown")
        return
    
    if not is_user_in_channel(user_id):
        markup = InlineKeyboardMarkup()
        for channel in REQUIRED_CHANNELS:
            markup.add(InlineKeyboardButton(f"🔗 Join {channel}", url=f"https://t.me/{channel.strip('@')}"))
        bot.reply_to(message, "❌ Join channels first", reply_markup=markup, parse_mode="Markdown")
        return
    
    help_text = f"📖 *Commands:*\n\n🧑‍💻 `/like <region> <uid>`\n🔰 `/start`\n🆘 `/help`\n\n📞 {OWNER_USERNAME}"
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['like'])
def handle_like(message):
    user_id = message.from_user.id
    args = message.text.split()

    if message.chat.type == "private" and user_id != OWNER_ID:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔗 Join Group", url=GROUP_JOIN_LINK))
        bot.reply_to(message, "❌ Not allowed here.\n\nJoin group:", reply_markup=markup)
        return

    if not is_user_in_channel(user_id):
        markup = InlineKeyboardMarkup()
        for channel in REQUIRED_CHANNELS:
            markup.add(InlineKeyboardButton(f"🔗 Join {channel}", url=f"https://t.me/{channel.strip('@')}"))
        bot.reply_to(message, "❌ Join channels first", reply_markup=markup, parse_mode="Markdown")
        return

    if len(args) != 3:
        bot.reply_to(message, "❌ Format: `/like region uid`", parse_mode="Markdown")
        return

    region, uid = args[1].upper(), args[2]
    if not region.isalpha() or not uid.isdigit():
        bot.reply_to(message, "⚠️ Invalid input", parse_mode="Markdown")
        return

    threading.Thread(target=process_like, args=(message, region, uid)).start()

def process_like(message, region, uid):
    user_id = message.from_user.id
    now_utc = datetime.utcnow()
    usage = like_tracker.get(user_id, {"used": 0, "last_used": now_utc - timedelta(days=1)})

    last_used_date = usage["last_used"].date()
    current_date = now_utc.date()
    if current_date > last_used_date:
        usage["used"] = 0

    max_limit = get_user_limit(user_id)
    if usage["used"] >= max_limit:
        bot.reply_to(message, f"⚠️ Daily limit exceeded!")
        return

    processing_msg = bot.reply_to(message, "⏳ Sending likes...")
    response = call_api(region, uid)

    if "error" in response:
        bot.edit_message_text(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id, text=f"⚠️ Error: {response['error']}")
        return

    if not isinstance(response, dict) or response.get("status") != 1:
        bot.edit_message_text(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id, text="❌ Failed to send like")
        return

    try:
        player_uid = str(response.get("UID", uid)).strip()
        player_name = response.get("PlayerNickname", "N/A")
        likes_before = str(response.get("LikesbeforeCommand", "N/A"))
        likes_after = str(response.get("LikesafterCommand", "N/A"))
        likes_given = str(response.get("LikesGivenByAPI", "N/A"))

        usage["used"] += 1
        usage["last_used"] = now_utc
        like_tracker[user_id] = usage
        
        response_text = f"✅ *Success*\n\n👤 *Name:* `{player_name}`\n🆔 *UID:* `{player_uid}`\n🤡 *Before:* `{likes_before}`\n📈 *Added:* `{likes_given}`\n🗿 *Total:* `{likes_after}`\n🔐 *Remaining:* `{max_limit - usage['used']}`"

        bot.edit_message_text(chat_id=processing_msg.chat.id, message_id=processing_msg.message_id, text=response_text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error: {e}")
        bot.reply_to(message, "⚠️ Something went wrong")

@bot.message_handler(commands=["remain"])
def owner_commands(message):
    if message.from_user.id != OWNER_ID:
        return

    lines = ["📊 *Daily Usage:*"]
    if not like_tracker:
        lines.append("❌ No users yet")
    else:
        for uid, usage in like_tracker.items():
            limit = get_user_limit(uid)
            used = usage.get("used", 0)
            limit_str = "∞" if limit > 1000 else str(limit)
            lines.append(f"👤 `{uid}` → {used}/{limit_str}")
    bot.reply_to(message, "\n".join(lines), parse_mode="Markdown")

@bot.message_handler(func=lambda message: True, content_types=['text'])
def reply_all(message):
    pass

if __name__ == '__main__':
    logger.info("Starting bot...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
