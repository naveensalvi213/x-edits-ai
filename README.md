# X (Twitter) Hiring Post Monitor & AI Pitch Generator

An automated 24/7 tool that monitors **X (Twitter)** for client hiring posts for **Video Editors** and **Thumbnail Designers**, filters spam using **Google Gemini AI**, drafts a personalized response comment, and sends instant alerts to your **Telegram**.

---

## 🌟 How It Works (5-Step Process)

1. **24/7 X Search**: Continuously queries X for keywords:
   - `"hiring editor"`, `"need editor"`, `"looking for editor"`
   - `"hiring thumbnail"`, `"need thumbnail"`, `"looking for thumbnail"`
2. **Deduplication**: Tracks seen tweet IDs in `seen_ids.json` so you never get duplicate alerts.
3. **Gemini AI Qualification (Step 2)**: Evaluates post content to verify if it's a real client looking to hire/contract (filters out self-promotions and spam).
4. **Gemini AI Pitch Generator (Step 3)**: Generates a short, personalized pitch comment customized to the client's post requirements.
5. **Telegram Instant Alert (Step 4)**: Sends post details, direct link to tweet, Gemini reasoning, and copy-pasteable pitch to your Telegram bot.
6. **GitHub Actions Hosting (Step 5)**: Runs 24/7 every 5 minutes on GitHub Actions cron schedule completely automated.

---

## 🛠️ Step-by-Step Setup Instructions

### 1. Get Your API Keys & Tokens

#### A. Twitter / X Bearer Token
- Go to [Twitter Developer Portal](https://developer.twitter.com/).
- Create a Project / App and grab your **Bearer Token** (or API Key & Secret + Access Token).

#### B. Google Gemini API Key
- Go to [Google AI Studio](https://aistudio.google.com/).
- Click **Get API Key** and copy your **Gemini API Key**.

#### C. Telegram Bot Token & Chat ID
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, follow the instructions, and copy the **HTTP API Token** (e.g., `123456789:ABCdefGhIJKlmNo...`).
3. Start a chat with your new bot by clicking `/start`.
4. To get your **Chat ID**, open Telegram and search for `@userinfobot` or `@GetIDBot` and send `/start`. Copy your numerical Chat ID (e.g. `987654321`).

---

### 2. Local Testing (Optional)

1. Clone or download this project folder.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your keys:
   ```env
   TWITTER_BEARER_TOKEN=your_twitter_bearer_token
   GEMINI_API_KEY=your_gemini_api_key
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   ```
4. Run the script:
   ```bash
   python main.py
   ```

---

### 3. Hosting 24/7 on GitHub Actions (Free)

1. Push this project to a **GitHub Repository** (Public or Private).
2. On your GitHub repository page:
   - Go to **Settings** -> **Secrets and variables** -> **Actions**.
   - Click **New repository secret** and add the following 4 secrets:
     - `TWITTER_BEARER_TOKEN`: Your Twitter Bearer Token
     - `GEMINI_API_KEY`: Your Gemini API Key
     - `TELEGRAM_BOT_TOKEN`: Your Telegram Bot Token
     - `TELEGRAM_CHAT_ID`: Your Telegram Chat ID
3. Enable GitHub Actions workflow:
   - Go to the **Actions** tab in your repository.
   - Select **X Hiring Post Monitor 24/7** and click **Enable workflow**.
   - You can click **Run workflow** to test it immediately!
4. The workflow will now automatically run **every 5 minutes, 24/7**, checking for new posts and sending alerts to your Telegram bot.

---

## ➕ Adding More Keywords in the Future

To add more search keywords in the future:
- Edit `DEFAULT_KEYWORDS` in `config.py` OR
- Pass a comma-separated environment variable `KEYWORDS="hiring editor,need thumbnail,hiring animator,looking for vfx"` in `.env` or GitHub Secrets.
