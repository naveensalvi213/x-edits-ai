import json
import logging
import time
from dataclasses import dataclass
from typing import Optional
from google import genai
from google.genai import types
import config

logger = logging.getLogger(__name__)


@dataclass
class GeminiAnalysisResult:
    is_hiring_post: bool
    role_type: str
    reasoning: str
    personalized_comment: str


class GeminiAnalyzer:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.client: Optional[genai.Client] = None

        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Gemini Client successfully initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini Client: {e}")
        else:
            logger.warning("GEMINI_API_KEY is missing. GeminiAnalyzer will not be able to evaluate posts.")

    def _is_obvious_self_promo(self, text: str) -> Optional[str]:
        """
        Fast rule-based pre-filter to catch obvious freelancer self-promotions
        without wasting Gemini API calls or burning rate limits.
        """
        lower = text.lower().strip()

        # Check for typical freelancer pitch phrases
        self_promo_phrases = [
            "i am a freelance",
            "i'm a freelance",
            "i am a video editor",
            "i'm a video editor",
            "i am a thumbnail",
            "i'm a thumbnail",
            "dm me for editing",
            "dm me for video",
            "dm me for thumbnails",
            "my portfolio:",
            "here is my portfolio",
            "check out my portfolio",
            "here's my portfolio",
            "hire me as your",
            "hire me for",
            "available for work",
            "open for commissions",
            "taking on new clients",
            "looking for clients",
            "need a video editor? dm",
            "need an editor? dm",
            "looking for work as",
        ]

        for phrase in self_promo_phrases:
            if phrase in lower:
                return f"Fast filter: Self-promotion detected ('{phrase}')"

        # If it's a direct reply starting with a greeting pitching services
        if lower.startswith("@") and ("saw your post" in lower or "saw you're hiring" in lower):
            return "Fast filter: Freelancer replying to a hiring post"

        return None

    def analyze_post(self, tweet_text: str, author_username: str) -> GeminiAnalysisResult:
        """
        Evaluates a post using Gemini to check if it's a genuine hiring post for a Video Editor / Thumbnail Designer,
        and generates a customized response pitch.
        Includes automatic 429 rate-limit backoff and pre-filtering.
        """
        # 1. Fast pre-filter
        promo_reason = self._is_obvious_self_promo(tweet_text)
        if promo_reason:
            return GeminiAnalysisResult(
                is_hiring_post=False,
                role_type="Unknown",
                reasoning=promo_reason,
                personalized_comment=""
            )

        if not self.client:
            logger.error("Gemini client not initialized.")
            return GeminiAnalysisResult(
                is_hiring_post=False,
                role_type="Unknown",
                reasoning="Gemini client uninitialized.",
                personalized_comment=""
            )

        prompt = f"""
You are an expert AI recruiter and outreach assistant for a high-end Video Editing & Thumbnail Design agency.

Analyze the following X (Twitter) post by user @{author_username}:

---
POST CONTENT:
"{tweet_text}"
---

TASK:
1. Determine if this post is a GENUINE client/creator/agency looking to HIRE or CONTRACT a Video Editor or Thumbnail Designer.
   - MUST QUALIFY (True): The poster is looking to pay/hire an editor or thumbnail designer for their channel/project.
   - MUST DISQUALIFY (False): Self-promotions (e.g. "I am a video editor for hire", "DM me for editing services"), portfolio showcases, general advice, memes, or bot posts.

2. Identify the role needed: "Video Editor", "Thumbnail Designer", "Both", or "Other".

3. If qualified, write a short, high-converting, personalized reply comment (2-4 sentences max) for X/Twitter.
   - Address their specific niche, project requirements, or tone mentioned in the tweet.
   - Highlight value (e.g. fast turnaround, high CTR thumbnails, retention-focused editing).
   - End with a clean Call To Action (e.g. "Sent you a DM with samples!", "Check your DMs for portfolio!").
   - Sound human, professional, confident, and non-spammy.

Respond ONLY with a valid JSON object strictly matching this schema:
{{
  "is_hiring_post": boolean,
  "role_type": string,
  "reasoning": string,
  "personalized_comment": string
}}
"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2,
                    )
                )

                response_text = response.text.strip()
                data = json.loads(response_text)

                return GeminiAnalysisResult(
                    is_hiring_post=bool(data.get("is_hiring_post", False)),
                    role_type=str(data.get("role_type", "Unknown")),
                    reasoning=str(data.get("reasoning", "")),
                    personalized_comment=str(data.get("personalized_comment", ""))
                )

            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_time = (attempt + 1) * 3
                    logger.warning(f"Gemini 429 rate limit hit. Backing off for {wait_time}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue

                logger.error(f"Error during Gemini analysis for post by @{author_username}: {e}")
                return GeminiAnalysisResult(
                    is_hiring_post=False,
                    role_type="Unknown",
                    reasoning=f"Error analyzing post: {err_str}",
                    personalized_comment=""
                )

        return GeminiAnalysisResult(
            is_hiring_post=False,
            role_type="Unknown",
            reasoning="Gemini rate limit exceeded after retries.",
            personalized_comment=""
        )
