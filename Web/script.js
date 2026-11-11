// Wolf AI Code Debugger - Enhanced Edition with Animated Wolf

const state = {
    selectedFiles: [],
    analyzing: false,
    logExpanded: true,
    wolfMood: 'happy', // happy, bored, sleeping, alert
    lastMouseMove: Date.now(),
    mouseX: 0,
    mouseY: 0,
    blinkInterval: null,
    moodInterval: null,
    settings: null,
    cards: [],        // per result card: { file, result, chat: [] }
    gitPath: null     // a file path in the queue's git repo, if any
};

const api = () => window.pywebview.api;

// Wait for Python bridge
window.addEventListener('pywebviewready', () => {
    initializeApp();
    checkSystemHealth();
    initializeAnimatedWolf();
});

function initializeApp() {
    // Element References
    const selectFilesBtn = document.getElementById('selectFilesBtn');
    const selectFolderBtn = document.getElementById('selectFolderBtn');
    const dropZone = document.getElementById('dropZone');
    const executeBtn = document.getElementById('executeBtn');
    const exportBtn = document.getElementById('exportBtn');
    const clearLogBtn = document.getElementById('clearLogBtn');
    const newChatBtn = document.getElementById('newChatBtn');
    const toggleLogBtn = document.getElementById('toggleLogBtn');
    
    // Offline Handlers
    document.getElementById('retryBtn').addEventListener('click', handleRetry);
    document.getElementById('quitBtn').addEventListener('click', () => {
        window.pywebview.api.quit_app();
    });

    // New Chat Handler
    newChatBtn.addEventListener('click', resetDashboard);

    // File Input Handlers
    selectFilesBtn.addEventListener('click', () => {
        window.pywebview.api.select_files().then(handleFolderFiles);
    });

    dropZone.addEventListener('click', () => {
        window.pywebview.api.select_files().then(handleFolderFiles);
    });

    selectFolderBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        window.pywebview.api.select_folder().then(handleFolderFiles);
    });

    // Drag & Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('drag-over');
    });
    
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('drag-over');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('drag-over');
        log('File drop detected, processing...', 'info');
    });

    // Button Actions
    executeBtn.addEventListener('click', startAnalysis);
    exportBtn.addEventListener('click', exportReport);
    clearLogBtn.addEventListener('click', () => {
        document.getElementById('logContent').innerHTML = '';
        log('Activity log cleared', 'info');
    });

    // Toggle Log Handler
    toggleLogBtn.addEventListener('click', toggleActivityLog);

    // Results: one delegated handler for every card's buttons
    document.getElementById('analysisResults').addEventListener('click', handleResultClick);
    document.getElementById('analysisResults').addEventListener('submit', handleChatSubmit);

    // Undo / git
    document.getElementById('revertBtn').addEventListener('click', revertLastFix);
    document.getElementById('commitBtn').addEventListener('click', commitFixes);
    document.getElementById('gitChangedBtn').addEventListener('click', loadGitChangedFiles);

    // Settings
    document.getElementById('settingsBtn').addEventListener('click', openSettings);
    document.getElementById('settingsCloseBtn').addEventListener('click', closeSettings);
    document.getElementById('settingsCancelBtn').addEventListener('click', closeSettings);
    document.getElementById('settingsSaveBtn').addEventListener('click', saveSettings);
    document.getElementById('refreshModelsBtn').addEventListener('click', () => refreshModels(true));
    document.getElementById('clearCacheBtn').addEventListener('click', async () => {
        await api().clear_cache();
        showToast('Saved results cleared', 'success');
        log('Analysis cache cleared', 'info');
    });
    document.getElementById('settingsModal').addEventListener('click', (e) => {
        if (e.target.id === 'settingsModal') closeSettings();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeSettings();
    });
    document.getElementById('temperatureInput').addEventListener('input', (e) => {
        document.getElementById('temperatureValue').textContent = e.target.value;
    });
    document.getElementById('concurrencyInput').addEventListener('input', (e) => {
        document.getElementById('concurrencyValue').textContent = e.target.value;
    });

    // What-to-check toggles save immediately
    document.querySelectorAll('#checkToggles input').forEach(input => {
        input.addEventListener('change', onCheckToggle);
    });

    // A file dropped outside the drop zone must not make the window navigate away from the app.
    // (Python receives the drop through pywebview's DOM events and fills the queue.)
    ['dragover', 'drop'].forEach(type => document.addEventListener(type, e => e.preventDefault()));

    api().get_version().then(v => {
        document.querySelector('.app-subtitle').textContent = `Code Debugger · v${v}`;
    }).catch(() => {});

    loadSettings();
    refreshUndoButton();

    log('Wolf AI initialized successfully', 'success');
}

// ==========================================
// 🐺 ANIMATED WOLF WITH MOODS & BEHAVIORS
// ==========================================

