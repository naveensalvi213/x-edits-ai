import json
import os
import logging
from pathlib import Path
from typing import Set
from config import SEEN_IDS_FILE

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, filepath: Path = SEEN_IDS_FILE, max_history: int = 5000):
        self.filepath = filepath
        self.max_history = max_history
        self.seen_ids: Set[str] = self._load_seen_ids()

    def _load_seen_ids(self) -> Set[str]:
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
            # Maintain only the most recent max_history IDs if set gets huge
            ids_list = list(self.seen_ids)[-self.max_history:]
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(ids_list, f, indent=2)
            logger.info(f"Saved {len(ids_list)} seen IDs to {self.filepath}")
        except Exception as e:
            logger.error(f"Error saving seen IDs to {self.filepath}: {e}")
