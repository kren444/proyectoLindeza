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
            // read role and normalize to 'user' or 'admin'
            let role = document.getElementById('register-role')?.value || 'user';
            if (role === 'usuario') role = 'user';
            const { user } = await api('/api/register', { method: 'POST', body: JSON.stringify({ name, email, password, role }) });
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

    // If products are updated in admin, reload the page to show new products
    window.addEventListener('storage', (e) => {
        if (e.key === 'products_updated') {
            // small delay to allow DB commit propagation
            setTimeout(() => location.reload(), 300);
        }
    });

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
    // Create a payment modal (select payment method)
    const paymentModal = document.createElement('div');
    paymentModal.className = 'modal-overlay hidden';
    paymentModal.innerHTML = `
        <div class="modal-content" style="max-width:520px;">
            <button class="close-modal">&times;</button>
            <h2>Datos de envío y método de pago</h2>
            <div style="margin:12px 0;">
                <label style="display:block;margin-bottom:8px;">Teléfono / Celular:<br><input type="text" id="pay-phone" style="width:100%;padding:8px;margin-top:6px;"></label>
                <label style="display:block;margin-bottom:8px;">Dirección de envío:<br><input type="text" id="pay-address" style="width:100%;padding:8px;margin-top:6px;"></label>
            </div>
            <h3 style="margin-top:6px;">Selecciona método de pago</h3>
            <div style="margin:12px 0;">
                <label style="display:block;margin-bottom:8px;"><input type="radio" name="pay" value="card" checked> Tarjeta de crédito / débito</label>
                <label style="display:block;margin-bottom:8px;"><input type="radio" name="pay" value="paypal"> PayPal</label>
                <label style="display:block;margin-bottom:8px;"><input type="radio" name="pay" value="nequi"> Nequi (App / Código)</label>
                <label style="display:block;margin-bottom:8px;"><input type="radio" name="pay" value="efecty"> Efecty (pago en punto físico)</label>
                <label style="display:block;margin-bottom:8px;"><input type="radio" name="pay" value="bancolombia"> Transferencia Bancolombia</label>
                <label style="display:block;margin-bottom:8px;"><input type="radio" name="pay" value="transfiya"> Transferencia Transfiya</label>
            </div>
            <div id="card-fields" style="margin-top:8px;">
                <h4>Datos de tarjeta</h4>
                <input type="text" id="card-number" placeholder="Número de tarjeta" style="width:100%;padding:8px;margin:6px 0;">
                <div style="display:flex;gap:8px;"><input type="text" id="card-exp" placeholder="MM/AA" style="flex:1;padding:8px;"><input type="text" id="card-cvc" placeholder="CVC" style="width:120px;padding:8px;"></div>
            </div>
            <div style="margin-top:16px;text-align:right;">
                <button class="btn btn-secondary cancel-payment">Cancelar</button>
                <button class="btn btn-primary confirm-payment">Pagar ahora</button>
            </div>
            <p id="payment-error" class="error-message hidden" style="margin-top:12px;"></p>
        </div>
    `;
    document.body.appendChild(paymentModal);

    // Track pending checkout after login
    let pendingCheckout = false;

    function showPaymentModal() {
        document.getElementById('payment-error').classList.add('hidden');
        paymentModal.classList.remove('hidden');
    }
    function hidePaymentModal() { paymentModal.classList.add('hidden'); }

    paymentModal.addEventListener('click', (e) => {
        if (e.target === paymentModal || e.target.classList.contains('close-modal') || e.target.classList.contains('cancel-payment')) {
            hidePaymentModal();
        }
    });

    // After successful login via existing login form handler, show payment modal if pending
    const originalUpdateUIForUser = updateUIForUser;
    // Replace the local function so all local calls (login/register) run the wrapper
    updateUIForUser = function(user) {
        originalUpdateUIForUser(user);
        if (user && pendingCheckout) {
            pendingCheckout = false;
            showPaymentModal();
        }
    };

    checkoutBtn.addEventListener('click', async () => {
        try {
            const session = await api('/api/session');
            if (!session.user) {
                // Ask user to login first, then continue to payment
                pendingCheckout = true;
                openModal();
                return;
            }
            // Already logged in -> show payment selection
            showPaymentModal();
        } catch (err) {
            alert('Error comprobando sesión: ' + (err.message || err));
        }
    });

    // Confirm payment button -> call /api/checkout with chosen method
    // show/hide card fields depending on selected method
    paymentModal.addEventListener('change', (e) => {
        const chosen = paymentModal.querySelector('input[name="pay"]:checked')?.value || 'card';
        const cardFields = document.getElementById('card-fields');
        if (chosen === 'card') cardFields.style.display = 'block'; else cardFields.style.display = 'none';
    });

    paymentModal.querySelector('.confirm-payment').addEventListener('click', async () => {
        const chosen = paymentModal.querySelector('input[name="pay"]:checked')?.value || 'card';
        const paymentError = document.getElementById('payment-error');
        const phone = document.getElementById('pay-phone')?.value || '';
        const address = document.getElementById('pay-address')?.value || '';
        const cardNumber = document.getElementById('card-number')?.value || '';
        try {
            const body = { payment_method: chosen, phone: phone, address: address };
            if (chosen === 'card') {
                // basic validation
                if (!cardNumber || cardNumber.length < 12) throw new Error('Ingrese un número de tarjeta válido');
                body.card_number = cardNumber;
            }
            const res = await api('/api/checkout', { method: 'POST', body: JSON.stringify(body) });
            // If offline method, server returns instructions with QR or text
            if (res.instructions) {
                hidePaymentModal();
                showPaymentResult(res);
            } else {
                alert(res.message || 'Pago procesado. ¡Gracias!');
                hidePaymentModal();
                await refreshCart();
                closeCart();
            }
        } catch (err) {
            paymentError.textContent = err.message || 'Error procesando el pago';
            paymentError.classList.remove('hidden');
        }
    });

    // Payment result modal
    const paymentResultModal = document.createElement('div');
    paymentResultModal.className = 'modal-overlay hidden';
    paymentResultModal.innerHTML = `
        <div class="modal-content" style="max-width:560px;">
            <button class="close-modal">&times;</button>
            <div id="payment-result-body"></div>
            <div style="margin-top:12px;">
                <label style="display:block;font-weight:600;margin-bottom:6px;">Adjuntar comprobante (imagen o PDF):</label>
                <input type="file" id="proof-file" accept="image/*,.pdf" style="display:block;margin-bottom:8px;">
                <button id="upload-proof-btn" class="btn" style="margin-right:8px;">Subir comprobante</button>
                <span id="upload-status" style="margin-left:8px;color:#333"></span>
            </div>
            <div style="text-align:right;margin-top:12px;"><button class="btn btn-primary close-result">Cerrar</button></div>
        </div>
    `;
    document.body.appendChild(paymentResultModal);
    const paymentResultBody = paymentResultModal.querySelector('#payment-result-body');
    paymentResultModal.addEventListener('click', (e) => {
        if (e.target === paymentResultModal || e.target.classList.contains('close-modal') || e.target.classList.contains('close-result')) {
            paymentResultModal.classList.add('hidden');
        }
    });

    function showPaymentResult(res) {
        // res.instructions may contain .qr (data URI) and .text
        const inst = res.instructions || {};
        let html = `<h3>Instrucciones de pago</h3>`;
        if (inst.qr) {
            html += `<p>Escanea este código con la app correspondiente (Nequi) o guarda la imagen:</p>`;
            html += `<img src="${inst.qr}" alt="QR de pago" style="max-width:320px;display:block;margin:0 auto 12px;">`;
        }
        if (inst.text) html += `<p style="white-space:pre-wrap">${inst.text}</p>`;
        if (res.reference) html += `<p><strong>Referencia:</strong> ${res.reference}</p>`;
        if (res.amount) html += `<p><strong>Monto:</strong> ${res.amount}</p>`;
        paymentResultBody.innerHTML = html;
        paymentResultModal.classList.remove('hidden');
        // wire upload button
        const uploadBtn = document.getElementById('upload-proof-btn');
        const fileInput = document.getElementById('proof-file');
        const statusSpan = document.getElementById('upload-status');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', async () => {
                const f = fileInput.files[0];
                if (!f) { statusSpan.textContent = 'Seleccione un archivo primero.'; return; }
                statusSpan.textContent = 'Subiendo...';
                const form = new FormData();
                form.append('file', f);
                try {
                    const resp = await fetch(`/api/orders/${res.order_id}/upload_proof`, { method: 'POST', credentials: 'same-origin', body: form });
                    const data = await resp.json();
                    if (!resp.ok) throw new Error(data.error || 'upload failed');
                    statusSpan.textContent = 'Comprobante subido.';
                    // show link or image
                    if (data.url) {
                        const link = document.createElement('a'); link.href = data.url; link.textContent = 'Ver comprobante'; link.target = '_blank';
                        statusSpan.innerHTML = ''; statusSpan.appendChild(link);
                    }
                } catch (err) {
                    statusSpan.textContent = 'Error: ' + (err.message || err);
                }
            });
        }
    }

    // Initial cart state
    refreshCart().catch(()=>{});
});