function initializeAnimatedWolf() {
    const pupilLeft = document.getElementById('pupilLeft');
    const pupilRight = document.getElementById('pupilRight');
    
    if (!pupilLeft || !pupilRight) return;

    // Track mouse movement
    document.addEventListener('mousemove', (e) => {
        state.mouseX = e.clientX;
        state.mouseY = e.clientY;
        state.lastMouseMove = Date.now();
        
        // Wake up if sleeping
        if (state.wolfMood === 'sleeping') {
            setWolfMood('alert');
        }
        
        // Move pupils to follow cursor
        movePupil(pupilLeft, state.mouseX, state.mouseY);
        movePupil(pupilRight, state.mouseX, state.mouseY);
    });

    // Start blinking
    startBlinking();
    
    // Start mood changes
    startMoodCycle();
    
    // Check for inactivity
    setInterval(checkInactivity, 5000); // Check every 5 seconds
}

function movePupil(pupil, mouseX, mouseY) {
    const eye = pupil.parentElement;
    const eyeRect = eye.getBoundingClientRect();
    const eyeCenterX = eyeRect.left + eyeRect.width / 2;
    const eyeCenterY = eyeRect.top + eyeRect.height / 2;
    
    // Calculate angle
    const deltaX = mouseX - eyeCenterX;
    const deltaY = mouseY - eyeCenterY;
    const angle = Math.atan2(deltaY, deltaX);
    
    // Calculate distance (limited to eye radius)
    const distance = Math.min(10, Math.sqrt(deltaX * deltaX + deltaY * deltaY) / 25);
    
    // Calculate new pupil position
    const pupilX = Math.cos(angle) * distance;
    const pupilY = Math.sin(angle) * distance;
    
    // Apply transform
    pupil.style.transform = `translate(calc(-50% + ${pupilX}px), calc(-50% + ${pupilY}px))`;
}

function startBlinking() {
    state.blinkInterval = setInterval(() => {
        if (state.wolfMood !== 'sleeping') {
            blink();
        }
    }, 3000 + Math.random() * 4000); // Random between 3-7 seconds
}

function blink() {
    const eyelidLeft = document.getElementById('eyelidLeft');
    const eyelidRight = document.getElementById('eyelidRight');
    
    if (eyelidLeft && eyelidRight) {
        eyelidLeft.classList.add('blinking');
        eyelidRight.classList.add('blinking');
        
        setTimeout(() => {
            eyelidLeft.classList.remove('blinking');
            eyelidRight.classList.remove('blinking');
        }, 200);
    }
}

function startMoodCycle() {
    state.moodInterval = setInterval(() => {
        const timeSinceLastMove = Date.now() - state.lastMouseMove;
        
        // Don't change mood if currently analyzing
        if (state.analyzing) {
            setWolfMood('alert');
            return;
        }
        
        // Random mood changes when active
        if (timeSinceLastMove < 10000) { // Active within last 10 seconds
            const moods = ['happy', 'happy', 'alert', 'bored']; // Happy more likely
            const randomMood = moods[Math.floor(Math.random() * moods.length)];
            setWolfMood(randomMood);
        }
    }, 8000 + Math.random() * 7000); // Random between 8-15 seconds
}

function checkInactivity() {
    const timeSinceLastMove = Date.now() - state.lastMouseMove;
    
    // If no mouse movement for 30 seconds and not analyzing, go to sleep
    if (timeSinceLastMove > 30000 && !state.analyzing && state.wolfMood !== 'sleeping') {
        setWolfMood('sleeping');
    }
}

function setWolfMood(mood) {
    state.wolfMood = mood;
    const wolf = document.getElementById('animatedWolf');
    const smilePath = document.getElementById('smilePath');
    const expression = document.getElementById('wolfExpression');
    
    if (!wolf || !smilePath || !expression) return;
    
    // Remove all mood classes
    wolf.classList.remove('mood-happy', 'mood-bored', 'mood-sleeping', 'mood-alert');
    
    // Add current mood class
    wolf.classList.add(`mood-${mood}`);
    
    // Adjust smile based on mood
    switch(mood) {
        case 'happy':
            smilePath.setAttribute('d', 'M 20 20 Q 50 35 80 20'); // Big smile
            expression.style.display = 'none';
            break;
        case 'bored':
            smilePath.setAttribute('d', 'M 20 30 L 80 30'); // Flat line
            expression.style.display = 'none';
            break;
        case 'sleeping':
            smilePath.setAttribute('d', 'M 20 25 Q 50 30 80 25'); // Small smile
            expression.style.display = 'block';
            closeEyes();
            break;
        case 'alert':
            smilePath.setAttribute('d', 'M 20 25 Q 50 28 80 25'); // Slight smile
            expression.style.display = 'none';
            break;
    }
}

function closeEyes() {
    const eyelidLeft = document.getElementById('eyelidLeft');
    const eyelidRight = document.getElementById('eyelidRight');
    
    if (eyelidLeft && eyelidRight) {
        eyelidLeft.style.top = '0';
        eyelidRight.style.top = '0';
    }
}

function openEyes() {
    const eyelidLeft = document.getElementById('eyelidLeft');
    const eyelidRight = document.getElementById('eyelidRight');
    
    if (eyelidLeft && eyelidRight) {
        eyelidLeft.style.top = '-100%';
        eyelidRight.style.top = '-100%';
    }
}

