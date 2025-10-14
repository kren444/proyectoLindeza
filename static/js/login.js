document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('login-form');
    const err = document.getElementById('login-error');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        err.classList.add('hidden');
        err.textContent = '';
        const email = document.getElementById('login-email').value.trim();
        const password = document.getElementById('login-password').value;
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email, password})
            });
            const data = await res.json();
            if (data.ok) {
                // Server may return a redirect path for admins
                if (data.redirect) {
                    window.location.href = data.redirect;
                } else {
                    // default to home
                    window.location.href = '/';
                }
            } else {
                err.textContent = data.error || 'Error en el inicio de sesión';
                err.classList.remove('hidden');
            }
        } catch (e) {
            err.textContent = 'Error de red. Inténtalo nuevamente.';
            err.classList.remove('hidden');
        }
    });
});

