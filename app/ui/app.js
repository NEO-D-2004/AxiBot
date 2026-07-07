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
    text: "Step 1: YouTube Connections. Check your accounts. Only your Streamer Channel needs to be linked here. AxiBot uses a permanent pre-configured bot account for posting replies.",
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

  // 6. Setup Custom Commands Manager handlers
  setupCommandsForm();

  // 7. Setup Highlights Log handlers
  setupHighlightsControls();

  // 8. Setup Radio Co-Host handlers
  setupRadioHandlers();
}

function updateSidebarChannelPill(config) {
  const sidebarChannel = document.getElementById('sidebar-channel-name');
  const sidebarAvatar = document.getElementById('sidebar-channel-avatar');
  const sidebarDot = document.getElementById('sidebar-channel-dot');
  
  if (!sidebarChannel) return;
  
  if (config && config.STREAMER_CHANNEL_NAME) {
    sidebarChannel.innerText = config.STREAMER_CHANNEL_NAME;
  } else if (config && config.STREAMER_CHANNEL_ID) {
    sidebarChannel.innerText = config.STREAMER_CHANNEL_ID;
  } else {
    sidebarChannel.innerText = "AxiBot";
  }
  
  if (config && config.STREAMER_AVATAR_URL) {
    if (sidebarAvatar) {
      sidebarAvatar.src = config.STREAMER_AVATAR_URL;
      sidebarAvatar.classList.remove('hidden');
    }
    if (sidebarDot) {
      sidebarDot.classList.add('hidden');
    }
  } else {
    if (sidebarAvatar) {
      sidebarAvatar.src = "";
      sidebarAvatar.classList.add('hidden');
    }
    if (sidebarDot) {
      sidebarDot.classList.remove('hidden');
    }
  }
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
      await loadAllCommands();
      await loadHighlights();
      
      // Update Streamer Handle pill at bottom
      const config = await window.pywebview.api.get_settings();
      updateSidebarChannelPill(config);

      // Start polling for stats and logs
      startPolling();

      // If streamer logged in successfully and tour is not done, auto-trigger tour starting in settings tab
      const isTourDone = await window.pywebview.api.check_tour_status();
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
  } else if (tabId === 'tab-commands') {
    loadAllCommands();
  } else if (tabId === 'tab-highlights') {
    loadHighlights();
  } else if (tabId === 'tab-radio') {
    loadRadioState();
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



  // Sidebar Channel Name Pill -> Toggle Logout Popup
  const sidebarUserMenu = document.querySelector('.sidebar-user-menu');
  const btnChannelPill = document.getElementById('btn-sidebar-channel');
  if (btnChannelPill && sidebarUserMenu) {
    btnChannelPill.addEventListener('click', (e) => {
      e.stopPropagation();
      sidebarUserMenu.classList.toggle('active');
    });

    document.addEventListener('click', () => {
      sidebarUserMenu.classList.remove('active');
    });
  }

  // Sidebar Logout Button handler
  const btnSidebarLogout = document.getElementById('btn-sidebar-logout');
  if (btnSidebarLogout) {
    btnSidebarLogout.addEventListener('click', async (e) => {
      e.stopPropagation();
      if (confirm("Disconnect account? This deletes the YouTube authentication credentials file.")) {
        if (botRunning) {
          await executeStopBot();
        }
        await window.pywebview.api.disconnect_youtube("streamer");
        // Clear cached channel name in config
        try {
          const config = await window.pywebview.api.get_settings();
          config["STREAMER_CHANNEL_NAME"] = "";
          config["STREAMER_CHANNEL_ID"] = "";
          await window.pywebview.api.save_settings(config);
        } catch (err) {
          console.error(err);
        }
        if (sidebarUserMenu) {
          sidebarUserMenu.classList.remove('active');
        }
        await checkAuthAndSwitchView();
      }
    });
  }

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
    const pointsVal = document.getElementById('edit-user-points').value || 0;
    const summaryVal = document.getElementById('edit-user-summary').value.trim();

    if (userId && nameVal) {
      try {
        btnSaveModal.disabled = true;
        const success = await window.pywebview.api.update_db_user(userId, nameVal, summaryVal, countVal, pointsVal);
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
          updateSidebarChannelPill(config);
          setTimeout(() => {
            if (settingsSaveStatus) settingsSaveStatus.innerText = "";
          }, 3000);
        } else {
          const errMsg = (result && result.error) ? result.error : "Unknown connection failure.";
          if (settingsSaveStatus) {
            settingsSaveStatus.innerHTML = `<span class="inline-error">${errMsg}</span>`;
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
            settingsSaveStatus.innerHTML = `<span class="inline-error">${errMsg}</span>`;
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

    const enableDbCheckbox = document.getElementById('setting-enable-database');
    if (enableDbCheckbox) {
      settingsObj["ENABLE_DATABASE"] = enableDbCheckbox.checked ? "True" : "False";
    }

    try {
      const success = await window.pywebview.api.save_settings(settingsObj);
      if (success) {
        settingsSaveStatus.innerText = "Settings saved successfully!";
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

  // Database toggle auto-save
  const enableDbCheckbox = document.getElementById('setting-enable-database');
  if (enableDbCheckbox) {
    enableDbCheckbox.addEventListener('change', async () => {
      try {
        const config = await window.pywebview.api.get_settings();
        config["ENABLE_DATABASE"] = enableDbCheckbox.checked ? "True" : "False";
        await window.pywebview.api.save_settings(config);
      } catch (err) {
        console.error("Failed to auto-save database status:", err);
      }
    });
  }

  // Commands toggle auto-save
  const enableCmdsCheckbox = document.getElementById('setting-enable-commands');
  if (enableCmdsCheckbox) {
    enableCmdsCheckbox.addEventListener('change', async () => {
      try {
        const config = await window.pywebview.api.get_settings();
        config["ENABLE_COMMANDS"] = enableCmdsCheckbox.checked ? "True" : "False";
        await window.pywebview.api.save_settings(config);
      } catch (err) {
        console.error("Failed to auto-save commands status:", err);
      }
    });
  }

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
    
    document.getElementById('setting-channel-id').value = config.STREAMER_CHANNEL_ID || "";
    
    const hiddenChInput = document.getElementById('setting-channel-id-hidden');
    if (hiddenChInput) {
      hiddenChInput.value = config.STREAMER_CHANNEL_ID || "";
    }

    document.getElementById('setting-api-key').value = config.NVIDIA_API_KEY || "";
    const modelSelect = document.getElementById('setting-model-id');
    if (modelSelect) {
      const val = config.NVIDIA_MODEL_ID || "openai/gpt-oss-120b";
      let exists = false;
      for (let i = 0; i < modelSelect.options.length; i++) {
        if (modelSelect.options[i].value === val) {
          exists = true;
          break;
        }
      }
      if (!exists) {
        const opt = document.createElement('option');
        opt.value = val;
        opt.innerHTML = val;
        modelSelect.appendChild(opt);
      }
      modelSelect.value = val;
    }
    
    const cooldownVal = parseInt(config.COOLDOWN_SECONDS || 60);
    document.getElementById('setting-cooldown').value = cooldownVal;
    document.getElementById('cooldown-val-display').innerText = `${cooldownVal}s`;

    const enableDbCheckbox = document.getElementById('setting-enable-database');
    if (enableDbCheckbox) {
      enableDbCheckbox.checked = config.ENABLE_DATABASE !== false;
    }

    const enableCmdsCheckbox = document.getElementById('setting-enable-commands');
    if (enableCmdsCheckbox) {
      enableCmdsCheckbox.checked = config.ENABLE_COMMANDS !== false;
    }

    // Load Radio Settings
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val !== undefined ? val : "";
    };
    const setChecked = (id, boolVal) => {
      const el = document.getElementById(id);
      if (el) el.checked = boolVal === true;
    };

    setVal('setting-radio-provider', config.RADIO_PROVIDER);
    if (typeof populateBrowserVoices === 'function') {
      populateBrowserVoices();
    }
    setVal('setting-radio-voice', config.RADIO_VOICE);
    setVal('setting-radio-language', config.RADIO_LANGUAGE);
    setVal('setting-radio-model-id', config.RADIO_MODEL_ID);

    const speedVal = parseFloat(config.RADIO_SPEED !== undefined ? config.RADIO_SPEED : 1.0);
    const speedEl = document.getElementById('setting-radio-speed');
    if (speedEl) speedEl.value = speedVal;
    const speedLbl = document.getElementById('label-radio-speed');
    if (speedLbl) speedLbl.innerText = `${speedVal.toFixed(2)}x`;

    setVal('setting-radio-pitch', config.RADIO_PITCH);
    setVal('setting-radio-energy', config.RADIO_ENERGY);
    setVal('setting-radio-format', config.RADIO_FORMAT);
    setVal('setting-radio-output-source', config.RADIO_OUTPUT_SOURCE);

    const volVal = parseInt(config.RADIO_VOLUME !== undefined ? config.RADIO_VOLUME : -8);
    const volEl = document.getElementById('setting-radio-volume');
    if (volEl) volEl.value = volVal;
    const volLbl = document.getElementById('label-radio-volume');
    if (volLbl) volLbl.innerText = `${volVal} dB`;

    const duckCheckbox = document.getElementById('setting-radio-duck-audio');
    if (duckCheckbox) duckCheckbox.checked = config.RADIO_DUCK_AUDIO !== false;
    
    setVal('setting-radio-duck-amount', config.RADIO_DUCK_AMOUNT);
    setChecked('setting-radio-auto', config.RADIO_AUTO);
    setChecked('setting-radio-auto-approve', config.RADIO_AUTO_APPROVE);
    setVal('setting-radio-interval', config.RADIO_INTERVAL);

    // Sync state text
    updateRadioStateUI(config.RADIO_ENABLED);

    // Render Streamer Connection Badge
    const statusStreamerBadge = document.getElementById('status-streamer-badge');
    if (statusStreamerBadge) {
      if (config.STREAMER_CONNECTED) {
        statusStreamerBadge.innerText = "Connected";
        statusStreamerBadge.className = "badge badge-connected";
      } else {
        statusStreamerBadge.innerText = "Disconnected";
        statusStreamerBadge.className = "badge badge-disconnected";
      }
    }

    // Render Bot Connection Badge
    const statusBotBadge = document.getElementById('status-bot-badge');
    if (statusBotBadge) {
      if (config.BOT_CONNECTED) {
        statusBotBadge.innerText = "Connected";
        statusBotBadge.className = "badge badge-connected";
      } else {
        statusBotBadge.innerText = "Disconnected";
        statusBotBadge.className = "badge badge-disconnected";
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
    container.innerHTML = `<span class="empty-state">No blocked phrases configured. Add one above.</span>`;
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
    listContainer.innerHTML = `<div class="empty-state padded">No fallback messages configured. Add one above.</div>`;
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
    tbody.innerHTML = `<tr><td colspan="6" class="text-center pad-all">No matching viewer records found.</td></tr>`;
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
      <td class="viewer-name">${u.display_name || "Unknown"}</td>
      <td class="viewer-date">${lastSeenStr}</td>
      <td class="text-center viewer-count">${u.message_count || 0}</td>
      <td class="text-center viewer-points">${u.points || 0}</td>
      <td class="viewer-summary" title="${u.personality_summary || ''}">${u.personality_summary || 'No memory recorded.'}</td>
      <td class="text-right">
        <div class="action-buttons-cell">
          <button class="action-link btn-edit-summary" data-id="${u.user_id}" data-name="${u.display_name}" data-count="${u.message_count || 0}" data-points="${u.points || 0}" data-summary="${u.personality_summary}">Edit</button>
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
      const upts = btn.getAttribute('data-points') || 0;
      const usum = btn.getAttribute('data-summary');

      document.getElementById('edit-user-id').value = uid;
      document.getElementById('edit-user-subtitle').innerText = `User ID: ${uid}`;
      document.getElementById('edit-user-display-name').value = uname;
      document.getElementById('edit-user-message-count').value = ucount;
      document.getElementById('edit-user-points').value = upts;
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
    } else if (currentActiveTab === 'tab-commands') {
      await loadAllCommands();
    } else if (currentActiveTab === 'tab-highlights') {
      await loadHighlights();
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
  window.pywebview.api.mark_tour_done();
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
      authStatusDesc.innerHTML = `<span class="inline-error">${errMsg}</span>`;
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

/* CUSTOM COMMANDS MANAGER HELPER FUNCTIONS */
let localCommands = [];
let editingCommandName = null;

async function loadAllCommands() {
  try {
    localCommands = await window.pywebview.api.get_all_commands();
    renderCommandsTable();
  } catch (err) {
    console.error("Error loading custom commands:", err);
  }
}

function renderCommandsTable() {
  const tbody = document.getElementById('commands-table-body');
  if (!tbody) return;
  tbody.innerHTML = "";

  if (localCommands.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center pad-all">No custom commands created yet. Use the editor to add one.</td></tr>`;
    return;
  }

  localCommands.forEach(cmd => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="viewer-name">!${cmd.command_name}</td>
      <td class="viewer-summary">${cmd.response_text}</td>
      <td class="text-center viewer-count">${cmd.use_count || 0}</td>
      <td class="text-right">
        <div class="action-buttons-cell">
          <button class="action-link btn-edit-command" data-name="${cmd.command_name}" data-response="${cmd.response_text}">Edit</button>
          <button class="action-link delete btn-delete-command" data-name="${cmd.command_name}">Delete</button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });

  // Bind edit action
  tbody.querySelectorAll('.btn-edit-command').forEach(btn => {
    btn.addEventListener('click', () => {
      const name = btn.getAttribute('data-name');
      const response = btn.getAttribute('data-response');

      editingCommandName = name;
      document.getElementById('command-editor-title').innerText = "Edit Command";
      
      const inputName = document.getElementById('input-command-name');
      inputName.value = name;
      inputName.disabled = true;

      document.getElementById('input-command-response').value = response;
      document.getElementById('modal-edit-command').classList.remove('hidden');
    });
  });

  // Bind delete action
  tbody.querySelectorAll('.btn-delete-command').forEach(btn => {
    btn.addEventListener('click', async () => {
      const name = btn.getAttribute('data-name');
      if (confirm(`Are you sure you want to delete command !${name}?`)) {
        try {
          const success = await window.pywebview.api.delete_command(name);
          if (success) {
            await loadAllCommands();
            if (editingCommandName === name) {
              resetCommandEditor();
            }
          } else {
            alert("Failed to delete command.");
          }
        } catch (err) {
          console.error(err);
        }
      }
    });
  });
}

function resetCommandEditor() {
  editingCommandName = null;
  document.getElementById('command-editor-title').innerText = "Create New Command";
  
  const inputName = document.getElementById('input-command-name');
  inputName.value = "";
  inputName.disabled = false;

  document.getElementById('input-command-response').value = "";
  document.getElementById('modal-edit-command').classList.add('hidden');
  document.getElementById('command-save-status').innerText = "";
}

function setupCommandsForm() {
  const form = document.getElementById('form-command-editor');
  if (!form) return;

  const btnCreate = document.getElementById('btn-show-add-command-panel');
  if (btnCreate) {
    btnCreate.addEventListener('click', () => {
      resetCommandEditor();
      document.getElementById('modal-edit-command').classList.remove('hidden');
    });
  }

  const btnCancel = document.getElementById('btn-cancel-command-edit');
  if (btnCancel) {
    btnCancel.addEventListener('click', () => {
      resetCommandEditor();
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const saveStatus = document.getElementById('command-save-status');
    saveStatus.innerText = "Saving command...";

    const nameInput = document.getElementById('input-command-name');
    const nameVal = nameInput.value.trim().toLowerCase().replace(/^!/, "");
    const responseVal = document.getElementById('input-command-response').value.trim();

    if (!nameVal || !responseVal) {
      saveStatus.innerText = "All fields required.";
      return;
    }

    try {
      const success = await window.pywebview.api.save_command(nameVal, responseVal);
      if (success) {
        saveStatus.innerText = "Command saved!";
        resetCommandEditor();
        await loadAllCommands();
        setTimeout(() => { saveStatus.innerText = ""; }, 2500);
      } else {
        saveStatus.innerText = "Failed to save command.";
      }
    } catch (err) {
      console.error(err);
      saveStatus.innerText = "Error communicating with backend.";
    }
  });
}

/* HIGHLIGHTS LOG MANAGER HELPER FUNCTIONS */
let localHighlights = [];

async function loadHighlights() {
  try {
    localHighlights = await window.pywebview.api.get_highlights();
    renderHighlightsTable();
  } catch (err) {
    console.error("Error loading highlights:", err);
  }
}

function renderHighlightsTable() {
  const tbody = document.getElementById('highlights-table-body');
  if (!tbody) return;
  tbody.innerHTML = "";

  if (localHighlights.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center pad-all">No stream VOD clips marked yet. Viewers can type !clip in chat.</td></tr>`;
    return;
  }

  localHighlights.forEach(hl => {
    const row = document.createElement('tr');
    
    let localDateStr = hl.created_at || "";
    if (hl.created_at) {
      try {
        const t = hl.created_at.split(/[- :]/);
        const dateUtc = new Date(Date.UTC(t[0], t[1]-1, t[2], t[3]||0, t[4]||0, t[5]||0));
        localDateStr = dateUtc.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + " " + dateUtc.toLocaleDateString();
      } catch (e) {
        localDateStr = hl.created_at;
      }
    }

    let streamUrl = "";
    if (hl.video_id) {
      streamUrl = `https://www.youtube.com/watch?v=${hl.video_id}&t=${hl.seconds_elapsed || 0}s`;
    }

    let offsetCell = "";
    let copyLinkBtn = "";
    if (streamUrl) {
      offsetCell = `<a href="${streamUrl}" target="_blank" class="highlight-link" style="font-family: monospace; font-size: 14px; font-weight: bold; color: var(--text-accent); text-decoration: underline;" title="Watch highlight on YouTube VOD">[${hl.timestamp}]</a>`;
      copyLinkBtn = `<button class="action-link btn-copy-highlight-link" data-url="${streamUrl}">Copy Link</button>`;
    } else {
      offsetCell = `<span style="font-family: monospace; font-size: 14px; font-weight: bold; color: var(--text-accent);">[${hl.timestamp}]</span>`;
    }

    row.innerHTML = `
      <td class="viewer-name">${offsetCell}</td>
      <td class="viewer-name">@${hl.user_trigger}</td>
      <td class="viewer-summary" style="font-style: italic; opacity: 0.85;">${hl.message_text || "-"}</td>
      <td class="viewer-name" style="font-size: 12px; opacity: 0.7;">${localDateStr}</td>
      <td class="text-right">
        <div class="action-buttons-cell">
          ${copyLinkBtn}
          <button class="action-link btn-copy-highlight" data-timestamp="${hl.timestamp}">Copy Stamp</button>
          <button class="action-link delete btn-delete-highlight" data-id="${hl.id}">Delete</button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });

  // Bind copy link actions
  tbody.querySelectorAll('.btn-copy-highlight-link').forEach(btn => {
    btn.addEventListener('click', () => {
      const url = btn.getAttribute('data-url');
      navigator.clipboard.writeText(url);
      const origText = btn.innerText;
      btn.innerText = "Copied!";
      setTimeout(() => { btn.innerText = origText; }, 1500);
    });
  });

  // Bind copy timestamp actions
  tbody.querySelectorAll('.btn-copy-highlight').forEach(btn => {
    btn.addEventListener('click', () => {
      const stamp = btn.getAttribute('data-timestamp');
      navigator.clipboard.writeText(stamp);
      const origText = btn.innerText;
      btn.innerText = "Copied!";
      setTimeout(() => { btn.innerText = origText; }, 1500);
    });
  });

  // Bind delete action
  tbody.querySelectorAll('.btn-delete-highlight').forEach(btn => {
    btn.addEventListener('click', async () => {
      const highlightId = btn.getAttribute('data-id');
      if (confirm(`Are you sure you want to delete this highlight entry?`)) {
        try {
          const success = await window.pywebview.api.delete_highlight(highlightId);
          if (success) {
            await loadHighlights();
          } else {
            alert("Failed to delete highlight.");
          }
        } catch (err) {
          console.error(err);
        }
      }
    });
  });
}

function setupHighlightsControls() {
  const btnClear = document.getElementById('btn-clear-highlights');
  if (btnClear) {
    btnClear.addEventListener('click', async () => {
      if (confirm("Are you sure you want to clear all highlight VOD clips from the database? This cannot be undone.")) {
        try {
          const success = await window.pywebview.api.clear_highlights();
          if (success) {
            await loadHighlights();
          } else {
            alert("Failed to clear highlights log.");
          }
        } catch (err) {
          console.error(err);
        }
      }
    });
  }
}

/* RADIO CO-HOST CLIENT HANDLERS & TTS ENGINE */
let radioQueue = [];
let radioLogs = [];

window.playRadioTTS = function(text) {
  console.log("Speaking text via browser synthesis:", text);
  const indicator = document.getElementById('radio-state-indicator');
  const stateText = document.getElementById('radio-state-text');
  const activeMarquee = document.getElementById('radio-active-marquee');
  
  if (indicator && stateText) {
    indicator.style.background = "#4caf50";
    stateText.innerText = "Speaking";
    stateText.style.color = "#4caf50";
  }
  if (activeMarquee) {
    activeMarquee.innerText = text;
  }

  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    
    const speed = parseFloat(document.getElementById('setting-radio-speed').value) || 1.0;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = speed;
    
    const voices = window.speechSynthesis.getVoices();
    const selectedVoiceName = document.getElementById('setting-radio-voice').value;
    const voiceObj = voices.find(v => v.name === selectedVoiceName);
    if (voiceObj) {
      utterance.voice = voiceObj;
    }
    
    utterance.onend = function() {
      resetRadioPlayStateUI();
    };
    utterance.onerror = function() {
      resetRadioPlayStateUI();
    };

    window.speechSynthesis.speak(utterance);
  } else {
    console.warn("Speech synthesis API not supported in this browser.");
    setTimeout(resetRadioPlayStateUI, 2000);
  }
};

async function resetRadioPlayStateUI() {
  const activeMarquee = document.getElementById('radio-active-marquee');
  if (activeMarquee) {
    activeMarquee.innerText = "Playback Idle";
  }
  try {
    const config = await window.pywebview.api.get_settings();
    updateRadioStateUI(config.RADIO_ENABLED);
  } catch (e) {
    console.error(e);
  }
}

function updateRadioStateUI(enabled) {
  const indicator = document.getElementById('radio-state-indicator');
  const stateText = document.getElementById('radio-state-text');
  if (indicator && stateText) {
    if (enabled) {
      indicator.style.background = "#4caf50";
      stateText.innerText = "Active";
      stateText.style.color = "#4caf50";
    } else {
      indicator.style.background = "#ff4d4d";
      stateText.innerText = "Stopped";
      stateText.style.color = "#ff4d4d";
    }
  }
}

async function loadRadioState() {
  try {
    radioQueue = await window.pywebview.api.get_radio_queue();
    radioLogs = await window.pywebview.api.get_radio_logs();
    
    const config = await window.pywebview.api.get_settings();
    updateRadioStateUI(config.RADIO_ENABLED);

    renderRadioQueueTable();
    renderRadioLogsTable();
  } catch (err) {
    console.error("Error loading radio state:", err);
  }
}

function renderRadioQueueTable() {
  const tbody = document.getElementById('radio-queue-body');
  if (!tbody) return;
  tbody.innerHTML = "";
  if (radioQueue.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center pad-all">No pending broadcasts in the queue.</td></tr>`;
    return;
  }
  radioQueue.forEach(item => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="viewer-name">${item.source}</td>
      <td class="viewer-summary">${item.text}</td>
      <td><span class="badge badge-connected" style="background: rgba(255, 193, 7, 0.15); color: #ffc107; font-size: 11px;">${item.status}</span></td>
      <td class="text-right">
        <div class="action-buttons-cell">
          <button class="action-link btn-approve-broadcast" data-id="${item.id}" style="color: #4caf50;">Approve & Speak</button>
          <button class="action-link delete btn-delete-queue" data-id="${item.id}">Delete</button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });

  tbody.querySelectorAll('.btn-approve-broadcast').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.getAttribute('data-id'));
      await window.pywebview.api.approve_and_speak(id);
      await loadRadioState();
    });
  });

  tbody.querySelectorAll('.btn-delete-queue').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = parseInt(btn.getAttribute('data-id'));
      await window.pywebview.api.delete_queue_item(id);
      await loadRadioState();
    });
  });
}