// ==========================================
// 🔄 NEW CHAT FUNCTIONALITY
// ==========================================

function resetDashboard() {
    // Clear results
    const analysisResults = document.getElementById('analysisResults');
    const welcomeScreen = document.getElementById('welcomeScreen');
    
    analysisResults.style.display = 'none';
    analysisResults.innerHTML = '';
    welcomeScreen.style.display = 'flex';
    
    // Hide export button
    document.getElementById('exportBtn').style.display = 'none';
    
    // Clear log
    document.getElementById('logContent').innerHTML = '';
    
    // Reset state (applied fixes, backups and the git commit list are kept: they're about files on disk)
    state.analyzing = false;
    state.cards = [];
    
    // Reset wolf to happy
    setWolfMood('happy');
    
    // Log the action
    log('New session started', 'system');
    log('Wolf AI initialized successfully', 'success');
    log('Waiting for input files...', 'info');
    
    showToast('New session started', 'success');
}

// ==========================================
// 📂 ACTIVITY LOG TOGGLE (VS CODE STYLE)
// ==========================================

function toggleActivityLog() {
    const activityLog = document.getElementById('activityLog');
    const toggleBtn = document.getElementById('toggleLogBtn');
    const icon = toggleBtn.querySelector('svg polyline');
    
    state.logExpanded = !state.logExpanded;
    
    if (state.logExpanded) {
        activityLog.classList.remove('collapsed');
        icon.setAttribute('points', '18 15 12 9 6 15'); // Up arrow
    } else {
        activityLog.classList.add('collapsed');
        icon.setAttribute('points', '6 9 12 15 18 9'); // Down arrow
    }
}

// ==========================================
// 📡 SYSTEM HEALTH CHECK (Internet + API)
// ==========================================

async function checkSystemHealth() {
    updateConnectionStatus('Checking...', 'checking');
    
    try {
        // Check internet connection
        const isOnline = await window.pywebview.api.check_connection();
        
        if (!isOnline) {
            showOfflineOverlay();
            return;
        }
        
        // Check API key
        const apiValid = await window.pywebview.api.check_api_key();
        
        if (apiValid) {
            document.getElementById('offlineOverlay').style.display = 'none';
            updateConnectionStatus('Brain Active', 'online');
            log('Connection established - Internet & API ready', 'success');
        } else {
            document.getElementById('offlineOverlay').style.display = 'none';
            updateConnectionStatus('Brain Off', 'offline');
            log('Warning: API key not configured or invalid. Add it in Settings.', 'warning');
            showToast('Add your Groq API key in Settings', 'warning');
            if (!state.healthChecked) openSettings();
        }
        
    } catch (error) {
        console.error('System health check failed:', error);
        showOfflineOverlay();
    }
    state.healthChecked = true;
}

function showOfflineOverlay() {
    document.getElementById('offlineOverlay').style.display = 'flex';
    updateConnectionStatus('Brain Off', 'offline');
    log('No internet connection detected', 'error');
}

function handleRetry() {
    const spinner = document.getElementById('offlineSpinner');
    const btnGroup = document.getElementById('offlineBtnGroup');
    
    // Show spinner
    spinner.style.display = 'block';
    btnGroup.style.display = 'none';
    
    // Check connection after delay
    setTimeout(async () => {
        await checkSystemHealth();
        
        // Reset UI
        spinner.style.display = 'none';
        btnGroup.style.display = 'flex';
    }, 1500);
}

function updateConnectionStatus(text, status) {
    const statusElement = document.getElementById('connectionStatus');
    const dot = statusElement.querySelector('.status-dot');
    const label = statusElement.querySelector('.status-label');
    
    label.textContent = text;
    
    // Update dot color based on status
    if (status === 'online') {
        dot.style.background = 'var(--success)';
        dot.style.boxShadow = '0 0 8px var(--success)';
    } else if (status === 'offline') {
        dot.style.background = 'var(--danger)';
        dot.style.boxShadow = '0 0 8px var(--danger)';
    } else {
        dot.style.background = 'var(--warning)';
        dot.style.boxShadow = '0 0 8px var(--warning)';
    }
}

// ==========================================
// 📁 FILE HANDLING
// ==========================================

function handleFolderFiles(files) {
    if (!files || files.length === 0) return;

    let addedCount = 0;
    files.forEach(file => {
        if (!state.selectedFiles.find(f => f.path === file.path)) {
            state.selectedFiles.push(file);
            addedCount++;
        }
    });

    updateFilesList();
    refreshGitPanel();

    if (addedCount > 0) {
        log(`Added ${addedCount} file(s) to queue`, 'info');
        showToast(`${addedCount} files loaded`, 'success');
        setWolfMood('happy');
    } else {
        showToast('Files already in queue', 'warning');
    }
}

function updateFilesList() {
    const container = document.getElementById('selectedFiles');
    
    if (state.selectedFiles.length === 0) {
        container.innerHTML = '<div class="empty-state"><span>No files selected</span></div>';
        return;
    }
    
    container.innerHTML = state.selectedFiles.map((file, index) => `
        <div class="file-item">
            <div class="file-info">
                <div class="file-name">${escapeHtml(file.name)}</div>
                <div class="file-meta">${escapeHtml(file.language)} • ${formatBytes(file.size)}</div>
            </div>
            <button class="file-remove" onclick="removeFile(${index})">×</button>
        </div>
    `).join('');
}

