document.addEventListener('DOMContentLoaded', () => {
    // --- Filtro por categoría en barra de menú ---
    document.querySelectorAll('.nav-list a').forEach(link => {
        const categorias = ['Labios', 'Ojos', 'Rostro'];
        if (categorias.includes(link.textContent.trim())) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const categoria = link.textContent.trim();
                document.querySelectorAll('.product-gallery-card').forEach(prodCard => {
                    if (prodCard.dataset.categoria === categoria) {
                        prodCard.style.display = 'block';
                    } else {
                        prodCard.style.display = 'none';
                    }
                });
                document.getElementById('novedades').scrollIntoView({ behavior: 'smooth' });
            });
        }
    });
    // --- Filtro por categoría ---
    document.querySelectorAll('.category-card').forEach(card => {
        card.addEventListener('click', function(e) {
            e.preventDefault();
            const categoria = card.querySelector('.category-title').textContent.trim();
            document.querySelectorAll('.product-gallery-card').forEach(prodCard => {
                if (prodCard.dataset.categoria === categoria) {
                    prodCard.style.display = 'block';
                } else {
                    prodCard.style.display = 'none';
                }
            });
            document.getElementById('novedades').scrollIntoView({ behavior: 'smooth' });
        });
    });
    // Mostrar todos los productos si se hace clic en "Novedades"
    document.querySelector('a[href="#novedades"]').addEventListener('click', function(e) {
        document.querySelectorAll('.product-gallery-card').forEach(prodCard => {
            prodCard.style.display = 'block';
        });
    });
    // --- Mobile Menu ---
    const hamburger = document.getElementById('hamburger');
    const navList = document.querySelector('.nav-list');

    hamburger.addEventListener('click', () => {
        navList.classList.toggle('active');
        const icon = hamburger.querySelector('i');
        if (navList.classList.contains('active')) {
            icon.classList.remove('fa-bars');
            icon.classList.add('fa-times');
        } else {
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        }
    });

    document.querySelectorAll('.nav-list a').forEach(link => {
        link.addEventListener('click', () => {
            if (navList.classList.contains('active')) {
                navList.classList.remove('active');
                const icon = hamburger.querySelector('i');
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
    });

    // --- Search Logic ---
    const searchIcon = document.getElementById('search-icon');
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');

    searchIcon.addEventListener('click', (e) => {
        e.preventDefault();
        searchForm.classList.toggle('hidden');
        if (!searchForm.classList.contains('hidden')) {
            searchInput.focus();
        }
    });

    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const searchTerm = searchInput.value.trim().toLowerCase();
        if(!searchTerm) return;

        document.querySelectorAll('.product-gallery-card').forEach(card => {
            const productName = card.querySelector('.product-gallery-title').textContent.toLowerCase();
            const productDescription = card.querySelector('.product-gallery-desc').textContent.toLowerCase();
            if (productName.includes(searchTerm) || productDescription.includes(searchTerm)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
        document.getElementById('novedades').scrollIntoView({ behavior: 'smooth' });
    });

    // --- Modal Elements & Logic ---
    const loginModal = document.getElementById('login-modal');
    const loginIcon = document.getElementById('login-icon');
    const showRegisterLink = document.getElementById('show-register');
    const showLoginLink = document.getElementById('show-login');
    const loginFormContainer = document.getElementById('login-form');
    const registerFormContainer = document.getElementById('register-form-container');

    const openModal = () => loginModal.classList.remove('hidden');
    const closeModal = () => {
        loginModal.classList.add('hidden');
        loginFormContainer.classList.remove('hidden');
        registerFormContainer.classList.add('hidden');
    };

    loginIcon.addEventListener('click', (e) => {
        e.preventDefault();
        openModal();
    });
    loginModal.addEventListener('click', (e) => {
        if (e.target === loginModal || e.target.classList.contains('close-modal')) {
            closeModal();
        }
    });

    showRegisterLink.addEventListener('click', (e) => {
        e.preventDefault();
        loginFormContainer.classList.add('hidden');
        registerFormContainer.classList.remove('hidden');
    });

    showLoginLink.addEventListener('click', (e) => {
        e.preventDefault();
        registerFormContainer.classList.add('hidden');
        loginFormContainer.classList.remove('hidden');
    });

    // --- Helpers for API ---
    async function api(path, opts = {}) {
        const res = await fetch(path, {
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            ...opts,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.ok === false) {
            const msg = data.error || "Error inesperado";
            throw new Error(msg);
        }
        return data;
    }

    // --- Auth Logic via Flask Session ---
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const loginError = document.getElementById('login-error');
    const registerError = document.getElementById('register-error');
    const logoutBtn = document.getElementById('logout-btn');

    // LOGIN CORREGIDO
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({ email, password })
            });
            
            const data = await response.json();
            
            if (data.ok) {
                // Si hay redirect (admin), redirigir
                if (data.redirect) {
                    window.location.href = data.redirect;
                } else {
                    // Usuario normal: actualizar UI y cerrar modal
                    updateUIForUser(data.user);
                    closeModal();
                }
                loginError.classList.add('hidden');
            } else {
                throw new Error(data.error || "Credenciales inválidas");
            }
        } catch (err) {
            loginError.textContent = err.message;
            loginError.classList.remove('hidden');
        }
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const name = document.getElementById('register-name').value;
            const email = document.getElementById('register-email').value;
            const password = document.getElementById('register-password').value;
            const { user } = await api('/api/register', { method: 'POST', body: JSON.stringify({ name, email, password }) });
            updateUIForUser(user);
            closeModal();
            registerError.classList.add('hidden');
        } catch (err) {
            registerError.textContent = err.message;
            registerError.classList.remove('hidden');
        }
    });

    logoutBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        await api('/api/logout', { method: 'POST', body: JSON.stringify({}) });
        updateUIForUser(null);
    });

    function updateUIForUser(currentUser) {
        const authLinks = document.getElementById('auth-links');
        const userInfo = document.getElementById('user-info');
        const welcomeMsg = document.getElementById('welcome-msg');
        const adminLink = document.getElementById('admin-link');
        const body = document.body;

        if (currentUser) {
            authLinks.classList.add('hidden');
            userInfo.classList.remove('hidden');
            welcomeMsg.textContent = `Hola, ${currentUser.name}`;
            if(currentUser.role === 'admin') {
                adminLink.classList.remove('hidden');
                body.classList.add('admin-view');
            } else {
                adminLink.classList.add('hidden');
                body.classList.remove('admin-view');
            }
        } else {
            authLinks.classList.remove('hidden');
            userInfo.classList.add('hidden');
            adminLink.classList.add('hidden');
            body.classList.remove('admin-view');
        }
    }

    // --- Restore session on load ---
    (async () => {
        try {
            const { user } = await api('/api/session');
            updateUIForUser(user);
        } catch {}
    })();

    // --- Cart Logic (Session-backed) ---
    const cartIcon = document.getElementById('cart-icon');
    const cartSidebar = document.getElementById('cart-sidebar');
    const closeCartBtn = document.getElementById('close-cart');
    const cartItemsContainer = document.getElementById('cart-items');
    const cartCount = document.getElementById('cart-count');
    const cartSubtotal = document.getElementById('cart-subtotal');

    const openCart = () => cartSidebar.classList.remove('hidden');
    const closeCart = () => cartSidebar.classList.add('hidden');

    cartIcon.addEventListener('click', async (e) => {
        e.preventDefault();
        await refreshCart();
        openCart();
    });
    closeCartBtn.addEventListener('click', closeCart);
    cartSidebar.addEventListener('click', (e) => {
        if (e.target === cartSidebar) {
            closeCart();
        }
    });

    // --- Add to cart for gallery cards (delegación de eventos) ---
    // Modal de detalles reutilizando el login modal
    const detailsModal = document.createElement('div');
    detailsModal.className = 'modal-overlay hidden';
    detailsModal.innerHTML = `
        <div class="modal-content">
            <button class="close-modal">&times;</button>
            <div id="details-content"></div>
        </div>
    `;
    document.body.appendChild(detailsModal);
    const detailsContent = detailsModal.querySelector('#details-content');
    detailsModal.addEventListener('click', (e) => {
        if (e.target === detailsModal || e.target.classList.contains('close-modal')) {
            detailsModal.classList.add('hidden');
        }
    });

    document.addEventListener('click', async (e) => {
        if (e.target.classList.contains('add-to-cart')) {
            const card = e.target.closest('.product-gallery-card');
            if (!card) return;
            const product = {
                id: card.dataset.id,
                quantity: 1
            };
            await api('/api/cart/add', { method: 'POST', body: JSON.stringify(product) });
            await refreshCart();
            openCart();
        }
        if (e.target.classList.contains('view-details')) {
            const card = e.target.closest('.product-gallery-card');
            if (!card) return;
            const id = card.dataset.id;
            const name = card.querySelector('.product-gallery-title')?.textContent || '';
            const price = card.querySelector('.product-gallery-price')?.textContent || '';
            const img = card.querySelector('img')?.src || '';
            const desc = card.querySelector('.product-gallery-desc')?.textContent || '';
            detailsContent.innerHTML = `
                <img src="${img}" alt="${name}" style="max-width:220px;display:block;margin:0 auto 1rem auto;border-radius:16px;box-shadow:0 2px 12px #d9669022;">
                <h2 style="text-align:center;color:#d96690;">${name}</h2>
                <p style="text-align:center;font-size:1.1rem;color:#333;margin-bottom:1rem;">${desc}</p>
                <div style="text-align:center;font-size:1.3rem;font-weight:700;color:#d96690;margin-bottom:1.2rem;">${price}</div>
                <button class="btn btn-primary add-to-cart-modal" data-id="${id}" style="display:block;margin:0 auto;">Agregar al carrito</button>
            `;
            detailsModal.classList.remove('hidden');
            detailsContent.querySelector('.add-to-cart-modal').addEventListener('click', async () => {
                await api('/api/cart/add', { method: 'POST', body: JSON.stringify({ id, quantity: 1 }) });
                await refreshCart();
                openCart();
                detailsModal.classList.add('hidden');
            });
        }
    });

    async function refreshCart() {
        const data = await api('/api/cart');
        renderCart(data.items);
        cartCount.textContent = data.count;
        cartSubtotal.textContent = data.subtotal;
    }

    function renderCart(items) {
        cartItemsContainer.innerHTML = '';
        if (!items || items.length === 0) {
            cartItemsContainer.innerHTML = '<p class="empty-cart-msg">Tu carrito está vacío.</p>';
            return;
        }
        items.forEach(item => {
            const itemEl = document.createElement('div');
            itemEl.classList.add('cart-item');
            // Asegura que la ruta de la imagen incluya /static/
            let imgSrc = item.image;
            if (imgSrc && !imgSrc.startsWith('/static/')) {
                imgSrc = '/static/' + imgSrc.replace(/^\/*/, '');
            }
            itemEl.innerHTML = `
                <img src="${imgSrc}" alt="${item.name}" style="max-width:80px;max-height:80px;border-radius:10px;margin-right:12px;object-fit:cover;">
                <div class="cart-item-info">
                    <h4>${item.name}</h4>
                    <p>${item.price}</p>
                    <div class="quantity-controls">
                        <button class="quantity-btn" data-id="${item.id}" data-action="decrease">-</button>
                        <span>${item.quantity}</span>
                        <button class="quantity-btn" data-id="${item.id}" data-action="increase">+</button>
                    </div>
                </div>
                <button class="remove-item" data-id="${item.id}">&times;</button>
            `;
            cartItemsContainer.appendChild(itemEl);
        });
    }

    cartItemsContainer.addEventListener('click', async (e) => {
        const target = e.target;
        if(target.classList.contains('quantity-btn')) {
            const id = target.dataset.id;
            const action = target.dataset.action;
            await api('/api/cart/update', { method: 'POST', body: JSON.stringify({ id, action }) });
            await refreshCart();
        }
        if(target.classList.contains('remove-item')) {
            const id = target.dataset.id;
            await api('/api/cart/remove', { method: 'POST', body: JSON.stringify({ id }) });
            await refreshCart();
        }
    });

    // --- Checkout Logic ---
    const checkoutBtn = document.querySelector('.btn-checkout');
    checkoutBtn.addEventListener('click', async () => {
        try {
            // Verificar sesión antes de checkout
            const session = await api('/api/session');
            if (!session.user) {
                alert('Debes iniciar sesión para finalizar la compra.');
                openModal(); // Mostrar modal de login
                return;
            }
            const res = await api('/api/checkout', { method: 'POST', body: JSON.stringify({}) });
            alert(res.message || '¡Gracias por tu compra!');
            await refreshCart();
            closeCart();
        } catch (err) {
            alert(err.message);
        }
    });

    // Initial cart state
    refreshCart().catch(()=>{});
});