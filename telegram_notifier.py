import logging
import requests
from typing import Optional
import config

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing. TelegramNotifier disabled.")

    def send_hiring_alert(
        self,
        role_type: str,
        author_username: str,
        tweet_text: str,
        tweet_url: str,
        keyword: str,
        reasoning: str,
        personalized_comment: str
    ) -> bool:
        """
        Sends a formatted hiring lead notification to Telegram.
        """
        if not self.bot_token or not self.chat_id:
            logger.error("Cannot send Telegram message: bot token or chat ID missing.")
            return False

        message = (
            "🚨 <b>NEW HIRING POST DETECTED ON X!</b>\n\n"
            f"🎯 <b>Target Role:</b> {role_type}\n"
            f"👤 <b>Author:</b> @{author_username}\n"
            f"🔑 <b>Keyword:</b> <code>{keyword}</code>\n\n"
            "📝 <b>Post Content:</b>\n"
            f"<i>\"{tweet_text}\"</i>\n\n"
            "💡 <b>Gemini Qualification:</b>\n"
            f"<code>{reasoning}</code>\n\n"
            "💬 <b>Suggested Pitch Comment:</b>\n"
            f"<code>{personalized_comment}</code>\n\n"
            f"🔗 <a href=\"{tweet_url}\">Open Post on X (Twitter)</a>"
        )

        telegram_api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        try:
            response = requests.post(telegram_api_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info(f"Successfully sent Telegram alert for tweet by @{author_username}")
                return True
            else:
                logger.error(f"Telegram API error ({response.status_code}): {response.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to send message to Telegram: {e}")
            return False
