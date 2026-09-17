import logging
import sys
import time
import config
from state_manager import StateManager
from x_monitor import XMonitor, TweetPost
from gemini_analyzer import GeminiAnalyzer
from telegram_notifier import TelegramNotifier
from auto_replier import AutoReplier

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("X_Hiring_Monitor")

from datetime import datetime, timezone

def is_recent_tweet(created_at_str: str, max_age_minutes: int = 45) -> bool:
    """Ignore any tweet older than max_age_minutes to prevent re-alerting on old historical posts."""
    try:
        dt = datetime.fromisoformat(created_at_str)
        now = datetime.now(timezone.utc)
        age_minutes = (now - dt).total_seconds() / 60
        return age_minutes <= max_age_minutes
    except Exception:
        return True

# Shared persistent state across runs in the same process
global_state_mgr = StateManager()

def run_monitor():
    logger.info("Starting X (Twitter) Hiring Post Monitor run...")
    
    # 1. Initialize components
    x_monitor = XMonitor()
    gemini_analyzer = GeminiAnalyzer()
    telegram_notifier = TelegramNotifier()
    auto_replier = AutoReplier()

    keywords = config.get_keywords()
    logger.info(f"Target Keywords ({len(keywords)}): {keywords}")

    # 2. Fetch recent posts from X
    posts = x_monitor.fetch_all_new_posts(keywords)
    logger.info(f"Retrieved {len(posts)} total posts across all keywords.")

    # Strict deduplication across keywords and state manager
    seen_in_batch = set()
    fresh_posts = []
    for p in posts:
        if p.id in seen_in_batch or global_state_mgr.is_seen(p.id):
            continue
        seen_in_batch.add(p.id)
        if is_recent_tweet(p.created_at, max_age_minutes=45):
            fresh_posts.append(p)
        else:
            global_state_mgr.mark_seen(p.id)

    new_posts = fresh_posts
    logger.info(f"Found {len(new_posts)} fresh un-seen posts (< 45m old) to evaluate.")

    # Cap to max 15 candidate posts per 5-minute run for speed and strict quota safety
    MAX_PER_RUN = 15
    if len(new_posts) > MAX_PER_RUN:
        logger.info(f"Capping evaluation to latest {MAX_PER_RUN} posts for this run.")
        new_posts = new_posts[:MAX_PER_RUN]

    qualified_count = 0
    alerts_sent = 0

    # 3. Analyze each new post with Gemini and notify via Telegram if qualified
    for post in new_posts:
        # Mark as seen so we don't re-process in case of retry
        global_state_mgr.mark_seen(post.id)

        logger.info(f"Evaluating tweet ID {post.id} by @{post.author_username} ('{post.keyword}')...")
        analysis = gemini_analyzer.analyze_post(post.text, post.author_username)

        if analysis.is_hiring_post:
            qualified_count += 1
            logger.info(f"QUALIFIED LEAD! Role: {analysis.role_type} | Tweet by @{post.author_username}")

            success = telegram_notifier.send_hiring_alert(
                role_type=analysis.role_type,
                author_username=post.author_username,
                tweet_text=post.text,
                tweet_url=post.url,
                keyword=post.keyword,
                reasoning=analysis.reasoning,
                personalized_comment=analysis.personalized_comment
            )
            if success:
                alerts_sent += 1

            # Auto-reply during night window (11 PM - 7 AM IST) with human pacing
            if analysis.personalized_comment:
                replied = auto_replier.post_reply(
                    tweet_id=post.id,
                    author_username=post.author_username,
                    comment_text=analysis.personalized_comment
                )
                if replied:
                    telegram_notifier.send_auto_reply_notification(
                        author_username=post.author_username,
                        tweet_url=post.url,
                        comment=analysis.personalized_comment
                    )
        else:
            logger.info(f"Disqualified tweet ID {post.id}: {analysis.reasoning}")

        # Pace calls (4.0s) to strictly stay within the 15 RPM Gemini Free Tier limit
        time.sleep(4.0)

    # 4. Save updated state
    global_state_mgr.save()
    logger.info(f"Run completed. Evaluated: {len(new_posts)} | Qualified: {qualified_count} | Telegram Alerts: {alerts_sent}")

if __name__ == "__main__":
    run_monitor()