function removeFile(index) {
    const file = state.selectedFiles[index];
    state.selectedFiles.splice(index, 1);
    updateFilesList();
    refreshGitPanel();
    log(`Removed ${file.name} from queue`, 'info');
    showToast('File removed', 'info');
}

// ==========================================
// 🔬 ANALYSIS (parallel)
// ==========================================

async function startAnalysis() {
    if (state.analyzing) return;
    if (state.selectedFiles.length === 0) {
        showToast('Please select files first', 'warning');
        setWolfMood('bored');
        return;
    }

    // Show activity log when execution starts
    const activityLog = document.getElementById('activityLog');
    if (activityLog.classList.contains('collapsed')) {
        toggleActivityLog();
    }

    state.analyzing = true;
    state.cards = [];
    setWolfMood('alert');

    const welcomeScreen = document.getElementById('welcomeScreen');
    const analysisResults = document.getElementById('analysisResults');
    welcomeScreen.style.display = 'none';
    analysisResults.style.display = 'block';
    analysisResults.innerHTML = '';

    const pContainer = document.getElementById('progressContainer');
    const pFill = document.getElementById('progressFill');
    const pPercent = document.getElementById('progressPercent');
    const pText = document.getElementById('progressText');
    pContainer.style.display = 'block';
    document.getElementById('executeBtn').disabled = true;

    const files = [...state.selectedFiles];
    const langOverride = document.getElementById('languageSelect').value;
    const concurrency = Math.max(1, Math.min(5, (state.settings && state.settings.concurrency) || 3));
    const running = new Set();
    let done = 0;
    let next = 0;

    const setProgress = () => {
        const percent = Math.round((done / files.length) * 100);
        pFill.style.width = percent + '%';
        pPercent.textContent = percent + '%';
        const names = [...running].slice(0, 2).join(', ') + (running.size > 2 ? ', …' : '');
        pText.textContent = running.size ? `${done}/${files.length} · ${names}` : `${done}/${files.length}`;
    };
    setProgress();

    log(`Starting code analysis: ${files.length} file(s), ${Math.min(concurrency, files.length)} at a time`, 'system');

    const worker = async () => {
        while (next < files.length) {
            const file = files[next++];
            running.add(file.name);
            setProgress();
            log(`Analyzing ${file.name} [${langOverride === 'auto' ? file.language : langOverride}]`, 'info');
            try {
                const result = await api().start_analysis(file.path, langOverride);
                displayResult(file, result);
                logResult(file, result);
            } catch (error) {
                console.error(error);
                log(`✗ Error analyzing ${file.name}`, 'error');
                displayError(file, 'Analysis failed');
            }
            running.delete(file.name);
            done++;
            setProgress();
        }
    };
    await Promise.all(Array.from({ length: Math.min(concurrency, files.length) }, worker));

    pText.textContent = 'Complete';
    const pending = state.cards.filter(c => c.result.success && c.result.hunks.length).length;

    setTimeout(() => {
        pContainer.style.display = 'none';
        document.getElementById('executeBtn').disabled = false;
        document.getElementById('exportBtn').style.display = 'flex';
        state.analyzing = false;
        setWolfMood('happy');
        showToast(pending ? `Analysis complete · ${pending} fix(es) to review` : 'Analysis complete', 'success');
        log('Analysis cycle completed' + (pending ? `. ${pending} fix(es) waiting for review; nothing has been written yet.` : ''), 'success');
    }, 600);
}

function logResult(file, result) {
    if (!result.success) {
        log(`✗ ${file.name} - ${result.error}`, 'error');
        return;
    }
    const issues = result.errors.length;
    const changes = result.hunks.length;
    const prefix = result.cached ? '↺' : '✓';
    const cachedNote = result.cached ? ' (unchanged since last run, reused result)' : '';
    if (changes) {
        log(`${prefix} ${file.name} - ${issues} issue(s), fix ready for review (${changes} change${changes > 1 ? 's' : ''})${cachedNote}`, 'success');
    } else if (issues) {
        log(`${prefix} ${file.name} - ${issues} issue(s), no code changes suggested${cachedNote}`, 'success');
    } else {
        log(`${prefix} ${file.name} - No issues found${cachedNote}`, 'success');
    }
    (result.warnings || []).forEach(w => log(`⚠ ${file.name}: ${w}`, 'warning'));
}

// ==========================================
// 📊 RESULT RENDERING
// ==========================================

