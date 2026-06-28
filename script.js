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
                <div class="card">
                    <h3>${title}</h3>
                    <p>${description}</p>
                    ${tags}
                    <span class="muted-text" style="font-size:0.72rem;display:block;margin-top:0.6rem">
                        Updated ${updated}
                    </span>
                </div>`;
        }).join('');

    } catch {
        container.innerHTML = '<p class="muted-text">Could not load projects right now.</p>';
    }
}

// ── Mobile / touch ────────────────────────────────────────────────────────────

const isTouchDevice = () => window.matchMedia('(hover: none)').matches || window.innerWidth <= 640;

function initTouch() {
    if (!isTouchDevice()) return;

    document.querySelectorAll('.panel').forEach(panel => {
        const label = panel.querySelector('.panel-label');
        label.addEventListener('click', () => {
            const isOpen = panel.classList.contains('open');
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('open'));
            if (!isOpen) panel.classList.add('open');
        });
    });

    const first = document.querySelector('.panel');
    if (first) first.classList.add('open');
}

document.addEventListener('DOMContentLoaded', () => {
    initTouch();
    loadGitHubProjects();
});

window.addEventListener('resize', () => {
    if (!isTouchDevice()) {
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('open'));
    }
});