function renderRadioLogsTable() {
  const tbody = document.getElementById('radio-logs-body');
  if (!tbody) return;
  tbody.innerHTML = "";
  if (radioLogs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="text-center pad-all">No history logged yet.</td></tr>`;
    return;
  }
  radioLogs.forEach(item => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td class="viewer-name" style="font-family: monospace; font-size: 12px;">${item.time || "-"}</td>
      <td class="viewer-name">${item.source}</td>
      <td class="viewer-summary" style="font-style: italic; opacity: 0.85;">${item.text}</td>
      <td><span class="badge badge-connected" style="font-size: 11px;">${item.status}</span></td>
    `;
    tbody.appendChild(row);
  });
}

function setupRadioHandlers() {
  const speedSlider = document.getElementById('setting-radio-speed');
  const speedLabel = document.getElementById('label-radio-speed');
  if (speedSlider && speedLabel) {
    speedSlider.addEventListener('input', () => {
      const v = parseFloat(speedSlider.value);
      speedLabel.innerText = `${v.toFixed(2)}x`;
    });
  }

  const volSlider = document.getElementById('setting-radio-volume');
  const volLabel = document.getElementById('label-radio-volume');
  if (volSlider && volLabel) {
    volSlider.addEventListener('input', () => {
      const v = parseInt(volSlider.value);
      volLabel.innerText = `${v} dB`;
    });
  }

  const btnSave = document.getElementById('btn-save-radio-settings');
  if (btnSave) {
    btnSave.addEventListener('click', async () => {
      btnSave.disabled = true;
      try {
        const config = await window.pywebview.api.get_settings();
        
        config.RADIO_PROVIDER = document.getElementById('setting-radio-provider').value;
        config.RADIO_VOICE = document.getElementById('setting-radio-voice').value;
        config.RADIO_LANGUAGE = document.getElementById('setting-radio-language').value;
        config.RADIO_MODEL_ID = document.getElementById('setting-radio-model-id').value;
        config.RADIO_SPEED = parseFloat(document.getElementById('setting-radio-speed').value);
        config.RADIO_PITCH = document.getElementById('setting-radio-pitch').value;
        config.RADIO_ENERGY = document.getElementById('setting-radio-energy').value;
        config.RADIO_FORMAT = document.getElementById('setting-radio-format').value;
        config.RADIO_OUTPUT_SOURCE = document.getElementById('setting-radio-output-source').value;
        config.RADIO_VOLUME = parseInt(document.getElementById('setting-radio-volume').value);
        config.RADIO_DUCK_AUDIO = document.getElementById('setting-radio-duck-audio').checked;
        config.RADIO_DUCK_AMOUNT = document.getElementById('setting-radio-duck-amount').value;
        
        config.RADIO_AUTO = document.getElementById('setting-radio-auto').checked;
        config.RADIO_AUTO_APPROVE = document.getElementById('setting-radio-auto-approve').checked;
        config.RADIO_INTERVAL = parseInt(document.getElementById('setting-radio-interval').value);
        
        const success = await window.pywebview.api.save_settings(config);
        if (success) {
          const orig = btnSave.innerText;
          btnSave.innerText = "Saved Voice Configurations!";
          setTimeout(() => { btnSave.innerText = orig; }, 2000);
        } else {
          alert("Failed to save voice configurations.");
        }
      } catch (err) {
        console.error(err);
      } finally {
        btnSave.disabled = false;
      }
    });
  }

  const btnStart = document.getElementById('btn-radio-start');
  if (btnStart) {
    btnStart.addEventListener('click', async () => {
      try {
        const config = await window.pywebview.api.get_settings();
        config.RADIO_ENABLED = true;
        await window.pywebview.api.save_settings(config);
        updateRadioStateUI(true);
      } catch (e) {
        console.error(e);
      }
    });
  }

  const btnStop = document.getElementById('btn-radio-stop');
  if (btnStop) {
    btnStop.addEventListener('click', async () => {
      try {
        const config = await window.pywebview.api.get_settings();
        config.RADIO_ENABLED = false;
        await window.pywebview.api.save_settings(config);
        updateRadioStateUI(false);
        if ('speechSynthesis' in window) {
          window.speechSynthesis.cancel();
        }
        resetRadioPlayStateUI();
      } catch (e) {
        console.error(e);
      }
    });
  }

  const btnPanic = document.getElementById('btn-panic-mute');
  if (btnPanic) {
    btnPanic.addEventListener('click', async () => {
      try {
        await window.pywebview.api.control_playback("panic");
        if ('speechSynthesis' in window) {
          window.speechSynthesis.cancel();
        }
        resetRadioPlayStateUI();
        btnPanic.innerText = "SILENCED!";
        setTimeout(() => { btnPanic.innerText = "EMERGENCY MUTE (PANIC)"; }, 2000);
      } catch (e) {
        console.error(e);
      }
    });
  }

  const btnPause = document.getElementById('btn-radio-pause');
  if (btnPause) {
    btnPause.addEventListener('click', () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.pause();
        document.getElementById('radio-state-text').innerText = "Paused";
      }
    });
  }

  const btnResume = document.getElementById('btn-radio-resume');
  if (btnResume) {
    btnResume.addEventListener('click', () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.resume();
        document.getElementById('radio-state-text').innerText = "Speaking";
      }
    });
  }

  const btnSkip = document.getElementById('btn-radio-skip');
  if (btnSkip) {
    btnSkip.addEventListener('click', () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        resetRadioPlayStateUI();
      }
    });
  }

  const btnReplay = document.getElementById('btn-radio-replay');
  if (btnReplay) {
    btnReplay.addEventListener('click', () => {
      const activeMarquee = document.getElementById('radio-active-marquee');
      if (activeMarquee && activeMarquee.innerText !== "Playback Idle") {
        window.playRadioTTS(activeMarquee.innerText);
      }
    });
  }

  const btnGenerate = document.getElementById('btn-radio-generate');
  const topicInput = document.getElementById('radio-topic-input');
  if (btnGenerate && topicInput) {
    btnGenerate.addEventListener('click', async () => {
      const topic = topicInput.value.trim();
      if (!topic) {
        alert("Please enter a topic or script prompt first!");
        return;
      }
      btnGenerate.disabled = true;
      btnGenerate.innerText = "Generating...";
      try {
        const script = await window.pywebview.api.generate_radio_script(topic);
        topicInput.value = script;
      } catch (e) {
        console.error(e);
      } finally {
        btnGenerate.disabled = false;
        btnGenerate.innerText = "Generate Script";
      }
    });
  }

  const btnPreview = document.getElementById('btn-radio-preview');
  if (btnPreview && topicInput) {
    btnPreview.addEventListener('click', () => {
      const txt = topicInput.value.trim();
      if (!txt) {
        alert("No script to preview. Enter a text or generate one.");
        return;
      }
      window.playRadioTTS(txt);
    });
  }

  const btnBroadcast = document.getElementById('btn-radio-broadcast');
  if (btnBroadcast && topicInput) {
    btnBroadcast.addEventListener('click', async () => {
      const txt = topicInput.value.trim();
      if (!txt) {
        alert("Enter script text before broadcasting.");
        return;
      }
      btnBroadcast.disabled = true;
      try {
        await window.pywebview.api.add_radio_queue_item(txt, "Streamer");
        topicInput.value = "";
        await loadRadioState();
      } catch (e) {
        console.error(e);
      } finally {
        btnBroadcast.disabled = false;
      }
    });
  }

  const providerSelect = document.getElementById('setting-radio-provider');
  if (providerSelect) {
    providerSelect.addEventListener('change', () => {
      populateBrowserVoices();
    });
  }
}

