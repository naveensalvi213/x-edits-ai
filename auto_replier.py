import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Set

from curl_cffi import requests
from x_monitor import XMonitor, DEFAULT_PROXIES

logger = logging.getLogger(__name__)

CREATE_TWEET_QUERY_ID = "CUWCG7oBfrG71ZUXUtpwbw"
BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

class AutoReplier:
    def __init__(self, state_file: str = "replied_state.json"):
        self.state_file = state_file
        self.enabled = os.environ.get("AUTO_REPLY_ENABLED", "true").lower() in ("true", "1", "yes")
        
        # Pacing configuration
        self.min_gap_seconds = 900       # Minimum 15 minutes between auto-replies
        self.max_replies_per_hour = 2     # Max 2 replies per rolling hour
        self.max_replies_per_night = 6    # Max 6 replies per night window (11 PM - 7 AM IST)

        # In-memory and persistent state
        self.replied_ids: Set[str] = set()
        self.reply_history: list = []     # List of timestamps (epoch seconds)
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.replied_ids = set(data.get("replied_ids", []))
                    self.reply_history = data.get("reply_history", [])
            except Exception as e:
                logger.warning(f"Failed to load replied_state: {e}")

    def _save_state(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump({
                    "replied_ids": list(self.replied_ids),
                    "reply_history": self.reply_history[-50:]
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save replied_state: {e}")

    def is_night_window_ist(self) -> bool:
        """
        Returns True ONLY if current time is between 11:00 PM and 7:00 AM IST.
        IST is UTC+5:30.
        """
        now_utc = datetime.utcnow()
        now_ist = now_utc + timedelta(hours=5, minutes=30)
        hour = now_ist.hour
        # Active between 23:00 (11 PM) and 06:59 (before 7 AM)
        return hour >= 23 or hour < 7

    def can_reply_now(self, tweet_id: str) -> tuple[bool, str]:
        """
        Checks all safety rules: time window, pacing, hourly limit, and duplicate prevention.
        """
        if not self.enabled:
            return False, "Auto-reply is disabled via AUTO_REPLY_ENABLED config."

        if not self.is_night_window_ist():
            return False, "Outside night window (Active only 11:00 PM - 07:00 AM IST)."

        if tweet_id in self.replied_ids:
            return False, f"Tweet {tweet_id} has already been replied to."

        now = time.time()
        # Clean history older than 24 hours
        self.reply_history = [ts for ts in self.reply_history if now - ts < 86400]

        # 1. Minimum gap between replies (15 mins)
        if self.reply_history:
            last_reply = self.reply_history[-1]
            elapsed = now - last_reply
            if elapsed < self.min_gap_seconds:
                remaining_mins = int((self.min_gap_seconds - elapsed) / 60)
                return False, f"Pacing cooldown active: {remaining_mins}m remaining before next reply."

        # 2. Hourly rate limit (max 2 per hour)
        recent_hour_replies = [ts for ts in self.reply_history if now - ts < 3600]
        if len(recent_hour_replies) >= self.max_replies_per_hour:
            return False, f"Hourly limit reached ({len(recent_hour_replies)}/{self.max_replies_per_hour})."

        # 3. Night window limit (max 6 in last 8 hours)
        recent_night_replies = [ts for ts in self.reply_history if now - ts < 28800]
        if len(recent_night_replies) >= self.max_replies_per_night:
            return False, f"Night quota reached ({len(recent_night_replies)}/{self.max_replies_per_night})."

        return True, "All safety checks passed."

    def post_reply(self, tweet_id: str, author_username: str, comment_text: str) -> bool:
        """
        Posts a reply to the tweet on X via web GraphQL through Webshare proxy.
        """
        can_reply, reason = self.can_reply_now(tweet_id)
        if not can_reply:
            logger.info(f"Auto-reply skipped for tweet {tweet_id} by @{author_username}: {reason}")
            return False

        auth_token = os.environ.get("TWITTER_AUTH_TOKEN", "").strip()
        if not auth_token:
            logger.error("Cannot reply: TWITTER_AUTH_TOKEN missing.")
            return False

        # Use XMonitor proxy helper to get ct0
        xm = XMonitor()
        proxy = xm.proxies[0] if xm.proxies else None
        ct0, _ = xm._get_ct0(proxy=proxy)

        if not ct0:
            logger.error("Failed to get ct0 cookie for posting reply.")
            return False

        session = requests.Session(impersonate="chrome124")
        session.cookies.set("auth_token", auth_token, domain=".x.com")
        session.cookies.set("ct0", ct0, domain=".x.com")

        headers = {
            "authorization": f"Bearer {BEARER}",
            "x-csrf-token": ct0,
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "content-type": "application/json",
            "referer": f"https://x.com/{author_username}/status/{tweet_id}"
        }

        # Format comment text (clean whitespace, enforce length)
        clean_comment = comment_text.strip()
        if not clean_comment:
            logger.warning("Empty reply comment generated. Skipping.")
            return False

        payload = {
            "variables": {
                "tweet_text": clean_comment,
                "reply": {
                    "in_reply_to_tweet_id": str(tweet_id),
                    "exclude_reply_user_ids": []
                },
                "batch_compose": "BatchSubsequent",
                "dark_request": False,
                "media": {
                    "media_entities": [],
                    "possibly_sensitive": False
                },
                "semantic_annotation_ids": []
            },
            "features": {
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "creator_subscriptions_quote_tweet_preview_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "rweb_video_timestamps_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_enhance_cards_enabled": False
            },
            "queryId": CREATE_TWEET_QUERY_ID
        }

        url = f"https://x.com/i/api/graphql/{CREATE_TWEET_QUERY_ID}/CreateTweet"
        try:
            logger.info(f"Posting auto-reply to tweet {tweet_id} by @{author_username}...")
            resp = session.post(url, headers=headers, json=payload, proxy=proxy, timeout=20)
            
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data and "create_tweet" in data.get("data", {}):
                    logger.info(f"SUCCESS: Auto-reply posted to @{author_username} (ID {tweet_id})!")
                    self.replied_ids.add(tweet_id)
                    self.reply_history.append(time.time())
                    self._save_state()
                    return True
                else:
                    logger.error(f"Failed to create tweet, response: {resp.text[:300]}")
                    return False
            else:
                logger.error(f"X API error when replying ({resp.status_code}): {resp.text[:300]}")
                return False

        except Exception as e:
            logger.error(f"Exception while posting auto-reply: {e}", exc_info=True)
            return False
