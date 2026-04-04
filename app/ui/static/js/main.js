// ── Auto-hide flash messages ──
document.addEventListener('DOMContentLoaded', () => {
    const flash = document.querySelector('[data-flash]');
    if (flash) {
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transition = 'opacity 0.5s';
            setTimeout(() => flash.remove(), 500);
        }, 4000);
    }
});

// ── Confirm delete actions ──
document.querySelectorAll('form[action*="delete"]').forEach(form => {
    form.addEventListener('submit', (e) => {
        if (!confirm('Are you sure you want to delete this?')) {
            e.preventDefault();
        }
    });
});

// ── Active nav link highlight ──
const currentPath = window.location.pathname;
document.querySelectorAll('.sidebar-link').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
        link.classList.add('active');
    }
});