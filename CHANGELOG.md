# Changelog - AxiBot

All notable changes, new features, and visual panels added to AxiBot are documented in this file.

---

## [1.3.0] - 2026-07-07

### Added
* **Interactive Chat Economy (Loyalty Points)**:
  * Viewers now earn **10 AxiCoins** automatically for each valid message they contribute to the live chat.
  * Added default commands:
    * `!axicoins`: Displays the user's active point balance.
    * `!axitop` / `!axileaderboard`: Shows a leaderboard of the top 3 wealthiest chatters on the stream.
  * Exposed points balances in the **Database** panel table. Streamers can manually adjust or award points to any viewer using the Edit Viewer modal.
* **Custom Commands Manager**:
  * Created a dedicated **Commands** manager tab in the sidebar layout.
  * Streamers can now design, edit, and delete custom triggers (e.g. `!discord`, `!socials`) that output automated responses in YouTube chat.
  * Intercepted triggers are fetched from the database and resolved instantly, bypassing LLM queries to optimize API quotas.
  * Supports placeholders:
    * `{user}`: Mentions the viewer who typed the trigger.
    * `{count}`: Prints the total usage count of the command.
  * Added an **Enable Custom Commands** toggle switch in the tab header to activate or deactivate the commands feature globally.
  * Changed the command creation panel into a visual **"+ Create Command"** button that opens a glassmorphic overlay editor modal.
* **Stream VOD Clip & Highlight Marker**:
  * Intercepts `!clip` and `!highlight` command triggers in live chat.
  * Automatically resolves the stream's `actualStartTime` using the YouTube API, calculating the exact time offset in `HH:MM:SS` format.
  * Marks VOD clips with a confirmation chat message back to the viewer: `"@{user} Added Clip at [HH:MM:SS]"`.
  * Created a dedicated **Highlights** tab inside the sidebar to monitor and copy logged highlights.
  * Clickable offset anchors: Clicking the timestamp offset in the highlights log table deep-links directly to the VOD on YouTube (`https://www.youtube.com/watch?v=VIDEO_ID&t=Xs`) at the exact moment the clip was recorded.
  * Added **Copy Link**, **Copy Stamp**, and **Clear Logs** clipboard buttons inside the dashboard panel.
* **AI Radio Co-Host (Speech Synthesis)**:
  * Added `!radio <query>` command trigger costing **100 AxiCoins** with a global **30-second cooldown** to prevent viewer spam.
  * Injects query into a custom Nvidia NIM LLM co-host context, producing a clean, broadcast-safe Tamil-English (Tanglish) speech script.
  * Links to a dedicated **Radio** panel tab inside the dashboard.
  * Plays announcements on-stream using the Web Speech Synthesis API inside PyWebView, with volume, ducking, style, speed, and pitch parameters.
  * Triggers background Windows `SAPI.SpVoice` PowerShell subprocess speech if the GUI dashboard window is not active.
  * Features an **Emergency Panic Mute button** to immediately silence active audio playback and clear speech synthesis queues.

### Changed
* **Database Schema Migrations**:
  * Added startup SQL migrations in `database.py` that check the SQLite schema and append `points` (for loyalty points) and `video_id` (for clip highlights) columns to their respective tables if missing, preventing database corruption errors.
  * Exposes new API endpoints to the PyWebView wrapper interface to fetch, edit, and clear highlight items.
