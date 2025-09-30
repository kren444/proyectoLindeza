
from flask import Flask, render_template, jsonify, request, session # type: ignore
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
app.permanent_session_lifetime = timedelta(days=7)

# --- Simulated data stores (in-memory) ---
# Default admin user
USERS = {
    "admin@glamora.com": {"name": "Admin", "email": "admin@glamora.com", "password": "admin", "role": "admin"}
}

# Products (match the cards in index.html by id)
PRODUCTS = {
    "1": {"id": "1", "name": "Labial Matte", "price": 18.00, "image": "img/BASE MEDIA COBERTURA.jpg"},
    "2": {"id": "2", "name": "Paleta de Sombras", "price": 45.00, "image": "product2.png"},
    "3": {"id": "3", "name": "Base Fluida", "price": 35.00, "image": "product3.png"},
    "4": {"id": "4", "name": "Máscara Volumen", "price": 22.00, "image": "product4.png"},
}

# --- Helpers ---
def get_cart():
    return session.setdefault("cart", {})



def cart_summary(cart):
    items = []
    subtotal = 0.0
    total_qty = 0
    for pid, qty in cart.items():
        # Buscar en la lista de productos generados dinámicamente
        try:
            idx = int(pid) - 1
        except:
            continue
        # Usar los datos de productos generados en index()
        img_files = [
            'BASE MEDIA COBERTURA.jpg','BASE QUEEN.webp','BASE TRENDY.webp','BASE.jpg','BB CREAM.jpg','BRONZER.jpg','CONTORNO TRENDY.webp','CORRECOTR TRENDY.webp','CORRECTOR BLOM.png','CORRECTOR MAGIC.webp','CORRECTOR OJERA.webp','CORRECTOR VITAMINA E.jpg','CORRECTOR.jpg','DELINEADOR COLOR.webp','DELINEADOR LIQUIDO.jpg','DELINEADOR PLUMON.webp','DELINEADOR PROFESIONAL.webp','DELINEADOR.jpg','FIJADOR TRENDY CEJAS.webp','GEL 2 EN 1 CEJAS.jpg','GEL FIJADPR CEJAS.webp','ILIMINADOR POLVO.jpg','ILUMINADOR CREMA.jpg','ILUMINADOR LIQUI TRENDY.webp','ILUMINADOR LIQUIDO.jpg','ILUMINADOR TRENDY.webp','KIT LIP GLOSS.webp','LIP GLOSS ATENEA.webp','LIP GLOSS MYK.webp','LIP GLOSS TREND.webp','LIP GLOSS TRENDY.webp','PALETA CONTORNOS.jpg','PALETA SOMBRAS.jpg','PALETA.jpg','PESTAÑA SERENITY.jpg','PESTAÑINA LASH.jpg','PESTAÑINA PROSA.webp','PESTAÑINA.jpg','RUBOR CREMA.jpg','RUBOR LIQUID.jpg','RUBOR POLVO.jpg','RUBOR PRIMAVERA.webp','RUBOR STAR.webp','SOMBR SAFARI.webp','SOMBRA CHOCOLATE.webp','SOMBRAS BLOSSOM.webp','TINTA BLOOM.png','TINTA ESCARCHA.webp','TINTA.jpg','TINTA.png'
        ]
        if idx < 0 or idx >= len(img_files):
            continue
        nombre = img_files[idx].rsplit('.',1)[0].replace('_',' ').replace('-',' ')
        # Usar la lista de precios reales
        precios_reales = [28000,15000,26000,35000,22000,22000,19500,21900,24800,13900,16300,24000,18900,14000,10000,21000,26900,10500,13500,12000,18000,14600,21900,19500,13900,16000,28000,42000,15000,15900,13600,21900,26000,23400,18500,19000,22000,21000,21900,12600,13000,16700,24000,24900,27000,23000,18000,17900,10000,18000]
        precio = precios_reales[idx] if idx < len(precios_reales) else 20000
        imagen = 'img/' + img_files[idx]
        line_total = precio * qty
        subtotal += line_total
        total_qty += qty
        items.append({
            "id": str(idx+1),
            "name": nombre,
            "price": f"${precio:,.0f}",
            "image": imagen,
            "quantity": qty,
            "line_total": f"${line_total:,.0f}"
        })
    return {"items": items, "subtotal": f"${subtotal:,.0f}", "count": total_qty}

