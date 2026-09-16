import os
# Force twscrape to use curl-cffi (Chrome TLS fingerprint) instead of httpx
# This bypasses X's bot detection on Linux datacenter/cloud runners like GitHub Actions
os.environ["TWS_HTTP_BACKEND"] = "curl"
os.environ["TWS_RAISE_WHEN_NO_ACCOUNT"] = "1"

import logging
import asyncio
import re
import time
import tempfile
import random
from dataclasses import dataclass
from typing import List, Optional

import twscrape
from twscrape.accounts_pool import parse_cookies, has_required_cookies
from curl_cffi import requests as cr

import config

logger = logging.getLogger(__name__)

# Pool of Webshare proxies to bypass datacenter IP blocks on cloud runners
DEFAULT_PROXIES = [
    "http://umskkzac:k6inespkkljj@31.59.20.176:6754",
    "http://umskkzac:k6inespkkljj@45.38.107.97:6014",
    "http://umskkzac:k6inespkkljj@198.105.121.200:6462",
    "http://umskkzac:k6inespkkljj@64.137.96.74:6641",
    "http://umskkzac:k6inespkkljj@198.23.243.226:6361",
    "http://umskkzac:k6inespkkljj@38.154.185.97:6370",
    "http://umskkzac:k6inespkkljj@84.247.60.125:6095",
    "http://umskkzac:k6inespkkljj@142.111.67.146:5611",
]


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
    Scrapes X search results using twscrape + curl_cffi (Chrome TLS fingerprint)
    routed through Webshare proxies to bypass Cloudflare/X datacenter IP blocking.
    """

    def __init__(self):
        self.auth_token = config.TWITTER_AUTH_TOKEN.strip()
        self._db_path = os.path.join(tempfile.gettempdir(), "twscrape_x_monitor.db")
        custom_proxy = os.getenv("PROXY_URL", "").strip()
        if custom_proxy:
            self.proxies = [custom_proxy]
        else:
            self.proxies = list(DEFAULT_PROXIES)

    def _get_active_proxy(self) -> Optional[str]:
        """Returns a proxy from the pool."""
        return random.choice(self.proxies) if self.proxies else None

    def _get_ct0(self, proxy: Optional[str] = None) -> tuple:
        """
        Use curl_cffi (Chrome TLS impersonation) via proxy to obtain the ct0 CSRF cookie.
        """
        BEARER = (
            "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
            "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
        )
        
        urls_to_try = [
            ("https://x.com/home", {}),
            ("https://x.com/", {}),
            ("https://x.com/i/flow/login", {}),
            ("https://x.com/search?q=hello&f=live", {}),
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
                    proxy=proxy,
                    headers=extra_headers if extra_headers else None,
                )
                ct0 = session.cookies.get("ct0")
                twid = session.cookies.get("twid", "")
                if ct0:
                    logger.info(f"ct0 obtained (HTTP {resp.status_code}) via proxy: {proxy.split('@')[-1] if proxy else 'direct'}")
                    return ct0, twid
            except Exception as e:
                logger.debug(f"Failed to fetch ct0 from {url} via {proxy}: {e}")
        
        logger.error("Failed to obtain ct0 from all URL attempts.")
        return None, None

    async def _search_async(self, keywords: List[str], max_per_keyword: int) -> List[TweetPost]:
        """Run all keyword searches via twscrape using proxy and curl-cffi backend."""
        # Try proxies in pool until one obtains ct0
        proxy = None
        ct0, twid = None, None
        proxy_candidates = list(self.proxies)
        random.shuffle(proxy_candidates)

        for candidate in proxy_candidates:
            ct0, twid = self._get_ct0(proxy=candidate)
            if ct0:
                proxy = candidate
                break

        if not ct0:
            logger.error("Cannot search — ct0 cookie not obtained across all proxies.")
            return []

        cookie_str = f"auth_token={self.auth_token}; ct0={ct0}"
        if twid:
            cookie_str += f"; twid={twid}"

        # Clean up existing db to prevent duplicate account errors
        if os.path.exists(self._db_path):
            try:
                os.remove(self._db_path)
            except Exception:
                pass

        api = twscrape.API(self._db_path, proxy=proxy)
        await api.pool.add_account(
            username="x_monitor_account",
            password="dummy",
            email="dummy@dummy.com",
            email_password="dummy",
            cookies=cookie_str,
            proxy=proxy,
        )

        accounts = await api.pool.get_all()
        if not accounts or not accounts[0].active:
            logger.error("twscrape account is not active — cookies may be invalid.")
            return []

        logger.info(f"twscrape account active with proxy {proxy.split('@')[-1]}. Starting searches...")

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
            time.sleep(1)

        return all_posts

    def fetch_all_new_posts(self, keywords: List[str]) -> List[TweetPost]:
        if not self.auth_token:
            logger.error("TWITTER_AUTH_TOKEN is not set!")
            return []
        return asyncio.run(self._search_async(keywords, config.MAX_TWEETS_PER_KEYWORD))

    def search_keyword(self, keyword: str, max_results: int = 15) -> List[TweetPost]:
        return self.fetch_all_new_posts([keyword])
