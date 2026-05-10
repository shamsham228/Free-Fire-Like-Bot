"""
Configuration file for Free Fire Like Bot
"""
import os
from datetime import datetime

# ========== BOT CONFIGURATION ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = ""
PORT = int(os.getenv("PORT", 5000))

# Telegram settings
REQUIRED_CHANNELS = ["@liketutorial228"]
GROUP_JOIN_LINK = "https://t.me/liketutorial228group"
OWNER_ID = 6602027873
OWNER_USERNAME = "@Jingen_333"

# ========== API CONFIGURATION ==========
API_BASE_URL = "https://free-fire-like-api-chi-neon.vercel.app"
API_TIMEOUT = 30

# ========== LIKE LIMITS (Based on User Type) ==========
LIKE_LIMITS = {
    "regular_user": {
        "daily_limit": 10,
        "delay_between_requests": 1
    },
    "premium_user": {
        "daily_limit": 30,
        "delay_between_requests": 0.5
    },
    "owner": {
        "daily_limit": 999999,
        "delay_between_requests": 0.2
    }
}

# ========== RATE LIMITING ==========
USER_DAILY_REQUESTS = 10
OWNER_DAILY_REQUESTS = 999999

# ========== LOGGING ==========
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ========== CONSTANTS ==========
SUPPORTED_REGIONS = ["IND", "BD", "BR", "US", "SAC", "NA", "GLOBAL"]
DEFAULT_REGION = "IND"

# ========== ERROR MESSAGES ==========
ERRORS = {
    "no_token": "❌ BOT_TOKEN not found! Please set your bot token.",
    "not_member": "❌ You must join all our channels to use this command.",
    "invalid_format": "❌ *Invalid Format*\n\nUse: `/like <region> <uid>`\n\nExample: `/like IND 123456789`",
    "invalid_input": "⚠️ *Invalid Input*\nRegion must be letters, UID must be numbers.",
    "daily_limit": "⚠️ *Daily Limit Exceeded*\n\nYour limit: {limit} likes/day\nCome back tomorrow!",
    "api_error": "⚠️ *API Error*\n`{error}`",
    "no_likes": "❌ UID has already received max likes. Try another UID or after 24 hours.",
    "invalid_uid": "⚠️ Invalid UID or unable to fetch data.",
    "processing_error": "⚠️ Something went wrong while processing your request.",
    "failed_to_send": "⚠️ *Failed to Send Like*\n\nPossible reasons:\n• Player doesn't exist\n• Already has max likes\n• API temporarily down",
    "api_timeout": "⏱️ *API Timeout*\n\nThe request took too long. Please try again."
}

# ========== SUCCESS MESSAGES ==========
SUCCESS = {
    "verified": "✅ *Verified!*\n\nUse `/like <region> <uid>` to send likes\n\nExample: `/like IND 123456789`",
    "likes_sent": "✅ *Like sent successfully!*",
    "start_message": (
        "✅ *Verified!*\n\n"
        "Use `/like <region> <uid>` to send likes\n\n"
        "📝 *Example:* `/like IND 123456789`\n\n"
        "🌍 *Regions:* IND, BD, BR, US, GLOBAL"
    ),
    "help_message": (
        "📖 *Available Commands:*\n\n"
        "🎯 `/like <region> <uid>` - Send like to player\n"
        "📊 `/remain` - Check remaining likes\n"
        "🆘 `/help` - Show this message\n\n"
        "*Supported Regions:*\n"
        "• IND - India\n"
        "• BD - Bangladesh\n"
        "• BR - Brazil\n"
        "• US - USA\n"
        "• GLOBAL - Global\n\n"
        f"👑 *Owner:* {OWNER_USERNAME}"
    )
}

# Get current date for cache tracking
CURRENT_DATE = datetime.utcnow().strftime("%Y-%m-%d")

# ========== UTILS ==========
def get_user_limit(user_id):
    """Get daily like limit based on user type"""
    if user_id == OWNER_ID:
        return LIKE_LIMITS["owner"]["daily_limit"]
    else:
        return LIKE_LIMITS["regular_user"]["daily_limit"]

def get_user_type(user_id):
    """Determine user type"""
    if user_id == OWNER_ID:
        return "owner"
    else:
        return "regular_user"
