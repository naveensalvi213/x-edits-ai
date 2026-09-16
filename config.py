import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if available
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Default search keywords requested by user
DEFAULT_KEYWORDS = [
    "hiring editor",
    "need editor",
    "looking for editor",
    "hiring thumbnail",
    "need thumbnail",
    "looking for thumbnail",
]

def get_keywords() -> list[str]:
    """Retrieve keywords from ENV variable KEYWORDS if present, otherwise default list."""
    env_keywords = os.getenv("KEYWORDS")
    if env_keywords:
        return [k.strip() for k in env_keywords.split(",") if k.strip()]
    return DEFAULT_KEYWORDS

# X / Twitter API Credentials
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")

# Gemini API Credentials
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Telegram Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Operational settings
MAX_TWEETS_PER_KEYWORD = int(os.getenv("MAX_TWEETS_PER_KEYWORD", "15"))
SEEN_IDS_FILE = Path(__file__).parent / "seen_ids.json"
