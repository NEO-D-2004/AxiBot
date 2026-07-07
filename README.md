# AxiBot - AI YouTube Moderator & Live Assistant

AxiBot is a smart, privacy-focused YouTube Live Chat bot powered by the NVIDIA NIM Inference API (using models such as Qwen 3.5). It moderates chat, welcomes subscribers, engages viewers, and tracks stream goals like a human moderator—all optimized for low latency and minimal YouTube API quota usage.

AxiBot features a dark-themed glassmorphic desktop GUI dashboard built with PyWebView for easy configuration, visual log streaming, database management, and engine control.

---

## Features

- **Desktop GUI Dashboard**: A dark-themed dashboard to monitor bot status, live viewer metrics, likes goals, subscriber counts, and real-time logs.
- **High-Performance Intelligence**: Integrates NVIDIA NIM API to run top-tier open-source LLMs (like Qwen 3.5 or GPT-OSS) with extremely low response latency.
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

1. **NVIDIA API Key**: Obtain a key from the [NVIDIA Build Console](https://build.nvidia.com/) (Required for LLM reply generation).
2. **Google API Credentials (Optional)**: If you run your own client secret for custom API limits.

---

## Installation & Setup

1. **Download the Setup Program**
   - Head to the **Releases** section on the GitHub repository.
   - Download the latest `AxiBotSetup.exe` installer file from the Assets section.

2. **Run the Installer Wizard**
   - Double-click the downloaded `AxiBotSetup.exe` to run the setup.
   - Follow the steps in the wizard. It is recommended to check the option to **Create a desktop shortcut** before completing the installation.
   - Upon finish, the application will automatically launch, and a quick-start guide text file will open in your default editor.

3. **Get YouTube OAuth Credentials (Optional)**
   - By default, AxiBot is ready to link. If you need higher API quota limits, you can download your own Google API client secrets.
   - Follow the step-by-step instructions in the **Configuration & OAuth Setup** section below to obtain a `client_secret.json` file.
   - Copy your `client_secret.json` file and paste it directly into the AxiBot installation directory:
     `C:\Users\<YourUsername>\AppData\Local\Programs\AxiBot\` (or type `%LocalAppData%\Programs\AxiBot` in Windows Run dialog).

4. **Link Your YouTube Accounts**
   - Launch AxiBot from your Desktop or Start Menu shortcut.
   - On the landing screen, click **Get Started** to authenticate your main YouTube Streamer Channel in your browser. This automatically configures AxiBot to listen to your stream's live chat.
   - Once the dashboard loads, navigate to the **Settings** tab.
   - Under the **YouTube Connections** section, click **Link Bot Account** to authenticate your secondary Bot account (the account that will post the AI comments).

5. **Assign Bot as Moderator**
   - To let the bot account perform actions (like timing out users or deleting spam), you **must** assign the Bot account as a moderator on the Streamer's YouTube Creator Studio (instructions in the section below).

6. **Add NVIDIA API Key and Go Live**
   - In the Settings tab, paste your **Nvidia API Key** (required for LLM reply generation).
   - Go to the **Dashboard** and click **Start Bot Engine**. AxiBot is now active and monitoring your stream!

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
   NVIDIA_MODEL_ID=qwen/qwen3.5-122b-a10b
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



## Troubleshooting

- **Google OAuth Login Warning**: If Google warns that the app is unverified during sign-in, click **Advanced** -> **Go to AxiBot (unsafe)** to proceed. This is standard for local testing apps.
- **Bot is reading but not posting replies**: Double-check that your Bot Account is linked in the Settings tab, and that it has been granted Moderator rights on the Streamer's channel.
- **SQLite Database Locked or Write Permissions Error**: Ensure the application is installed in a directory where it has write permissions (like `AppData/Local/Programs/AxiBot/` or a local development folder). Installing to `Program Files` is not recommended unless running as administrator.
- **API Key Invalid Error**: Ensure you have a valid Nvidia NIM API key pasted in the settings tab and that you have selected a valid model ID (e.g. `qwen/qwen3.5-122b-a10b`).

---

## Contact Support

If you encounter any issues or have questions, please reach out:
- **YouTube Channel**: [@TexaPlayzYT](https://www.youtube.com/@TexaPlayzYT)
- **Discord**: `.dhanuz_`
