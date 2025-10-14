from flask import Flask, render_template, jsonify, request, session # type: ignore
from datetime import timedelta, datetime
import random
import os
import pymysql
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
try:
    from passlib.hash import scrypt as passlib_scrypt
except Exception:
    passlib_scrypt = None

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
app.permanent_session_lifetime = timedelta(days=7)


def get_mysql_conn():
    """Try to obtain a pymysql connection.
    Priority:
      1) Environment variables MYSQL_HOST/USER/PASSWORD/DB
      2) Local default: host=localhost, user=root, password='' , db='lindeza'
    Returns a connection or None if cannot connect.
    """
    mysql_host = os.environ.get('MYSQL_HOST')
    mysql_user = os.environ.get('MYSQL_USER')
    mysql_password = os.environ.get('MYSQL_PASSWORD')
    mysql_db = os.environ.get('MYSQL_DB')

    # Try env vars first (require host,user,db)
    if mysql_host and mysql_user and mysql_db:
        try:
            return pymysql.connect(host=mysql_host, user=mysql_user, password=mysql_password or '', db=mysql_db, cursorclass=pymysql.cursors.DictCursor)
        except Exception:
            pass

    # Fallback to common local defaults used by many phpMyAdmin installs
    try:
        return pymysql.connect(host='localhost', user='root', password='', db='lindeza', cursorclass=pymysql.cursors.DictCursor)
    except Exception:
        return None


