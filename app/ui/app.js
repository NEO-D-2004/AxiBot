// AxiBot Dashboard Frontend Logic

// Global state variables
let botRunning = false;
let currentActiveTab = 'tab-dashboard';
let logPoller = null;
let statsPoller = null;
let dbPoller = null;
let allDbUsers = [];
let localBannedWords = [];
let localEngagementMsgs = [];

// Tour State Variables
let tourActive = false;
let tourStep = 0;

const tourSteps = [
  {
    targetId: 'settings-accounts-card',
    text: "Step 1: YouTube Connections. Link your Bot account here. Since you connected your Streamer account, your Streamer Channel ID is registered automatically!",
    placement: 'left',
    tab: 'tab-settings'
  },
  {
    targetId: 'settings-config-card',
    text: "Step 2: Environment Variables. Enter your NVIDIA API key, Display Name, and adjust your user reply cooldown limit.",
    placement: 'right',
    tab: 'tab-settings'
  },
  {
    targetId: 'settings-control-card',
    text: "Step 3: Engine Run Control. Use these buttons to Start, Stop, or Restart the bot engine directly.",
    placement: 'left',
    tab: 'tab-settings'
  },
  {
    targetId: 'nav-moderation',
    text: "Step 4: Moderation. Protect your chat by defining banned words and choosing automated user timeouts or comment deletions.",
    placement: 'right',
    tab: 'tab-moderation'
  },
  {
    targetId: 'nav-engagement',
    text: "Step 5: Engagement Triggers. Setup periodic reminders, Milestones, and Viewer Count spike warnings.",
    placement: 'right',
    tab: 'tab-engagement'
  },
  {
    targetId: 'nav-database',
    text: "Step 6: Viewers Database. Modify AI personality profiles, check message contribution metrics, or edit profiles.",
    placement: 'right',
    tab: 'tab-viewers'
  },
  {
    targetId: 'btn-toggle-bot',
    text: "Step 7: Dashboard. You are all set! Click 'Start Bot Engine' here to go live. Have a great stream!",
    placement: 'bottom',
    tab: 'tab-dashboard'
  }
];

let isAppInitialized = false;

function startApp() {
  if (isAppInitialized) return;
  isAppInitialized = true;
  console.log("AxiBot App Initializing...");
  initApp();
}

// Wait for PyWebView interface to be injected, handling potential race condition
if (window.pywebview && window.pywebview.api) {
  console.log("PyWebView api already injected. Initializing immediately...");
  startApp();
} else {
  // Bind to both window and document events for maximum compatibility
  window.addEventListener('pywebviewready', () => {
    console.log("pywebviewready fired on window. Initializing...");
    startApp();
  });
  document.addEventListener('pywebviewready', () => {
    console.log("pywebviewready fired on document. Initializing...");
    startApp();
  });

  // Polling fallback check
  let pollCount = 0;
  const pollInterval = setInterval(() => {
    pollCount++;
    if (window.pywebview && window.pywebview.api) {
      console.log("PyWebView api detected via polling. Initializing...");
      clearInterval(pollInterval);
      startApp();
    } else if (pollCount > 50) {
      clearInterval(pollInterval);
      console.error("PyWebView API could not be detected after 5 seconds.");
      const statusDesc = document.getElementById('auth-status-desc');
      if (statusDesc) {
        statusDesc.innerText = "Error: Connection to AxiBot backend timed out.";
      }
    }
  }, 100);
}

// App Entry Point
async function initApp() {
  if (!window.pywebview || !window.pywebview.api) {
    console.error("PyWebView API not available.");
    const statusDesc = document.getElementById('auth-status-desc');
    if (statusDesc) {
      statusDesc.innerText = "Error: PyWebView API not ready.";
    }
    return;
  }

  // 0. Check for first-time launch README guide popup
  const isReadmeDone = localStorage.getItem('axibot_readme_done');
  if (!isReadmeDone) {
    const readmeOverlay = document.getElementById('readme-overlay');
    if (readmeOverlay) {
      readmeOverlay.classList.remove('hidden');
    }
  }

  // 1. Check if user is already authenticated
  await checkAuthAndSwitchView();

  // 2. Setup Navigation Tab switches
  setupNavigation();

  // 3. Setup Button Event Handlers
  setupButtonListeners();

  // 4. Setup Form Event Handlers
  setupFormListeners();

  // 5. Setup Search Filters
  setupSearchFilters();
}

