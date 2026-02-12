# 🤖 AxiBot - Local AI YouTube Moderator

AxiBot is a smart, privacy-focused YouTube Live Chat bot powered by **Local AI** (Google Gemma 2 via Ollama) or **Gemini**. It moderates chat, welcomes subscribers, engages viewers, and manages stream goals just like a human moderator—all optimized for minimal API usage.

![License](https://img.shields.io/badge/license-MIT-blue.svg) ![Python](https://img.shields.io/badge/python-3.10+-blue.svg) ![Local AI](https://img.shields.io/badge/AI-Ollama-orange.svg)

## ✨ Features

- **🧠 Hybrid Intelligence**: Runs locally using **Gemma 2 (2B)** via Ollama or wirelessly via **Gemini 2.0 Flash**.
- **🎯 Auto-Updating Goals**:
    - **Like Target**: Automatically sets a goal (starts at 10). When hit, it celebrates and sets the next goal (+10).
    - **Subscriber Target**: Tracks your sub count. When you get a new sub (hitting the "Next 10" milestone), it celebrates and updates the target.
- **📣 Smart Engagement**:
    - **Dynamic Hype**: Generates unique, non-repeating "Like & Subscribe" reminders using AI.
    - **Human-like Timing**: Posts messages at random intervals (5-15 mins) to feel natural.
    - **Spike Detection**: Welcomes new viewers when traffic spikes.
- **🛡️ Auto-Moderation**: Instantly deletes abusive messages and timeouts users (5 mins).
- **🚫 Anti-Spam**: Enforces a 60-second cooldown per user.
- **⚡ Optimized Quota**: Smart polling allows the bot to run for **8.5+ hours** continuously on the free YouTube quota.

---

## 🛠️ Prerequisites

1.  **Python 3.10+**: [Download Here](https://www.python.org/downloads/)
2.  **Ollama** (Optional for Local AI): [Download Here](https://ollama.com/download)
3.  **Google Gemini Key** (Optional for Cloud AI): [Get Key Here](https://aistudio.google.com/)

---

## 📥 Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/axibot.git
    cd axibot
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup AI (Choose One)**
    - **Option A: Local (Ollama)**
        - Install Ollama.
        - Run: `ollama pull gemma2:2b`
        - Keep `ollama serve` running.
    - **Option B: Cloud (Gemini)**
        - Get an API key and add it to `.env`.

---

## 🔑 Configuration (.env)

1.  **Create `.env` file**
    Copy the example file:
    ```bash
    cp .env.example .env
    ```

2.  **Get YouTube Credentials**
    - Go to **[Google Cloud Console](https://console.cloud.google.com/)**.
    - Create a New Project & Enable **YouTube Data API v3**.
    - Create **OAuth client ID** (Desktop App).
    - Download JSON as `client_secret.json`.

3.  **Edit `.env`**
    ```ini
    YOUTUBE_CLIENT_SECRET_PATH=client_secret.json
    YOUTUBE_TOKEN_PATH=storage/token.json
    STREAMER_CHANNEL_ID=UCxxxxxxxxxxxxxxxxx
    BOT_NAME=AxiBot
    GEMINI_API_KEY=your_key_here (Optional)
    ```

---

## 🚀 How to Run

1.  **Start the Bot**
    ```powershell
    python -m app.main
    ```

2.  **First Time Login**
    - A browser window will open. Log in with the account you want the bot to speak from.
    - If you see "Unsafe App", click **Advanced -> Go to (Project) -> Allow**.

3.  **You're Live!**
    - The bot will detect your active stream.
    - It will automatically greet viewers and start monitoring chat.

---

## 📝 Customization

- **Bad Words**: Edit `app/moderation_filter.py`.
- **Engagement Settings**: Edit `app/engagement.py` to change message frequency or target increments.
- **AI Personality**: Edit prompt templates in `app/local_client.py` or `app/gemini_client.py`.

---

## ❓ Troubleshooting

- **"Quota Exceeded"**: The bot is optimized for ~8.5 hours. If you stream longer, create a second project/credential.
- **"Ollama Connection Error"**: Ensure `ollama serve` is running.
- **Bot replying to itself**: Ensure `BOT_NAME` in `.env` matches the bot's display name exactly.
