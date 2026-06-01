# 🤖 AxiBot - AI YouTube Moderator & Live Assistant

AxiBot is a smart, privacy-focused YouTube Live Chat bot powered by the **Nvidia NIM Inference API** (e.g., Google Gemma 3). It moderates chat, welcomes subscribers, engages viewers, and manages stream goals just like a human moderator—all optimized for minimal YouTube API usage and blazing-fast inference.

It features a premium glassmorphic desktop GUI dashboard built with PyWebView for easy configuration, visual log streaming, database management, and engine control.

![License](https://img.shields.io/badge/license-MIT-blue.svg) ![Python](https://img.shields.io/badge/python-3.10+-blue.svg) ![AI API](https://img.shields.io/badge/AI-Nvidia_NIM-green.svg)

---

## ✨ Features

- **🖥️ Desktop GUI Dashboard**: A premium dark-themed interface to monitor bot status, live viewer metrics, likes goals, subscriber counts, and real-time captured console logs.
- **🧠 High-Performance Intelligence**: Integrates NVIDIA NIM API to run top-tier open-source LLMs (like Google Gemma 3 or Llama 3) with extremely low response latency.
- **👥 Dual YouTube Account Support**: 
  - **Streamer Account**: Links the streamer's channel via OAuth to automatically register `STREAMER_CHANNEL_ID` and sync live chat data.
  - **Bot Account**: Links a secondary bot account (saved to `storage/token.json`) that polls live chat and replies to viewer messages.
- **💾 Viewer Memory Database Manager**:
  - View, search, edit, or delete viewer logs from the local SQLite database (`storage/axibot.db`) directly through a graphic Database Manager tab.
  - Automatically builds and updates 1-sentence viewer personality profiles based on historical chat records.
- **🛡️ Custom Automated Moderation**: Define timed banned terms and toggle automated viewer timeouts or message deletions.
- **📣 Engagement Triggers**: Setup custom periodic announcements, milestone goals, and welcome alerts during traffic spikes.
- **⚡ Fast, Quota-Optimized Polling**: Adaptive polling (3s when active, 8s when idle) delivers near-instant reactions while allowing for **8+ hours** of streaming on a free YouTube API quota.

---

## 🛠️ Prerequisites

1. **Python 3.10+**: [Download Python](https://www.python.org/downloads/)
2. **Nvidia API Key**: [Get Key from NVIDIA Build](https://build.nvidia.com/) (Required for LLM reply generation)
3. **Google API Credentials**: Download client secrets for Desktop Application authentication.

---

## 📥 Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/axibot.git
   cd axibot
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🔑 Configuration & OAuth Setup

AxiBot requires two separate credentials paths in your `.env` configuration file.

1. **Get YouTube OAuth Credentials**
   - Go to the **[Google Cloud Console](https://console.cloud.google.com/)**.
   - Create a project and enable the **YouTube Data API v3**.
   - Navigate to **API & Services** &rarr; **Credentials** &rarr; **Create Credentials** &rarr; **OAuth client ID** (Application type: Desktop App).
   - Download the JSON configuration and save it as `client_secret.json` in the project root.

2. **Create `.env` file**
   ```ini
   YOUTUBE_CLIENT_SECRET_PATH=client_secret.json
   YOUTUBE_TOKEN_PATH=storage/token.json
   YOUTUBE_STREAMER_TOKEN_PATH=storage/streamer_token.json
   STREAMER_CHANNEL_ID=
   BOT_NAME=AxiBot
   NVIDIA_API_KEY=your_nvidia_api_key_here
   NVIDIA_MODEL_ID=google/gemma-3n-e2b-it
   COOLDOWN_SECONDS=60
   ```

---

## 🚨 CRITICAL RULE: Make Bot Account a Moderator

To allow AxiBot to perform moderation actions (deleting spam comments, timing out viewers, banning trolls):
**You MUST make the Bot Account a Moderator on the Streamer's YouTube Channel.**

1. Visit the [YouTube Creator Studio](https://studio.youtube.com/) of the Streamer account.
2. Go to **Settings** &rarr; **Community** &rarr; **Automated Filters**.
3. Under the **Managing Moderators** section, paste the YouTube Channel URL of your Bot Account.
4. Save the changes.

---

## 🚀 How to Run

### Run from Source
1. **Start the Desktop GUI**
   ```bash
   python main_gui.py
   ```
2. **First-Launch Guide**: A setup popup will guide you through connecting your YouTube accounts, entering API keys, and setting permissions.
3. **Connect Accounts**:
   - Click **Get Started** to log in to the YouTube Streamer Account (auto-detects channel ID).
   - In Settings, click **Link Bot Account** to authenticate the Bot Account.
4. **Go Live**: Head to the dashboard and click **Start Bot Engine**.

### Compile and Build Standalone Executable
You can bundle the Python application into a single executable folder for distribution:
```bash
python build.py
```
This cleans the workspace and compiles the executable at `dist/AxiBot/AxiBot.exe`. Make sure `client_secret.json` and `.env` are present in the same folder as the binary when launching.
