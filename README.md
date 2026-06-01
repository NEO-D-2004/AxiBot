# 🤖 AxiBot - AI YouTube Moderator

AxiBot is a smart, privacy-focused YouTube Live Chat bot powered by **Nvidia Open-Source Models API** (e.g., Google Gemma 3). It moderates chat, welcomes subscribers, engages viewers, and manages stream goals just like a human moderator—all optimized for minimal YouTube API usage and blazing fast inference.

![License](https://img.shields.io/badge/license-MIT-blue.svg) ![Python](https://img.shields.io/badge/python-3.10+-blue.svg) ![AI API](https://img.shields.io/badge/AI-Nvidia_NIM-green.svg)

## ✨ Features

- **🧠 High-Performance Intelligence**: Uses NVIDIA's NIM API to run top-tier open-source models (like Gemma 3 or Gemma 2) with extremely low latency.
- **💾 Iterative User Memory (SQLite)**: 
    - **Long-term Recognition**: Stores a unique personality summary for every viewer in a local SQLite database (`storage/axibot.db`).
    - **Cumulative Learning**: Every 6 messages, it merges new conversation details with existing memories, building a deeper understanding of each viewer over time.
    - **Self-Awareness**: Viewers can ask "Who am I?" or "Tell about me" to hear what the bot knows about them.
- **🗣️ Smart Context & Interaction**: 
    - **Strict Doubt Filtering**: Only intervenes if it detects a clear question, a doubt, or a request for help—ignoring casual chatter and greetings.
    - **1:1 Language Matching**: Detects English, Tamil, or Tanglish and replies in the **exact same language**. No forced Tamil for English speakers.
    - **Pro-Gamer Persona**: Adopt a friendly, informal "pro-gamer" moderator friend vibe with emotional empathy (happy for wins, supportive for losses).
- **🎯 Auto-Updating Goals**:
    - **Like Target**: Automatically sets a goal (starts at 10). When hit, it celebrates and sets the next goal (+10).
    - **Subscriber Target**: Tracks milestones and celebrates new sub goals (+10).
- **📣 Smart Engagement**:
    - **Dynamic Hype**: Generates unique, low-emoji "Like & Subscribe" reminders using AI.
    - **Spike Detection**: Welcomes new viewers when traffic spikes (threshold: 8).
- **🛡️ Auto-Moderation**: Instantly deletes abusive messages and timeouts users.
- **⚡ Optimized Quota**: Smart polling allows for **8.5+ hours** of continuous streaming on the free YouTube quota.

---

## 🛠️ Prerequisites

1.  **Python 3.10+**: [Download Here](https://www.python.org/downloads/)
2.  **Nvidia API Key**: [Get Key Here](https://build.nvidia.com/) (Required for AI generation)

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
    NVIDIA_API_KEY=your_nvidia_api_key_here
    NVIDIA_MODEL_ID=google/gemma-3n-e2b-it
    ```

---

## 🚀 How to Run

1.  **Start the Bot**
    ```powershell
    python app/main.py
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
- **AI Personality**: Edit prompt templates in `app/nvidia_client.py`.

---

## ❓ Troubleshooting

- **"Quota Exceeded"**: The bot is optimized for ~8.5 hours. If you stream longer, create a second project/credential.
- **"401 Unauthorized" or API Key Errors**: Ensure your `NVIDIA_API_KEY` is correct in `.env`.
- **Bot replying to itself**: Ensure `BOT_NAME` in `.env` matches the bot's display name exactly.
