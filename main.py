import os
import telebot
import requests
import time
import threading
from datetime import datetime, timedelta, timezone
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, jsonify
import logging
import sys

# ===== IMPORT CONFIG =====
from config import (
    BOT_TOKEN, WEBHOOK_URL, PORT, REQUIRED_CHANNELS, GROUP_JOIN_LINK,
    OWNER_ID, OWNER_USERNAME, API_BASE_URL, API_TIMEOUT,
    LIKE_LIMITS, ERRORS, SUCCESS, SUPPORTED_REGIONS, DEFAULT_REGION,
    get_user_limit, get_user_type, LOG_LEVEL, LOG_FORMAT
)

# ===== LOGGING =====
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

# ===== VALIDATION =====
if not BOT_TOKEN:
    logger.error(ERRORS["no_token"])
    sys.exit(1)

# ===== BOT & APP INITIALIZATION =====
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
app = Flask(__name__)
like_tracker = {}

logger.info(f"✅ Bot initialized")
logger.info(f"🔗 API: {API_BASE_URL}")
logger.info(f"👑 Owner: {OWNER_USERNAME} (ID: {OWNER_ID})")
logger.info(f"📢 Required Channels: {REQUIRED_CHANNELS}")

# ===== FUNCTIONS =====

def get_utc_now():
    """Get current UTC time (handles deprecation warning)"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def reset_limits():
    """Reset daily limits at 00:00 UTC"""
    while True:
        try:
            now_utc = get_utc_now()
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

def send_channel_join_message(message):
    """Send channel join prompt"""
    markup = InlineKeyboardMarkup()
    for channel in REQUIRED_CHANNELS:
        channel_name = channel.lstrip('@')
        markup.add(InlineKeyboardButton(f"🔗 Join {channel}", url=f"https://t.me/{channel_name}"))
    
    bot.reply_to(message, ERRORS["not_member"], reply_markup=markup)

def call_api(uid, region):
    """Call the API to send like"""
    url = f"{API_BASE_URL}/like?uid={uid}&server_name={region.upper()}"
    try:
        logger.info(f"🔗 API Call: {url}")
        response = requests.get(url, timeout=API_TIMEOUT)
        
        logger.info(f"📊 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ API Response: {data}")
            return data
        else:
            logger.error(f"❌ API Error {response.status_code}")
            return {
                "error": f"API Error {response.status_code}",
                "status": 0
            }
    except requests.Timeout:
        logger.error("⏱️ API Request Timeout")
        return {
            "error": "API request timed out. Please try again.",
            "status": 0
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ API Request Error: {e}")
        return {
            "error": "API Failed. Please try again later.",
            "status": 0
        }
    except ValueError as e:
        logger.error(f"❌ JSON Parse Error: {e}")
        return {
            "error": "Invalid response from API.",
            "status": 0
        }
    except Exception as e:
        logger.error(f"❌ Unexpected API error: {e}")
        return {
            "error": str(e)[:100],
            "status": 0
        }

def format_response(data):
    """Format API response for Telegram"""
    try:
        # Check for error first
        if "error" in data:
            return f"❌ *Error*\n\n{data['error']}"
        
        # Check status
        if data.get("status") != 1:
            return ERRORS["failed_to_send"]
        
        # Extract data with fallbacks
        player_name = data.get("PlayerNickname", "Unknown")
        player_uid = data.get("UID", "N/A")
        likes_before = data.get("LikesbeforeCommand", 0)
        likes_given = data.get("LikesGivenByAPI", 0)
        likes_after = data.get("LikesafterCommand", 0)
        region = data.get("Region", "IND")
        level = data.get("PlayerLevel", 0)
        
        return (
            f"✅ *Success!*\n\n"
            f"👤 *Name:* `{player_name}`\n"
            f"🆔 *UID:* `{player_uid}`\n"
            f"🏆 *Level:* `{level}`\n"
            f"🌍 *Region:* `{region}`\n"
            f"❤️ *Before:* `{likes_before}`\n"
            f"➕ *Added:* `{likes_given}`\n"
            f"❤️‍🔥 *Total:* `{likes_after}`"
        )
    except Exception as e:
        logger.error(f"❌ Format error: {e}")
        return ERRORS["processing_error"]

# ===== TELEGRAM COMMANDS =====

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    logger.info(f"👤 User /start: {username} ({user_id})")
    
    if not is_user_in_channel(user_id):
        send_channel_join_message(message)
        return
    
    if user_id not in like_tracker:
        like_tracker[user_id] = {"used": 0, "last_used": get_utc_now() - timedelta(days=1)}
    
    bot.reply_to(message, SUCCESS["start_message"])

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.from_user.id
    
    if not is_user_in_channel(user_id):
        send_channel_join_message(message)
        return
    
    bot.reply_to(message, SUCCESS["help_message"])

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
        send_channel_join_message(message)
        return
    
    # Validate format
    if len(args) != 3:
        bot.reply_to(message, ERRORS["invalid_format"])
        return
    
    region, uid = args[1].upper(), args[2]
    
    # Validate input
    if not region.isalpha() or not uid.isdigit():
        bot.reply_to(message, ERRORS["invalid_input"])
        return
    
    # Validate region
    if region not in SUPPORTED_REGIONS:
        bot.reply_to(
            message,
            f"⚠️ *Invalid Region*\n\nSupported regions: {', '.join(SUPPORTED_REGIONS)}"
        )
        return
    
    # Process in background
    threading.Thread(target=process_like, args=(message, user_id, region, uid)).start()

def process_like(message, user_id, region, uid):
    """Process like request"""
    try:
        now_utc = get_utc_now()
        
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
                ERRORS["daily_limit"].format(limit=max_limit)
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
        
        # Check for errors
        if "error" in response:
            error_msg = f"⚠️ *API Error*\n\n{response['error']}"
            try:
                bot.edit_message_text(
                    error_msg,
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
            except:
                bot.reply_to(message, error_msg)
            return
        
        # Check status
        if response.get("status") != 1:
            error_msg = "❌ *Failed to Send Like*\n\nPossible reasons:\n• UID already has max likes\n• Invalid UID\n• Try another UID or wait 24 hours"
            try:
                bot.edit_message_text(
                    error_msg,
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
            except:
                bot.reply_to(message, error_msg)
            return
        
        # Update tracker only on success
        usage["used"] += 1
        usage["last_used"] = now_utc
        like_tracker[user_id] = usage
        
        # Format and send response
        response_text = format_response(response)
        remaining = max_limit - usage["used"]
        
        response_text += f"\n\n🔐 *Remaining:* `{remaining}/{max_limit}`"
        
        bot.edit_message_text(
            response_text,
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id
        )
        
    except Exception as e:
        logger.error(f"❌ Process error: {e}", exc_info=True)
        try:
            bot.reply_to(message, f"{ERRORS['processing_error']}\n\n`{str(e)[:100]}`")
        except:
            pass

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
            user_type = get_user_type(uid)
            
            lines.append(f"`{uid}` ({user_type}) → {used}/{limit_str} (Remaining: {remaining})")
    
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Show bot statistics"""
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        bot.reply_to(message, "❌ *Owner Only Command*")
        return
    
    total_users = len(like_tracker)
    total_likes_sent = sum(u.get("used", 0) for u in like_tracker.values())
    
    stats_text = (
        f"📈 *Bot Statistics:*\n\n"
        f"👥 *Total Users:* `{total_users}`\n"
        f"❤️ *Total Likes Sent:* `{total_likes_sent}`\n"
        f"🔗 *API:* `{API_BASE_URL}`\n"
        f"🕐 *Time:* `{get_utc_now().strftime('%Y-%m-%d %H:%M:%S')} UTC`"
    )
    
    bot.reply_to(message, stats_text)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Ignore other messages"""
    pass

# ===== FLASK ROUTES =====

@app.route('/')
def index():
    return jsonify({
        'status': '✅ Bot Running',
        'bot_name': 'Free Fire Likes Bot',
        'bot_username': '@LIKE_ShittBOT',
        'version': '2.1',
        'health': 'OK',
        'api_url': API_BASE_URL,
        'timestamp': get_utc_now().isoformat()
    })


@app.route('/token-info')
def token_info():
    """Fetch and display token info from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/token-info", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'status': 'success',
                'api_url': API_BASE_URL,
                'token_data': data,
                'timestamp': get_utc_now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'API returned status {response.status_code}',
                'api_url': API_BASE_URL
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'api_url': API_BASE_URL
        }), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'users_tracked': len(like_tracker),
        'api_url': API_BASE_URL,
        'timestamp': get_utc_now().isoformat()
    }), 200