# --- Pages ---
@app.route("/")
def index():
    # Lista de imágenes y datos para las tarjetas
    img_files = [
        'BASE MEDIA COBERTURA.jpg','BASE QUEEN.webp','BASE TRENDY.webp','BASE.jpg','BB CREAM.jpg','BRONZER.jpg','CONTORNO TRENDY.webp','CORRECOTR TRENDY.webp','CORRECTOR BLOM.png','CORRECTOR MAGIC.webp','CORRECTOR OJERA.webp','CORRECTOR VITAMINA E.jpg','CORRECTOR.jpg','DELINEADOR COLOR.webp','DELINEADOR LIQUIDO.jpg','DELINEADOR PLUMON.webp','DELINEADOR PROFESIONAL.webp','DELINEADOR.jpg','FIJADOR TRENDY CEJAS.webp','GEL 2 EN 1 CEJAS.jpg','GEL FIJADPR CEJAS.webp','ILIMINADOR POLVO.jpg','ILUMINADOR CREMA.jpg','ILUMINADOR LIQUI TRENDY.webp','ILUMINADOR LIQUIDO.jpg','ILUMINADOR TRENDY.webp','KIT LIP GLOSS.webp','LIP GLOSS ATENEA.webp','LIP GLOSS MYK.webp','LIP GLOSS TREND.webp','LIP GLOSS TRENDY.webp','PALETA CONTORNOS.jpg','PALETA SOMBRAS.jpg','PALETA.jpg','PESTAÑA SERENITY.jpg','PESTAÑINA LASH.jpg','PESTAÑINA PROSA.webp','PESTAÑINA.jpg','RUBOR CREMA.jpg','RUBOR LIQUID.jpg','RUBOR POLVO.jpg','RUBOR PRIMAVERA.webp','RUBOR STAR.webp','SOMBR SAFARI.webp','SOMBRA CHOCOLATE.webp','SOMBRAS BLOSSOM.webp','TINTA BLOOM.png','TINTA ESCARCHA.webp','TINTA.jpg','TINTA.png'
    ]
    productos = []
    descripciones_bonitas = [
        "Descubre la magia de un acabado profesional y luminoso en tu piel.",
        "Realza tu belleza con tonos vibrantes y texturas suaves.",
        "Un toque de elegancia y color para cada ocasión especial.",
        "Transforma tu rutina con productos que cuidan y embellecen.",
        "Siente la frescura y el glamour en cada aplicación.",
        "Explora la tendencia y la innovación en maquillaje.",
        "Brilla con confianza y estilo único todos los días.",
        "La perfección en cada detalle para tu look ideal.",
        "Colores intensos y fórmulas de larga duración para ti.",
        "Haz que tu belleza sea inolvidable con cada producto Lindeza."
    ]
    precios = [28000,15000,26000,35000,22000,22000,19500,21900,24800,13900,16300,24000,18900,14000,10000,21000,26900,10500,13500,12000,18000,14600,21900,19500,13900,16000,28000,42000,15000,15900,13600,21900,26000,23400,18500,19000,22000,21000,21900,12600,13000,16700,24000,24900,27000,23000,18000,17900,10000,18000]
    nombres = [
        "base media cobertura myk", "base queen trendy", "base corrector trendy", "base alta cobertura myk", "bb cream myk", "paleta bronzer myk", "bronzer liquido trendy", "corrector magc trendy", "corrector bloomshell", "corrector magico  trendy", "corrector rebel girl trendy", "corrector vitamina e myk", "corrector myk", "delineadores plumon colores trendy", "delineador liquido myk", "delineador plumon duo trendy", "delineador profesional artist", "delineador duo myk", "fijador de cejas trendy", "gel 2 en 1 cejas myk", "gel fijador cejas melu", "paleta iluminadores myk", "stick iluminador en crema myk", "ilumniador liquido trendy", "iluminador liquido myk", "iluminador trendy", "kit lip gloss trendy", "lip gloss atenea", "drip gloss myk", "lip gloss duo trendy", "labial matte trendy", "paleta de contornos myk", "paleta de sombras rude myk", "paleta atraccion myk", "pestañina serenity myk", "pestañina lash myk", "pestañina prosa", "pestañina myk", "stick rubor en crema myk", "rubor liquido myk", "rubor en polvo myk", "paleta de rubor primavera trendy", "rubor liquido star trendy", "paleta de sombras safari trendy", "paleta de sombras chocolate trendy", "paleta de sombras bloomshell", "tinta kiss bloomshell", "tinta escarchada trendy", "tinta cherry bloom myk", "tinta kiss bloomshell"
    ]
    for idx, img in enumerate(img_files, start=1):
        nombre = (nombres[idx-1] if idx-1 < len(nombres) else img.rsplit('.',1)[0].replace('_',' ').replace('-',' ')).upper()
        descripcion = descripciones_bonitas[(idx-1) % len(descripciones_bonitas)]
        precio = precios[idx-1] if idx-1 < len(precios) else 20000
        # Asignar categoría automáticamente por nombre
        nombre_lower = nombre.lower()
        if any(word in nombre_lower for word in ['labial', 'lip', 'gloss']):
            categoria = 'Labios'
        elif any(word in nombre_lower for word in ['ojo', 'delineador', 'pestañina', 'sombras']):
            categoria = 'Ojos'
        elif any(word in nombre_lower for word in ['base', 'corrector', 'rubor', 'bronzer', 'rostro', 'iluminador', 'contornos']):
            categoria = 'Rostro'
        else:
            categoria = 'Otros'
        productos.append({
            'id': idx,
            'imagen': 'img/' + img,
            'nombre': nombre,
            'descripcion': descripcion,
            'precio': f"${precio:,.0f}",
            'categoria': categoria
        })
    return render_template("index.html", productos=productos)

