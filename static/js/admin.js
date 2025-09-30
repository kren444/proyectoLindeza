import { getProducts, saveProduct, deleteProduct } from './data.js';

document.addEventListener('DOMContentLoaded', () => {
    // Proteger la ruta: si no está autenticado, redirigir al login
    if (sessionStorage.getItem('isAdminAuthenticated') !== 'true') {
        window.location.href = 'login.html';
        return;
    }

    const tableBody = document.getElementById('product-table-body');
    const modal = document.getElementById('product-modal');
    const modalTitle = document.getElementById('modal-title');
    const productForm = document.getElementById('product-form');
    const addProductBtn = document.getElementById('add-product-btn');
    const closeModalBtn = document.querySelector('.close-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const feedbackMessage = document.getElementById('feedback-message');
    
    const formFields = {
        id: document.getElementById('product-id'),
        name: document.getElementById('name'),
        description: document.getElementById('description'),
        price: document.getElementById('price'),
        stock: document.getElementById('stock'),
        sold: document.getElementById('sold'),
        image: document.getElementById('image'),
    };

    function renderTable() {
        const products = getProducts();
        tableBody.innerHTML = '';
        products.forEach(p => {
            const row = document.createElement('tr');
            const revenue = p.price * p.sold;
            row.innerHTML = `
                <td><img src="${p.image}" alt="${p.name}" class="product-table-img"></td>
                <td>${p.name}</td>
                <td class="description-cell" title="${p.description}">${p.description}</td>
                <td>$${p.price.toFixed(2)}</td>
                <td>${p.stock}</td>
                <td>${p.sold}</td>
                <td>$${revenue.toFixed(2)}</td>
                <td class="action-buttons">
                    <button class="btn btn-icon edit-btn" data-id="${p.id}" title="Editar"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-icon btn-danger delete-btn" data-id="${p.id}" title="Eliminar"><i class="fas fa-trash"></i></button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    function openModal(product = null) {
        productForm.reset();
        if (product) {
            modalTitle.textContent = 'Editar Producto';
            formFields.id.value = product.id;
            formFields.name.value = product.name;
            formFields.description.value = product.description;
            formFields.price.value = product.price;
            formFields.stock.value = product.stock;
            formFields.sold.value = product.sold;
            formFields.image.value = product.image;
        } else {
            modalTitle.textContent = 'Añadir Nuevo Producto';
            formFields.id.value = '';
        }
        modal.style.display = 'flex';
    }

    function closeModal() {
        modal.style.display = 'none';
    }

    function showFeedback(message, type = 'success') {
        feedbackMessage.textContent = message;
        feedbackMessage.className = `feedback-message ${type}`;
        feedbackMessage.style.display = 'block';

        setTimeout(() => {
            feedbackMessage.style.display = 'none';
        }, 3000);
    }

    function handleFormSubmit(e) {
        e.preventDefault();
        const product = {
            id: formFields.id.value,
            name: formFields.name.value,
            description: formFields.description.value,
            price: parseFloat(formFields.price.value),
            stock: parseInt(formFields.stock.value, 10),
            sold: parseInt(formFields.sold.value, 10),
            image: formFields.image.value,
        };
        const isNew = !product.id;
        saveProduct(product);
        renderTable();
        closeModal();
        showFeedback(isNew ? 'Producto añadido con éxito.' : 'Producto actualizado con éxito.');
    }

    function handleTableClick(e) {
        const target = e.target.closest('button');
        if (!target) return;

        const productId = target.dataset.id;

        if (target.classList.contains('edit-btn')) {
            const products = getProducts();
            const productToEdit = products.find(p => p.id === productId);
            if (productToEdit) {
                openModal(productToEdit);
            }
        }

        if (target.classList.contains('delete-btn')) {
            if (confirm('¿Estás seguro de que quieres eliminar este producto?')) {
                deleteProduct(productId);
                renderTable();
                showFeedback('Producto eliminado con éxito.', 'success');
            }
        }
    }
    
    function logout() {
        sessionStorage.removeItem('isAdminAuthenticated');
        window.location.href = 'login.html';
    }

    // Event Listeners
    addProductBtn.addEventListener('click', () => openModal());
    closeModalBtn.addEventListener('click', closeModal);
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });
    productForm.addEventListener('submit', handleFormSubmit);
    tableBody.addEventListener('click', handleTableClick);
    logoutBtn.addEventListener('click', logout);

    // Initial render
    renderTable();
});