/* 1. AUTHENTICATION & VIEW TRANSITIONS */
async function checkAuthAndSwitchView() {
  try {
    const isConnected = await window.pywebview.api.check_auth_status();
    const loginView = document.getElementById('login-view');
    const dashboardView = document.getElementById('dashboard-view');
    const authStatusDesc = document.getElementById('auth-status-desc');
    const sidebarChannel = document.getElementById('sidebar-channel-name');

    if (isConnected) {
      // Transition to Dashboard View
      loginView.classList.add('hidden');
      dashboardView.classList.remove('hidden');
      
      // Load current configuration and data initially
      await loadAllSettings();
      await loadModerationData();
      await loadEngagementData();
      await loadDbUsers();
      
      // Update Streamer Handle pill at bottom
      const config = await window.pywebview.api.get_settings();
      if (config && config.STREAMER_CHANNEL_ID) {
        sidebarChannel.innerText = `@${config.BOT_NAME || 'AxiBot'}`;
      } else {
        sidebarChannel.innerText = "@AxiBot";
      }

      // Start polling for stats and logs
      startPolling();

      // If streamer logged in successfully and tour is not done, auto-trigger tour starting in settings tab
      const isTourDone = localStorage.getItem('axibot_tour_done');
      if (!isTourDone && !tourActive) {
        switchTab('tab-settings');
        startTour();
      }
    } else {
      // Stay on login view
      loginView.classList.remove('hidden');
      dashboardView.classList.add('hidden');
      authStatusDesc.innerText = "AxiBot is currently disconnected. Click 'Get Started' to set up.";
      stopPolling();
    }
  } catch (err) {
    console.error("Error checking auth status:", err);
  }
}

/* 2. TAB NAVIGATION LOGIC */
function setupNavigation() {
  const navItems = document.querySelectorAll('[data-tab]');
  const panels = document.querySelectorAll('.tab-panel');

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      // If a tour is running, block manually switching tabs
      if (tourActive) return;

      const tabId = item.getAttribute('data-tab');
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  const navItems = document.querySelectorAll('[data-tab]');
  const panels = document.querySelectorAll('.tab-panel');

  // Toggle nav item highlight
  navItems.forEach(nav => {
    if (nav.getAttribute('data-tab') === tabId) {
      nav.classList.add('active');
    } else {
      nav.classList.remove('active');
    }
  });

  // Toggle panels
  panels.forEach(panel => {
    if (panel.id === tabId) {
      panel.classList.add('active');
    } else {
      panel.classList.remove('active');
    }
  });

  currentActiveTab = tabId;
  
  // Trigger instant database reload if navigating to users
  if (tabId === 'tab-viewers') {
    loadDbUsers();
  }
}