def get_metrics_conn():
    """Return a sqlite3 connection to store lightweight metrics (login events, product views).
    Uses the repo-local data.db file so it persists across restarts without touching MySQL.
    """
    db_path = os.path.join(os.path.dirname(__file__), 'data.db')
    conn = sqlite3.connect(db_path, timeout=5)
    conn.row_factory = sqlite3.Row
    # Ensure visits table exists
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                role TEXT,
                event TEXT,
                product_id TEXT,
                ts DATETIME
            )
        ''')
        conn.commit()
    except Exception:
        pass
    return conn


def record_visit(email, role, event, product_id=None):
    try:
        conn = get_metrics_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO visits (email, role, event, product_id, ts) VALUES (?,?,?,?,?)', (email, role, event, product_id, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
    except Exception:
        # swallow metrics errors - should not break login flow
        print('metrics write failed')

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


def generate_products():
    """Return the list of products used by the site (same data as index page).
    Each product is a dict with fields: id, imagen, nombre, descripcion, precio (formatted), precio_val (numeric), categoria
    """
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
        "base media cobertura myk", "base queen trendy", "base corrector trendy", "base alta cobertura myk", "bb cream myk", "paleta bronzer myk", "bronzer liquido trendy", "corrector magc trendy", "corrector bloomshell", "corrector magico  trendy", "corrector rebel girl trendy", "corrector vitamina e myk", "corrector myk", "delineadores plumon colores trendy", "delineador liquido myk", "delineador plumon duo trendy", "delineador profesional artist", "delineador duo myk", "fijador de cejas trendy", "gel 2 en 1 cejas myk", "gel fijador cejas melu", "paleta iluminadores myk", "stick iluminador en crema myk", "ilumniador liquido trendy", "iluminador liquido myk", "iluminador trendy", "kit lip gloss trendy", "lip gloss atenea", "drip gloss myk", "lip gloss duo trendy", "labial matte trendy", "paleta de contornos myk", "paleta de sombras rude myk", "paleta atraccion myk", "pestañina serenity myk", "pestañina lash myk", "pestañina prosa", "pestañina myk", "stick rubor en crema myk", "rubor liquido myk", "rubur en polvo myk", "paleta de rubor primavera trendy", "rubor liquido star trendy", "paleta de sombras safari trendy", "paleta de sombras chocolate trendy", "paleta de sombras bloomshell", "tinta kiss bloomshell", "tinta escarchada trendy", "tinta cherry bloom myk", "tinta kiss bloomshell"
    ]
    for idx, img in enumerate(img_files, start=1):
        nombre = (nombres[idx-1] if idx-1 < len(nombres) else img.rsplit('.',1)[0].replace('_',' ').replace('-',' ')).upper()
        descripcion = descripciones_bonitas[(idx-1) % len(descripciones_bonitas)]
        precio_val = precios[idx-1] if idx-1 < len(precios) else 20000
        precio = f"${precio_val:,.0f}"
        nombre_upper = nombre
        # Asignar categoría automáticamente por nombre
        nombre_lower = nombre_upper.lower()
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
            'nombre': nombre_upper,
            'descripcion': descripcion,
            'precio': precio,
            'precio_val': precio_val,
            'categoria': categoria
        })
    return productos
@app.route("/")
def index():
    # Attempt to read products from DB; fallback to generated list
    conn = get_mysql_conn()
    productos = []
    if conn:
        try:
            cur = conn.cursor(pymysql.cursors.DictCursor)
            tried = ['producto', 'productos', 'productos_catalogo', 'items']
            rows = []
            for t in tried:
                try:
                    cur.execute(f"SELECT * FROM {t} LIMIT 100")
                    rows = cur.fetchall()
                    if rows:
                        break
                except Exception:
                    rows = []
            # Normalize DB rows to template-friendly dicts
            for r in rows:
                imagen = r.get('imagen') or r.get('image') or ''
                # If image is a filename without folder, prefix with img/
                if imagen and not (imagen.startswith('http') or '/' in imagen):
                    imagen = 'img/' + imagen
                # If still empty, use a placeholder
                if not imagen:
                    imagen = 'img/BASE.jpg'
                precio_val = r.get('precio') if r.get('precio') is not None else r.get('price')
                precio = f"${int(precio_val):,}.00" if precio_val is not None else '$0.00'
                productos.append({
                    'id': r.get('id'),
                    'imagen': imagen,
                    'nombre': r.get('nombre') or r.get('name'),
                    'descripcion': r.get('descripcion') or r.get('description') or '',
                    'precio': precio,
                    'categoria': r.get('categoria') or r.get('category') or ''
                })
            try:
                cur.close()
            except Exception:
                pass
        except Exception:
            productos = generate_products()
        try:
            conn.close()
        except Exception:
            pass
    else:
        productos = generate_products()

    # Ensure every producto.imagen is prefixed correctly for url_for('static') in template
    for p in productos:
        img = p.get('imagen') or ''
        if img and not (img.startswith('/') or img.startswith('http')) and not img.startswith('img/'):
            p['imagen'] = 'img/' + img
        if not img:
            p['imagen'] = 'img/BASE.jpg'

    return render_template("index.html", productos=productos)

# --- Auth API ---
@app.post("/api/register")
def api_register():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "user")
    if not name or not email or not password:
        return jsonify({"ok": False, "error": "Todos los campos son obligatorios."}), 400
    # Try to save to MySQL if configured
    mysql_host = os.environ.get('MYSQL_HOST')
    mysql_user = os.environ.get('MYSQL_USER')
    mysql_password = os.environ.get('MYSQL_PASSWORD')
    mysql_db = os.environ.get('MYSQL_DB')

    hashed = generate_password_hash(password)

    # Always require MySQL: try to get a connection (env vars or sensible defaults)
    conn = get_mysql_conn()
    if not conn:
        return jsonify({"ok": False, "error": "No se pudo conectar a la base de datos MySQL. Revisa MYSQL_HOST/USER/PASSWORD/DB o la configuración local."}), 500

    try:
        with conn.cursor() as cur:
            table = 'administradores' if role == 'admin' else 'usuarios'
            cur.execute(f'SELECT COUNT(1) AS c FROM {table} WHERE LOWER(email)=%s', (email,))
            exists = cur.fetchone()
            if exists and exists.get('c', 0) > 0:
                conn.close()
                return jsonify({"ok": False, "error": "Este correo ya está registrado."}), 400
            if table == 'usuarios':
                cur.execute(f"INSERT INTO {table} (nombre,email,password,rol) VALUES (%s,%s,%s,%s)", (name, email, hashed, role))
            else:
                cur.execute(f"INSERT INTO {table} (nombre,email,password) VALUES (%s,%s,%s)", (name, email, hashed))
            conn.commit()
        conn.close()
        session["user"] = {"name": name, "email": email, "role": role}
        session.permanent = True
        return jsonify({"ok": True, "user": session["user"]})
    except Exception as e:
        # Return DB error so caller sees why insert failed
        try:
            conn.close()
        except Exception:
            pass
        print('DB register error:', e)
        return jsonify({"ok": False, "error": "DB error: " + str(e)}), 500

@app.post("/api/login")
def api_login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    # Try MySQL using the shared helper (this supports env vars or local fallback)
    conn = get_mysql_conn()
    if conn:
        try:
            with conn.cursor() as cur:
                # 1) Check administradores
                cur.execute('SELECT nombre,email,password FROM administradores WHERE LOWER(email)=%s LIMIT 1', (email,))
                row = cur.fetchone()
                if row:
                    stored = row.get('password') or ''
                    # scrypt via passlib if available
                    if stored.startswith('scrypt:') and passlib_scrypt is not None:
                        try:
                            if passlib_scrypt.verify(password, stored):
                                session["user"] = {"name": row.get('nombre'), "email": row.get('email'), "role": "admin"}
                                session.permanent = True
                                conn.close()
                                return jsonify({"ok": True, "user": session["user"], "redirect": "/admin"})
                        except Exception:
                            pass
                    # Werkzeug-style pbkdf2
                    if stored.startswith('pbkdf2:') or (stored and len(stored) > 40):
                        if check_password_hash(stored, password):
                            session["user"] = {"name": row.get('nombre'), "email": row.get('email'), "role": "admin"}
                            session.permanent = True
                            # record admin login metric
                            try: record_visit(row.get('email'), 'admin', 'login')
                            except: pass
                            conn.close()
                            return jsonify({"ok": True, "user": session["user"], "redirect": "/admin"})
                    # Plaintext fallback
                    if stored == password:
                        session["user"] = {"name": row.get('nombre'), "email": row.get('email'), "role": "admin"}
                        session.permanent = True
                        conn.close()
                        return jsonify({"ok": True, "user": session["user"], "redirect": "/admin"})

                # 2) Check usuarios
                cur.execute('SELECT nombre,email,password,rol FROM usuarios WHERE LOWER(email)=%s LIMIT 1', (email,))
                urow = cur.fetchone()
                if urow:
                    stored = urow.get('password') or ''
                    if stored.startswith('scrypt:') and passlib_scrypt is not None:
                        try:
                            if passlib_scrypt.verify(password, stored):
                                session["user"] = {"name": urow.get('nombre'), "email": urow.get('email'), "role": urow.get('rol') or 'user'}
                                session.permanent = True
                                conn.close()
                                return jsonify({"ok": True, "user": session["user"], "redirect": False})
                        except Exception:
                            pass
                    if stored.startswith('pbkdf2:') or (stored and len(stored) > 40):
                        if check_password_hash(stored, password):
                            session["user"] = {"name": urow.get('nombre'), "email": urow.get('email'), "role": urow.get('rol') or 'user'}
                            session.permanent = True
                            # record user login metric
                            try: record_visit(urow.get('email'), urow.get('rol') or 'user', 'login')
                            except: pass
                            conn.close()
                            return jsonify({"ok": True, "user": session["user"], "redirect": False})
                    if stored == password:
                        session["user"] = {"name": urow.get('nombre'), "email": urow.get('email'), "role": urow.get('rol') or 'user'}
                        session.permanent = True
                        try: record_visit(urow.get('email'), urow.get('rol') or 'user', 'login')
                        except: pass
                        conn.close()
                        return jsonify({"ok": True, "user": session["user"], "redirect": False})
            conn.close()
        except Exception:
            # If anything goes wrong with DB, fall back to in-memory
            try:
                conn.close()
            except Exception:
                pass

    # Fallback: in-memory USERS dictionary
    user = USERS.get(email)
    if not user or not check_password_hash(user.get("password", "")) and user.get("password") != password:
        # Support legacy plain-text password in USERS (original demo)
        if not user or user.get("password") != password:
            return jsonify({"ok": False, "error": "Credenciales inválidas."}), 401

    # If stored in-memory password is a hash, use it; otherwise equality already passed
    if user:
        stored_pw = user.get("password")
        if stored_pw and stored_pw.startswith('pbkdf2:'):
            if not check_password_hash(stored_pw, password):
                return jsonify({"ok": False, "error": "Credenciales inválidas."}), 401

        session["user"] = {"name": user["name"], "email": user["email"], "role": user["role"]}
        session.permanent = True
        try: record_visit(user.get('email'), user.get('role'), 'login')
        except: pass
        if user["role"] == "admin":
            return jsonify({"ok": True, "user": session["user"], "redirect": "/admin"})
        else:
            return jsonify({"ok": True, "user": session["user"], "redirect": False})

    
@app.route('/admin')
def admin_page():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return "Not authorized", 403
    # Pass user explicitly to the template so templates that reference `user` won't crash
    return render_template('admin.html', user=user)


@app.route('/api/admin/stats')
def api_admin_stats():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    # Prefer direct counts from MySQL tables for admins, users and products
    conn = get_mysql_conn()
    if not conn:
        return jsonify({'error': 'db connection failed'}), 500

    users = admins = products = 0
    try:
        cur = conn.cursor()
        try:
            cur.execute("SELECT COUNT(*) FROM usuarios")
            users = int(cur.fetchone()[0] or 0)
        except Exception:
            users = 0
        try:
            cur.execute("SELECT COUNT(*) FROM administradores")
            admins = int(cur.fetchone()[0] or 0)
        except Exception:
            admins = 0 

        # Probe common product table names
        product_tables = ['productos', 'producto', 'products', 'items', 'productos_catalogo']
        for t in product_tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                products = int(cur.fetchone()[0] or 0)
                break
            except Exception:
                products = 0
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

    # Keep sales and monthly synthetic series for charting placeholders
    sales = 0
    months = []
    monthly_sales = []
    monthly_visits = []
    today = datetime.utcnow()
    for i in range(11, -1, -1):
        y = today.year
        mnum = today.month - i
        while mnum <= 0:
            mnum += 12
            y -= 1
        label = datetime(y, mnum, 1).strftime('%b %Y')
        months.append(label)
        monthly_sales.append(random.randint(20, 220))
        monthly_visits.append(random.randint(800, 5200))

    return jsonify({'users': users, 'admins': admins, 'products': products, 'sales': sales, 'months': months, 'monthly_sales': monthly_sales, 'monthly_visits': monthly_visits})


@app.route('/api/admin/users')
def api_admin_users():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    conn = get_mysql_conn()
    if not conn:
        return jsonify({'error': 'db connection failed'}), 500
    cur = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cur.execute("SELECT nombre, email, rol FROM usuarios")
        rows = cur.fetchall()
    except Exception:
        rows = []
    cur.close()
    try:
        conn.close()
    except Exception:
        pass
    return jsonify(rows)


@app.route('/api/admin/products')
def api_admin_products():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    conn = get_mysql_conn()
    if not conn:
        return jsonify({'error': 'db connection failed'}), 500
    cur = conn.cursor(pymysql.cursors.DictCursor)
    tried = ['producto', 'productos', 'productos_catalogo', 'products', 'items']
    rows = []
    for t in tried:
        try:
            cur.execute(f"SELECT * FROM {t} LIMIT 100")
            rows = cur.fetchall()
            if rows:
                break
        except Exception:
            rows = []
    cur.close()
    try:
        conn.close()
    except Exception:
        pass
    return jsonify(rows)


@app.route('/api/admin/sync_products', methods=['POST'])
def api_admin_sync_products():
    """Insert generated site products into the DB table 'producto' (or 'productos') if they don't exist yet.
    This is idempotent: it will skip products with the same nombre.
    """
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    conn = get_mysql_conn()
    if not conn:
        return jsonify({'error': 'db connection failed'}), 500
    products = generate_products()
    cur = conn.cursor()
    # Prefer 'producto' table if present
    target_table = None
    for t in ['producto', 'productos']:
        try:
            cur.execute(f"SELECT 1 FROM {t} LIMIT 1")
            target_table = t
            break
        except Exception:
            target_table = None
    if not target_table:
        cur.close()
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'error': 'no product table found'}), 500

    inserted = 0
    inserted = 0
    inserted_names = []
    failed = []

    # Inspect target table columns to insert only available fields
    try:
        cur.execute(f"SHOW COLUMNS FROM {target_table}")
        col_rows = cur.fetchall()
        # col_rows may be tuples like (Field, Type, Null, Key, Default, Extra)
        existing_cols = set()
        for row in col_rows:
            # first element is field name
            if isinstance(row, (list, tuple)) and len(row) > 0:
                existing_cols.add(str(row[0]).lower())
            elif isinstance(row, dict) and 'Field' in row:
                existing_cols.add(str(row['Field']).lower())
    except Exception:
        existing_cols = set()

    for p in products:
        try:
            # Determine if product already exists (by nombre/name)
            exists_count = 0
            try:
                if 'nombre' in existing_cols:
                    cur.execute(f"SELECT COUNT(1) FROM {target_table} WHERE LOWER(nombre)=%s", (p['nombre'].lower(),))
                    exists_count = int(cur.fetchone()[0])
                elif 'name' in existing_cols:
                    cur.execute(f"SELECT COUNT(1) FROM {target_table} WHERE LOWER(name)=%s", (p['nombre'].lower(),))
                    exists_count = int(cur.fetchone()[0])
            except Exception:
                exists_count = 0
            if exists_count > 0:
                continue

            # Build insert statement with available columns
            fields = []
            values = []
            # nombre / name
            if 'nombre' in existing_cols:
                fields.append('nombre'); values.append(p['nombre'])
            elif 'name' in existing_cols:
                fields.append('name'); values.append(p['nombre'])
            # descripcion / description
            if 'descripcion' in existing_cols:
                fields.append('descripcion'); values.append(p['descripcion'])
            elif 'description' in existing_cols:
                fields.append('description'); values.append(p['descripcion'])
            # precio / price
            if 'precio' in existing_cols:
                fields.append('precio'); values.append(p['precio_val'])
            elif 'price' in existing_cols:
                fields.append('price'); values.append(p['precio_val'])
            # imagen / image
            if 'imagen' in existing_cols:
                fields.append('imagen'); values.append(p['imagen'])
            elif 'image' in existing_cols:
                fields.append('image'); values.append(p['imagen'])
            # categoria / category
            if 'categoria' in existing_cols:
                fields.append('categoria'); values.append(p['categoria'])
            elif 'category' in existing_cols:
                fields.append('category'); values.append(p['categoria'])
            # stock
            if 'stock' in existing_cols:
                fields.append('stock'); values.append(10)
            # created/updated timestamps
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            if 'creado_en' in existing_cols:
                fields.append('creado_en'); values.append(now)
            if 'actualizado_en' in existing_cols:
                fields.append('actualizado_en'); values.append(now)

            if not fields:
                failed.append({'nombre': p['nombre'], 'reason': 'No matching columns found in target table'})
                continue

            placeholders = ','.join(['%s'] * len(values))
            sql = f"INSERT INTO {target_table} ({','.join(fields)}) VALUES ({placeholders})"
            try:
                cur.execute(sql, tuple(values))
                try:
                    conn.commit()
                except Exception:
                    pass
                inserted += 1
                inserted_names.append(p['nombre'])
            except Exception as e:
                failed.append({'nombre': p['nombre'], 'reason': str(e)})
                continue
        except Exception as e:
            failed.append({'nombre': p.get('nombre', '<unknown>'), 'reason': str(e)})
            continue
    cur.close()
    try:
        conn.close()
    except Exception:
        pass
    return jsonify({'inserted': inserted, 'inserted_names': inserted_names, 'failed': failed})

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
    # Prefer DB-backed products (table 'producto' or 'productos'), otherwise fall back to code-generated PRODUCTS
    conn = get_mysql_conn()
    if conn:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        tried = ['producto', 'productos', 'productos_catalogo', 'items']
        rows = []
        for t in tried:
            try:
                cur.execute(f"SELECT * FROM {t} LIMIT 100")
                rows = cur.fetchall()
                if rows:
                    break
            except Exception:
                rows = []
        cur.close()
        try:
            conn.close()
        except Exception:
            pass
        if rows:
            # normalize fields
            out = []
            for r in rows:
                out.append({
                    'id': r.get('id'),
                    'nombre': r.get('nombre') or r.get('name'),
                    'descripcion': r.get('descripcion') or r.get('description') or '',
                    'precio': r.get('precio'),
                    'imagen': r.get('imagen') or r.get('image') or '',
                    'categoria': r.get('categoria') or r.get('category') or '',
                    'stock': r.get('stock') if 'stock' in r else None
                })
            return jsonify(out)

    # Fallback: return generated products
    return jsonify(list(map(lambda p: {
        'id': p.get('id'), 'nombre': p.get('nombre'), 'descripcion': p.get('descripcion'), 'precio': p.get('precio_val'), 'imagen': p.get('imagen'), 'categoria': p.get('categoria')
    }, generate_products())))



@app.post('/api/products')
def api_products_create():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(force=True)
    nombre = data.get('nombre')
    descripcion = data.get('descripcion', '')
    precio = data.get('precio')
    imagen = data.get('imagen', '')
    categoria = data.get('categoria', '')
    stock = int(data.get('stock', 0)) if data.get('stock') is not None else None
    if not nombre or precio is None:
        return jsonify({'error': 'nombre y precio son requeridos'}), 400
    conn = get_mysql_conn()
    if not conn:
        return jsonify({'error': 'db connection failed'}), 500
    cur = conn.cursor()
    target = None
    for t in ['producto', 'productos']:
        try:
            cur.execute(f"SELECT 1 FROM {t} LIMIT 1")
            target = t
            break
        except Exception:
            target = None
    if not target:
        cur.close()
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'error': 'no product table found'}), 500
    # Inspect target table columns and build a safe INSERT with existing columns only
    try:
        cur.execute(f"SHOW COLUMNS FROM {target}")
        cols = cur.fetchall()
        existing_cols = set()
        for row in cols:
            if isinstance(row, (list, tuple)) and len(row) > 0:
                existing_cols.add(str(row[0]).lower())
            elif isinstance(row, dict) and 'Field' in row:
                existing_cols.add(str(row['Field']).lower())
    except Exception:
        existing_cols = set()

    fields = []
    values = []
    # Map available fields
    if 'nombre' in existing_cols or 'name' in existing_cols:
        fields.append('nombre' if 'nombre' in existing_cols else 'name'); values.append(nombre)
    if 'descripcion' in existing_cols or 'description' in existing_cols:
        fields.append('descripcion' if 'descripcion' in existing_cols else 'description'); values.append(descripcion)
    if 'precio' in existing_cols or 'price' in existing_cols:
        fields.append('precio' if 'precio' in existing_cols else 'price'); values.append(precio)
    if 'imagen' in existing_cols or 'image' in existing_cols:
        fields.append('imagen' if 'imagen' in existing_cols else 'image'); values.append(imagen)
    if 'categoria' in existing_cols or 'category' in existing_cols:
        fields.append('categoria' if 'categoria' in existing_cols else 'category'); values.append(categoria)
    if 'stock' in existing_cols:
        fields.append('stock'); values.append(stock if stock is not None else 0)
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    if 'creado_en' in existing_cols:
        fields.append('creado_en'); values.append(now)
    if 'actualizado_en' in existing_cols:
        fields.append('actualizado_en'); values.append(now)

    if not fields:
        cur.close(); conn.close()
        return jsonify({'error': 'target table has no compatible columns'}), 500

    placeholders = ','.join(['%s'] * len(values))
    sql = f"INSERT INTO {target} ({','.join(fields)}) VALUES ({placeholders})"
    try:
        cur.execute(sql, tuple(values))
        try:
            conn.commit()
        except Exception:
            pass
        inserted_id = cur.lastrowid
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'error': 'insert failed', 'detail': str(e)}), 500
    cur.close()
    try:
        conn.close()
    except Exception:
        pass
    return jsonify({'ok': True, 'id': inserted_id})


@app.put('/api/products/<int:pid>')
def api_products_update(pid):
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(force=True)
    nombre = data.get('nombre')
    descripcion = data.get('descripcion')
    precio = data.get('precio')
    imagen = data.get('imagen')
    categoria = data.get('categoria')
    stock = data.get('stock')
    conn = get_mysql_conn()
    if not conn:
        return jsonify({'error': 'db connection failed'}), 500
    cur = conn.cursor()
    target = None
    for t in ['producto', 'productos']:
        try:
            cur.execute(f"SELECT 1 FROM {t} LIMIT 1")
            target = t
            break
        except Exception:
            target = None
    if not target:
        cur.close()
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'error': 'no product table found'}), 500
    fields = []
    params = []
    if nombre is not None:
        fields.append('nombre=%s'); params.append(nombre)
    if descripcion is not None:
        fields.append('descripcion=%s'); params.append(descripcion)
    if precio is not None:
        fields.append('precio=%s'); params.append(precio)
    if imagen is not None:
        fields.append('imagen=%s'); params.append(imagen)
    if categoria is not None:
        fields.append('categoria=%s'); params.append(categoria)
    if stock is not None:
        fields.append('stock=%s'); params.append(int(stock))
    if not fields:
        cur.close(); conn.close(); return jsonify({'ok': True})
    params.append(pid)
    try:
        cur.execute(f"UPDATE {target} SET " + ",".join(fields) + " WHERE id=%s", tuple(params))
        conn.commit()
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'error': 'update failed', 'detail': str(e)}), 500
    cur.close()
    try:
        conn.close()
    except Exception:
        pass
    return jsonify({'ok': True})


@app.delete('/api/products/<int:pid>')
def api_products_delete(pid):
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    conn = get_mysql_conn()
    if not conn:
        return jsonify({'error': 'db connection failed'}), 500
    cur = conn.cursor()
    target = None
    for t in ['producto', 'productos']:
        try:
            cur.execute(f"SELECT 1 FROM {t} LIMIT 1")
            target = t
            break
        except Exception:
            target = None
    if not target:
        cur.close()
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'error': 'no product table found'}), 500
    try:
        cur.execute(f"DELETE FROM {target} WHERE id=%s", (pid,))
        conn.commit()
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'error': 'delete failed', 'detail': str(e)}), 500
    cur.close()
    try:
        conn.close()
    except Exception:
        pass
    return jsonify({'ok': True})

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
