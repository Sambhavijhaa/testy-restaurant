from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "testy.db"
app = Flask(__name__)
CORS(app)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL NOT NULL,
            image TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Available',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT DEFAULT '',
            payment_method TEXT DEFAULT 'Cash on Delivery',
            subtotal REAL NOT NULL,
            delivery_fee REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            menu_item_id INTEGER,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        );
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            guests INTEGER NOT NULL,
            request TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()


@app.get('/api/health')
def health():
    return jsonify({'status': 'ok', 'service': 'Testy Restaurant API'})


@app.get('/api/menu')
def menu():
    conn = get_db()
    rows = conn.execute("SELECT * FROM menu_items WHERE status = 'Available' ORDER BY category, name").fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.get('/api/admin/menu')
def admin_menu():
    conn = get_db()
    rows = conn.execute('SELECT * FROM menu_items ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.post('/api/menu')
def create_menu_item():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('category') or data.get('price') is None:
        return jsonify({'error': 'name, category and price are required'}), 400
    try:
        price = float(data['price'])
    except (TypeError, ValueError):
        return jsonify({'error': 'price must be a number'}), 400
    if price < 0:
        return jsonify({'error': 'price cannot be negative'}), 400
    conn = get_db()
    cur = conn.execute('''INSERT INTO menu_items (name, category, description, price, image, status, created_at)
                          VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (data['name'].strip(), data['category'], data.get('description', ''), price,
                        data.get('image', ''), data.get('status', 'Available'), datetime.utcnow().isoformat()))
    conn.commit()
    item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(item)), 201


@app.patch('/api/menu/<int:item_id>')
def update_menu_item(item_id):
    data = request.get_json() or {}
    allowed = {'name', 'category', 'description', 'price', 'image', 'status'}
    updates = {k: data[k] for k in allowed if k in data}
    if 'price' in updates:
        try:
            updates['price'] = float(updates['price'])
            if updates['price'] < 0:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({'error': 'price must be a non-negative number'}), 400
    if not updates:
        return jsonify({'error': 'no fields to update'}), 400
    conn = get_db()
    assignments = ', '.join(f'{key} = ?' for key in updates)
    cur = conn.execute(f'UPDATE menu_items SET {assignments} WHERE id = ?', (*updates.values(), item_id))
    conn.commit()
    if cur.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Menu item not found'}), 404
    item = conn.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    return jsonify(dict(item))


@app.delete('/api/menu/<int:item_id>')
def delete_menu_item(item_id):
    conn = get_db()
    cur = conn.execute('DELETE FROM menu_items WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({'error': 'Menu item not found'}), 404
    return jsonify({'success': True})


@app.get('/api/orders')
def orders():
    conn = get_db()
    rows = conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall()
    result = []
    for order in rows:
        item_rows = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order['id'],)).fetchall()
        item = dict(order)
        item['items'] = [dict(row) for row in item_rows]
        result.append(item)
    conn.close()
    return jsonify(result)


@app.post('/api/orders')
def create_order():
    data = request.get_json() or {}
    customer, items = data.get('customer', {}), data.get('items', [])
    if not customer.get('name') or not customer.get('phone') or not items:
        return jsonify({'error': 'customer name, phone and items are required'}), 400
    subtotal = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in items)
    delivery_fee = float(data.get('delivery_fee', 49))
    total = subtotal + delivery_fee
    now = datetime.utcnow().isoformat()
    order_number = 'TR-' + datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:17]
    conn = get_db()
    cur = conn.execute('''INSERT INTO orders (order_number, customer_name, phone, address, payment_method,
                       subtotal, delivery_fee, total, status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)''',
                       (order_number, customer['name'], customer['phone'], customer.get('address', ''),
                        data.get('payment_method', 'Cash on Delivery'), subtotal, delivery_fee, total, now))
    for item in items:
        conn.execute('''INSERT INTO order_items (order_id, menu_item_id, name, price, quantity)
                        VALUES (?, ?, ?, ?, ?)''',
                     (cur.lastrowid, item.get('id'), item.get('name', 'Item'), float(item.get('price', 0)), int(item.get('quantity', 1))))
    conn.commit()
    conn.close()
    return jsonify({'order_number': order_number, 'status': 'Pending', 'subtotal': subtotal,
                    'delivery_fee': delivery_fee, 'total': total}), 201


@app.patch('/api/orders/<int:order_id>/status')
def update_order_status(order_id):
    status = (request.get_json() or {}).get('status')
    if status not in {'Pending', 'Confirmed', 'Preparing', 'Ready', 'Completed', 'Cancelled'}:
        return jsonify({'error': 'Invalid order status'}), 400
    conn = get_db()
    cur = conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit(); conn.close()
    if cur.rowcount == 0:
        return jsonify({'error': 'Order not found'}), 404
    return jsonify({'success': True, 'status': status})


@app.get('/api/reservations')
def reservations():
    conn = get_db(); rows = conn.execute('SELECT * FROM reservations ORDER BY date, time').fetchall(); conn.close()
    return jsonify([dict(row) for row in rows])


@app.post('/api/reservations')
def create_reservation():
    data = request.get_json() or {}
    required = ['name', 'phone', 'date', 'time', 'guests']
    if any(not data.get(field) for field in required):
        return jsonify({'error': 'name, phone, date, time and guests are required'}), 400
    booking_number = 'TB-' + datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:17]
    conn = get_db()
    conn.execute('''INSERT INTO reservations (booking_number, name, phone, date, time, guests, request, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', ?)''',
                 (booking_number, data['name'], data['phone'], data['date'], data['time'], int(data['guests']),
                  data.get('request', ''), datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return jsonify({'booking_number': booking_number, 'status': 'Pending'}), 201


@app.patch('/api/reservations/<int:reservation_id>/status')
def update_reservation_status(reservation_id):
    status = (request.get_json() or {}).get('status')
    if status not in {'Pending', 'Confirmed', 'Rejected', 'Completed'}:
        return jsonify({'error': 'Invalid reservation status'}), 400
    conn = get_db(); cur = conn.execute('UPDATE reservations SET status = ? WHERE id = ?', (status, reservation_id)); conn.commit(); conn.close()
    if cur.rowcount == 0:
        return jsonify({'error': 'Reservation not found'}), 404
    return jsonify({'success': True, 'status': status})


init_db()
if __name__ == '__main__':
    app.run(debug=True, port=5000)
