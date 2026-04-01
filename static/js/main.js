document.addEventListener('DOMContentLoaded', () => {
    // Inject cursor styles dynamically (so no separate CSS file is needed)
    const cursorStyle = document.createElement('style');
    cursorStyle.textContent = `
        * { cursor: none; }
        .cursor {
            position: fixed;
            width: 18px;
            height: 18px;
            background: rgba(94, 42, 132, 0.7);
            border: 2px solid #d4af37;
            border-radius: 50%;
            pointer-events: none;
            transform: translate(-50%, -50%);
            transition: transform 0.15s ease, background 0.2s ease, width 0.2s ease, height 0.2s ease;
            z-index: 9999;
        }
        .cursor.hovered {
            width: 30px;
            height: 30px;
            background: rgba(212, 175, 55, 0.5);
        }
        section.reveal {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }
    `;
    document.head.appendChild(cursorStyle);

    // Custom Cursor Logic
    const cursor = document.createElement('div');
    cursor.classList.add('cursor');
    document.body.appendChild(cursor);

    document.addEventListener('mousemove', (e) => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
    });

    // Hover effects for cursor
    const interactiveElements = document.querySelectorAll('a, button, .btn-premium, .menu-card');
    interactiveElements.forEach(el => {
        el.addEventListener('mouseenter', () => cursor.classList.add('hovered'));
        el.addEventListener('mouseleave', () => cursor.classList.remove('hovered'));
    });

    // Scroll Reveal Animation (IntersectionObserver is sufficient — no redundant scroll listener needed)
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('reveal');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('section').forEach(section => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(50px)';
        section.style.transition = 'all 1s cubic-bezier(0.16, 1, 0.3, 1)';
        observer.observe(section);
    });
});

// Sound (Mock)
function playSound() {
    // In a real implementation, this would trigger WebAudio API
    console.log("Audio feedback triggered");
}
