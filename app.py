from flask import Flask, render_template, jsonify, request, session # type: ignore
import config
from datetime import timedelta, datetime
import random
import os
import pymysql
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
import traceback
try:
    from passlib.hash import scrypt as passlib_scrypt
except Exception:
    passlib_scrypt = None
try:
    import qrcode
    from io import BytesIO
    import base64
except Exception:
    qrcode = None
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

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
    # prefer explicit config.py values, fallback to environment variables
    mysql_host = getattr(config, 'MYSQL_HOST', None) or os.environ.get('MYSQL_HOST')
    mysql_port = getattr(config, 'MYSQL_PORT', None) or os.environ.get('MYSQL_PORT')
    mysql_user = getattr(config, 'MYSQL_USER', None) or os.environ.get('MYSQL_USER')
    mysql_password = getattr(config, 'MYSQL_PASSWORD', None) or os.environ.get('MYSQL_PASSWORD')
    mysql_db = getattr(config, 'MYSQL_DB', None) or os.environ.get('MYSQL_DB')

    # Normalize host:port if provided in MYSQL_HOST
    host = None; port = None
    if mysql_host:
        if ':' in mysql_host:
            try:
                host_part, port_part = mysql_host.split(':', 1)
                host = host_part.strip()
                port = int(port_part)
            except Exception:
                host = mysql_host.strip()
        else:
            host = mysql_host.strip()
    if mysql_port and not port:
        try:
            port = int(mysql_port)
        except Exception:
            port = None

    # Try env vars first (require host,user,db)
    if host and mysql_user and mysql_db:
        try:
            conn_args = dict(host=host, user=mysql_user, password=mysql_password or '', db=mysql_db, cursorclass=pymysql.cursors.DictCursor)
            if port:
                conn_args['port'] = port
            return pymysql.connect(**conn_args)
        except Exception:
            pass

    # No remote defaults here — fall back to local defaults if explicit config/env not provided

    # Fallback: try common local defaults
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