function displayResult(file, result) {
    const container = document.getElementById('analysisResults');

    if (!result.success) {
        displayError(file, result.error, 'FAILED');
        return;
    }

    const idx = state.cards.push({ file, result, chat: [] }) - 1;
    const errors = result.errors || [];
    const status = errors.length === 0 ? 'CLEAN' : 'ISSUES FOUND';
    const statusClass = errors.length === 0 ? 'status-success' : 'status-warning';

    let html = `
        <div class="result-card" data-idx="${idx}">
            <div class="result-header">
                <div class="result-title" title="${escapeHtml(file.path)}">${escapeHtml(file.name)}</div>
                <div class="result-badges">
                    ${result.cached ? '<span class="badge badge-muted" title="File unchanged since the last run">cached</span>' : ''}
                    ${result.chunks > 1 ? `<span class="badge badge-muted" title="Large file analyzed in parts">${result.chunks} parts</span>` : ''}
                    <span class="badge badge-muted">${escapeHtml(result.language)}</span>
                    <div class="result-status ${statusClass}">${status}</div>
                </div>
            </div>
            <p class="result-summary">${escapeHtml(result.summary)}</p>`;

    if (result.warnings && result.warnings.length) {
        html += `<div class="result-warnings">${result.warnings.map(w => `<div>⚠ ${escapeHtml(w)}</div>`).join('')}</div>`;
    }

    if (errors.length > 0) {
        html += '<div class="error-list">';
        errors.forEach(err => {
            const hasLine = err.line > 0;
            html += `
                <div class="error-item severity-${escapeHtml(err.severity)} ${hasLine ? 'clickable' : ''}"
                     ${hasLine ? `data-action="toggle-snippet" data-line="${err.line}" title="Show code"` : ''}>
                    <div class="error-header">
                        <span class="error-type">${escapeHtml(err.type)}${err.category ? ` <span class="error-category">${escapeHtml(err.category)}</span>` : ''}</span>
                        <span class="error-line">${hasLine ? `Line ${err.line} ▾` : 'Line ?'}</span>
                    </div>
                    <div class="error-description">${escapeHtml(err.description)}</div>
                    <div class="error-fix">💡 ${escapeHtml(err.fix)}</div>
                    <div class="code-snippet" hidden></div>
                </div>`;
        });
        html += '</div>';
    }

    if (result.hunks.length) {
        html += renderFixSection(result);
    }

    html += `
            <div class="card-actions">
                <button class="btn btn-ghost btn-sm" data-action="toggle-chat">💬 Ask about this file</button>
            </div>
            <div class="chat-section" hidden>
                <div class="chat-messages"></div>
                <form class="chat-form">
                    <input class="form-input chat-input" placeholder="e.g. Why is line ${errors[0] ? errors[0].line : 1} a bug?" autocomplete="off">
                    <button class="btn btn-primary btn-sm" type="submit">Ask</button>
                </form>
            </div>
        </div>`;

    container.insertAdjacentHTML('beforeend', html);
}

function renderFixSection(result) {
    const n = result.hunks.length;
    const hunksHtml = result.hunks.map((h, i) => renderHunk(h, i, n)).join('');
    const actions = result.analyzeOnly
        ? '<div class="fix-note">Analyze-only mode is on, so this fix can\'t be applied. Turn it off in Settings to apply fixes.</div>'
        : `<div class="fix-actions">
               <button class="btn btn-secondary btn-sm" data-action="reject">Reject</button>
               <button class="btn btn-secondary btn-sm" data-action="apply-selected">Apply selected</button>
               <button class="btn btn-primary btn-sm" data-action="apply-all">Apply all ${n}</button>
           </div>`;
    return `
        <div class="fix-section">
            <div class="fix-bar">
                <span>🛠 Suggested fix · ${n} change${n > 1 ? 's' : ''} · <em>not saved yet</em></span>
                <button class="btn btn-ghost btn-sm" data-action="toggle-diff">Review fix ▾</button>
            </div>
            <div class="diff-view" hidden>
                ${hunksHtml}
                ${actions}
            </div>
        </div>`;
}

function renderHunk(h, i, total) {
    const rowsMiddle = Math.max(h.removed.length, h.added.length);
    const row = (num, text, cls) =>
        `<div class="diff-row ${cls}"><span class="ln">${num ?? ''}</span><span class="code">${text === null ? '' : escapeHtml(text) || ' '}</span></div>`;

    let oldSide = '';
    let newSide = '';
    const newBeforeStart = h.newStart - h.before.length;
    h.before.forEach((line, k) => {
        oldSide += row(h.beforeStart + k, line, 'ctx');
        newSide += row(newBeforeStart + k, line, 'ctx');
    });
    for (let k = 0; k < rowsMiddle; k++) {
        oldSide += k < h.removed.length ? row(h.oldStart + k, h.removed[k], 'del') : row(null, null, 'pad');
        newSide += k < h.added.length ? row(h.newStart + k, h.added[k], 'add') : row(null, null, 'pad');
    }
    h.after.forEach((line, k) => {
        oldSide += row(h.oldStart + h.removed.length + k, line, 'ctx');
        newSide += row(h.newStart + h.added.length + k, line, 'ctx');
    });

    return `
        <div class="hunk">
            <label class="hunk-head">
                <input type="checkbox" data-hunk="${h.id}" checked>
                <span>Change ${i + 1} of ${total} · line ${h.oldStart}</span>
            </label>
            <div class="hunk-body">
                <div class="diff-side"><div class="diff-side-label">Current</div>${oldSide}</div>
                <div class="diff-side"><div class="diff-side-label">Fixed</div>${newSide}</div>
            </div>
        </div>`;
}

