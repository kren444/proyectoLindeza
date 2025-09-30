const PRODUCTS_KEY = 'makeup_products';

// Datos iniciales si no hay nada en localStorage
const initialProducts = [
    {
        id: 'prod1',
        name: 'Base de Maquillaje Líquida',
        description: 'Cobertura perfecta y acabado natural para todo tipo de piel. Larga duración y resistente al agua.',
        price: 29.99,
        stock: 50,
        sold: 120,
        image: 'https://images.unsplash.com/photo-1590155288535-234b162f2dbb?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=600'
    },
    {
        id: 'prod2',
        name: 'Paleta de Sombras "Sunset"',
        description: '12 tonos cálidos y vibrantes con acabados mate y brillantes, perfectos para looks de día y de noche.',
        price: 45.50,
        stock: 30,
        sold: 85,
        image: 'https://images.unsplash.com/photo-1583241801235-9d912a7813a0?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=600'
    },
    {
        id: 'prod3',
        name: 'Labial Rojo Intenso',
        description: 'Acabado mate aterciopelado de alta pigmentación. Fórmula cremosa que no reseca los labios.',
        price: 19.95,
        stock: 80,
        sold: 250,
        image: 'https://images.unsplash.com/photo-1599948123714-25a8a48b3992?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=600'
    },
    {
        id: 'prod4',
        name: 'Máscara de Pestañas Volumen',
        description: 'Consigue unas pestañas más largas y con volumen extremo al instante. Cepillo diseñado para no dejar grumos.',
        price: 15.00,
        stock: 120,
        sold: 300,
        image: 'https://images.unsplash.com/photo-1560790671-b765b8224155?ixlib=rb-4.0.3&q=85&fm=jpg&crop=entropy&cs=srgb&w=600'
    }
];

// Función para obtener todos los productos
export function getProducts() {
    const products = localStorage.getItem(PRODUCTS_KEY);
    if (!products) {
        // Si no hay productos, inicializa con los datos de ejemplo
        localStorage.setItem(PRODUCTS_KEY, JSON.stringify(initialProducts));
        return initialProducts;
    }
    return JSON.parse(products);
}

// Función para guardar todos los productos
export function saveProducts(products) {
    localStorage.setItem(PRODUCTS_KEY, JSON.stringify(products));
}

// Función para añadir o actualizar un producto
export function saveProduct(product) {
    const products = getProducts();
    const index = products.findIndex(p => p.id === product.id);

    if (index !== -1) {
        // Actualizar producto existente
        products[index] = product;
    } else {
        // Añadir nuevo producto
        product.id = `prod${new Date().getTime()}`; // Generar un ID único
        products.push(product);
    }

    saveProducts(products);
}

// Función para eliminar un producto
export function deleteProduct(productId) {
    let products = getProducts();
    products = products.filter(p => p.id !== productId);
    saveProducts(products);
}