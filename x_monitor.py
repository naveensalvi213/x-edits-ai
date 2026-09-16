import logging
import asyncio
import os
import re
import time
from dataclasses import dataclass
from typing import List, Optional

import twscrape
from twscrape.accounts_pool import parse_cookies, has_required_cookies
from curl_cffi import requests as cr

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
    """
    Scrapes X search results using twscrape + curl_cffi for authentication.
    
    Flow:
      1. curl_cffi (Chrome TLS fingerprint) fetches x.com/home with auth_token
         cookie → X returns ct0 CSRF token in response cookies
      2. twscrape uses auth_token + ct0 to authenticate and call X's GraphQL
         search API directly — no browser, works on GitHub Actions Linux
    """

    _API_DB = "/tmp/twscrape_x_monitor.db"

    def __init__(self):
        self.auth_token = config.TWITTER_AUTH_TOKEN.strip()

    def _get_ct0(self) -> tuple:
        """
        Use curl_cffi (Chrome TLS impersonation) to obtain the ct0 CSRF cookie.
        
        Key insight: ANY request to x.com — even ones returning 403 — will set
        the ct0 cookie. We try multiple endpoints in order, stopping at the first
        that provides ct0. This works even on GitHub Actions cloud IPs that may
        get 403 from x.com/home.
        """
        BEARER = (
            "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
            "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
        )
        
        # Try URLs in order — badge_count works from cloud IPs even when it 403s
        urls_to_try = [
            ("https://x.com/home", {}),
            ("https://x.com/", {}),
            ("https://x.com/i/flow/login", {}),
            ("https://x.com/search?q=hello&f=live", {}),
            # Lightweight API endpoint — 403 response but STILL sets ct0 cookie!
            ("https://x.com/i/api/2/badge_count/badge_count.json?supports_ntab_urt=1", {
                "authorization": f"Bearer {BEARER}",
                "x-twitter-active-user": "yes",
            }),
        ]
        
        for url, extra_headers in urls_to_try:
            try:
                session = cr.Session(impersonate="chrome124")
                session.cookies.set("auth_token", self.auth_token, domain=".x.com")
                resp = session.get(
                    url, 
                    allow_redirects=True, 
                    timeout=15,
                    headers=extra_headers if extra_headers else None,
                )
                ct0 = session.cookies.get("ct0")
                twid = session.cookies.get("twid", "")
                if ct0:
                    logger.info(f"ct0 obtained from {url.split('?')[0].split('/')[-1]} (HTTP {resp.status_code})")
                    return ct0, twid
                else:
                    logger.debug(f"ct0 not set by {url.split('?')[0]} (HTTP {resp.status_code})")
            except Exception as e:
                logger.debug(f"Failed to fetch ct0 from {url}: {e}")
        
        logger.error("Failed to obtain ct0 from all URL attempts.")
        return None, None

    async def _search_async(self, keywords: List[str], max_per_keyword: int) -> List[TweetPost]:
        """Run all keyword searches via twscrape."""
        ct0, twid = self._get_ct0()
        if not ct0:
            logger.error("Cannot search — ct0 cookie not obtained.")
            return []

        # Build cookie string
        cookie_str = f"auth_token={self.auth_token}; ct0={ct0}"
        if twid:
            cookie_str += f"; twid={twid}"

        # Remove stale DB to avoid "account already exists" warning
        if os.path.exists(self._API_DB):
            os.remove(self._API_DB)

        api = twscrape.API(self._API_DB)
        await api.pool.add_account(
            username="x_monitor_account",
            password="dummy",
            email="dummy@dummy.com",
            email_password="dummy",
            cookies=cookie_str,
        )

        accounts = await api.pool.get_all()
        if not accounts or not accounts[0].active:
            logger.error("twscrape account is not active — cookies may be invalid.")
            return []

        logger.info("twscrape account active. Starting keyword searches.")

        all_posts: List[TweetPost] = []
        for keyword in keywords:
            logger.info(f"Searching for keyword: '{keyword}'")
            count = 0
            try:
                async for tweet in api.search(f"{keyword} lang:en", limit=max_per_keyword):
                    try:
                        post = TweetPost(
                            id=str(tweet.id),
                            text=tweet.rawContent or "",
                            author_username=tweet.user.username if tweet.user else "unknown",
                            created_at=str(tweet.date) if tweet.date else "",
                            url=tweet.url or f"https://x.com/i/web/status/{tweet.id}",
                            keyword=keyword,
                        )
                        all_posts.append(post)
                        count += 1
                    except Exception as parse_err:
                        logger.warning(f"Error parsing tweet: {parse_err}")
                logger.info(f"Found {count} tweets for '{keyword}'.")
            except Exception as search_err:
                logger.error(f"twscrape search error for '{keyword}': {search_err}")
            time.sleep(0.5)

        return all_posts

    def fetch_all_new_posts(self, keywords: List[str]) -> List[TweetPost]:
        if not self.auth_token:
            logger.error("TWITTER_AUTH_TOKEN is not set!")
            return []
        return asyncio.run(self._search_async(keywords, config.MAX_TWEETS_PER_KEYWORD))

    def search_keyword(self, keyword: str, max_results: int = 15) -> List[TweetPost]:
        return self.fetch_all_new_posts([keyword])
