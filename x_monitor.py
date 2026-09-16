import logging
import asyncio
import re
import urllib.parse
from dataclasses import dataclass
from typing import List, Optional
from playwright.async_api import async_playwright
import config

logger = logging.getLogger(__name__)

@dataclass
class TweetPost:
    id: str
    text: str
    author_username: str
    created_at: str
    url: str
    keyword: str

class XMonitor:
    def __init__(self):
        self.auth_token = config.TWITTER_AUTH_TOKEN.strip()

    def _scrape_keyword_sync(self, keyword: str, max_results: int = 15) -> List[TweetPost]:
        return asyncio.run(self._scrape_keyword_async(keyword, max_results))

    async def _scrape_keyword_async(self, keyword: str, max_results: int = 15) -> List[TweetPost]:
        results: List[TweetPost] = []
        if not self.auth_token:
            logger.error("No auth_token provided in TWITTER_AUTH_TOKEN!")
            return results

        logger.info(f"Playwright searching X for keyword: '{keyword}'...")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )

                # Inject auth_token cookie
                await context.add_cookies([
                    {
                        "name": "auth_token",
                        "value": self.auth_token,
                        "domain": ".x.com",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True,
                        "sameSite": "Lax"
                    },
                    {
                        "name": "auth_token",
                        "value": self.auth_token,
                        "domain": "x.com",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True,
                        "sameSite": "Lax"
                    }
                ])

                page = await context.new_page()
                search_url = f"https://x.com/search?q={urllib.parse.quote(keyword)}&f=live"
                
                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_timeout(4000)
                except Exception as goto_err:
                    logger.warning(f"Page navigation timeout or error: {goto_err}")

                # Scroll down slightly to trigger loading extra tweets
                await page.evaluate("window.scrollBy(0, 800)")
                await page.wait_for_timeout(2000)

                tweet_elements = await page.query_selector_all('[data-testid="tweet"]')
                logger.info(f"Found {len(tweet_elements)} raw tweet elements for '{keyword}'.")

                for t_el in tweet_elements[:max_results]:
                    try:
                        inner_text = await t_el.inner_text()
                        if not inner_text:
                            continue

                        status_links = await t_el.query_selector_all('a[href*="/status/"]')
                        tweet_url = ""
                        tweet_id = ""
                        author_username = "unknown"

                        for link in status_links:
                            href = await link.get_attribute("href")
                            if href and "/status/" in href:
                                match = re.search(r'/([^/]+)/status/(\d+)', href)
                                if match:
                                    author_username = match.group(1)
                                    tweet_id = match.group(2)
                                    tweet_url = f"https://x.com/{author_username}/status/{tweet_id}"
                                    break

                        if not tweet_id:
                            continue

                        lines = [line.strip() for line in inner_text.splitlines() if line.strip()]
                        full_text = " ".join(lines)

                        results.append(TweetPost(
                            id=tweet_id,
                            text=full_text,
                            author_username=author_username,
                            created_at="",
                            url=tweet_url,
                            keyword=keyword
                        ))
                    except Exception as el_err:
                        logger.warning(f"Error parsing tweet element: {el_err}")

                await browser.close()

        except Exception as e:
            logger.error(f"Playwright error during search for '{keyword}': {e}")

        return results

    def search_keyword(self, keyword: str, max_results: int = 15) -> List[TweetPost]:
        return self._scrape_keyword_sync(keyword, max_results)

    def fetch_all_new_posts(self, keywords: List[str]) -> List[TweetPost]:
        all_posts: List[TweetPost] = []
        for kw in keywords:
            posts = self.search_keyword(kw, max_results=config.MAX_TWEETS_PER_KEYWORD)
            logger.info(f"Retrieved {len(posts)} posts for '{kw}'.")
            all_posts.extend(posts)
        return all_posts
