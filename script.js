// Mobile / touch: toggle panels open/closed on click
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

    // Open the first panel by default on mobile
    const first = document.querySelector('.panel');
    if (first) first.classList.add('open');
}

document.addEventListener('DOMContentLoaded', initTouch);
window.addEventListener('resize', () => {
    if (!isTouchDevice()) {
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('open'));
    }
});
