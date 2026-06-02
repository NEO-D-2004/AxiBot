# AxiBot - AI YouTube Moderator & Live Assistant

AxiBot is a smart, privacy-focused YouTube Live Chat bot powered by the NVIDIA NIM Inference API (using models such as Google Gemma 3). It moderates chat, welcomes subscribers, engages viewers, and tracks stream goals like a human moderator—all optimized for low latency and minimal YouTube API quota usage.

AxiBot features a dark-themed glassmorphic desktop GUI dashboard built with PyWebView for easy configuration, visual log streaming, database management, and engine control.

---

## Features

- **Desktop GUI Dashboard**: A dark-themed dashboard to monitor bot status, live viewer metrics, likes goals, subscriber counts, and real-time logs.
- **High-Performance Intelligence**: Integrates NVIDIA NIM API to run top-tier open-source LLMs (like Google Gemma 3 or Llama 3) with extremely low response latency.
- **Dual YouTube Account Support**: 
  - **Streamer Account**: Links the streamer's channel via OAuth to automatically register `STREAMER_CHANNEL_ID` and sync live chat data.
  - **Bot Account**: Links a secondary bot account that polls live chat and replies to viewer messages.
- **Viewer Memory Database Manager**:
  - View, search, edit, or delete viewer logs from the local SQLite database directly through a graphic Database Manager tab.
  - Automatically builds and updates 1-sentence viewer personality profiles based on historical chat records.
- **Custom Automated Moderation**: Define timed banned terms and toggle automated viewer timeouts or message deletions.
- **Engagement Triggers**: Setup custom periodic announcements, milestone goals, and welcome alerts during traffic spikes.
- **Fast, Quota-Optimized Polling**: Adaptive polling (3s when active, 8s when idle) delivers near-instant reactions while allowing for 8+ hours of streaming on a free YouTube API quota.

---

## Prerequisites

1. **Python 3.10+**: Download and install from [Python.org](https://www.python.org/downloads/)
2. **NVIDIA API Key**: Obtain a key from the [NVIDIA Build Console](https://build.nvidia.com/) (Required for LLM reply generation)
3. **Google API Credentials**: Download client secrets for Desktop Application authentication.

---

## Installation & Running from Source

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/axibot.git
   cd axibot
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Desktop GUI**
   ```bash
   python main_gui.py
   ```

4. **Connect Accounts**:
   - Click **Get Started** to log in to the YouTube Streamer Account (auto-detects channel ID).
   - In Settings, click **Link Bot Account** to authenticate the Bot Account.
   - Go to the Settings tab in AxiBot and add your Nvidia API Key.
5. **Go Live**: Head to the dashboard and click **Start Bot Engine**.

---

## Configuration & OAuth Setup

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

## Critical Rule: Make Bot Account a Moderator

To allow AxiBot to perform moderation actions (deleting spam comments, timing out viewers, banning trolls):
**You MUST make the Bot Account a Moderator on the Streamer's YouTube Channel.**

1. Visit the [YouTube Creator Studio](https://studio.youtube.com/) of the Streamer account.
2. Go to **Settings** &rarr; **Community** &rarr; **Automated Filters**.
3. Under the **Managing Moderators** section, paste the YouTube Channel URL of your Bot Account.
4. Save the changes.

---

## Packaging and Build Automation

### Compile standalone directory
To bundle the Python application into a single executable folder:
```bash
python build.py
```
This cleans the workspace and compiles the executable at `dist/AxiBot/AxiBot.exe`. Make sure `client_secret.json` and `.env` are present in the same folder as the binary when launching.

### Generate Standalone Setup Installer (.exe)
If Inno Setup is installed on your system, running `python build.py` will automatically compile a standalone setup installer wizard (`dist-installer/AxiBotSetup.exe`) that installs the application per-user without requiring administrative rights.

---

## Troubleshooting

- **Google OAuth Login Warning**: If Google warns that the app is unverified during sign-in, click **Advanced** -> **Go to AxiBot (unsafe)** to proceed. This is standard for local testing apps.
- **Bot is reading but not posting replies**: Double-check that your Bot Account is linked in the Settings tab, and that it has been granted Moderator rights on the Streamer's channel.
- **SQLite Database Locked or Write Permissions Error**: Ensure the application is installed in a directory where it has write permissions (like `AppData/Local/Programs/AxiBot/` or a local development folder). Installing to `Program Files` is not recommended unless running as administrator.
- **API Key Invalid Error**: Ensure you have a valid Nvidia NIM API key pasted in the settings tab and that you have selected a valid model ID (e.g. `google/gemma-3n-e2b-it`).

---

## Contact Support

If you encounter any issues or have questions, please reach out:
- **YouTube Channel**: [@TexaPlayzYT](https://www.youtube.com/@TexaPlayzYT)
- **Discord**: `.dhanuz_`
