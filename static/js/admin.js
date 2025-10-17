// Simple admin JS: list/products and CRUD via REST
async function api(path, opts = {}) {
    const res = await fetch(path, { credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, ...opts });
    // try to parse json body, but fallback to text
    let data = {};
    try { data = await res.json(); } catch(e) { try { const txt = await res.text(); data = txt ? { text: txt } : {}; } catch(e2) { data = {}; } }
    if (!res.ok) {
        const message = (data && (data.error || data.detail || data.message)) || `${res.status} ${res.statusText}`;
        const err = new Error(message);
        err.status = res.status;
        err.response = data;
        throw err;
    }
    return data;
}

async function listProducts() {
    const p = await api('/api/products', { method: 'GET' });
    return p;
}

async function fetchStatsAndUsers() {
    const stats = await api('/api/admin/stats');
    const users = await api('/api/admin/users');
    return { stats, users };
}

async function listOrders() {
    return await api('/api/admin/orders', { method: 'GET' });
}

function renderOrders(orders) {
    const container = document.getElementById('orders-list');
    if (!container) return;
    if (!orders || orders.length === 0) { container.innerHTML = '<p>No hay pedidos</p>'; return; }
    container.innerHTML = '';
    orders.forEach(o => {
        const div = document.createElement('div');
        div.style = 'background:#fff;padding:12px;border-radius:8px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;gap:12px';
        div.innerHTML = `
            <div style="flex:1">
                <div class="order-row-click" style="cursor:pointer"><strong>#${o.id}</strong> — ${o.user_email} — <em>${o.payment_method}</em></div>
                <div style="color:#666;margin-top:6px">Referencia: ${o.reference} — Monto: ${o.amount} — Estado: <strong>${o.status}</strong></div>
                <div style="margin-top:6px;color:#444">Tel: ${o.phone || '-'} — Dir: ${o.address || '-'}</div>
                <div style="margin-top:6px;color:#333">Items: ${o.items || ''} ${o.card_last4 ? (' — Tarjeta: ****'+o.card_last4) : ''}</div>
            </div>
            <div style="width:160px;text-align:right">
                <button class="btn btn-mark-paid" data-id="${o.id}" ${o.status==='paid'?'disabled':''}>Marcar pagado</button>
            </div>
        `;
        container.appendChild(div);
    });
}

// Admin: order detail modal
function openOrderDetail(oid) {
    (async ()=>{
        try {
            const data = await api('/api/admin/orders/' + oid);
            // create modal
            let modal = document.getElementById('order-detail-modal');
            if (!modal) {
                modal = document.createElement('div'); modal.id = 'order-detail-modal'; modal.className = 'modal-overlay';
                modal.innerHTML = `<div class="modal-content"><button class="close-modal">&times;</button><div id="order-detail-body"></div></div>`;
                document.body.appendChild(modal);
                modal.addEventListener('click', (e)=>{ if (e.target===modal || e.target.classList.contains('close-modal')) modal.classList.add('hidden'); });
            }
            const body = modal.querySelector('#order-detail-body');
            let html = `<h3>Pedido #${data.id}</h3>`;
            html += `<p><strong>Usuario:</strong> ${data.user_email}</p>`;
            html += `<p><strong>Método:</strong> ${data.payment_method}</p>`;
            html += `<p><strong>Referencia:</strong> ${data.reference}</p>`;
            html += `<p><strong>Monto:</strong> ${data.amount}</p>`;
            html += `<p><strong>Tel:</strong> ${data.phone || '-'}</p>`;
            html += `<p><strong>Dirección:</strong> ${data.address || '-'}</p>`;
            html += `<p><strong>Items:</strong> ${data.items || ''}</p>`;
            if (data.proof_path) html += `<p><strong>Comprobante:</strong> <a href="/uploads/${data.proof_path}" target="_blank">Ver</a></p>`;
            html += `<div style="margin-top:8px;"><label>Adjuntar/Remplazar comprobante: <input type="file" id="admin-proof-file" accept="image/*,.pdf"></label> <button id="admin-upload-proof" class="btn">Subir</button></div>`;
            html += `<div style="margin-top:8px;text-align:right"><button id="admin-mark-paid" class="btn">Marcar pagado</button></div>`;
            body.innerHTML = html;
            modal.classList.remove('hidden');
            modal.querySelector('#admin-upload-proof').addEventListener('click', async ()=>{
                const f = modal.querySelector('#admin-proof-file').files[0];
                if (!f) { alert('Seleccione un archivo'); return; }
                const form = new FormData(); form.append('file', f);
                try {
                    const res = await fetch(`/api/orders/${data.id}/upload_proof`, { method: 'POST', credentials: 'same-origin', body: form });
                    const j = await res.json(); if (!res.ok) throw new Error(j.error||'upload failed');
                    alert('Comprobante subido');
                    openOrderDetail(oid); // refresh modal
                } catch (err) { alert('Error: '+(err.message||err)); }
            });
            modal.querySelector('#admin-mark-paid').addEventListener('click', async ()=>{
                if (!confirm('Marcar pedido #' + data.id + ' como pagado?')) return;
                try {
                    await api('/api/admin/orders/' + data.id + '/mark_paid', { method: 'POST' });
                    alert('Pedido marcado como pagado');
                    modal.classList.add('hidden');
                    const orders = await listOrders(); renderOrders(orders);
                } catch (err) { alert('Error: ' + err.message); }
            });
        } catch (err) {
            alert('No se pudo cargar detalle del pedido: ' + err.message);
        }
    })();
}

