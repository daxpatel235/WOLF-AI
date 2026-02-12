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
    moodInterval: null
};

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
    
    // Reset state
    state.analyzing = false;
    
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
            updateConnectionStatus('Brain Off', 'offline');
            log('Warning: API key not configured or invalid', 'warning');
            showToast('Brain offline - Check API configuration', 'warning');
        }
        
    } catch (error) {
        console.error('System health check failed:', error);
        showOfflineOverlay();
    }
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
    log(`Removed ${file.name} from queue`, 'info');
    showToast('File removed', 'info');
}

// ==========================================
// 🔬 ANALYSIS
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
    setWolfMood('alert');
    
    // Reset UI
    const welcomeScreen = document.getElementById('welcomeScreen');
    const analysisResults = document.getElementById('analysisResults');
    welcomeScreen.style.display = 'none';
    analysisResults.style.display = 'block';
    analysisResults.innerHTML = '';
    
    // Setup Progress
    const pContainer = document.getElementById('progressContainer');
    const pFill = document.getElementById('progressFill');
    const pPercent = document.getElementById('progressPercent');
    const pText = document.getElementById('progressText');
    
    pContainer.style.display = 'block';
    document.getElementById('executeBtn').disabled = true;
    
    log('Starting code analysis...', 'system');
    
    // Processing Loop
    for (let i = 0; i < state.selectedFiles.length; i++) {
        const file = state.selectedFiles[i];
        
        // Update Progress
        const percent = Math.round((i / state.selectedFiles.length) * 100);
        pFill.style.width = percent + '%';
        pPercent.textContent = percent + '%';
        pText.textContent = `Analyzing: ${file.name}`;
        
        log(`Analyzing ${file.name} [${file.language}]`, 'info');
        
        try {
            const langOverride = document.getElementById('languageSelect').value;
            const result = await window.pywebview.api.start_analysis(file.path, langOverride);
            
            displayResult(file, result);
            
            if (result.success) {
                if (result.fixedCode && result.fixedCode !== "") {
                    log(`✓ Fixed ${file.name} (auto-saved)`, 'success');
                } else {
                    log(`✓ ${file.name} - No issues found`, 'success');
                }
            } else {
                log(`✗ ${file.name} - ${result.error}`, 'error');
            }
            
        } catch (error) {
            console.error(error);
            log(`✗ Error analyzing ${file.name}`, 'error');
            displayError(file, "Analysis failed");
        }
    }
    
    // Finalize
    pFill.style.width = '100%';
    pPercent.textContent = '100%';
    pText.textContent = 'Complete';
    
    setTimeout(() => {
        pContainer.style.display = 'none';
        document.getElementById('executeBtn').disabled = false;
        document.getElementById('exportBtn').style.display = 'block';
        state.analyzing = false;
        setWolfMood('happy');
        showToast('Analysis complete', 'success');
        log('Analysis cycle completed', 'success');
    }, 800);
}

// ==========================================
// 📊 RESULT RENDERING
// ==========================================

function displayResult(file, result) {
    const container = document.getElementById('analysisResults');
    
    if (!result.success) {
        container.innerHTML += `
            <div class="result-card">
                <div class="result-header">
                    <div class="result-title">${escapeHtml(file.name)}</div>
                    <div class="result-status status-error">FAILED</div>
                </div>
                <p class="result-summary" style="color: var(--danger);">${escapeHtml(result.error)}</p>
            </div>`;
        return;
    }
    
    const errors = result.errors || [];
    const status = errors.length === 0 ? 'CLEAN' : 'ISSUES FOUND';
    const statusClass = errors.length === 0 ? 'status-success' : 'status-warning';
    
    let html = `
        <div class="result-card">
            <div class="result-header">
                <div class="result-title">${escapeHtml(file.name)}</div>
                <div class="result-status ${statusClass}">${status}</div>
            </div>
            <p class="result-summary">${escapeHtml(result.summary)}</p>`;
    
    if (errors.length > 0) {
        html += '<div class="error-list">';
        errors.forEach(err => {
            html += `
                <div class="error-item severity-${escapeHtml(err.severity)}">
                    <div class="error-header">
                        <span class="error-type">${escapeHtml(err.type)}</span>
                        <span class="error-line">Line ${escapeHtml(String(err.line))}</span>
                    </div>
                    <div class="error-description">${escapeHtml(err.description)}</div>
                    <div class="error-fix">💡 ${escapeHtml(err.fix)}</div>
                </div>`;
        });
        html += '</div>';
    }
    
    html += '</div>';
    container.innerHTML += html;
}

function displayError(file, msg) {
    const container = document.getElementById('analysisResults');
    container.innerHTML += `
        <div class="result-card">
            <div class="result-header">
                <div class="result-title">${escapeHtml(file.name)}</div>
                <div class="result-status status-error">ERROR</div>
            </div>
            <p class="result-summary" style="color: var(--danger);">${escapeHtml(msg)}</p>
        </div>`;
}

// ==========================================
// 🛠️ UTILITIES
// ==========================================

function exportReport() {
    const content = document.getElementById('analysisResults').innerHTML;
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
