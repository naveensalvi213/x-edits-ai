import logging
import tweepy
import requests
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
        self.client: Optional[tweepy.Client] = None
        
        if self.bearer_token:
            try:
                self.client = tweepy.Client(bearer_token=self.bearer_token)
                logger.info("Tweepy client initialized with Bearer Token.")
            except Exception as e:
                logger.error(f"Failed to initialize Tweepy client: {e}")
        elif config.TWITTER_API_KEY and config.TWITTER_ACCESS_TOKEN:
            try:
                self.client = tweepy.Client(
                    consumer_key=config.TWITTER_API_KEY,
                    consumer_secret=config.TWITTER_API_SECRET,
                    access_token=config.TWITTER_ACCESS_TOKEN,
                    access_token_secret=config.TWITTER_ACCESS_SECRET
                )
                logger.info("Tweepy client initialized with OAuth 1.0a User Context.")
            except Exception as e:
                logger.error(f"Failed to initialize Tweepy client with OAuth: {e}")
        else:
            logger.warning("No Twitter credentials provided. XMonitor will require TWITTER_BEARER_TOKEN.")

    def search_keyword(self, keyword: str, max_results: int = 10) -> List[TweetPost]:
        """
        Searches recent posts on X for a specific keyword.
        Excludes retweets to focus on original posts.
        """
        results: List[TweetPost] = []
        if not self.client:
            logger.error("Tweepy Client not initialized. Check TWITTER_BEARER_TOKEN.")
            return results

        # Construct query excluding retweets
        query = f'"{keyword}" -is:retweet'

        try:
            # Request recent tweets with author details and expansions
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max(max_results, 10), 100), # Tweepy search_recent_tweets allows 10..100
                tweet_fields=["created_at", "author_id", "text"],
                expansions=["author_id"],
                user_fields=["username"]
            )

            if not response or not response.data:
                logger.info(f"No tweets found for keyword: '{keyword}'")
                return results

            # Map author IDs to usernames
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

        except tweepy.TweepyException as e:
            logger.error(f"Twitter API error for keyword '{keyword}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error searching keyword '{keyword}': {e}")

        return results

    def fetch_all_new_posts(self, keywords: List[str]) -> List[TweetPost]:
        """
        Searches posts for all keywords in the list.
        """
        all_posts: List[TweetPost] = []
        for kw in keywords:
            logger.info(f"Searching X for keyword: '{kw}'...")
            posts = self.search_keyword(kw, max_results=config.MAX_TWEETS_PER_KEYWORD)
            logger.info(f"Found {len(posts)} posts for '{kw}'.")
            all_posts.extend(posts)
        return all_posts