function displayError(file, msg, label = 'ERROR') {
    const container = document.getElementById('analysisResults');
    container.insertAdjacentHTML('beforeend', `
        <div class="result-card">
            <div class="result-header">
                <div class="result-title" title="${escapeHtml(file.path)}">${escapeHtml(file.name)}</div>
                <div class="result-status status-error">${label}</div>
            </div>
            <p class="result-summary" style="color: var(--danger);">${escapeHtml(msg)}</p>
        </div>`);
}

// ==========================================
// 🖱️ RESULT CARD ACTIONS
// ==========================================

function handleResultClick(e) {
    const target = e.target.closest('[data-action]');
    if (!target) return;
    const cardEl = target.closest('.result-card');
    const card = cardEl && state.cards[cardEl.dataset.idx];
    if (!card) return;

    switch (target.dataset.action) {
        case 'toggle-snippet':
            if (e.target.closest('.code-snippet')) return; // allow selecting code
            toggleSnippet(target, card);
            break;
        case 'toggle-diff': {
            const view = cardEl.querySelector('.diff-view');
            view.hidden = !view.hidden;
            target.textContent = view.hidden ? 'Review fix ▾' : 'Hide fix ▴';
            break;
        }
        case 'apply-all':
            applyFix(cardEl, card, null);
            break;
        case 'apply-selected': {
            const ids = [...cardEl.querySelectorAll('[data-hunk]:checked')].map(cb => Number(cb.dataset.hunk));
            if (!ids.length) {
                showToast('Select at least one change', 'warning');
                return;
            }
            applyFix(cardEl, card, ids);
            break;
        }
        case 'reject':
            rejectFix(cardEl, card);
            break;
        case 'toggle-chat': {
            const chat = cardEl.querySelector('.chat-section');
            chat.hidden = !chat.hidden;
            if (!chat.hidden) chat.querySelector('.chat-input').focus();
            break;
        }
    }
}

function toggleSnippet(item, card) {
    const box = item.querySelector('.code-snippet');
    if (!box.hidden) {
        box.hidden = true;
        return;
    }
    const lines = card.result.code.split(/\r?\n/);
    if (lines.length > 1 && lines[lines.length - 1] === '') lines.pop(); // trailing newline isn't a line
    const target = Number(item.dataset.line);
    if (target < 1 || target > lines.length) {
        box.innerHTML = '<div class="snippet-empty">That line isn\'t in the file (the model may have miscounted).</div>';
    } else {
        const from = Math.max(1, target - 4);
        const to = Math.min(lines.length, target + 4);
        let html = '';
        for (let n = from; n <= to; n++) {
            html += `<div class="snippet-row ${n === target ? 'hl' : ''}"><span class="ln">${n}</span><span class="code">${escapeHtml(lines[n - 1]) || ' '}</span></div>`;
        }
        box.innerHTML = html;
    }
    box.hidden = false;
}

async function applyFix(cardEl, card, ids) {
    const section = cardEl.querySelector('.fix-section');
    section.querySelectorAll('button').forEach(b => b.disabled = true);
    const res = await api().apply_fix(card.file.path, ids);
    if (!res.success) {
        section.querySelectorAll('button').forEach(b => b.disabled = false);
        showToast(res.error, 'error');
        log(`✗ ${card.file.name} - ${res.error}`, 'error');
        return;
    }
    section.innerHTML = `<div class="fix-done">✓ Applied ${res.applied} change(s). A backup was saved; use “Revert last fix” to undo.</div>`;
    const status = cardEl.querySelector('.result-status');
    status.textContent = 'FIXED';
    status.className = 'result-status status-success';
    log(`✓ Applied ${res.applied} change(s) to ${card.file.name} (backup saved)`, 'success');
    showToast(`Fix applied to ${card.file.name}`, 'success');
    setWolfMood('happy');
    refreshUndoButton();
    refreshCommitButton();
}

async function rejectFix(cardEl, card) {
    await api().reject_fix(card.file.path);
    cardEl.querySelector('.fix-section').innerHTML = '<div class="fix-note">Fix rejected. The file was not changed.</div>';
    log(`Rejected fix for ${card.file.name}`, 'info');
}

// ==========================================
// 💬 FOLLOW-UP QUESTIONS
// ==========================================

async function handleChatSubmit(e) {
    if (!e.target.classList.contains('chat-form')) return;
    e.preventDefault();
    const cardEl = e.target.closest('.result-card');
    const card = state.cards[cardEl.dataset.idx];
    const input = e.target.querySelector('.chat-input');
    const button = e.target.querySelector('button');
    const question = input.value.trim();
    if (!question || !card) return;

    const messages = cardEl.querySelector('.chat-messages');
    const history = card.chat.slice();
    card.chat.push({ role: 'user', content: question });
    messages.insertAdjacentHTML('beforeend', `<div class="chat-msg chat-user">${escapeHtml(question)}</div>`);
    messages.insertAdjacentHTML('beforeend', '<div class="chat-msg chat-bot chat-pending">Thinking…</div>');
    messages.scrollTop = messages.scrollHeight;
    input.value = '';
    input.disabled = button.disabled = true;

    const res = await api().ask_question(card.file.path, question, history);
    const pending = messages.querySelector('.chat-pending');
    if (res.success) {
        card.chat.push({ role: 'assistant', content: res.answer });
        pending.innerHTML = renderMarkdownLite(res.answer);
    } else {
        card.chat.pop();
        pending.innerHTML = `<span style="color: var(--danger)">${escapeHtml(res.error)}</span>`;
    }
    pending.classList.remove('chat-pending');
    input.disabled = button.disabled = false;
    input.focus();
    messages.scrollTop = messages.scrollHeight;
}