function createRowForProduct(prod) {
    const tr = document.createElement('div');
    tr.className = 'product-row';
    tr.style.display = 'flex'; tr.style.justifyContent = 'space-between'; tr.style.alignItems = 'center'; tr.style.padding = '10px'; tr.style.borderBottom = '1px solid #eee';
    tr.innerHTML = `
        <div style="display:flex;gap:12px;align-items:center;flex:1">
            <img src="${normalizeImage(prod.imagen||prod.image||'')}" style="width:72px;height:72px;object-fit:cover;border-radius:8px;"/>
            <div>
                <div style="font-weight:700">${prod.nombre||prod.name||''}</div>
                <div style="font-size:0.9rem;color:#666">${prod.descripcion||prod.description||''}</div>
            </div>
        </div>
        <div style="width:160px;text-align:right">
            <div style="font-weight:700;color:#d96690">${prod.precio}</div>
            <div style="margin-top:8px;display:flex;gap:8px;justify-content:flex-end">
                <button class="btn btn-edit" data-id="${prod.id}">Editar</button>
                <button class="btn btn-danger btn-delete" data-id="${prod.id}">Eliminar</button>
            </div>
        </div>
    `;
    return tr;
}

function normalizeImage(img) {
    if (!img) return '/static/img/BASE.jpg';
    if (img.startsWith('http')) return img;
    // ensure it points to static path
    if (img.startsWith('/static/')) return img;
    if (img.startsWith('img/')) return '/static/' + img;
    if (img.indexOf('/') >= 0) return '/static/' + img.replace(/^\/*/, '');
    return '/static/img/' + img;
}

async function refreshProductsList() {
    const container = document.getElementById('products-list');
    container.innerHTML = 'Cargando...';
    try {
        const list = await listProducts();
        if (!Array.isArray(list)) {
            container.innerHTML = '<p>No hay productos</p>';
            return;
        }
        container.innerHTML = '';
        // Render each product as a vertical card row
        list.forEach(p => {
            const row = createRowForProduct(p);
            // build inner layout
            const mid = document.createElement('div'); mid.className = 'product-mid';
            const title = document.createElement('h4'); title.textContent = p.nombre || p.name || '';
            const desc = document.createElement('p'); desc.className = 'product-desc'; desc.textContent = p.descripcion || p.description || '';
            mid.appendChild(title); mid.appendChild(desc);
            const right = document.createElement('div'); right.className = 'product-right';
            const price = document.createElement('div'); price.className = 'price'; price.textContent = p.precio || p.price || '';
            const actions = document.createElement('div'); actions.className = 'actions';
            const editBtn = document.createElement('button'); editBtn.className = 'btn btn-edit'; editBtn.dataset.id = p.id; editBtn.textContent = 'Editar';
            const delBtn = document.createElement('button'); delBtn.className = 'btn btn-danger btn-delete'; delBtn.dataset.id = p.id; delBtn.textContent = 'Eliminar';
            actions.appendChild(editBtn); actions.appendChild(delBtn);
            right.appendChild(price); right.appendChild(actions);

            // image
            const img = document.createElement('img'); img.src = normalizeImage(p.imagen||p.image||''); img.alt = p.nombre||p.name||'';
            row.innerHTML = '';
            row.appendChild(img);
            row.appendChild(mid);
            row.appendChild(right);
            container.appendChild(row);
        });
    } catch (err) {
        console.error(err);
        container.innerHTML = '<p>Error cargando productos</p>';
    }
}

// Modal helpers
function openProductModal(ctx) {
    const modal = document.getElementById('product-modal');
    modal.classList.remove('hidden');
    const title = document.getElementById('product-modal-title');
    const idField = document.getElementById('product-id');
    // Clear previous error
    try { const errBox = document.getElementById('product-error'); if (errBox) { errBox.textContent = ''; errBox.style.display = 'none'; } } catch(e){}
    // Set fields safely (check elements exist before setting value)
    try {
        const nombreEl = document.getElementById('product-nombre'); if (nombreEl) nombreEl.value = ctx?.nombre||ctx?.name||'';
        const precioEl = document.getElementById('product-precio'); if (precioEl) precioEl.value = ctx?.precio||ctx?.price||ctx?.precio||'';
        const stockEl = document.getElementById('product-stock'); if (stockEl) stockEl.value = ctx?.stock||'';
        const imagenEl = document.getElementById('product-imagen'); if (imagenEl) imagenEl.value = ctx?.imagen||ctx?.image||'';
        const categoriaEl = document.getElementById('product-categoria'); if (categoriaEl) categoriaEl.value = ctx?.categoria||'';
        const descEl = document.getElementById('product-descripcion'); if (descEl) descEl.value = ctx?.descripcion||ctx?.description||'';
        if (idField) idField.value = ctx?.id || '';
    } catch (err) {
        console.error('openProductModal failed to populate fields', err);
        const errBox = document.getElementById('product-error');
        if (errBox) { errBox.textContent = 'No se pudieron cargar los campos del producto. Revisa la consola.'; errBox.style.display = 'block'; }
    }
    title.textContent = ctx ? 'Editar producto' : 'Nuevo producto';
}
function closeProductModal() { document.getElementById('product-modal').classList.add('hidden'); }

async function saveProductFromForm(e) {
    e.preventDefault();
    const id = document.getElementById('product-id').value;
    const body = {
        nombre: document.getElementById('product-nombre').value,
        descripcion: document.getElementById('product-descripcion').value,
        precio: parseFloat(document.getElementById('product-precio').value) || 0,
        imagen: document.getElementById('product-imagen').value,
        categoria: document.getElementById('product-categoria').value,
        stock: parseInt(document.getElementById('product-stock').value || '0', 10)
    };
    const saveBtn = document.getElementById('product-save');
    const originalText = saveBtn ? saveBtn.textContent : null;
    try {
        console.log('Saving product...', body, 'id=', id);
        if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Guardando...'; }
        let res;
        if (id) {
            res = await api('/api/products/' + id, { method: 'PUT', body: JSON.stringify(body) });
        } else {
            res = await api('/api/products', { method: 'POST', body: JSON.stringify(body) });
        }
    // success
    console.log('Save response:', res);
    // clear any previous error
    const errBox = document.getElementById('product-error'); if (errBox) { errBox.textContent = ''; errBox.style.display = 'none'; }
    closeProductModal();
    await refreshProductsList();
        // notify other tabs/pages that products changed so main page can reload
        try { localStorage.setItem('products_updated', Date.now()); } catch (e) {}
        // if user was not on admin page (rare), reload to show changes
        if (location.pathname !== '/admin') {
            location.reload();
        }
    } catch (err) {
        console.error('Save error:', err);
        const errBox = document.getElementById('product-error');
        let msg = 'Error al guardar producto: ' + (err.message || String(err));
        if (err.status) msg += ` (status: ${err.status})`;
        if (err.response) {
            try {
                // prefer server-provided detail/sql/params
                if (err.response.detail) msg += '\nDetalle: ' + err.response.detail;
                if (err.response.sql) msg += '\nSQL: ' + err.response.sql;
                if (err.response.params) msg += '\nPARAMS: ' + JSON.stringify(err.response.params);
            } catch (e) {
                msg += '\n' + JSON.stringify(err.response);
            }
        }
        if (errBox) { errBox.textContent = msg; errBox.style.display = 'block'; }
        console.error('Save response details:', err.response || null);
        // keep alert as fallback
        alert(msg);
    } finally {
        if (saveBtn) { saveBtn.disabled = false; if (originalText) saveBtn.textContent = originalText; }
    }
}

async function deleteProductById(id) {
    if (!confirm('¿Eliminar producto?')) return;
    try {
        console.log('Deleting product id=', id);
        const res = await api('/api/products/' + id, { method: 'DELETE' });
        console.log('Delete response', res);
        await refreshProductsList();
        try { localStorage.setItem('products_updated', Date.now()); } catch (e) {}
    } catch (err) {
        console.error('Delete error:', err);
        alert('Error al eliminar: ' + err.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    (async ()=>{
        // Fetch stats, users and monthly data, populate cards and draw charts
        try{
            const statsResp = await api('/api/admin/stats', { method: 'GET' });
            // populate simple stat cards (replace "Cargando...")
            document.getElementById('stat-users').textContent = statsResp.users ?? 0;
            document.getElementById('stat-admins').textContent = statsResp.admins ?? 0;
            document.getElementById('stat-products').textContent = statsResp.products ?? 0;

            // users list
            try{
                const users = await api('/api/admin/users');
                const usersList = document.getElementById('users-list');
                usersList.innerHTML = users.length ? `<ul>${users.map(u=>`<li>${u.nombre} — ${u.email}</li>`).join('')}</ul>` : '<p>No hay usuarios</p>';
            }catch(e){ console.error('users fetch', e); }

            // draw charts if Chart available
            const months = statsResp.months || [];
            const monthly_sales = statsResp.monthly_sales || [];
            const monthly_visits = statsResp.monthly_visits || [];
            // load Chart.js dynamically if needed
            if (typeof Chart === 'undefined') {
                await new Promise((resolve, reject) => {
                    const s = document.createElement('script');
                    s.src = 'https://cdn.jsdelivr.net/npm/chart.js';
                    s.onload = resolve; s.onerror = reject; document.head.appendChild(s);
                }).catch(err=>console.error('Chart.js load failed',err));
            }
            try{
                const ctxSales = document.getElementById('chart-sales').getContext('2d');
                new Chart(ctxSales, {
                    type: 'line',
                    data: {
                        labels: months,
                        datasets: [{ label: 'Ventas', data: monthly_sales, borderColor: '#d96690', backgroundColor: 'rgba(217,102,144,0.12)', tension: 0.2 }]
                    },
                    options: { responsive: true, plugins: { legend: { display: false } } }
                });
            }catch(e){ console.error('render sales chart', e); }
            try{
                const ctxVisits = document.getElementById('chart-visits').getContext('2d');
                new Chart(ctxVisits, {
                    type: 'bar',
                    data: {
                        labels: months,
                        datasets: [{ label: 'Visitas', data: monthly_visits, backgroundColor: 'rgba(217,102,144,0.18)', borderColor: '#f09bb3' }]
                    },
                    options: { responsive: true, plugins: { legend: { display: false } } }
                });
            }catch(e){ console.error('render visits chart', e); }
        }catch(err){ console.error('stats/users',err) }
        await refreshProductsList();
        // load orders
        try{
            const orders = await listOrders();
            renderOrders(orders);
        }catch(e){ console.error('orders fetch', e); document.getElementById('orders-list').innerHTML = '<p>Error cargando pedidos</p>'; }
    })();
    document.getElementById('btn-add-product').addEventListener('click', () => openProductModal(null));
    const btnSync = document.getElementById('btn-sync-products');
    if (btnSync) btnSync.addEventListener('click', async () => {
        if (!confirm('¿Insertar los productos predefinidos en la base de datos? Esto podría crear duplicados si ya existen.')) return;
        try {
            const res = await api('/api/admin/sync_products', { method: 'POST' });
            const inserted = res.inserted || 0;
            const names = res.inserted_names || [];
            const failed = res.failed || [];
            // Build a friendly message
            let msg = `Productos insertados: ${inserted}`;
            if (names.length) msg += "\n\nNombres insertados:\n" + names.join('\n');
            if (failed.length) {
                msg += "\n\nErrores:\n" + failed.map(f => `${f.nombre}: ${f.reason}`).join('\n');
            }
            // show results in a resizable alert-like window
            if (msg.length < 2000) {
                alert(msg);
            } else {
                // fallback to opening a new tab with details
                const w = window.open('', '_blank');
                w.document.body.style.whiteSpace = 'pre-wrap';
                w.document.title = 'Resultados sincronización';
                w.document.body.textContent = msg;
            }
            // Refresh products list
            await refreshProductsList();
        } catch (err) {
            alert('Error al sincronizar: ' + err.message);
        }
    });
    document.getElementById('close-product-modal').addEventListener('click', closeProductModal);
    const pf = document.getElementById('product-form'); if(pf) pf.addEventListener('submit', saveProductFromForm);
    document.getElementById('products-list').addEventListener('click', (e) => {
        const edit = e.target.closest('.btn-edit');
        if (edit) {
            const id = edit.dataset.id;
            // fetch product detail from API to ensure latest fields (descripcion etc.)
            (async () => {
                try {
                    const prod = await api('/api/products/' + id, { method: 'GET' });
                    openProductModal(prod);
                } catch (err) {
                    console.error('Failed to fetch product (single). Falling back to list fetch', err);
                    // show server error in modal error box
                    const errBox = document.getElementById('product-error');
                    if (errBox) {
                        let msg = 'No se pudo obtener detalles del producto: ' + (err.message || '');
                        if (err.response) msg += '\n' + JSON.stringify(err.response);
                        errBox.textContent = msg; errBox.style.display = 'block';
                    }
                    // fallback: try full list and find the product
                    try {
                        const list = await listProducts();
                        const prod = list.find(x => String(x.id) === String(id));
                        if (prod) openProductModal(prod);
                        else alert('Producto no encontrado en la lista.');
                    } catch (err2) {
                        console.error('Failed to fetch product list fallback', err2);
                        alert('No se pudo obtener detalles del producto. Revisa la consola.');
                    }
                }
            })();
            return;
        }
        const del = e.target.closest('.btn-delete');
        if (del) {
            deleteProductById(del.dataset.id);
        }
    });
    // bottom buttons
    const btnViewProducts = document.getElementById('btn-view-products');
    const btnViewUsers = document.getElementById('btn-view-users');
    const btnViewOrders = document.getElementById('btn-view-orders');
    if (btnViewProducts) btnViewProducts.addEventListener('click', async () => { window.scrollTo({top: document.getElementById('products-list').offsetTop - 100, behavior: 'smooth'}); });
    if (btnViewUsers) btnViewUsers.addEventListener('click', async () => { window.scrollTo({top: document.getElementById('users-list').offsetTop - 100, behavior: 'smooth'}); });
    if (btnViewOrders) btnViewOrders.addEventListener('click', async () => { alert('No hay pedidos implementados aún.'); });
    // handle mark paid clicks inside orders list
    document.getElementById('orders-list').addEventListener('click', async (e) => {
        const btn = e.target.closest('.btn-mark-paid');
        if (!btn) return;
        const id = btn.dataset.id;
        if (!confirm('Marcar pedido #' + id + ' como pagado?')) return;
        try {
            await api('/api/admin/orders/' + id + '/mark_paid', { method: 'POST' });
            // refresh orders list
            const orders = await listOrders(); renderOrders(orders);
        } catch (err) { alert('Error marcando pagado: ' + err.message); }
    });

    // open detail when clicking row
    document.getElementById('orders-list').addEventListener('click', (e) => {
        const clickRow = e.target.closest('.order-row-click');
        if (clickRow) {
            const parent = clickRow.closest('[data-id]') || clickRow.closest('div');
            // try to find id from nearby button
            const btn = clickRow.closest('div').querySelector('.btn-mark-paid');
            let id = btn ? btn.dataset.id : null;
            // fallback: parse from text
            if (!id) {
                const m = clickRow.textContent.match(/#(\d+)/);
                id = m ? m[1] : null;
            }
            if (id) openOrderDetail(id);
        }
    });
    // logout already wired on template but ensure it triggers API
    const logout = document.getElementById('logout-btn');
    if (logout) logout.addEventListener('click', async (e) => { e.preventDefault(); await api('/api/logout',{method:'POST'}); window.location.href = '/'; });
});