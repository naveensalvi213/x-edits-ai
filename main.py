import logging
import sys
import time
import config
from state_manager import StateManager
from x_monitor import XMonitor, TweetPost
from gemini_analyzer import GeminiAnalyzer
from telegram_notifier import TelegramNotifier

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("X_Hiring_Monitor")

def run_monitor():
    logger.info("Starting X (Twitter) Hiring Post Monitor run...")
    
    # 1. Initialize components
    state_mgr = StateManager()
    x_monitor = XMonitor()
    gemini_analyzer = GeminiAnalyzer()
    telegram_notifier = TelegramNotifier()

    keywords = config.get_keywords()
    logger.info(f"Target Keywords ({len(keywords)}): {keywords}")

    # 2. Fetch recent posts from X
    posts = x_monitor.fetch_all_new_posts(keywords)
    logger.info(f"Retrieved {len(posts)} total posts across all keywords.")

    new_posts = [p for p in posts if not state_mgr.is_seen(p.id)]
    logger.info(f"Found {len(new_posts)} un-seen posts to evaluate.")

    qualified_count = 0
    alerts_sent = 0

    # 3. Analyze each new post with Gemini and notify via Telegram if qualified
    for post in new_posts:
        # Mark as seen so we don't re-process in case of retry
        state_mgr.mark_seen(post.id)

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
        else:
            logger.info(f"Disqualified tweet ID {post.id}: {analysis.reasoning}")

        # Pace calls (4.0s) to strictly stay within the 15 RPM Gemini Free Tier limit
        time.sleep(4.0)

    # 4. Save updated state
    state_mgr.save()
    logger.info(f"Run completed. Evaluated: {len(new_posts)} | Qualified: {qualified_count} | Telegram Alerts: {alerts_sent}")

if __name__ == "__main__":
    run_monitor()
