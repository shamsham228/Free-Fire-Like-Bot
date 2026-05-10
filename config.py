"""
Configuration file for Free Fire Like Bot
"""
import os
from datetime import datetime

# ========== BOT CONFIGURATION ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", 5000))

# Telegram settings
REQUIRED_CHANNELS = ["@liketutorial228"]
GROUP_JOIN_LINK = "https://t.me/liketutorial228group"
OWNER_ID = 6602027873
OWNER_USERNAME = "@Jingen_333"

# ========== API CONFIGURATION ==========
API_BASE_URL = "https://free-fire-like-api-chi-neon.vercel.app"
API_TIMEOUT = 30

# ========== LIKE LIMITS (Based on account level) ==========
LIKE_LIMITS = {
    "level_1_2": {
        "daily_limit": 20,
        "likes_per_uid": 5,
        "requests_per_call": 5,
        "delay_between_requests": 0.8
    },
    "level_3_10": {
        "daily_limit": 50,
        "likes_per_uid": 10,
        "requests_per_call": 10,
        "delay_between_requests": 0.6
    },
    "level_11_30": {
        "daily_limit": 150,
        "likes_per_uid": 30,
        "requests_per_call": 30,
        "delay_between_requests": 0.4
    },
    "level_30_plus": {
        "daily_limit": 300,
        "likes_per_uid": 50,
        "requests_per_call": 50,
        "delay_between_requests": 0.2
    }
}

# ========== RATE LIMITING ==========
USER_DAILY_REQUESTS = 1
OWNER_DAILY_REQUESTS = 999999

# ========== LOGGING ==========
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ========== CONSTANTS ==========
SUPPORTED_REGIONS = ["IND", "BD", "BR", "US", "SAC", "NA", "GLOBAL"]
DEFAULT_REGION = "IND"

# ========== ERROR MESSAGES ==========
ERRORS = {
    "no_token": "❌ BOT_TOKEN not found! Please set your bot token in environment variables.",
    "not_member": "❌ You must join all our channels to use this command.",
    "invalid_format": "❌ Invalid format. Use: `/like server_name uid`\n\nExample: `/like IND 123456789`",
    "invalid_input": "⚠️ Invalid input. UID must be numbers, region must be letters.",
    "daily_limit": "⚠️ You have exceeded your daily request limit! Come back tomorrow.",
    "api_error": "⚠️ API Error: {error}",
    "no_likes": "❌ UID has already received its max amount of likes. Try another UID or after 24 hours.",
    "invalid_uid": "⚠️ Invalid UID or unable to fetch data.",
    "processing_error": "⚠️ Something went wrong while processing your request."
}

# ========== SUCCESS MESSAGES ==========
SUCCESS = {
    "verified": "✅ You're verified! Use /like to send likes.\nHelp Menu: Use /like [region] [uid]",
    "likes_sent": "✅ Likes sent successfully!"
}

# Get current date for cache tracking
CURRENT_DATE = datetime.utcnow().strftime("%Y-%m-%d")
