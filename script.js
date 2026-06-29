// ── Service Worker registration ───────────────────────────────────────────────
// Registers sw.js, which fixes Safari/iOS stale-cache issues by using a
// network-first fetch strategy that bypasses the browser's disk cache.

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js').catch(() => {});
    });
}

// ── GitHub Projects ───────────────────────────────────────────────────────────

const GITHUB_USERNAME = 'CtrlUserKnown';

// Add repo names here to control what shows in the Projects panel.
// Each repo should have a description written in its GitHub "About" field.
const FEATURED_REPOS = [
    'Charvim',
    'dots',
    'GabyLearnsPython',
    'pylings-tui',
    'Capella.it2249',
    'Capella.it3240',
];

// Uncomment and paste your token here if you ever need to raise the rate limit
// from 60 to 5,000 requests/hr. Not needed for normal portfolio use.
// const GITHUB_TOKEN = 'ghp_yourTokenHere';

async function loadGitHubProjects() {
    const container = document.getElementById('projects-container');
    if (!container) return;

    const headers = { 'Accept': 'application/vnd.github+json' };
    // if (GITHUB_TOKEN) headers['Authorization'] = `Bearer ${GITHUB_TOKEN}`;

    try {
        const results = await Promise.all(
            FEATURED_REPOS.map(name =>
                fetch(`https://api.github.com/repos/${GITHUB_USERNAME}/${name}`, { headers })
                    .then(r => r.ok ? r.json() : null)
                    .catch(() => null)
            )
        );

        const repos = results.filter(Boolean);

        if (repos.length === 0) {
            container.innerHTML = '<p class="muted-text">Could not load projects right now.</p>';
            return;
        }

        container.innerHTML = repos.map(repo => {
            const title = repo.name
                .replace(/-/g, ' ')
                .replace(/\b\w/g, l => l.toUpperCase());

            const description = repo.description
                || 'No description yet — add one in the repo\'s About section on GitHub.';

            const topics = (repo.topics || [])
                .map(t => `<span class="tag small">${t}</span>`)
                .join('');

            const language = repo.language
                ? `<span class="tag small">${repo.language}</span>`
                : '';

            const tags = topics || language
                ? `<div class="tag-grid" style="margin-top:0.6rem">${topics}${language}</div>`
                : '';

            const updated = new Date(repo.updated_at).toLocaleDateString('en-US', {
                month: 'short', year: 'numeric'
            });

            return `
                <a class="card" href="${repo.html_url}" target="_blank" rel="noopener noreferrer">
                    <h3>${title}</h3>
                    <p>${description}</p>
                    ${tags}
                    <span class="muted-text" style="font-size:0.72rem;display:block;margin-top:0.6rem">
                        Updated ${updated}
                    </span>
                </a>`;
        }).join('');

    } catch {
        container.innerHTML = '<p class="muted-text">Could not load projects right now.</p>';
    }
}

// ── Panel active state (desktop) ──────────────────────────────────────────────

function initPanels() {
    if (isTouchDevice()) return;

    const panels = document.querySelectorAll('.panel');

    // About is open by default so the page never looks blank on first load
    document.getElementById('panel-about')?.classList.add('active');

    panels.forEach(panel => {
        panel.addEventListener('mouseenter', () => {
            panels.forEach(p => p.classList.remove('active'));
            panel.classList.add('active');
        });
    });
}

// ── Mobile / touch ────────────────────────────────────────────────────────────

const isTouchDevice = () => window.matchMedia('(hover: none)').matches || window.innerWidth <= 640;

function initTouch() {
    if (!isTouchDevice()) return;

    document.querySelectorAll('.panel').forEach(panel => {
        const label = panel.querySelector('.panel-label');
        label.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = panel.classList.contains('open');
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('open'));
            if (!isOpen) panel.classList.add('open');
        });
    });

    // Open About by default on mobile
    const about = document.getElementById('panel-about');
    if (about) about.classList.add('open');
}

// ── Theme Toggle ──────────────────────────────────────────────────────────────

const systemDark = window.matchMedia('(prefers-color-scheme: dark)');

function getEffectiveTheme() {
    return document.documentElement.getAttribute('data-theme')
        || (systemDark.matches ? 'dark' : 'light');
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);

    const btn = document.getElementById('theme-toggle');
    if (btn) {
        btn.textContent = theme === 'dark' ? '☀' : '☽';
        btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    }

    const favicon = document.getElementById('favicon');
    if (favicon) {
        favicon.href = `img/favicon/${theme === 'dark' ? 'Dark' : 'Light'}ModeFavicon.svg`;
    }

    const logoMain = document.querySelector('.about-logo .logo-main');
    const logoAlt  = document.querySelector('.about-logo .logo-alt');
    if (logoMain) logoMain.src = `img/Logo/logo-${theme}.svg`;
    if (logoAlt)  logoAlt.src  = `img/Logo/logo-${theme}-alt.svg`;
}

function initTheme() {
    const saved = localStorage.getItem('theme');
    applyTheme(saved || (systemDark.matches ? 'dark' : 'light'));

    // Follow system changes only while the user hasn't set a manual preference
    systemDark.addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });

    document.getElementById('theme-toggle')?.addEventListener('click', () => {
        const next = getEffectiveTheme() === 'dark' ? 'light' : 'dark';
        localStorage.setItem('theme', next);
        applyTheme(next);
    });
}

// ── Nav Hint ──────────────────────────────────────────────────────────────────

function initNavHint() {
    if (sessionStorage.getItem('nav-hint-dismissed')) return;

    const hint = document.getElementById('nav-hint');
    const closeBtn = document.getElementById('nav-hint-close');
    const text = document.getElementById('nav-hint-text');
    if (!hint) return;

    text.textContent = isTouchDevice()
        ? 'Tap a section to expand'
        : 'Hover a panel to explore';

    let timer;

    function dismiss() {
        clearTimeout(timer);
        hint.classList.add('hiding');
        hint.addEventListener('transitionend', () => hint.remove(), { once: true });
        sessionStorage.setItem('nav-hint-dismissed', '1');
    }

    closeBtn.addEventListener('click', dismiss);

    // Show after a short delay so the page settles first
    setTimeout(() => {
        hint.classList.add('visible');
        timer = setTimeout(dismiss, 5000);
    }, 800);
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initTouch();
    initPanels();
    loadGitHubProjects();
    initNavHint();
});

window.addEventListener('resize', () => {
    const panels = document.querySelectorAll('.panel');
    if (!isTouchDevice()) {
        panels.forEach(p => p.classList.remove('open'));
        // Restore a default active panel if none is set (e.g. after switching from mobile)
        if (!document.querySelector('.panel.active')) {
            document.getElementById('panel-about')?.classList.add('active');
        }
    } else {
        panels.forEach(p => p.classList.remove('active'));
    }
});

// Safari keeps a frozen page snapshot in its Back-Forward Cache (bfcache).
// When the user taps Back from an external link, Safari restores that snapshot
// instead of fetching a fresh copy. Detecting event.persisted and reloading
// forces Safari to request the current version from the network (or SW cache).
window.addEventListener('pageshow', event => {
    if (event.persisted) window.location.reload();
});