function renderMarkdownLite(text) {
    // Code blocks, inline code, bold and line breaks; everything else is escaped.
    const parts = String(text).split(/```[\w+-]*\n?([\s\S]*?)```/g);
    return parts.map((part, i) => {
        if (i % 2 === 1) return `<pre class="chat-code">${escapeHtml(part.replace(/\n$/, ''))}</pre>`;
        return escapeHtml(part)
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
    }).join('');
}

// ==========================================
// ↩️ UNDO & GIT
// ==========================================

async function refreshUndoButton() {
    const status = await api().undo_status();
    const btn = document.getElementById('revertBtn');
    btn.style.display = status.count > 0 ? 'flex' : 'none';
    btn.title = status.latest ? `Restore ${status.latest} as it was before the last applied fix` : '';
}

async function refreshCommitButton() {
    const status = await api().git_commit_status();
    document.getElementById('commitBtn').style.display = status.count > 0 ? 'flex' : 'none';
}

async function revertLastFix() {
    let res = await api().revert_last(false);
    if (!res.success && res.needsConfirm) {
        if (!confirm(res.error + '\n\nRevert anyway?')) return;
        res = await api().revert_last(true);
    }
    if (res.success) {
        showToast(`Reverted ${res.name}`, 'success');
        log(`↩ Reverted ${res.name} to its state before the fix`, 'success');
    } else {
        showToast(res.error, 'warning');
    }
    refreshUndoButton();
    refreshCommitButton();
}

async function commitFixes() {
    const ok = confirm(
        'Commit the fixes applied in this session to a new git branch?\n\n' +
        'Wolf AI creates a branch named wolf-ai/fixes-<time>, commits only the fixed files, ' +
        'then switches back to your current branch, which is left as it was before the fixes. ' +
        'Files that had your own uncommitted changes are skipped.'
    );
    if (!ok) return;
    const res = await api().commit_fixes();
    (res.results || []).forEach(r => {
        if (r.success) {
            log(`✓ ${r.repo}: committed ${r.files} file(s) to ${r.branch}` +
                (r.switchedBack ? `, back on ${r.returnedTo}` : `. Could not switch back: ${r.switchError}`), 'success');
            showToast(`Committed to ${r.branch}`, 'success');
        } else {
            log(`✗ ${r.repo}: ${r.error}`, 'error');
        }
    });
    (res.skipped || []).forEach(s => log(`Skipped ${s}`, 'warning'));
    if (!res.success) showToast(res.error || 'Commit failed', 'error');
    refreshCommitButton();
    refreshGitPanel();
}

async function refreshGitPanel() {
    const panel = document.getElementById('gitPanel');
    if (!state.selectedFiles.length) {
        panel.style.display = 'none';
        state.gitPath = null;
        return;
    }
    const path = state.selectedFiles[0].path;
    const info = await api().git_info(path);
    if (info.isRepo) {
        state.gitPath = path;
        document.getElementById('gitRepoLabel').textContent = `${info.name} · ${info.branch}`;
        panel.style.display = 'block';
    } else {
        state.gitPath = null;
        panel.style.display = 'none';
    }
}

async function loadGitChangedFiles() {
    if (!state.gitPath) return;
    const res = await api().git_changed_files(state.gitPath);
    if (!res.success) {
        showToast(res.error, 'error');
        return;
    }
    if (!res.files.length) {
        showToast('No changed code files in this repo', 'info');
        return;
    }
    state.selectedFiles = res.files;
    updateFilesList();
    log(`Loaded ${res.files.length} changed file(s) from git`, 'info');
    showToast(`${res.files.length} changed file(s) loaded`, 'success');
}

// ==========================================
// ⚙️ SETTINGS
// ==========================================

async function loadSettings() {
    state.settings = await api().get_settings();
    document.querySelectorAll('#checkToggles input').forEach(input => {
        input.checked = !!state.settings.checks[input.dataset.check];
    });
    document.getElementById('analyzeOnlyNote').style.display = state.settings.analyze_only ? 'block' : 'none';
}

async function onCheckToggle(e) {
    const checks = {};
    document.querySelectorAll('#checkToggles input').forEach(input => {
        checks[input.dataset.check] = input.checked;
    });
    if (!Object.values(checks).some(Boolean)) {
        e.target.checked = true;
        showToast('Keep at least one check enabled', 'warning');
        return;
    }
    const res = await api().save_settings({ checks });
    if (res.success) state.settings = res.settings;
}

