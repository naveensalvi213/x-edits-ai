import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

DEFAULT_KEYWORDS = [
    "hiring editor",
    "need editor",
    "looking for editor",
    "hiring thumbnail",
    "need thumbnail",
    "looking for thumbnail",
]

def get_keywords() -> list[str]:
    env_keywords = os.getenv("KEYWORDS")
    if env_keywords:
        return [k.strip() for k in env_keywords.split(",") if k.strip()]
    return DEFAULT_KEYWORDS

TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
TWITTER_AUTH_TOKEN = os.getenv("TWITTER_AUTH_TOKEN", os.getenv("TWITTER_BEARER_TOKEN", ""))
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

MAX_TWEETS_PER_KEYWORD = int(os.getenv("MAX_TWEETS_PER_KEYWORD", "15"))
SEEN_IDS_FILE = Path(__file__).parent / "seen_ids.json"