/* 3. BUTTON CLICK HANDLERS */
function setupButtonListeners() {
  // Landing Get Started Button
  const btnConnect = document.getElementById('btn-connect-youtube');
  const authStatusDesc = document.getElementById('auth-status-desc');

  btnConnect.addEventListener('click', async () => {
    // Direct Connect Flow for Streamer Channel
    await executeYouTubeConnection();
  });

  // README Done Button
  const btnReadmeDone = document.getElementById('btn-readme-done');
  if (btnReadmeDone) {
    btnReadmeDone.addEventListener('click', () => {
      const readmeOverlay = document.getElementById('readme-overlay');
      if (readmeOverlay) {
        readmeOverlay.classList.add('hidden');
      }
      localStorage.setItem('axibot_readme_done', 'true');
    });
  }

  // Sidebar Channel Name Pill -> Disconnect option
  const btnChannelPill = document.getElementById('btn-sidebar-channel');
  btnChannelPill.addEventListener('click', async () => {
    if (confirm("Disconnect account? This deletes the YouTube authentication credentials file.")) {
      if (botRunning) {
        await executeStopBot();
      }
      await window.pywebview.api.disconnect_youtube("streamer");
      await checkAuthAndSwitchView();
    }
  });

  // Start / Stop Bot Engine from Dashboard
  const btnToggleBot = document.getElementById('btn-toggle-bot');
  btnToggleBot.addEventListener('click', async () => {
    btnToggleBot.disabled = true;
    if (!botRunning) {
      await executeStartBot();
    } else {
      await executeStopBot();
    }
    btnToggleBot.disabled = false;
  });

  // Controls from Settings Tab
  const btnSettingsStart = document.getElementById('btn-settings-start');
  const btnSettingsStop = document.getElementById('btn-settings-stop');
  const btnSettingsRestart = document.getElementById('btn-settings-restart');

  btnSettingsStart.addEventListener('click', async () => {
    btnSettingsStart.disabled = true;
    await executeStartBot();
    btnSettingsStart.disabled = false;
  });

  btnSettingsStop.addEventListener('click', async () => {
    btnSettingsStop.disabled = true;
    await executeStopBot();
    btnSettingsStop.disabled = false;
  });

  btnSettingsRestart.addEventListener('click', async () => {
    btnSettingsRestart.disabled = true;
    await executeRestartBot();
    btnSettingsRestart.disabled = false;
  });

  // Clear stdout logs
  const btnClearLogs = document.getElementById('btn-clear-logs');
  btnClearLogs.addEventListener('click', () => {
    const consoleLogs = document.getElementById('console-logs');
    consoleLogs.innerHTML = `<div class="log-line system">[${new Date().toLocaleTimeString()}] Logs cleared by operator.</div>`;
  });

  // Copy stdout logs to clipboard
  const btnCopyLogs = document.getElementById('btn-copy-logs');
  btnCopyLogs.addEventListener('click', () => {
    const consoleLogs = document.getElementById('console-logs');
    navigator.clipboard.writeText(consoleLogs.innerText);
    
    const origText = btnCopyLogs.innerText;
    btnCopyLogs.innerText = "Copied!";
    setTimeout(() => { btnCopyLogs.innerText = origText; }, 1500);
  });

  // Moderation Chips Adding
  const btnAddWord = document.getElementById('btn-add-word');
  const inputBannedWord = document.getElementById('input-banned-word');
  btnAddWord.addEventListener('click', () => {
    const val = inputBannedWord.value.trim().toLowerCase();
    if (val && !localBannedWords.includes(val)) {
      localBannedWords.push(val);
      renderBannedChips();
      inputBannedWord.value = "";
    }
  });

  // Moderation Apply Changes
  const btnSaveModeration = document.getElementById('btn-save-moderation');
  const moderationSaveStatus = document.getElementById('moderation-save-status');
  btnSaveModeration.addEventListener('click', async () => {
    try {
      btnSaveModeration.disabled = true;
      moderationSaveStatus.innerText = "Saving changes...";
      const timeoutDuration = parseInt(document.getElementById('setting-timeout-duration').value) || 300;
      const enableTimeout = document.getElementById('setting-enable-timeout').checked;
      const enableDelete = document.getElementById('setting-enable-delete').checked;

      const rulesData = {
        words: localBannedWords,
        timeout_duration: timeoutDuration,
        enable_timeout: enableTimeout,
        enable_delete: enableDelete
      };

      const res = await window.pywebview.api.save_moderation_rules(rulesData);
      if (res) {
        moderationSaveStatus.innerText = "Applied successfully!";
        setTimeout(() => { moderationSaveStatus.innerText = ""; }, 2500);
      } else {
        moderationSaveStatus.innerText = "Failed to save.";
      }
    } catch (err) {
      console.error(err);
      moderationSaveStatus.innerText = "Execution failed.";
    } finally {
      btnSaveModeration.disabled = false;
    }
  });

  // Engagement Msg Adding
  const btnAddEngMsg = document.getElementById('btn-add-engagement-msg');
  const inputEngMsg = document.getElementById('input-engagement-msg');
  btnAddEngMsg.addEventListener('click', () => {
    const msgText = inputEngMsg.value.trim();
    if (msgText && !localEngagementMsgs.includes(msgText)) {
      localEngagementMsgs.push(msgText);
      renderEngagementMessagesList();
      inputEngMsg.value = "";
    }
  });

  // Force Engagement message
  const btnForceEng = document.getElementById('btn-force-engagement');
  btnForceEng.addEventListener('click', async () => {
    try {
      btnForceEng.disabled = true;
      const res = await window.pywebview.api.force_trigger_engagement();
      if (res) {
        console.log("Forced engagement message successfully.");
      } else {
        alert("Bot is not running or engagement manager not active.");
      }
    } catch (err) {
      console.error(err);
    } finally {
      btnForceEng.disabled = false;
    }
  });

  // Modal Cancel
  const modalEditUser = document.getElementById('modal-edit-user');
  const btnCancelModal = document.getElementById('btn-cancel-modal');
  btnCancelModal.addEventListener('click', () => {
    modalEditUser.classList.add('hidden');
  });

  // Modal Save
  const btnSaveModal = document.getElementById('btn-save-modal');
  btnSaveModal.addEventListener('click', async () => {
    const userId = document.getElementById('edit-user-id').value;
    const nameVal = document.getElementById('edit-user-display-name').value.trim();
    const countVal = document.getElementById('edit-user-message-count').value;
    const summaryVal = document.getElementById('edit-user-summary').value.trim();

    if (userId && nameVal) {
      try {
        btnSaveModal.disabled = true;
        const success = await window.pywebview.api.update_db_user(userId, nameVal, summaryVal, countVal);
        if (success) {
          modalEditUser.classList.add('hidden');
          await loadDbUsers();
        } else {
          alert("Error updating viewer profile.");
        }
      } catch (err) {
        console.error(err);
      } finally {
        btnSaveModal.disabled = false;
      }
    } else {
      alert("Display Name cannot be blank.");
    }
  });

  // Tour Buttons
  document.getElementById('btn-tour-skip').addEventListener('click', () => {
    endTour(true); // skips and forces auth
  });

  document.getElementById('btn-tour-next').addEventListener('click', () => {
    advanceTour();
  });

  // System Maintenance Buttons
  const btnClearCache = document.getElementById('btn-clear-cache');
  if (btnClearCache) {
    btnClearCache.addEventListener('click', async () => {
      if (confirm("Are you sure you want to clear the cached livestream IDs? This will force the bot to search for a new active livestream next time it starts.")) {
        try {
          const success = await window.pywebview.api.clear_stream_cache();
          if (success) {
            alert("Livestream cache cleared successfully!");
          } else {
            alert("Failed to clear cache.");
          }
        } catch (err) {
          console.error(err);
        }
      }
    });
  }

  const btnResetDb = document.getElementById('btn-reset-db');
  if (btnResetDb) {
    btnResetDb.addEventListener('click', async () => {
      if (confirm("WARNING: Are you sure you want to permanently reset the viewers database? This will erase all viewer profiles and message history.")) {
        try {
          const success = await window.pywebview.api.reset_db();
          if (success) {
            alert("Database has been reset successfully!");
            await loadDbUsers();
          } else {
            alert("Failed to reset database.");
          }
        } catch (err) {
          console.error(err);
        }
      }
    });
  }

  // Streamer Link Button
  const btnLinkStreamer = document.getElementById('btn-link-streamer');
  if (btnLinkStreamer) {
    btnLinkStreamer.addEventListener('click', async () => {
      btnLinkStreamer.disabled = true;
      const settingsSaveStatus = document.getElementById('settings-save-status');
      if (settingsSaveStatus) {
        settingsSaveStatus.innerText = "Connecting to Streamer YouTube OAuth...";
      }
      try {
        const result = await window.pywebview.api.connect_youtube("streamer");
        if (result && result.success) {
          if (settingsSaveStatus) {
            settingsSaveStatus.innerText = "Streamer YouTube account linked successfully!";
          }
          await loadAllSettings();
          // Update Streamer Handle pill at bottom
          const config = await window.pywebview.api.get_settings();
          const sidebarChannel = document.getElementById('sidebar-channel-name');
          if (sidebarChannel) {
            if (config && config.STREAMER_CHANNEL_ID) {
              sidebarChannel.innerText = `@${config.BOT_NAME || 'AxiBot'}`;
            } else {
              sidebarChannel.innerText = "@AxiBot";
            }
          }
          setTimeout(() => {
            if (settingsSaveStatus) settingsSaveStatus.innerText = "";
          }, 3000);
        } else {
          const errMsg = (result && result.error) ? result.error : "Unknown connection failure.";
          if (settingsSaveStatus) {
            settingsSaveStatus.innerHTML = `<span style="color:#ef4444; font-weight:600;">${errMsg}</span>`;
          } else {
            alert("OAuth error: " + errMsg);
          }
        }
      } catch (err) {
        console.error(err);
        if (settingsSaveStatus) {
          settingsSaveStatus.innerText = "Fatal: OAuth connection failed.";
        } else {
          alert("OAuth connection failed.");
        }
      } finally {
        btnLinkStreamer.disabled = false;
      }
    });
  }

  // Streamer Unlink Button
  const btnUnlinkStreamer = document.getElementById('btn-unlink-streamer');
  if (btnUnlinkStreamer) {
    btnUnlinkStreamer.addEventListener('click', async () => {
      if (confirm("Disconnect streamer account? This deletes the Streamer YouTube credentials file.")) {
        if (botRunning) {
          await executeStopBot();
        }
        await window.pywebview.api.disconnect_youtube("streamer");
        await loadAllSettings();
        await checkAuthAndSwitchView();
      }
    });
  }

  // Bot Link Button
  const btnLinkBot = document.getElementById('btn-link-bot');
  if (btnLinkBot) {
    btnLinkBot.addEventListener('click', async () => {
      btnLinkBot.disabled = true;
      const settingsSaveStatus = document.getElementById('settings-save-status');
      if (settingsSaveStatus) {
        settingsSaveStatus.innerText = "Connecting to Bot YouTube OAuth...";
      }
      try {
        const result = await window.pywebview.api.connect_youtube("bot");
        if (result && result.success) {
          if (settingsSaveStatus) {
            settingsSaveStatus.innerText = "Bot YouTube account linked successfully!";
          }
          await loadAllSettings();
          setTimeout(() => {
            if (settingsSaveStatus) settingsSaveStatus.innerText = "";
          }, 3000);
        } else {
          const errMsg = (result && result.error) ? result.error : "Unknown connection failure.";
          if (settingsSaveStatus) {
            settingsSaveStatus.innerHTML = `<span style="color:#ef4444; font-weight:600;">${errMsg}</span>`;
          } else {
            alert("OAuth error: " + errMsg);
          }
        }
      } catch (err) {
        console.error(err);
        if (settingsSaveStatus) {
          settingsSaveStatus.innerText = "Fatal: OAuth connection failed.";
        } else {
          alert("OAuth connection failed.");
        }
      } finally {
        btnLinkBot.disabled = false;
      }
    });
  }

  // Bot Unlink Button
  const btnUnlinkBot = document.getElementById('btn-unlink-bot');
  if (btnUnlinkBot) {
    btnUnlinkBot.addEventListener('click', async () => {
      if (confirm("Disconnect bot account? This deletes the Bot YouTube credentials file.")) {
        if (botRunning) {
          await executeStopBot();
        }
        await window.pywebview.api.disconnect_youtube("bot");
        await loadAllSettings();
      }
    });
  }
}

