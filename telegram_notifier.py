import logging
import requests
import html
from typing import Optional
import config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self):
        self.bot_token = config.TELEGRAM_BOT_TOKEN
        # Support default migration to supergroup ID if still set to old regular group ID
        raw_chat_id = config.TELEGRAM_CHAT_ID.strip()
        if raw_chat_id == "-5406812151":
            raw_chat_id = "-1004329851670"
        self.chat_id = raw_chat_id

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
        Handles HTML escaping and automatic migration to supergroups.
        """
        if not self.bot_token or not self.chat_id:
            logger.error("Cannot send Telegram message: bot token or chat ID missing.")
            return False

        # Escape user-generated text for safe HTML rendering in Telegram
        safe_text = html.escape(tweet_text)
        safe_reasoning = html.escape(reasoning)
        safe_comment = html.escape(personalized_comment)
        safe_role = html.escape(role_type)
        safe_kw = html.escape(keyword)
        safe_author = html.escape(author_username)

        message = (
            "🚨 <b>NEW HIRING POST DETECTED ON X!</b>\n\n"
            f"🎯 <b>Target Role:</b> {safe_role}\n"
            f"👤 <b>Author:</b> @{safe_author}\n"
            f"🔑 <b>Keyword:</b> <code>{safe_kw}</code>\n\n"
            "📝 <b>Post Content:</b>\n"
            f"<i>\"{safe_text}\"</i>\n\n"
            "💡 <b>Gemini Qualification:</b>\n"
            f"<code>{safe_reasoning}</code>\n\n"
            "💬 <b>Suggested Pitch Comment:</b>\n"
            f"<code>{safe_comment}</code>\n\n"
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

            data = response.json()
            # Check if group was migrated to supergroup
            params = data.get("parameters", {})
            new_chat_id = params.get("migrate_to_chat_id")
            if new_chat_id:
                logger.info(f"Detected chat migration from {self.chat_id} to {new_chat_id}. Retrying...")
                self.chat_id = str(new_chat_id)
                payload["chat_id"] = self.chat_id
                retry_resp = requests.post(telegram_api_url, json=payload, timeout=10)
                if retry_resp.status_code == 200:
                    logger.info(f"Successfully sent Telegram alert to new supergroup ID {new_chat_id}")
                    return True

            logger.error(f"Telegram API error ({response.status_code}): {response.text}")
            return False

        except Exception as e:
            logger.error(f"Failed to send message to Telegram: {e}")
            return False

    def send_auto_reply_notification(self, author_username: str, tweet_url: str, comment: str) -> bool:
        """
        Sends an instant notification to Telegram informing that an auto-reply was posted to X.
        """
        if not self.bot_token or not self.chat_id:
            return False

        safe_author = html.escape(author_username)
        safe_comment = html.escape(comment)

        message = (
            "🤖 <b>[NIGHT AUTO-REPLY POSTED ON X]</b>\n\n"
            f"👤 <b>Replied To:</b> @{safe_author}\n"
            f"💬 <b>Posted Comment:</b>\n<i>\"{safe_comment}\"</i>\n\n"
            f"🔗 <a href=\"{tweet_url}\">View Conversation on X</a>"
        )

        telegram_api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        try:
            r = requests.post(telegram_api_url, json=payload, timeout=10)
            return r.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send auto-reply notification to Telegram: {e}")
            return False