# --- Auth API ---
@app.post("/api/register")
def api_register():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not name or not email or not password:
        return jsonify({"ok": False, "error": "Todos los campos son obligatorios."}), 400
    if email in USERS:
        return jsonify({"ok": False, "error": "Este correo ya está registrado."}), 400
    USERS[email] = {"name": name, "email": email, "password": password, "role": "user"}
    session["user"] = {"name": name, "email": email, "role": "user"}
    session.permanent = True
    return jsonify({"ok": True, "user": session["user"]})

@app.post("/api/login")
def api_login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    user = USERS.get(email)

    if not user or user["password"] != password:
        return jsonify({"ok": False, "error": "Credenciales inválidas."}), 401

    session["user"] = {"name": user["name"], "email": user["email"], "role": user["role"]}
    session.permanent = True
   #juu


    # 🚀 Administrador se redirige FUERA, usuario normal se queda
    if user["role"] == "admin":
        return jsonify({"ok": True, "user": session["user"], "redirect": "/admin"})
    else:
        return jsonify({"ok": True, "user": session["user"], "redirect": False})

    
@app.post("/api/logout")
def api_logout():
    session.pop("user", None)
    return jsonify({"ok": True})

@app.get("/api/session")
def api_session():
    return jsonify({"ok": True, "user": session.get("user")})

# --- Products API (optional) ---
@app.get("/api/products")
def api_products():
    return jsonify({"ok": True, "products": list(PRODUCTS.values())})

# --- Cart API ---
@app.get("/api/cart")
def api_cart():
    cart = get_cart()
    return jsonify({"ok": True, **cart_summary(cart)})