def init_orders_table():
    conn = get_metrics_conn()
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                payment_method TEXT,
                amount INTEGER,
                items TEXT,
                reference TEXT,
                phone TEXT,
                address TEXT,
                card_last4 TEXT,
                mysql_id INTEGER,
                status TEXT,
                created_at DATETIME
            )
        ''')
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


# Ensure uploads dir exists
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)


@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    from flask import send_from_directory
    return send_from_directory(UPLOADS_DIR, filename)


@app.route('/api/orders/<int:oid>/upload_proof', methods=['POST'])
def api_upload_proof(oid):
    # allow both user and admin to upload proof (but require auth)
    user = session.get('user')
    if not user:
        return jsonify({'error':'forbidden'}), 403
    if 'file' not in request.files:
        return jsonify({'error': 'no file uploaded'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'error': 'invalid file'}), 400
    # validate extension
    allowed_ext = ['.png','.jpg','.jpeg','.pdf']
    fn = f.filename
    _, ext = os.path.splitext(fn.lower())
    if ext not in allowed_ext:
        return jsonify({'error': 'tipo de archivo no permitido'}), 400
    # save file with safe name
    safe_name = f"order_{oid}_{int(datetime.utcnow().timestamp())}{ext}"
    dest = os.path.join(UPLOADS_DIR, safe_name)
    try:
        f.save(dest)
        # update order record
        conn = get_metrics_conn()
        cur = conn.cursor()
        cur.execute('UPDATE orders SET status=?, created_at=created_at WHERE id=?', ('pending', oid))
        # add proof_path column if missing (attempt)
        try:
            cur.execute('PRAGMA table_info(orders)')
            cols = [r[1] for r in cur.fetchall()]
            if 'proof_path' not in cols:
                cur.execute('ALTER TABLE orders ADD COLUMN proof_path TEXT')
        except Exception:
            pass
        try:
            cur.execute('UPDATE orders SET proof_path=? WHERE id=?', (safe_name, oid))
            conn.commit()
        except Exception:
            pass
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        # notify admin with attachment if small
        try:
            att = None
            path = dest
            if os.path.exists(path) and os.path.getsize(path) < 5 * 1024 * 1024:
                with open(path, 'rb') as fh:
                    data = fh.read()
                mimetype = 'application/octet-stream'
                if ext in ('.png', '.jpg', '.jpeg'):
                    mimetype = 'image/png' if ext=='.png' else 'image/jpeg'
                elif ext == '.pdf':
                    mimetype = 'application/pdf'
                send_email(f'Nuevo comprobante pedido #{oid}', f'Comprobante subido para pedido {oid}', attachments=[(safe_name, data, mimetype)])
        except Exception:
            pass
        return jsonify({'ok': True, 'file': safe_name, 'url': f"/uploads/{safe_name}"})
    except Exception as e:
        return jsonify({'error': 'save failed', 'detail': str(e)}), 500


@app.route('/api/admin/orders/<int:oid>')
def api_admin_order_detail(oid):
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return jsonify({'error':'forbidden'}), 403
    try:
        conn = get_metrics_conn()
        cur = conn.cursor()
        cur.execute('SELECT id, user_email, payment_method, amount, items, reference, phone, address, card_last4, proof_path, status, created_at FROM orders WHERE id=?', (oid,))
        r = cur.fetchone()
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        if not r:
            return jsonify({'error':'not found'}), 404
        return jsonify({ 'id': r[0], 'user_email': r[1], 'payment_method': r[2], 'amount': r[3], 'items': r[4], 'reference': r[5], 'phone': r[6], 'address': r[7], 'card_last4': r[8], 'proof_path': r[9], 'status': r[10], 'created_at': r[11] })
    except Exception as e:
        return jsonify({'error':'failed','detail': str(e)}), 500


def create_order_in_db(user_email, payment_method, amount, items, reference, phone=None, address=None, card_last4=None):
    # Try to insert into MySQL first (table 'pedidos'), but always persist in local SQLite as fallback/replica.
    mysql_id = None
    try:
        mconn = get_mysql_conn()
        if mconn:
            try:
                with mconn.cursor() as mcur:
                    # Prepare insert; attempt directly. If table missing, create it and retry.
                    insert_sql = ("INSERT INTO pedidos (user_email,payment_method,amount,items,reference,phone,address,card_last4,status,created_at) "
                                  "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)")
                    params = (user_email, payment_method, float(amount), items, reference, phone, address, card_last4, 'pending', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))
                    try:
                        mcur.execute(insert_sql, params)
                        try:
                            mconn.commit()
                        except Exception:
                            pass
                        try:
                            mysql_id = mcur.lastrowid
                        except Exception:
                            mysql_id = None
                    except Exception:
                        # Try to create a compatible 'pedidos' table and insert again
                        try:
                            create_sql = '''
                            CREATE TABLE IF NOT EXISTS pedidos (
                                id INT AUTO_INCREMENT PRIMARY KEY,
                                user_email VARCHAR(255),
                                payment_method VARCHAR(64),
                                amount DECIMAL(12,2),
                                items TEXT,
                                reference VARCHAR(128),
                                phone VARCHAR(64),
                                address TEXT,
                                card_last4 VARCHAR(8),
                                status VARCHAR(32),
                                created_at DATETIME
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                            '''
                            mcur.execute(create_sql)
                            try:
                                mconn.commit()
                            except Exception:
                                pass
                            # retry insert
                            mcur.execute(insert_sql, params)
                            try:
                                mconn.commit()
                            except Exception:
                                pass
                            try:
                                mysql_id = mcur.lastrowid
                            except Exception:
                                mysql_id = None
                        except Exception:
                            # give up on mysql insertion for now
                            mysql_id = None
            finally:
                try:
                    mconn.close()
                except Exception:
                    pass
    except Exception:
        mysql_id = None

    # Always persist a local copy in SQLite. Ensure orders table has mysql_id column (older DBs may miss it).
    conn = get_metrics_conn()
    try:
        cur = conn.cursor()
        # Ensure mysql_id column exists
        try:
            cur.execute('PRAGMA table_info(orders)')
            cols = [r[1] for r in cur.fetchall()]
            if 'mysql_id' not in cols:
                try:
                    cur.execute('ALTER TABLE orders ADD COLUMN mysql_id INTEGER')
                except Exception:
                    pass
        except Exception:
            pass

        cur.execute('INSERT INTO orders (user_email,payment_method,amount,items,reference,phone,address,card_last4,mysql_id,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    (user_email, payment_method, int(amount), items, reference, phone, address, card_last4, mysql_id, 'pending', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        oid = cur.lastrowid
        return oid
    except Exception:
        return None
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def generate_qr_base64(payload_text):
    # returns base64-encoded PNG data URI or None if qrcode not available
    if qrcode is None:
        return None
    try:
        img = qrcode.make(payload_text)
        buf = BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        return 'data:image/png;base64,' + b64
    except Exception:
        return None


def send_email(subject, body, to_addr=None, attachments=None):
    # attachments: list of (filename, bytes, mimetype)
    smtp_host = getattr(config, 'SMTP_HOST', '') or os.environ.get('SMTP_HOST','')
    smtp_port = getattr(config, 'SMTP_PORT', 587) or int(os.environ.get('SMTP_PORT', 587))
    smtp_user = getattr(config, 'SMTP_USER', '') or os.environ.get('SMTP_USER','')
    smtp_pass = getattr(config, 'SMTP_PASSWORD', '') or os.environ.get('SMTP_PASSWORD','')
    use_tls = getattr(config, 'SMTP_USE_TLS', True)
    from_addr = getattr(config, 'EMAIL_FROM', 'no-reply@localhost')
    admin_to = to_addr or getattr(config, 'ADMIN_EMAIL', os.environ.get('ADMIN_EMAIL',''))
    if not smtp_host or not admin_to:
        # SMTP not configured; skip sending
        print('send_email skipped: no smtp_host or admin email configured')
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = formataddr(('Lindeza', from_addr))
        msg['To'] = admin_to
        msg.set_content(body)
        if attachments:
            for fname, data, mimetype in attachments:
                maintype, subtype = mimetype.split('/',1) if '/' in mimetype else ('application','octet-stream')
                msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=fname)
        # connect
        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        if smtp_user:
            server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print('send_email failed:', e)
        return False


def try_mysql_connect_debug():
    """Try several connection candidates and return (conn, error_message, used_params).
    conn is a live pymysql connection on success (caller should close it), or None on failure.
    error_message is None on success or a string describing last exception.
    used_params gives host/port/user/db attempted (no passwords returned).
    """
    mysql_host = os.environ.get('MYSQL_HOST')
    mysql_port = os.environ.get('MYSQL_PORT')
    mysql_user = os.environ.get('MYSQL_USER')
    mysql_password = os.environ.get('MYSQL_PASSWORD')
    mysql_db = os.environ.get('MYSQL_DB')

    candidates = []
    # If explicit env vars, try them first
    if mysql_host and mysql_user and mysql_db:
        # allow host:port
        host = mysql_host
        port = None
        if ':' in mysql_host:
            try:
                h, p = mysql_host.split(':', 1)
                host = h.strip(); port = int(p)
            except Exception:
                host = mysql_host
        elif mysql_port:
            try:
                port = int(mysql_port)
            except Exception:
                port = None
        candidates.append({'host': host, 'port': port, 'user': mysql_user, 'db': mysql_db})

    # try remote isladigital as shown in screenshot
    candidates.append({'host': os.environ.get('MYSQL_HOST','isladigital.xyz'), 'port': int(os.environ.get('MYSQL_PORT','3311')), 'user': os.environ.get('MYSQL_USER','f58_karen'), 'db': os.environ.get('MYSQL_DB','f58_karen')})
    # try local
    candidates.append({'host': 'localhost', 'port': None, 'user': 'root', 'db': 'lindeza'})

    last_err = None
    for c in candidates:
        try:
            conn_args = dict(host=c['host'], user=c['user'], db=c['db'], cursorclass=pymysql.cursors.DictCursor)
            if c.get('port'):
                conn_args['port'] = int(c['port'])
            pwd = mysql_password or ''
            conn = pymysql.connect(password=pwd, **conn_args)
            return conn, None, {'host': c['host'], 'port': c.get('port'), 'user': c['user'], 'db': c['db']}
        except Exception as e:
            last_err = str(e)
            continue
    return None, (last_err or 'unknown error'), {}


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
    # common image list used for generated-product fallbacks and name/image fallbacks
    img_files = [
        'BASE MEDIA COBERTURA.jpg','BASE QUEEN.webp','BASE TRENDY.webp','BASE.jpg','BB CREAM.jpg','BRONZER.jpg','CONTORNO TRENDY.webp','CORRECOTR TRENDY.webp','CORRECTOR BLOM.png','CORRECTOR MAGIC.webp','CORRECTOR OJERA.webp','CORRECTOR VITAMINA E.jpg','CORRECTOR.jpg','DELINEADOR COLOR.webp','DELINEADOR LIQUIDO.jpg','DELINEADOR PLUMON.webp','DELINEADOR PROFESIONAL.webp','DELINEADOR.jpg','FIJADOR TRENDY CEJAS.webp','GEL 2 EN 1 CEJAS.jpg','GEL FIJADPR CEJAS.webp','ILIMINADOR POLVO.jpg','ILUMINADOR CREMA.jpg','ILUMINADOR LIQUI TRENDY.webp','ILIMINADOR LIQUIDO.jpg','ILUMINADOR TRENDY.webp','KIT LIP GLOSS.webp','LIP GLOSS ATENEA.webp','LIP GLOSS MYK.webp','LIP GLOSS TREND.webp','LIP GLOSS TRENDY.webp','PALETA CONTORNOS.jpg','PALETA SOMBRAS.jpg','PALETA.jpg','PESTAÑA SERENITY.jpg','PESTAÑINA LASH.jpg','PESTAÑINA PROSA.webp','PESTAÑINA.jpg','RUBOR CREMA.jpg','RUBOR LIQUID.jpg','RUBOR POLVO.jpg','RUBOR PRIMAVERA.webp','RUBOR STAR.webp','SOMBR SAFARI.webp','SOMBRA CHOCOLATE.webp','SOMBRAS BLOSSOM.webp','TINTA BLOOM.png','TINTA ESCARCHA.webp','TINTA.jpg','TINTA.png'
    ]
    for pid, qty in cart.items():
        # First try to read the product price from the DB (if available)
        precio_val = None
        imagen = ''
        nombre = ''
        try:
            conn = get_mysql_conn()
            if conn:
                try:
                    cur = conn.cursor(pymysql.cursors.DictCursor)
                    # probe common product tables
                    tried = ['producto', 'productos', 'productos_catalogo', 'items']
                    row = None
                    for t in tried:
                        try:
                            cur.execute(f"SELECT * FROM {t} WHERE id=%s LIMIT 1", (pid,))
                            rows = cur.fetchall()
                            if rows:
                                row = rows[0]
                                break
                        except Exception:
                            row = None
                    if row:
                        imagen = row.get('imagen') or row.get('image') or ''
                        nombre = (row.get('nombre') or row.get('name') or '')
                        precio_val = row.get('precio') if row.get('precio') is not None else row.get('price')
                    try:
                        cur.close()
                    except Exception:
                        pass
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
        except Exception:
            precio_val = None

        # Fallback: use generated products/prices if DB lookup failed
        if precio_val is None:
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
            precios_reales = [28000,15000,26000,35000,22000,22000,19500,21900,24800,13900,16300,24000,18900,14000,10000,21000,26900,10500,13500,12000,18000,14600,21900,19500,13900,16000,28000,42000,15000,15900,13600,21900,26000,23400,18500,19000,22000,21000,21900,12600,13000,16700,24000,24900,27000,23000,18000,17900,10000,18000]
            precio = precios_reales[idx] if idx < len(precios_reales) else 20000
            imagen = 'img/' + img_files[idx]
        else:
            # we have precio_val, nombre, imagen from DB row
            try:
                precio = int(float(precio_val))
            except Exception:
                precio = 0
        line_total = precio * qty
        subtotal += line_total
        total_qty += qty
        items.append({
            "id": str(pid),
            "name": nombre or (img_files[int(pid)-1].rsplit('.',1)[0].replace('_',' ').replace('-',' ') if pid.isdigit() and int(pid)-1 < len(img_files) else ''),
            "price": f"${precio:,.0f}",
            "image": imagen if imagen else (('img/' + img_files[int(pid)-1]) if pid.isdigit() and int(pid)-1 < len(img_files) else ''),
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
    # Always force role to 'user' for self-registration to prevent users creating admin accounts
    role = 'user'
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
        # attempt to get debug info
        dbg_conn, err_msg, used = try_mysql_connect_debug()
        if dbg_conn:
            try:
                dbg_conn.close()
            except Exception:
                pass
            # weird: get_mysql_conn returned None but debug succeeded; still fail-safe message
            return jsonify({"ok": False, "error": "Conexión fallida (inconsistente). Intenta de nuevo."}), 500
        else:
            human = f"No se pudo conectar a MySQL. Último error: {err_msg}. Intentados: {used}"
            return jsonify({"ok": False, "error": human}), 500

    try:
        with conn.cursor() as cur:
            table = 'administradores' if role == 'admin' else 'usuarios'
            cur.execute(f'SELECT COUNT(1) AS c FROM {table} WHERE LOWER(email)=%s', (email,))
            exists = cur.fetchone()
            if exists and exists.get('c', 0) > 0:
                conn.close()
                return jsonify({"ok": False, "error": "Este correo ya está registrado."}), 400
            # Inspect columns to optionally include creado_en timestamp
            try:
                cur.execute(f"SHOW COLUMNS FROM {table}")
                cols = cur.fetchall()
                col_names = set()
                for r in cols:
                    if isinstance(r, (list, tuple)) and len(r) > 0:
                        col_names.add(str(r[0]).lower())
                    elif isinstance(r, dict) and 'Field' in r:
                        col_names.add(str(r['Field']).lower())
            except Exception:
                col_names = set()

            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            # Prepare insert columns and values, optionally including creado_en and handling missing AUTO_INCREMENT id
            insert_cols = []
            insert_vals = []
            # include id if table has id but it's not AUTO_INCREMENT (compute next id)
            try:
                include_id = False
                if 'id' in col_names:
                    try:
                        cur.execute(f"SHOW COLUMNS FROM {table} WHERE Field='id'")
                        id_row = cur.fetchone()
                        extra = None
                        if isinstance(id_row, dict) and 'Extra' in id_row:
                            extra = id_row.get('Extra')
                        elif isinstance(id_row, (list, tuple)) and len(id_row) >= 6:
                            extra = id_row[5]
                        if not (extra and 'auto_increment' in str(extra).lower()):
                            include_id = True
                    except Exception:
                        include_id = False
                if include_id:
                    cur.execute(f"SELECT COALESCE(MAX(id),0)+1 FROM {table}")
                    nextid_row = cur.fetchone()
                    nextid = None
                    if isinstance(nextid_row, dict):
                        vals = list(nextid_row.values())
                        nextid = vals[0] if vals else None
                    elif isinstance(nextid_row, (list, tuple)):
                        nextid = nextid_row[0]
                    if nextid is None:
                        include_id = False
                    else:
                        insert_cols.append('id')
                        insert_vals.append(int(nextid))
            except Exception:
                include_id = False

            # Common fields
            insert_cols.extend(['nombre', 'email', 'password'])
            insert_vals.extend([name, email, hashed])
            if table == 'usuarios':
                # include role column if present (some schemas use 'rol')
                if 'rol' in col_names:
                    insert_cols.append('rol'); insert_vals.append(role)
                elif 'role' in col_names:
                    insert_cols.append('role'); insert_vals.append(role)
            # creado_en if exists
            if 'creado_en' in col_names:
                insert_cols.append('creado_en'); insert_vals.append(now)

            # Build SQL
            placeholders = ','.join(['%s'] * len(insert_vals))
            cols_sql = ','.join(insert_cols)
            sql = f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders})"
            cur.execute(sql, tuple(insert_vals))
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
    if not conn:
        # return debug info to frontend so the UI shows why DB isn't reachable
        dbg_conn, err_msg, used = try_mysql_connect_debug()
        if dbg_conn:
            try:
                dbg_conn.close()
            except Exception:
                pass
            return jsonify({"ok": False, "error": "Conexión inconsistente: get_mysql_conn falló pero debug succedió"}), 500
        else:
            return jsonify({"ok": False, "error": "No se pudo conectar a la base de datos MySQL.", "detail": err_msg, "attempted": used}), 500
    if conn:
        try:
            with conn.cursor() as cur:
                # 1) Check administradores
                cur.execute('SELECT nombre,email,password FROM administradores WHERE LOWER(email)=%s LIMIT 1', (email,))
                row = cur.fetchone()
                if row:
                    stored = row.get('password') or ''
                    print(f"[auth] admin lookup stored startswith: {stored[:40]}...")
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
                    # If the stored hash is scrypt but passlib is not installed, return a clear error
                    if stored.startswith('scrypt:') and passlib_scrypt is None:
                        try:
                            conn.close()
                        except Exception:
                            pass
                        return jsonify({"ok": False, "error": "Server missing 'passlib' library required to verify scrypt hashed passwords. Run: pip install passlib"}), 500
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
                    print(f"[auth] user lookup stored startswith: {stored[:40]}...")
                    if stored.startswith('scrypt:') and passlib_scrypt is not None:
                        try:
                            if passlib_scrypt.verify(password, stored):
                                session["user"] = {"name": urow.get('nombre'), "email": urow.get('email'), "role": urow.get('rol') or 'user'}
                                session.permanent = True
                                conn.close()
                                return jsonify({"ok": True, "user": session["user"], "redirect": False})
                        except Exception:
                            pass
                    if stored.startswith('scrypt:') and passlib_scrypt is None:
                        try:
                            conn.close()
                        except Exception:
                            pass
                        return jsonify({"ok": False, "error": "Server missing 'passlib' library required to verify scrypt hashed passwords. Run: pip install passlib"}), 500
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


@app.route('/api/admin/orders')
def api_admin_orders():
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    try:
        conn = get_metrics_conn()
        cur = conn.cursor()
        cur.execute('SELECT id, user_email, payment_method, amount, items, reference, phone, address, card_last4, status, created_at FROM orders ORDER BY created_at DESC')
        rows = cur.fetchall()
        out = []
        for r in rows:
            out.append({
                'id': r[0], 'user_email': r[1], 'payment_method': r[2], 'amount': r[3], 'items': r[4], 'reference': r[5], 'phone': r[6], 'address': r[7], 'card_last4': r[8], 'status': r[9], 'created_at': r[10]
            })
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        return jsonify(out)
    except Exception as e:
        return jsonify({'error': 'failed', 'detail': str(e)}), 500


@app.route('/api/admin/orders/<int:oid>/mark_paid', methods=['POST'])
def api_admin_orders_mark_paid(oid):
    user = session.get('user')
    if not user or user.get('role') != 'admin':
        return jsonify({'error': 'forbidden'}), 403
    try:
        conn = get_metrics_conn()
        cur = conn.cursor()
        cur.execute('UPDATE orders SET status=? WHERE id=?', ('paid', oid))
        conn.commit()
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': 'failed', 'detail': str(e)}), 500


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


@app.get('/api/debug/db')
def api_debug_db():
    conn, err, used = try_mysql_connect_debug()
    if conn:
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'ok': True, 'message': 'Conexión a MySQL establecida', 'used': used})
    return jsonify({'ok': False, 'error': err, 'attempted': used}), 500

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


@app.get('/api/products/<int:pid>')
def api_product_get(pid):
    """Return a single product by id from DB or generated list."""
    conn = get_mysql_conn()
    if conn:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        tried = ['producto', 'productos', 'productos_catalogo', 'items']
        row = None
        for t in tried:
            try:
                cur.execute(f"SELECT * FROM {t} WHERE id=%s LIMIT 1", (pid,))
                rows = cur.fetchall()
                if rows:
                    row = rows[0]
                    break
            except Exception:
                row = None
        cur.close()
        try:
            conn.close()
        except Exception:
            pass
        if row:
            return jsonify({
                'id': row.get('id'),
                'nombre': row.get('nombre') or row.get('name'),
                'descripcion': row.get('descripcion') or row.get('description') or '',
                'precio': row.get('precio'),
                'imagen': row.get('imagen') or row.get('image') or '',
                'categoria': row.get('categoria') or row.get('category') or '',
                'stock': row.get('stock') if 'stock' in row else None
            })

    # fallback to generated products
    for p in generate_products():
        if p.get('id') == pid:
            return jsonify({'id': p.get('id'), 'nombre': p.get('nombre'), 'descripcion': p.get('descripcion'), 'precio': p.get('precio_val'), 'imagen': p.get('imagen'), 'categoria': p.get('categoria')})
    return jsonify({'error': 'not found'}), 404



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
        # Try to create a compatible 'productos' table automatically to accept inserts
        try:
            create_sql = '''
            CREATE TABLE IF NOT EXISTS productos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(255),
                descripcion TEXT,
                precio DECIMAL(12,2),
                imagen VARCHAR(512),
                categoria VARCHAR(128),
                stock INT DEFAULT 0,
                creado_en DATETIME,
                actualizado_en DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            '''
            cur.execute(create_sql)
            conn.commit()
            target = 'productos'
        except Exception as e:
            cur.close()
            try:
                conn.close()
            except Exception:
                pass
            return jsonify({'error': 'no product table found and create failed', 'detail': str(e)}), 500
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

    # If the table has an 'id' column but it is not AUTO_INCREMENT, compute next id and include it
    try:
        id_auto = False
        if 'id' in existing_cols:
            try:
                cur.execute(f"SHOW COLUMNS FROM {target} WHERE Field='id'")
                id_row = cur.fetchone()
                if id_row:
                    # id_row may be tuple or dict; find the 'Extra' field
                    extra = None
                    if isinstance(id_row, dict) and 'Extra' in id_row:
                        extra = id_row.get('Extra')
                    elif isinstance(id_row, (list, tuple)) and len(id_row) >= 6:
                        extra = id_row[5]
                    if extra and 'auto_increment' in str(extra).lower():
                        id_auto = True
            except Exception:
                id_auto = False
        if 'id' in existing_cols and not id_auto:
            # compute next id
            try:
                cur.execute(f"SELECT COALESCE(MAX(id),0)+1 FROM {target}")
                nextid_row = cur.fetchone()
                nextid = None
                if isinstance(nextid_row, dict):
                    # dict cursor may return value by key; take first value
                    vals = list(nextid_row.values())
                    nextid = vals[0] if vals else None
                elif isinstance(nextid_row, (list, tuple)):
                    nextid = nextid_row[0]
                if nextid is None:
                    raise Exception('could not compute next id')
                # Prepend id to fields/values so INSERT includes it
                fields.insert(0, 'id')
                values.insert(0, int(nextid))
            except Exception as e:
                cur.close()
                try:
                    conn.close()
                except Exception:
                    pass
                return jsonify({'error': 'could not compute next id', 'detail': str(e)}), 500
    except Exception:
        pass

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
        # Log detailed DB error for debugging
        try:
            tb = traceback.format_exc()
            log_path = os.path.join(os.path.dirname(__file__), 'db_errors.log')
            with open(log_path, 'a', encoding='utf-8') as fh:
                fh.write(f"--- INSERT ERROR {datetime.utcnow().isoformat()} ---\n")
                fh.write(f"SQL: {sql}\n")
                fh.write(f"PARAMS: {repr(tuple(values))}\n")
                fh.write(tb + "\n")
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'error': 'insert failed', 'detail': str(e), 'sql': sql, 'params': tuple(values)}), 500
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
        # Will map to actual column name below after inspecting table
        params_map = {'nombre': nombre}
    else:
        params_map = {}
    if descripcion is not None:
        params_map['descripcion'] = descripcion
    if precio is not None:
        params_map['precio'] = precio
    if imagen is not None:
        params_map['imagen'] = imagen
    if categoria is not None:
        params_map['categoria'] = categoria
    if stock is not None:
        params_map['stock'] = int(stock)
    # Inspect table columns to map to existing names (support 'name','description','price','image','category')
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

    for logical, val in params_map.items():
        # prefer spanish column names, else english equivalents
        if logical in existing_cols:
            fields.append(f"{logical}=%s"); params.append(val)
        else:
            alt = {'nombre':'name','descripcion':'description','precio':'price','imagen':'image','categoria':'category'}.get(logical)
            if alt and alt in existing_cols:
                fields.append(f"{alt}=%s"); params.append(val)
    if not fields:
        cur.close(); conn.close(); return jsonify({'ok': True})
    params.append(pid)
    try:
        sql = f"UPDATE {target} SET " + ",".join(fields) + " WHERE id=%s"
        cur.execute(sql, tuple(params))
        conn.commit()
    except Exception as e:
        # Log detailed DB error for debugging
        try:
            tb = traceback.format_exc()
            log_path = os.path.join(os.path.dirname(__file__), 'db_errors.log')
            with open(log_path, 'a', encoding='utf-8') as fh:
                fh.write(f"--- UPDATE ERROR {datetime.utcnow().isoformat()} ---\n")
                fh.write(f"SQL: {sql}\n")
                fh.write(f"PARAMS: {repr(tuple(params))}\n")
                fh.write(tb + "\n")
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'error': 'update failed', 'detail': str(e), 'sql': sql, 'params': tuple(params)}), 500
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
    # Require authenticated user for checkout
    user = session.get('user')
    if not user:
        return jsonify({'ok': False, 'error': 'Autenticación requerida. Inicia sesión para continuar.'}), 401

    cart = get_cart()
    if not cart:
        return jsonify({"ok": False, "error": "Tu carrito está vacío."}), 400

    data = request.get_json(silent=True) or {}
    payment_method = (data.get('payment_method') or data.get('method') or '').lower()
    phone = data.get('phone') or data.get('telefono')
    address = data.get('address') or data.get('direccion')
    card_number = data.get('card_number')
    if not payment_method:
        # For the demo, require the frontend to pass a chosen method
        return jsonify({'ok': False, 'error': 'Seleccione un método de pago.'}), 400

    allowed = ['card', 'paypal', 'nequi', 'efecty']
    if payment_method not in allowed:
        return jsonify({'ok': False, 'error': f'Método de pago no soportado: {payment_method}'}), 400

    # Build order info
    total_amount = 0
    items_str = []
    for pid, qty in cart.items():
        # Attempt to get price via cart_summary logic
        try:
            pr = cart_summary({pid: qty})
            if pr and pr.get('items'):
                price_str = pr['items'][0].get('price','')
                # strip formatting e.g. $28,000
                num = int(''.join(ch for ch in price_str if ch.isdigit())) if price_str else 0
            else:
                num = 0
        except Exception:
            num = 0
        total_amount += num * qty
        items_str.append(f"{pid}:{qty}")

    # generate a reference
    ref = f"ORDER-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(1000,9999)}"

    # create orders table if missing
    try:
        init_orders_table()
    except Exception:
        pass

    # determine card_last4 if provided (do NOT store full card)
    card_last4 = None
    if card_number:
        try:
            s = str(card_number).strip()
            card_last4 = s[-4:]
        except Exception:
            card_last4 = None

    order_id = create_order_in_db(user.get('email'), payment_method, total_amount, ','.join(items_str), ref, phone=phone, address=address, card_last4=card_last4)

    # Record visit metric
    try:
        record_visit(user.get('email'), user.get('role'), 'checkout', ','.join(cart.keys()))
    except Exception:
        pass

    # Offline methods: return instructions / QR and leave order pending
    offline = ['nequi', 'efecty', 'bancolombia', 'transfiya']
    if payment_method in offline:
        instructions = {}
        if payment_method == 'nequi':
            # create a payload for a QR (this is a simple text payload; real provider requires specific format)
            payload = f"NEQUI|REF:{ref}|AMT:{total_amount}"
            qr = generate_qr_base64(payload)
            instructions['qr'] = qr
            instructions['text'] = f"Abre Nequi, escanea el QR o envía a cuenta 3001234567 con referencia {ref} por ${total_amount}."
        elif payment_method in ('efecty', 'bancolombia', 'transfiya'):
            instructions['text'] = f"Dirígete al punto {payment_method.upper()} y paga la referencia {ref} por ${total_amount}. Guarda el recibo y notifica al vendedor." 
        # notify admin by email
        try:
            subj = f"Nuevo pedido (ref {ref}) - {payment_method} - {total_amount}"
            body = f"Nuevo pedido\nReferencia: {ref}\nUsuario: {user.get('email')}\nMetodo: {payment_method}\nMonto: {total_amount}\nItems: {','.join(items_str)}\n\nInstrucciones:\n{instructions.get('text','')}\n"
            send_email(subj, body)
        except Exception:
            pass
        return jsonify({'ok': True, 'order_id': order_id, 'reference': ref, 'amount': total_amount, 'instructions': instructions})

    # Instant methods: simulate payment and clear cart
    try:
        # For demo, accept card/paypal immediately; if card, we simulated and saved last4 already
        session['cart'] = {}
        # mark order as paid in sqlite
        try:
            conn = get_metrics_conn()
            cur = conn.cursor()
            cur.execute('UPDATE orders SET status=? WHERE id=?', ('paid', order_id))
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
            pass
        return jsonify({'ok': True, 'message': f'Pago registrado con método: {payment_method}. Gracias por tu compra.', 'order_id': order_id})
    except Exception as e:
        return jsonify({'ok': False, 'error': 'Error procesando el pago', 'detail': str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
