// Frontend smoke test. Injected before Web/script.js by tests/test_frontend_smoke.py.
// It replaces the Python bridge with a fake one, drives the UI, and prints results
// into <pre id="out"> for the test runner to read from the dumped DOM.

window.__errors = [];
window.addEventListener('error', e => window.__errors.push(`${e.message} @${e.lineno}`));
window.addEventListener('unhandledrejection', e => window.__errors.push(`unhandled rejection: ${e.reason}`));
window.__calls = [];
window.confirm = () => true;

const CODE = 'import os\nx = 1\nprint(x)\n';
const okResult = () => ({
    success: true,
    errors: [{ line: 2, type: 'Logic', category: 'bugs', severity: 'high', description: 'd <b>', fix: 'f' }],
    summary: 'sum', warnings: ['w1'], chunks: 2, cached: false, language: 'Python', code: CODE,
    hunks: [{ id: 0, op: [1, 2, 1, 2], oldStart: 2, newStart: 2, before: ['import os'], beforeStart: 1,
              removed: ['x = 1'], added: ['x = 2', 'y = 3'], after: ['print(x)'] }],
    analyzeOnly: false,
});

let inFlight = 0;
let maxInFlight = 0;
const delay = (v, ms = 30) => new Promise(r => setTimeout(() => r(v), ms));

window.pywebview = { api: {
    get_version: () => delay('2.0.0'),
    check_connection: () => delay(true),
    check_api_key: () => delay(true),
    get_settings: () => delay({
        api_key: '', has_key: true, key_hint: 'gsk_…abcd', key_source: 'settings',
        model: 'llama-3.3-70b-versatile', temperature: 0.2, concurrency: 3,
        analyze_only: false, skip_unchanged: true,
        checks: { bugs: true, security: true, performance: true, style: false },
    }),
    save_settings: (c) => {
        window.__calls.push(['save_settings', c]);
        return delay({ success: true, settings: { checks: c.checks || {}, analyze_only: false, model: 'm', concurrency: 3 } });
    },
    list_models: () => delay({ success: true, models: ['a', 'b'] }),
    undo_status: () => delay({ count: window.__applied ? 1 : 0, latest: 'app.py' }),
    git_commit_status: () => delay({ count: window.__applied ? 1 : 0 }),
    git_info: () => delay({ isRepo: true, name: 'repo', branch: 'main' }),
    start_analysis: async (path, lang) => {
        window.__calls.push(['start_analysis', path, lang]);
        inFlight++;
        maxInFlight = Math.max(maxInFlight, inFlight);
        await delay(null, 80);
        inFlight--;
        return path.endsWith('bad.py') ? { success: false, error: 'boom' } : okResult();
    },
    apply_fix: (path, ids) => {
        window.__calls.push(['apply_fix', path, ids]);
        window.__applied = true;
        return delay({ success: true, applied: ids ? ids.length : 1, undoCount: 1 });
    },
    reject_fix: () => delay(true),
    ask_question: (path, q, history) => {
        window.__calls.push(['ask', q, history.length]);
        return delay({ success: true, answer: 'Because `x` is **wrong**\n```py\nx = 2\n```' });
    },
    clear_cache: () => delay(true),
}};

// The page must render on its own, before the Python bridge is ready (no blank window).
window.addEventListener('DOMContentLoaded', () => {
    const welcome = document.getElementById('welcomeScreen');
    window.__preBridge = {
        background: getComputedStyle(document.body).backgroundColor,
        welcomeVisible: !!welcome && getComputedStyle(welcome).display !== 'none',
        title: (document.querySelector('.welcome-title') || {}).textContent,
    };
});

setTimeout(() => window.dispatchEvent(new Event('pywebviewready')), 10);