@app.post("/api/cart/add")
def api_cart_add():
    data = request.get_json(force=True)
    pid = str(data.get("id"))
    qty = int(data.get("quantity", 1))
    # Permitir cualquier producto generado dinámicamente
    try:
        idx = int(pid) - 1
        img_files = [
            'BASE MEDIA COBERTURA.jpg','BASE QUEEN.webp','BASE TRENDY.webp','BASE.jpg','BB CREAM.jpg','BRONZER.jpg','CONTORNO TRENDY.webp','CORRECOTR TRENDY.webp','CORRECTOR BLOM.png','CORRECTOR MAGIC.webp','CORRECTOR OJERA.webp','CORRECTOR VITAMINA E.jpg','CORRECTOR.jpg','DELINEADOR COLOR.webp','DELINEADOR LIQUIDO.jpg','DELINEADOR PLUMON.webp','DELINEADOR PROFESIONAL.webp','DELINEADOR.jpg','FIJADOR TRENDY CEJAS.webp','GEL 2 EN 1 CEJAS.jpg','GEL FIJADPR CEJAS.webp','ILIMINADOR POLVO.jpg','ILUMINADOR CREMA.jpg','ILUMINADOR LIQUI TRENDY.webp','ILUMINADOR LIQUIDO.jpg','ILUMINADOR TRENDY.webp','KIT LIP GLOSS.webp','LIP GLOSS ATENEA.webp','LIP GLOSS MYK.webp','LIP GLOSS TREND.webp','LIP GLOSS TRENDY.webp','PALETA CONTORNOS.jpg','PALETA SOMBRAS.jpg','PALETA.jpg','PESTAÑA SERENITY.jpg','PESTAÑINA LASH.jpg','PESTAÑINA PROSA.webp','PESTAÑINA.jpg','RUBOR CREMA.jpg','RUBOR LIQUID.jpg','RUBOR POLVO.jpg','RUBOR PRIMAVERA.webp','RUBOR STAR.webp','SOMBR SAFARI.webp','SOMBRA CHOCOLATE.webp','SOMBRAS BLOSSOM.webp','TINTA BLOOM.png','TINTA ESCARCHA.webp','TINTA.jpg','TINTA.png'
        ]
        if idx < 0 or idx >= len(img_files):
            return jsonify({"ok": False, "error": "Producto no encontrado."}), 404
    except:
        return jsonify({"ok": False, "error": "Producto no válido."}), 400
    cart = get_cart()
    cart[pid] = cart.get(pid, 0) + max(1, qty)
    session["cart"] = cart
    return jsonify({"ok": True, **cart_summary(cart)})

@app.post("/api/cart/update")
def api_cart_update():
    data = request.get_json(force=True)
    pid = str(data.get("id"))
    action = data.get("action")
    cart = get_cart()
    if pid not in cart:
        return jsonify({"ok": False, "error": "El producto no está en el carrito."}), 404
    if action == "increase":
        cart[pid] += 1
    elif action == "decrease":
        cart[pid] -= 1
        if cart[pid] <= 0:
            cart.pop(pid, None)
    else:
        return jsonify({"ok": False, "error": "Acción no válida."}), 400
    session["cart"] = cart
    return jsonify({"ok": True, **cart_summary(cart)})

@app.post("/api/cart/remove")
def api_cart_remove():
    data = request.get_json(force=True)
    pid = str(data.get("id"))
    cart = get_cart()
    cart.pop(pid, None)
    session["cart"] = cart
    return jsonify({"ok": True, **cart_summary(cart)})

@app.post("/api/checkout")
def api_checkout():
    cart = get_cart()
    if not cart:
        return jsonify({"ok": False, "error": "Tu carrito está vacío."}), 400
    # Simulate checkout
    session["cart"] = {}
    return jsonify({"ok": True, "message": "¡Gracias por tu compra! Este es un sitio de demostración."})


if __name__ == "__main__":
    app.run(debug=True)