@app.route('/stats')
def flask_stats():
    """Public stats endpoint"""
    total_users = len(like_tracker)
    total_likes = sum(u.get("used", 0) for u in like_tracker.values())
    
    return jsonify({
        'status': 'running',
        'bot_username': '@LIKE_ShittBOT',
        'api_url': API_BASE_URL,
        'total_users': total_users,
        'total_likes_sent_today': total_likes,
        'required_channels': REQUIRED_CHANNELS,
        'timestamp': get_utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')
    })

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

# ===== BOT POLLING IN BACKGROUND THREAD =====

def start_bot_polling():
    """Run bot polling in background"""
    logger.info("🔔 Starting bot polling in background thread...")
    try:
        # Remove any existing webhook
        bot.remove_webhook()
        logger.info("✅ Webhook removed")
        
        # Start polling with retry
        while True:
            try:
                bot.infinity_polling(timeout=10, long_polling_timeout=5)
            except Exception as e:
                logger.error(f"⚠️ Polling error: {e}")
                time.sleep(5)
                logger.info("🔄 Retrying polling...")
                
    except Exception as e:
        logger.error(f"❌ Fatal bot polling error: {e}")
        sys.exit(1)

# ===== MAIN =====

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🚀 Starting Free Fire Likes Bot...")
    logger.info("=" * 70)
    logger.info("📌 Mode: POLLING ONLY (webhook disabled)")
    logger.info(f"🤖 Bot: @LIKE_ShittBOT")
    logger.info(f"🔗 API: {API_BASE_URL}")
    logger.info(f"👑 Owner: {OWNER_USERNAME} (ID: {OWNER_ID})")
    logger.info(f"📢 Channels: {', '.join(REQUIRED_CHANNELS)}")
    
    # Start limit reset thread
    reset_thread = threading.Thread(target=reset_limits, daemon=True)
    reset_thread.start()
    logger.info("✅ Reset thread started")
    
    # Start bot polling in background thread
    bot_thread = threading.Thread(target=start_bot_polling, daemon=True)
    bot_thread.start()
    logger.info("✅ Bot polling thread started")
    
    # Start Flask app on Render (for health checks only)
    logger.info(f"🌐 Starting Flask on port {PORT} (health checks only)...")
    logger.info("=" * 70)
    
    try:
        app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ Flask error: {e}")
        sys.exit(1)
