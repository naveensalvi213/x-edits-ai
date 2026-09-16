import logging
import json
import urllib.parse
import requests
import tweepy
from dataclasses import dataclass
from typing import List, Optional
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
        self.bearer_token = config.TWITTER_BEARER_TOKEN
        self.auth_token = config.TWITTER_BEARER_TOKEN  # Can also be passed as auth_token
        self.client: Optional[tweepy.Client] = None
        
        # Check if bearer token looks like official v2 bearer token (starts with AAAAAAAAAAAAAAAAAAAA)
        if self.bearer_token and self.bearer_token.startswith("AAAAAAAAAAAAAAAAAAAA"):
            try:
                self.client = tweepy.Client(bearer_token=self.bearer_token)
                logger.info("Tweepy client initialized with official Bearer Token.")
            except Exception as e:
                logger.error(f"Failed to initialize Tweepy client: {e}")

    def _search_via_auth_cookie(self, keyword: str, auth_token_val: str) -> List[TweetPost]:
        """
        Searches X using browser auth_token cookie session.
        """
        results: List[TweetPost] = []
        try:
            s = requests.Session()
            s.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAAPYXHAOAAAACALWWSpBxYuNd6L3cv4nRyZxiPw%3DZD82aKBoMVB44hWr8aWFreQuiZSSFzgWrLmswXxac9X4cn',
                'x-twitter-active-user': 'yes',
                'x-twitter-client-language': 'en',
            })
            s.cookies.set('auth_token', auth_token_val, domain='.x.com')
            s.get('https://x.com/i/flow/login')
            ct0 = s.cookies.get('ct0')
            
            if not ct0:
                logger.error("Could not obtain ct0 CSRF cookie from X. auth_token may be invalid or expired.")
                return results

            s.headers.update({'x-csrf-token': ct0})

            variables = {
                "rawQuery": f'"{keyword}" -is:retweet',
                "count": 20,
                "querySource": "typed_query",
                "product": "Latest"
            }
            
            features = {
                "rweb_tipjar_consumption_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "communities_web_enable_tweet_community_results_fetch": True,
                "c9s_tweet_anatomy_subscribable_bookmarks_is_enabled": True,
                "tweet_awards_web_tipping_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_media_due_to_visibility_risk": True,
                "responsive_web_enhance_cards_enabled": False
            }

            url = f"https://x.com/i/api/graphql/nK1FbB0vLEj3f7lQ5YyMvA/SearchTimeline?variables={urllib.parse.quote(json.dumps(variables))}&features={urllib.parse.quote(json.dumps(features))}"
            
            res = s.get(url, timeout=15)
            if res.status_code == 200:
                data = res.json()
                instructions = data.get("data", {}).get("search_by_raw_query", {}).get("search_timeline", {}).get("timeline", {}).get("instructions", [])
                
                for inst in instructions:
                    entries = inst.get("entries", [])
                    for entry in entries:
                        item = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                        if not item:
                            continue
                        legacy = item.get("legacy", {})
                        user_legacy = item.get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {})
                        
                        tweet_id = str(legacy.get("id_str") or item.get("rest_id", ""))
                        text = legacy.get("full_text", "")
                        username = user_legacy.get("screen_name", "unknown")
                        created_at = legacy.get("created_at", "")
                        
                        if tweet_id and text:
                            url_link = f"https://x.com/{username}/status/{tweet_id}"
                            results.append(TweetPost(
                                id=tweet_id,
                                text=text,
                                author_username=username,
                                created_at=created_at,
                                url=url_link,
                                keyword=keyword
                            ))
            else:
                logger.error(f"X Web Search failed ({res.status_code}): {res.text[:200]}")

        except Exception as e:
            logger.error(f"Error during auth_cookie search for '{keyword}': {e}")

        return results

    def search_keyword(self, keyword: str, max_results: int = 10) -> List[TweetPost]:
        """
        Searches recent posts on X using official Tweepy API v2 client or auth_token cookie fallback.
        """
        # If official tweepy client initialized, use API v2
        if self.client:
            results: List[TweetPost] = []
            query = f'"{keyword}" -is:retweet'
            try:
                response = self.client.search_recent_tweets(
                    query=query,
                    max_results=min(max(max_results, 10), 100),
                    tweet_fields=["created_at", "author_id", "text"],
                    expansions=["author_id"],
                    user_fields=["username"]
                )

                if response and response.data:
                    users_map = {}
                    if response.includes and "users" in response.includes:
                        for user in response.includes["users"]:
                            users_map[user.id] = user.username

                    for tweet in response.data:
                        author_username = users_map.get(tweet.author_id, "unknown_user")
                        tweet_url = f"https://x.com/{author_username}/status/{tweet.id}"
                        created_str = tweet.created_at.isoformat() if tweet.created_at else ""

                        post = TweetPost(
                            id=str(tweet.id),
                            text=tweet.text,
                            author_username=author_username,
                            created_at=created_str,
                            url=tweet_url,
                            keyword=keyword
                        )
                        results.append(post)
                return results
            except Exception as e:
                logger.error(f"Tweepy search error for '{keyword}': {e}")

        # Fallback: search via auth_token cookie
        if self.auth_token:
            logger.info(f"Attempting search for '{keyword}' via auth_token cookie...")
            return self._search_via_auth_cookie(keyword, self.auth_token)

        logger.error("No valid search mechanism available. Provide TWITTER_BEARER_TOKEN or valid auth_token.")
        return []

    def fetch_all_new_posts(self, keywords: List[str]) -> List[TweetPost]:
        all_posts: List[TweetPost] = []
        for kw in keywords:
            logger.info(f"Searching X for keyword: '{kw}'...")
            posts = self.search_keyword(kw, max_results=config.MAX_TWEETS_PER_KEYWORD)
            logger.info(f"Found {len(posts)} posts for '{kw}'.")
            all_posts.extend(posts)
        return all_posts