/* 4. SETTINGS FORM SUBMISSIONS */
function setupFormListeners() {
  // Main settings form
  const formSettings = document.getElementById('form-settings');
  const settingsSaveStatus = document.getElementById('settings-save-status');
  formSettings.addEventListener('submit', async (e) => {
    e.preventDefault();
    settingsSaveStatus.innerText = "Saving configuration...";

    const formData = new FormData(formSettings);
    const settingsObj = {};
    formData.forEach((value, key) => {
      settingsObj[key] = value.trim();
    });

    try {
      const success = await window.pywebview.api.save_settings(settingsObj);
      if (success) {
        settingsSaveStatus.innerText = "Settings saved successfully!";
        // Reload handle representation
        const sidebarChannel = document.getElementById('sidebar-channel-name');
        sidebarChannel.innerText = `@${settingsObj.BOT_NAME || 'AxiBot'}`;
        setTimeout(() => { settingsSaveStatus.innerText = ""; }, 3000);
      } else {
        settingsSaveStatus.innerText = "Error: Check your configuration values.";
      }
    } catch (err) {
      console.error(err);
      settingsSaveStatus.innerText = "Fatal: Unable to write config.";
    }
  });

  // Cooldown slider visual synchronization
  const cooldownSlider = document.getElementById('setting-cooldown');
  const cooldownDisplay = document.getElementById('cooldown-val-display');
  cooldownSlider.addEventListener('input', () => {
    cooldownDisplay.innerText = `${cooldownSlider.value}s`;
  });

  // Engagement Settings form
  const formEngagement = document.getElementById('form-engagement-settings');
  const engagementSaveStatus = document.getElementById('engagement-save-status');
  formEngagement.addEventListener('submit', async (e) => {
    e.preventDefault();
    engagementSaveStatus.innerText = "Applying triggers...";
    
    const minVal = parseInt(document.getElementById('setting-min-interval').value) || 300;
    const maxVal = parseInt(document.getElementById('setting-max-interval').value) || 900;
    const thresholdVal = parseInt(document.getElementById('setting-spike-threshold').value) || 8;
    const stepVal = parseInt(document.getElementById('setting-like-target-step').value) || 10;
    const currentTargetVal = parseInt(document.getElementById('setting-like-target').value) || 10;

    const config = {
      fallback_messages: localEngagementMsgs,
      min_interval: minVal,
      max_interval: maxVal,
      viewer_spike_threshold: thresholdVal,
      like_target_step: stepVal,
      like_target: currentTargetVal
    };

    try {
      const success = await window.pywebview.api.save_engagement_settings(config);
      if (success) {
        engagementSaveStatus.innerText = "Triggers applied successfully!";
        setTimeout(() => { engagementSaveStatus.innerText = ""; }, 3000);
      } else {
        engagementSaveStatus.innerText = "Failed to save.";
      }
    } catch (err) {
      console.error(err);
      engagementSaveStatus.innerText = "Error applying settings.";
    }
  });
}

