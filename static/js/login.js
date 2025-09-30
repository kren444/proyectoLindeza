document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const errorMessage = document.getElementById('error-message');
    const passwordInput = document.getElementById('password');

    // Si el usuario ya está logueado, redirigir al panel de admin
    if (sessionStorage.getItem('isAdminAuthenticated') === 'true') {
        window.location.href = 'admin.html';
    }

    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const password = passwordInput.value;
        // Simulación de autenticación
        if (password === 'admin123') {
            sessionStorage.setItem('isAdminAuthenticated', 'true');
            window.location.href = 'admin.html';
        } else {
            errorMessage.textContent = 'Contraseña incorrecta. Inténtalo de nuevo.';
            passwordInput.focus();
        }
    });
});
// Ejemplo usando fetch y login-form
document.getElementById('login-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const res = await fetch('/api/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({email, password})
    });
    const data = await res.json();
    if (data.ok) {
        window.location.href = data.redirect; // Redirige según el tipo de usuario
    } else {
        document.getElementById('login-error').textContent = data.error || 'Error';
        document.getElementById('login-error').classList.remove('hidden');
    }
});

