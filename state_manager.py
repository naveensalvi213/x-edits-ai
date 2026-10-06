import json
import os
import logging
import base64
import urllib.request
from pathlib import Path
from typing import Set, Tuple, Optional
from config import SEEN_IDS_FILE

logger = logging.getLogger(__name__)

REPO_OWNER = "naveensalvi213"
REPO_NAME = "x-edits-ai"
FILE_PATH_IN_REPO = "seen_ids.json"


class StateManager:
    """
    Manages persistent set of seen tweet IDs across runs.
    Syncs with GitHub REST API so state survives Render container restarts/spin-downs.
    """

    def __init__(self, filepath: Path = SEEN_IDS_FILE, max_history: int = 5000):
        self.filepath = filepath
        self.max_history = max_history
        self.github_token = os.getenv("GITHUB_TOKEN", "").strip()
        self.sha: Optional[str] = None
        self.seen_ids: Set[str] = self._load_seen_ids()

    def _fetch_from_github(self) -> Tuple[Optional[Set[str]], Optional[str]]:
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
                ids_list = json.loads(raw_bytes.decode("utf-8"))
                logger.info(f"Loaded {len(ids_list)} seen IDs from GitHub API (sha: {sha[:7] if sha else 'none'}).")
                return set(ids_list), sha
        except Exception as e:
            logger.warning(f"Failed to fetch seen_ids from GitHub API: {e}")
            return None, None

    def _save_to_github(self, ids_list: list) -> None:
        """Commit updated seen_ids.json to GitHub Contents API."""
        if not self.github_token:
            return
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH_IN_REPO}"
        try:
            content_str = json.dumps(ids_list, indent=2)
            content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

            payload = {
                "message": "sync seen_ids.json [bot]",
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
                logger.info(f"Synced seen_ids.json to GitHub API (sha: {self.sha[:7] if self.sha else 'unknown'}).")
        except Exception as e:
            logger.warning(f"Failed to sync seen_ids.json to GitHub API: {e}")

    def _load_seen_ids(self) -> Set[str]:
        # Try loading from GitHub first
        remote_ids, sha = self._fetch_from_github()
        if remote_ids is not None:
            self.sha = sha
            try:
                with open(self.filepath, "w", encoding="utf-8") as f:
                    json.dump(list(remote_ids), f, indent=2)
            except Exception:
                pass
            return remote_ids

        # Fallback to local file
        if not self.filepath.exists():
            return set()
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data)
        except Exception as e:
            logger.error(f"Error loading seen IDs from {self.filepath}: {e}")
            return set()

    def is_seen(self, tweet_id: str) -> bool:
        return str(tweet_id) in self.seen_ids

    def mark_seen(self, tweet_id: str) -> None:
        self.seen_ids.add(str(tweet_id))

    def save(self) -> None:
        try:
            ids_list = list(self.seen_ids)[-self.max_history:]
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(ids_list, f, indent=2)
            logger.info(f"Saved {len(ids_list)} seen IDs locally.")
            self._save_to_github(ids_list)
        except Exception as e:
            logger.error(f"Error saving seen IDs: {e}")