/* 5. SEARCH VIEWER DATABASE */
function setupSearchFilters() {
  const searchInput = document.getElementById('search-viewers');
  searchInput.addEventListener('input', () => {
    const query = searchInput.value.trim().toLowerCase();
    renderViewerTable(query);
  });
}

/* API DATA LOADING FUNCTIONS */
async function loadAllSettings() {
  try {
    const config = await window.pywebview.api.get_settings();
    
    document.getElementById('setting-bot-name').value = config.BOT_NAME || "AxiBot";
    document.getElementById('setting-channel-id').value = config.STREAMER_CHANNEL_ID || "";
    
    const hiddenChInput = document.getElementById('setting-channel-id-hidden');
    if (hiddenChInput) {
      hiddenChInput.value = config.STREAMER_CHANNEL_ID || "";
    }

    document.getElementById('setting-api-key').value = config.NVIDIA_API_KEY || "";
    document.getElementById('setting-model-id').value = config.NVIDIA_MODEL_ID || "google/gemma-3n-e2b-it";
    
    const cooldownVal = parseInt(config.COOLDOWN_SECONDS || 60);
    document.getElementById('setting-cooldown').value = cooldownVal;
    document.getElementById('cooldown-val-display').innerText = `${cooldownVal}s`;

    // Render Streamer Connection Badge
    const statusStreamerBadge = document.getElementById('status-streamer-badge');
    if (statusStreamerBadge) {
      if (config.STREAMER_CONNECTED) {
        statusStreamerBadge.innerText = "Connected";
        statusStreamerBadge.style.background = "rgba(16, 185, 129, 0.15)";
        statusStreamerBadge.style.color = "#10b981";
        statusStreamerBadge.style.border = "1px solid rgba(16, 185, 129, 0.2)";
      } else {
        statusStreamerBadge.innerText = "Disconnected";
        statusStreamerBadge.style.background = "rgba(239, 68, 68, 0.15)";
        statusStreamerBadge.style.color = "#ef4444";
        statusStreamerBadge.style.border = "1px solid rgba(239, 68, 68, 0.2)";
      }
    }

    // Render Bot Connection Badge
    const statusBotBadge = document.getElementById('status-bot-badge');
    if (statusBotBadge) {
      if (config.BOT_CONNECTED) {
        statusBotBadge.innerText = "Connected";
        statusBotBadge.style.background = "rgba(16, 185, 129, 0.15)";
        statusBotBadge.style.color = "#10b981";
        statusBotBadge.style.border = "1px solid rgba(16, 185, 129, 0.2)";
      } else {
        statusBotBadge.innerText = "Disconnected";
        statusBotBadge.style.background = "rgba(239, 68, 68, 0.15)";
        statusBotBadge.style.color = "#ef4444";
        statusBotBadge.style.border = "1px solid rgba(239, 68, 68, 0.2)";
      }
    }
  } catch (err) {
    console.error("Error loading settings:", err);
  }
}