async function runSmokeTest() {
    const out = [];
    const check = (name, cond) => out.push(`${cond ? 'PASS' : 'FAIL'} ${name}`);
    const pre = window.__preBridge || {};

    check('stylesheet applied (dark background)', pre.background === 'rgb(10, 10, 15)');
    check('welcome screen visible before bridge', pre.welcomeVisible && pre.title === 'Ready to Debug');

    await delay(null, 300);
    check('version shown in title bar', document.querySelector('.app-subtitle').textContent.includes('v2.0.0'));
    check('settings modal not auto-opened when key exists', document.getElementById('settingsModal').style.display === 'none');
    check('check toggles loaded from settings',
          document.querySelector('[data-check=bugs]').checked && !document.querySelector('[data-check=style]').checked);

    handleFolderFiles(['a.py', 'b.py', 'c.py', 'd.py', 'bad.py']
        .map(n => ({ name: n, path: 'C:\\repo\\' + n, size: 10, language: 'Python' })));
    await delay(null, 100);
    check('queue lists 5 files', document.querySelectorAll('#selectedFiles .file-item').length === 5);
    check('git panel shown for repo files', document.getElementById('gitPanel').style.display === 'block');

    await startAnalysis();
    check('runs 3 files in parallel', maxInFlight === 3);
    check('"auto" language sent to backend', window.__calls.find(c => c[0] === 'start_analysis')[2] === 'auto');
    check('one card per file', document.querySelectorAll('.result-card').length === 5);
    check('failed file shown as failed', document.querySelectorAll('.status-error').length === 1);
    check('model output is HTML-escaped', document.querySelector('.error-description').textContent === 'd <b>');

    const card = document.querySelector('.result-card[data-idx="0"]');
    card.querySelector('.error-item').click();
    const hl = card.querySelector('.snippet-row.hl');
    check('clicking an issue shows the highlighted line',
          hl && hl.textContent.includes('x = 1') && !card.querySelector('.code-snippet').hidden);

    card.querySelector('[data-action=toggle-diff]').click();
    check('fix review opens', !card.querySelector('.diff-view').hidden);
    check('side-by-side diff rows',
          card.querySelectorAll('.diff-row.del').length === 1
          && card.querySelectorAll('.diff-row.add').length === 2
          && card.querySelectorAll('.diff-row.pad').length === 1);

    card.querySelector('[data-action=apply-selected]').click();
    await delay(null, 150);
    const apply = window.__calls.find(c => c[0] === 'apply_fix');
    check('apply sends the selected change ids', apply && JSON.stringify(apply[2]) === '[0]');
    check('card marked FIXED', card.querySelector('.result-status').textContent === 'FIXED');
    check('revert and commit buttons appear',
          document.getElementById('revertBtn').style.display === 'flex'
          && document.getElementById('commitBtn').style.display === 'flex');

    card.querySelector('[data-action=toggle-chat]').click();
    card.querySelector('.chat-input').value = 'why?';
    card.querySelector('.chat-form').requestSubmit();
    await delay(null, 150);
    const bot = card.querySelector('.chat-bot');
    check('chat answer rendered with code formatting',
          bot && bot.querySelector('pre.chat-code') && bot.querySelector('strong') && bot.querySelector('code'));

    document.querySelector('[data-check=bugs]').click();
    await delay(null, 80);
    check('check toggles are saved',
          window.__calls.some(c => c[0] === 'save_settings' && c[1].checks && c[1].checks.bugs === false));

    await openSettings();
    check('settings modal opens', document.getElementById('settingsModal').style.display === 'flex');
    check('API key is never pre-filled', document.getElementById('apiKeyInput').value === '');

    check('no JavaScript errors', window.__errors.length === 0);
    out.push('ERRORS: ' + JSON.stringify(window.__errors));
    document.body.innerHTML = '<pre id="out"></pre>';
    document.getElementById('out').textContent = out.join('\n');
}

window.addEventListener('load', () => setTimeout(() => {
    runSmokeTest().catch(e => {
        document.body.innerHTML = '<pre id="out"></pre>';
        document.getElementById('out').textContent = 'FAIL test crashed: ' + e.stack;
    });
}, 50));
