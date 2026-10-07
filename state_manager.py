import json
import os
import logging
import base64
import time
import urllib.request
from pathlib import Path
from typing import Set, Dict, Tuple, Optional
from config import SEEN_IDS_FILE

logger = logging.getLogger(__name__)

REPO_OWNER = "naveensalvi213"
REPO_NAME = "x-edits-ai"
FILE_PATH_IN_REPO = "seen_ids.json"


class StateManager:
    """
    Manages persistent set of seen tweet IDs and seen authors across runs.
    Syncs with GitHub REST API so state survives Render container restarts/spin-downs.
    """

    def __init__(self, filepath: Path = SEEN_IDS_FILE, max_history: int = 5000):
        self.filepath = filepath
        self.max_history = max_history
        self.github_token = os.getenv("GITHUB_TOKEN", "").strip()
        self.sha: Optional[str] = None
        self.seen_ids: Set[str] = set()
        self.seen_authors: Dict[str, float] = {}
        self._load_state()

    def _parse_raw_data(self, raw_data: any) -> Tuple[Set[str], Dict[str, float]]:
        ids: Set[str] = set()
        authors: Dict[str, float] = {}
        if isinstance(raw_data, list):
            ids = set(str(i) for i in raw_data)
        elif isinstance(raw_data, dict):
            ids = set(str(i) for i in raw_data.get("seen_ids", []))
            authors = {str(k).lower().strip(): float(v) for k, v in raw_data.get("seen_authors", {}).items()}
        return ids, authors

    def _fetch_from_github(self) -> Tuple[Optional[Tuple[Set[str], Dict[str, float]]], Optional[str]]:
        """Fetch latest seen_ids.json from GitHub Contents API."""
        if not self.github_token:
            return None, None
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH_IN_REPO}"
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"token {self.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "x-edits-ai-bot"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                sha = data.get("sha")
                raw_bytes = base64.b64decode(data.get("content", ""))
                parsed_json = json.loads(raw_bytes.decode("utf-8"))
                ids, authors = self._parse_raw_data(parsed_json)
                logger.info(f"Loaded {len(ids)} seen IDs and {len(authors)} seen authors from GitHub API (sha: {sha[:7] if sha else 'none'}).")
                return (ids, authors), sha
        except Exception as e:
            logger.warning(f"Failed to fetch state from GitHub API: {e}")
            return None, None

    def _save_to_github(self, state_dict: dict) -> None:
        """Commit updated seen_ids.json to GitHub Contents API."""
        if not self.github_token:
            return
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH_IN_REPO}"
        try:
            content_str = json.dumps(state_dict, indent=2)
            content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

            payload = {
                "message": "sync state (seen_ids & seen_authors) [bot]",
                "content": content_b64,
            }
            if self.sha:
                payload["sha"] = self.sha

            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Authorization": f"token {self.github_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "Content-Type": "application/json",
                    "User-Agent": "x-edits-ai-bot"
                },
                method="PUT"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                new_sha = res_data.get("content", {}).get("sha")
                if new_sha:
                    self.sha = new_sha
                logger.info(f"Synced state to GitHub API (sha: {self.sha[:7] if self.sha else 'unknown'}).")
        except Exception as e:
            logger.warning(f"Failed to sync state to GitHub API: {e}")

    def _load_state(self) -> None:
        remote_data, sha = self._fetch_from_github()
        if remote_data is not None:
            self.seen_ids, self.seen_authors = remote_data
            self.sha = sha
            return

        # Fallback to local file
        if not self.filepath.exists():
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                parsed_json = json.load(f)
                self.seen_ids, self.seen_authors = self._parse_raw_data(parsed_json)
        except Exception as e:
            logger.error(f"Error loading state from {self.filepath}: {e}")

    def is_seen(self, tweet_id: str) -> bool:
        return str(tweet_id) in self.seen_ids

    def mark_seen(self, tweet_id: str) -> None:
        self.seen_ids.add(str(tweet_id))

    def is_author_recently_seen(self, author_username: str, cooldown_hours: int = 24) -> bool:
        """Returns True if a post by this author was picked within the cooldown period (default 24h)."""
        if not author_username:
            return False
        clean_author = author_username.lower().strip()
        last_seen = self.seen_authors.get(clean_author)
        if last_seen is None:
            return False
        
        elapsed_seconds = time.time() - last_seen
        return elapsed_seconds < (cooldown_hours * 3600)

    def mark_author_seen(self, author_username: str) -> None:
        """Record current timestamp for author when their post is picked/alerted."""
        if not author_username:
            return
        clean_author = author_username.lower().strip()
        self.seen_authors[clean_author] = time.time()

    def save(self) -> None:
        try:
            now = time.time()
            # Retain seen authors for up to 48 hours to clean up stale entries
            pruned_authors = {
                author: ts for author, ts in self.seen_authors.items()
                if (now - ts) < (48 * 3600)
            }
            self.seen_authors = pruned_authors

            ids_list = list(self.seen_ids)[-self.max_history:]
            state_dict = {
                "seen_ids": ids_list,
                "seen_authors": pruned_authors
            }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(state_dict, f, indent=2)
            logger.info(f"Saved {len(ids_list)} seen IDs and {len(pruned_authors)} authors locally.")
            self._save_to_github(state_dict)
        except Exception as e:
            logger.error(f"Error saving state: {e}")