async function loadModerationData() {
  try {
    const data = await window.pywebview.api.get_moderation_rules();
    
    localBannedWords = data.words || [];
    document.getElementById('setting-timeout-duration').value = data.timeout_duration || 300;
    document.getElementById('setting-enable-timeout').checked = data.enable_timeout !== false;
    document.getElementById('setting-enable-delete').checked = data.enable_delete !== false;
    
    renderBannedChips();
  } catch (err) {
    console.error("Error loading moderation words:", err);
  }
}

async function loadEngagementData() {
  try {
    const data = await window.pywebview.api.get_engagement_settings();
    localEngagementMsgs = data.fallback_messages || [];
    
    document.getElementById('setting-min-interval').value = data.min_interval || 300;
    document.getElementById('setting-max-interval').value = data.max_interval || 900;
    document.getElementById('setting-spike-threshold').value = data.viewer_spike_threshold || 8;
    document.getElementById('setting-like-target-step').value = data.like_target_step || 10;
    document.getElementById('setting-like-target').value = data.like_target || 10;
    
    renderEngagementMessagesList();
  } catch (err) {
    console.error("Error loading engagement configurations:", err);
  }
}

function renderBannedChips() {
  const container = document.getElementById('banned-words-container');
  container.innerHTML = "";
  
  if (localBannedWords.length === 0) {
    container.innerHTML = `<span style="font-size:12px; color:var(--text-muted);">No blocked phrases configured. Add one above.</span>`;
    return;
  }

  localBannedWords.forEach((word, idx) => {
    const chip = document.createElement('span');
    chip.className = 'chip';
    chip.innerHTML = `
      <span>${word}</span>
      <button class="chip-close" data-index="${idx}">&times;</button>
    `;
    container.appendChild(chip);
  });

  // Bind close buttons
  container.querySelectorAll('.chip-close').forEach(btn => {
    btn.addEventListener('click', () => {
      const index = parseInt(btn.getAttribute('data-index'));
      localBannedWords.splice(index, 1);
      renderBannedChips();
    });
  });
}

function renderEngagementMessagesList() {
  const listContainer = document.getElementById('engagement-msgs-list');
  listContainer.innerHTML = "";

  if (localEngagementMsgs.length === 0) {
    listContainer.innerHTML = `<div style="padding: 20px; font-size:13px; color:var(--text-muted); text-align:center;">No fallback messages configured. Add one above.</div>`;
    return;
  }

  localEngagementMsgs.forEach((msg, idx) => {
    const div = document.createElement('div');
    div.className = 'engagement-msg-item';
    div.innerHTML = `
      <span class="engagement-msg-text">${msg}</span>
      <button class="btn-msg-delete" data-index="${idx}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
      </button>
    `;
    listContainer.appendChild(div);
  });

  // Bind delete buttons
  listContainer.querySelectorAll('.btn-msg-delete').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.getAttribute('data-index'));
      localEngagementMsgs.splice(idx, 1);
      renderEngagementMessagesList();
    });
  });
}

async function loadDbUsers() {
  try {
    allDbUsers = await window.pywebview.api.get_db_users();
    renderViewerTable();
  } catch (err) {
    console.error("Error loading SQLite users:", err);
  }
}