async function openSettings() {
    if (!state.settings) await loadSettings();
    const s = state.settings;
    const keyInput = document.getElementById('apiKeyInput');
    keyInput.value = '';
    keyInput.placeholder = s.has_key ? `Saved (${s.key_hint}). Leave blank to keep it` : 'gsk_...';
    document.getElementById('apiKeyHint').textContent = s.has_key
        ? `Using the key from ${s.key_source}. Paste a new key to replace it.`
        : 'Get a key at console.groq.com. It is stored only on this computer.';
    document.getElementById('modelInput').value = s.model;
    document.getElementById('temperatureInput').value = s.temperature;
    document.getElementById('temperatureValue').textContent = s.temperature;
    document.getElementById('concurrencyInput').value = s.concurrency;
    document.getElementById('concurrencyValue').textContent = s.concurrency;
    document.getElementById('analyzeOnlyInput').checked = s.analyze_only;
    document.getElementById('skipUnchangedInput').checked = s.skip_unchanged;
    document.getElementById('settingsModal').style.display = 'flex';
    if (s.has_key && !document.getElementById('modelOptions').children.length) refreshModels(false);
}

function closeSettings() {
    document.getElementById('settingsModal').style.display = 'none';
}

async function refreshModels(announce) {
    const res = await api().list_models();
    document.getElementById('modelOptions').innerHTML =
        res.models.map(m => `<option value="${escapeHtml(m)}"></option>`).join('');
    if (announce) {
        showToast(res.success ? `${res.models.length} models available` : 'Could not load models, showing defaults',
                  res.success ? 'success' : 'warning');
    }
}

async function saveSettings() {
    const key = document.getElementById('apiKeyInput').value.trim();
    if (key && !key.startsWith('gsk_')) {
        showToast('Groq API keys start with gsk_', 'warning');
        return;
    }
    const res = await api().save_settings({
        api_key: key,
        model: document.getElementById('modelInput').value,
        temperature: document.getElementById('temperatureInput').value,
        concurrency: document.getElementById('concurrencyInput').value,
        analyze_only: document.getElementById('analyzeOnlyInput').checked,
        skip_unchanged: document.getElementById('skipUnchangedInput').checked,
    });
    if (!res.success) {
        showToast(res.error, 'error');
        return;
    }
    state.settings = res.settings;
    document.getElementById('analyzeOnlyNote').style.display = res.settings.analyze_only ? 'block' : 'none';
    closeSettings();
    showToast('Settings saved', 'success');
    log(`Settings saved (model: ${res.settings.model})`, 'info');
    checkSystemHealth();
}

// ==========================================
// 🛠️ UTILITIES
// ==========================================

function exportReport() {
    const clone = document.getElementById('analysisResults').cloneNode(true);
    clone.querySelectorAll('.fix-actions, .card-actions, .chat-form, .diff-view, .code-snippet, .fix-bar button').forEach(el => el.remove());
    clone.querySelectorAll('.chat-section').forEach(el => { if (!el.querySelector('.chat-msg')) el.remove(); else el.hidden = false; });
    const content = clone.innerHTML;
    const date = new Date().toISOString().split('T')[0];
    const filename = `wolf_ai_report_${date}.html`;
    
    const reportHTML = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Wolf AI Analysis Report</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; background: #0a0a0f; color: #fff; padding: 40px; }
        h1 { color: #6366f1; margin-bottom: 30px; }
        .result-card { background: #1e1e2e; border: 1px solid #27272a; border-radius: 12px; padding: 20px; margin-bottom: 20px; }
        .result-header { display: flex; justify-content: space-between; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #27272a; }
        .result-title { font-weight: 600; }
        .result-status { padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; }
        .status-success { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .status-warning { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
        .status-error { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
        .error-item { background: #13131a; border-left: 3px solid #ef4444; padding: 14px; margin: 10px 0; border-radius: 8px; }
        .error-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
        .error-fix { color: #10b981; background: rgba(16, 185, 129, 0.1); padding: 8px 12px; border-radius: 6px; margin-top: 8px; }
    </style>
</head>
<body>
    <h1>Wolf AI Code Debugger Report</h1>
    <p>Generated: ${new Date().toLocaleString()}</p>
    <hr style="border-color: #27272a; margin: 30px 0;">
    ${content}
</body>
</html>`;
    
    window.pywebview.api.save_report(filename, reportHTML).then(ok => {
        if (ok) {
            showToast('Report exported successfully', 'success');
            log('Report exported successfully', 'success');
        } else {
            showToast('Export failed', 'error');
        }
    }).catch(err => {
        console.error('Export failed:', err);
        showToast('Export failed', 'error');
    });
}

function log(msg, type = 'info') {
    const container = document.getElementById('logContent');
    if (!container) return;
    
    const p = document.createElement('p');
    p.className = `log-entry log-${type}`;
    p.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
    
    container.appendChild(p);
    container.scrollTop = container.scrollHeight;
}

function showToast(msg, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'toastSlide 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function formatBytes(bytes, decimals = 2) {
    if (!+bytes) return '0 B';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}