function populateBrowserVoices() {
  const providerSelect = document.getElementById('setting-radio-provider');
  if (!providerSelect) return;
  const provider = providerSelect.value;
  const voiceSelect = document.getElementById('setting-radio-voice');
  if (!voiceSelect) return;

  const currentVal = voiceSelect.value;

  if (provider === "SAPI5 Native Windows") {
    if ('speechSynthesis' in window) {
      const voices = window.speechSynthesis.getVoices();
      if (voices.length > 0) {
        voiceSelect.innerHTML = "";
        voices.forEach(v => {
          const opt = document.createElement('option');
          opt.value = v.name;
          opt.innerText = `${v.name} (${v.lang})`;
          voiceSelect.appendChild(opt);
        });
        if (currentVal && Array.from(voiceSelect.options).some(o => o.value === currentVal)) {
          voiceSelect.value = currentVal;
        }
      }
    }
  } else {
    voiceSelect.innerHTML = `
      <option value="Tamil Gaming Host">Tamil Gaming Host</option>
      <option value="English Host (Male)">English Host (Male)</option>
      <option value="English Host (Female)">English Host (Female)</option>
    `;
    if (currentVal && Array.from(voiceSelect.options).some(o => o.value === currentVal)) {
      voiceSelect.value = currentVal;
    }
  }
}

if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = () => {
    populateBrowserVoices();
  };
}