function renderViewerTable(filterQuery = "") {
  const tbody = document.getElementById('viewer-table-body');
  tbody.innerHTML = "";

  const filtered = allDbUsers.filter(u => {
    const name = (u.display_name || "").toLowerCase();
    const sum = (u.personality_summary || "").toLowerCase();
    return name.includes(filterQuery) || sum.includes(filterQuery);
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center pad-all">No matching viewer records found.</td></tr>`;
    return;
  }

  filtered.forEach(u => {
    let lastSeenStr = "Never";
    if (u.last_seen) {
      try {
        const dt = new Date(u.last_seen);
        lastSeenStr = dt.toLocaleString();
      } catch (err) {
        lastSeenStr = u.last_seen;
      }
    }

    const row = document.createElement('tr');
    row.innerHTML = `
      <td style="font-weight:600;">${u.display_name || "Unknown"}</td>
      <td style="font-size:12px; color:var(--text-muted);">${lastSeenStr}</td>
      <td class="text-center" style="font-weight:500;">${u.message_count || 0}</td>
      <td style="font-size:13px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${u.personality_summary || ''}">${u.personality_summary || 'No memory recorded.'}</td>
      <td class="text-right">
        <div class="action-buttons-cell">
          <button class="action-link btn-edit-summary" data-id="${u.user_id}" data-name="${u.display_name}" data-count="${u.message_count || 0}" data-summary="${u.personality_summary}">Edit</button>
          <button class="action-link delete btn-delete-user" data-id="${u.user_id}" data-name="${u.display_name}">Delete</button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });

  // Bind edit action click
  tbody.querySelectorAll('.btn-edit-summary').forEach(btn => {
    btn.addEventListener('click', () => {
      const uid = btn.getAttribute('data-id');
      const uname = btn.getAttribute('data-name');
      const ucount = btn.getAttribute('data-count');
      const usum = btn.getAttribute('data-summary');

      document.getElementById('edit-user-id').value = uid;
      document.getElementById('edit-user-subtitle').innerText = `User ID: ${uid}`;
      document.getElementById('edit-user-display-name').value = uname;
      document.getElementById('edit-user-message-count').value = ucount;
      document.getElementById('edit-user-summary').value = usum;

      document.getElementById('modal-edit-user').classList.remove('hidden');
    });
  });

  // Bind delete action click
  tbody.querySelectorAll('.btn-delete-user').forEach(btn => {
    btn.addEventListener('click', async () => {
      const uid = btn.getAttribute('data-id');
      const uname = btn.getAttribute('data-name');
      if (confirm(`Are you sure you want to permanently delete viewer ${uname} from the database?`)) {
        try {
          const success = await window.pywebview.api.delete_db_user(uid);
          if (success) {
            await loadDbUsers();
          } else {
            alert("Failed to delete user.");
          }
        } catch (err) {
          console.error(err);
        }
      }
    });
  });
}

/* CORE RUN ENGINE CONTROLLERS */
async function executeStartBot() {
  try {
    const started = await window.pywebview.api.start_bot();
    if (started) {
      syncBotRunningUI(true);
      console.log("Bot engine has successfully initialized and is listening to live chat.");
    } else {
      alert("Failed to start bot. Check your Streamer Channel ID or API Key in Settings.");
    }
  } catch (err) {
    console.error(err);
  }
}

async function executeStopBot() {
  try {
    await window.pywebview.api.stop_bot();
    syncBotRunningUI(false);
    console.log("Bot engine has been stopped.");
  } catch (err) {
    console.error(err);
  }
}

async function executeRestartBot() {
  try {
    console.log("Restarting engine via settings...");
    const started = await window.pywebview.api.restart_bot();
    if (started) {
      syncBotRunningUI(true);
      console.log("Bot engine has successfully restarted.");
    } else {
      syncBotRunningUI(false);
      alert("Failed to start bot after restart. Check settings.");
    }
  } catch (err) {
    console.error(err);
  }
}

function syncBotRunningUI(running) {
  botRunning = running;
  
  // Dashboard indicators
  const btnToggle = document.getElementById('btn-toggle-bot');
  const btnToggleText = document.getElementById('btn-toggle-bot-text');
  const botPulse = document.getElementById('bot-pulse');

  // Settings indicators
  const settingsStatusText = document.getElementById('settings-engine-status-text');

  if (running) {
    btnToggle.className = "btn btn-primary stop-state";
    btnToggleText.innerText = "Stop Bot Engine";
    botPulse.className = "pulse-indicator green";

    settingsStatusText.innerText = "Running";
    settingsStatusText.className = "engine-status-text status-running";
  } else {
    btnToggle.className = "btn btn-primary start-state";
    btnToggleText.innerText = "Start Bot Engine";
    botPulse.className = "pulse-indicator";

    settingsStatusText.innerText = "Stopped";
    settingsStatusText.className = "engine-status-text status-stopped";
  }
}

/* POLLING SYSTEMS */
function startPolling() {
  stopPolling();

  // 1. Poll logs every 2 seconds
  logPoller = setInterval(async () => {
    try {
      const logs = await window.pywebview.api.get_logs();
      renderLogs(logs);
    } catch (err) {
      console.error(err);
    }
  }, 2000);

  // 2. Poll statistics every 4 seconds
  statsPoller = setInterval(async () => {
    try {
      const status = await window.pywebview.api.get_bot_status();
      updateDashboardStats(status);
    } catch (err) {
      console.error(err);
    }
  }, 4000);

  // 3. Poll viewer db updates every 10 seconds if active tab
  dbPoller = setInterval(async () => {
    if (currentActiveTab === 'tab-viewers') {
      await loadDbUsers();
    }
  }, 10000);
}

function stopPolling() {
  if (logPoller) clearInterval(logPoller);
  if (statsPoller) clearInterval(statsPoller);
  if (dbPoller) clearInterval(dbPoller);
  
  logPoller = null;
  statsPoller = null;
  dbPoller = null;
}

function renderLogs(logs) {
  const consoleBody = document.getElementById('console-logs');
  
  if (logs.length > 0) {
    consoleBody.innerHTML = "";
    
    logs.forEach(log => {
      const line = document.createElement('div');
      line.className = 'log-line';
      
      if (log.includes("Bot Context-Aware Reply") || log.includes("Engagement Triggered")) {
        line.classList.add('outgoing');
      } else if (log.includes("[Router Parse]") || log.includes("explicitly mentioned")) {
        line.classList.add('incoming');
      } else if (log.includes("Error") || log.includes("CRITICAL") || log.includes("WARNING") || log.includes("failed")) {
        line.classList.add('error');
      } else {
        line.classList.add('system');
      }
      
      line.innerText = log;
      consoleBody.appendChild(line);
    });
    
    consoleBody.scrollTop = consoleBody.scrollHeight;
  }
}

function updateDashboardStats(statusObj) {
  syncBotRunningUI(statusObj.running);

  const stats = statusObj.stats;
  document.getElementById('stat-viewers').innerText = stats.viewers || 0;
  document.getElementById('stat-likes').innerText = stats.likes || 0;
  document.getElementById('stat-subs').innerText = stats.subs || 0;
  document.getElementById('stat-processed').innerText = stats.messages_processed || 0;
  
  const likesGoal = Math.ceil((stats.likes + 1) / 10) * 10;
  document.getElementById('stat-likes-trend').innerText = `Goal: ${likesGoal}`;
}

/* 13. GUIDED Setup TOUR WIZARD ENGINE */
function startTour() {
  tourActive = true;
  tourStep = 0;
  
  // Show Tour Overlay
  const overlay = document.getElementById('tour-overlay');
  overlay.classList.remove('hidden');
  
  renderTourStep();
}

function renderTourStep() {
  if (!tourActive) return;
  
  // Remove previous highlights
  document.querySelectorAll('.tour-highlight').forEach(el => {
    el.classList.remove('tour-highlight');
  });
  
  const stepObj = tourSteps[tourStep];
  const overlay = document.getElementById('tour-overlay');
  
  // Update step text and counter
  document.getElementById('tour-step-counter').innerText = `Step ${tourStep + 1} of ${tourSteps.length}`;
  document.getElementById('tour-text').innerText = stepObj.text;
  
  // Handle tab switching if required by step
  if (stepObj.tab) {
    switchTab(stepObj.tab);
  }
  
  // Highlight target element
  const targetEl = document.getElementById(stepObj.targetId);
  if (targetEl) {
    targetEl.classList.add('tour-highlight');
  }

  // Next Button Label Setup
  const btnNext = document.getElementById('btn-tour-next');
  if (tourStep === tourSteps.length - 1) {
    btnNext.innerText = "Finish";
  } else {
    btnNext.innerText = "Next Step";
  }
  
  // Position Tour Dialog relative to highlighted element
  setTimeout(() => positionTourCard(stepObj), 80);
}

function positionTourCard(stepObj) {
  const el = document.getElementById(stepObj.targetId);
  const card = document.getElementById('tour-card-element');
  if (!el || !card) return;
  
  if (stepObj.placement === 'center') {
    card.style.top = '50%';
    card.style.left = '50%';
    card.style.bottom = 'auto';
    card.style.right = 'auto';
    card.style.transform = 'translate(-50%, -50%)';
    return;
  }
  
  const rect = el.getBoundingClientRect();
  card.style.transform = 'none';
  card.style.bottom = 'auto';
  card.style.right = 'auto';
  
  if (stepObj.placement === 'bottom') {
    card.style.top = `${rect.bottom + 15}px`;
    card.style.left = `${rect.left + (rect.width - 320) / 2}px`;
  } else if (stepObj.placement === 'right') {
    card.style.top = `${rect.top}px`;
    card.style.left = `${rect.right + 20}px`;
  } else if (stepObj.placement === 'left') {
    card.style.top = `${rect.top}px`;
    card.style.left = `${rect.left - 340}px`;
  } else if (stepObj.placement === 'top') {
    card.style.top = `${rect.top - card.offsetHeight - 15}px`;
    card.style.left = `${rect.left + (rect.width - 320) / 2}px`;
  } else {
    card.style.bottom = '30px';
    card.style.right = '30px';
    card.style.top = 'auto';
    card.style.left = 'auto';
  }
  
  // Ensure tour card stays bounded inside view boundaries
  const cardRect = card.getBoundingClientRect();
  if (cardRect.left < 10) card.style.left = '10px';
  if (cardRect.right > window.innerWidth) card.style.left = `${window.innerWidth - 330}px`;
  if (cardRect.top < 10) card.style.top = '10px';
  if (cardRect.bottom > window.innerHeight) card.style.top = `${window.innerHeight - card.offsetHeight - 10}px`;
}

async function advanceTour() {
  if (tourStep < tourSteps.length - 1) {
    tourStep++;
    renderTourStep();
  } else {
    // Last step complete
    endTour(false);
  }
}

function endTour(skipAuth = false) {
  tourActive = false;
  
  // Remove active highlights
  document.querySelectorAll('.tour-highlight').forEach(el => {
    el.classList.remove('tour-highlight');
  });
  
  // Hide Tour overlay
  document.getElementById('tour-overlay').classList.add('hidden');
  
  // Mark tour completed
  localStorage.setItem('axibot_tour_done', 'true');
}

async function executeYouTubeConnection() {
  const btnConnect = document.getElementById('btn-connect-youtube');
  const authStatusDesc = document.getElementById('auth-status-desc');
  
  btnConnect.disabled = true;
  authStatusDesc.innerText = "Opening secure Google Sign-In in your browser...";
  
  try {
    const result = await window.pywebview.api.connect_youtube("streamer");
    if (result && result.success) {
      authStatusDesc.innerText = "Authenticated successfully! Launching...";
      setTimeout(async () => {
        await checkAuthAndSwitchView();
        btnConnect.disabled = false;
      }, 1500);
    } else {
      const errMsg = (result && result.error) ? result.error : "Unknown connection failure.";
      authStatusDesc.innerHTML = `<span style="color:#ef4444; font-weight:600;">${errMsg}</span>`;
      btnConnect.disabled = false;
    }
  } catch (err) {
    console.error(err);
    authStatusDesc.innerText = "Connection Error. Ensure python dependencies are installed.";
    btnConnect.disabled = false;
  }
}

// Adjust positioning of tour card on window resizing
window.addEventListener('resize', () => {
  if (tourActive) {
    positionTourCard(tourSteps[tourStep]);
  }
});
