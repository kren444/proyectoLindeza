import { getProducts } from './data.js';

document.addEventListener('DOMContentLoaded', () => {
    const productGrid = document.getElementById('product-grid');

    function renderProducts() {
        const products = getProducts();
        productGrid.innerHTML = ''; // Limpiar la vista actual

        if (products.length === 0) {
            productGrid.innerHTML = '<p>No hay productos disponibles en este momento.</p>';
            return;
        }
        
        products.forEach(product => {
            const card = document.createElement('div');
            card.className = 'product-card';
            card.innerHTML = `
                <div class="product-image-container">
                    <img src="${product.image}" alt="${product.name}" class="product-image">
                </div>
                <div class="product-info">
                    <h3>${product.name}</h3>
                    <p class="description">${product.description || 'Sin descripción disponible.'}</p>
                    <div class="product-footer">
                        <p class="price">$${product.price.toFixed(2)}</p>
                        <button class="btn">Comprar</button>
                    </div>
                </div>
            `;
            productGrid.appendChild(card);
        });
    }

    // Renderizar productos al cargar la página
    renderProducts();
    
    // Escuchar cambios en el localStorage para actualizar en tiempo real
    window.addEventListener('storage', (event) => {
        if (event.key === 'makeup_products') {
            renderProducts();
        }
    });
});