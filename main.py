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

# Shared persistent state across runs in the same process
global_state_mgr = StateManager()

def run_monitor():
    logger.info("Starting X (Twitter) Hiring Post Monitor run...")

    # 1. Initialize components
    x_monitor = XMonitor()
    gemini_analyzer = GeminiAnalyzer()
    telegram_notifier = TelegramNotifier()

    keywords = config.get_keywords()
    logger.info(f"Target Keywords ({len(keywords)}): {keywords}")

    # 2. Fetch posts from X
    posts = x_monitor.fetch_all_new_posts(keywords)
    logger.info(f"Retrieved {len(posts)} total posts across all keywords.")

    # Deduplication: skip any post ever seen before + skip authors seen in last 24h
    seen_in_batch = set()
    new_posts = []
    for p in posts:
        if p.id in seen_in_batch or global_state_mgr.is_seen(p.id):
            continue
        seen_in_batch.add(p.id)
        if global_state_mgr.is_author_recently_seen(p.author_username, cooldown_hours=24):
            logger.info(f"Skipping post {p.id} by @{p.author_username}: author already alerted within 24h.")
            global_state_mgr.mark_seen(p.id)
            continue
        new_posts.append(p)

    logger.info(f"Found {len(new_posts)} never-seen posts to evaluate.")

    # Cap to max 15 candidate posts per 5-minute run for speed and strict quota safety
    MAX_PER_RUN = 15
    if len(new_posts) > MAX_PER_RUN:
        logger.info(f"Capping evaluation to latest {MAX_PER_RUN} posts for this run.")
        new_posts = new_posts[:MAX_PER_RUN]

    qualified_count = 0
    alerts_sent = 0

    try:
        # 3. Analyze each new post with Gemini and notify via Telegram if qualified
        for post in new_posts:
            # Mark as seen so we don't re-process in case of retry
            global_state_mgr.mark_seen(post.id)

            if global_state_mgr.is_author_recently_seen(post.author_username, cooldown_hours=24):
                logger.info(f"Skipping tweet ID {post.id} by @{post.author_username}: author already picked in last 24h.")
                continue

            logger.info(f"Evaluating tweet ID {post.id} by @{post.author_username} ('{post.keyword}')...")
            analysis = gemini_analyzer.analyze_post(post.text, post.author_username)

            if analysis.is_hiring_post:
                qualified_count += 1
                global_state_mgr.mark_author_seen(post.author_username)
                logger.info(f"QUALIFIED LEAD! Role: {analysis.role_type} | Tweet by @{post.author_username}")

                success = telegram_notifier.send_hiring_alert(
                    role_type=analysis.role_type,
                    author_username=post.author_username,
                    tweet_text=post.text,
                    tweet_url=post.url,
                    keyword=post.keyword
                )
                if success:
                    alerts_sent += 1
            else:
                logger.info(f"Disqualified tweet ID {post.id}: {analysis.reasoning}")

            # Pace calls (4.0s) to stay within the 15 RPM Gemini Free Tier limit
            time.sleep(4.0)
    finally:
        # 4. Save updated state (synced with GitHub API)
        global_state_mgr.save()

    logger.info(f"Run completed. Evaluated: {len(new_posts)} | Qualified: {qualified_count} | Telegram Alerts: {alerts_sent}")

if __name__ == "__main__":
    run_monitor()
