from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3, os, secrets
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "testy.db"
app = Flask(__name__)
CORS(app)
ADMIN_KEY = os.environ.get('TESTY_ADMIN_KEY') or 'change-this-admin-key'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def admin_required():
    key = request.headers.get('X-Admin-Key')
    if not key or not secrets.compare_digest(key, ADMIN_KEY):
        return jsonify({'error': 'Admin authentication required'}), 401
    return None


def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS menu_items (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT NOT NULL,description TEXT DEFAULT '',price REAL NOT NULL,image TEXT DEFAULT '',status TEXT NOT NULL DEFAULT 'Available',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT,order_number TEXT UNIQUE NOT NULL,customer_name TEXT NOT NULL,phone TEXT NOT NULL,address TEXT DEFAULT '',payment_method TEXT DEFAULT 'Cash on Delivery',subtotal REAL NOT NULL,delivery_fee REAL NOT NULL DEFAULT 0,total REAL NOT NULL,status TEXT NOT NULL DEFAULT 'Pending',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS order_items (id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER NOT NULL,menu_item_id INTEGER,name TEXT NOT NULL,price REAL NOT NULL,quantity INTEGER NOT NULL,FOREIGN KEY(order_id) REFERENCES orders(id));
        CREATE TABLE IF NOT EXISTS reservations (id INTEGER PRIMARY KEY AUTOINCREMENT,booking_number TEXT UNIQUE NOT NULL,name TEXT NOT NULL,phone TEXT NOT NULL,date TEXT NOT NULL,time TEXT NOT NULL,guests INTEGER NOT NULL,request TEXT DEFAULT '',status TEXT NOT NULL DEFAULT 'Pending',created_at TEXT NOT NULL);
    ''')
    conn.commit(); conn.close()

@app.get('/api/health')
def health(): return jsonify({'status':'ok','service':'Testy Restaurant API'})

@app.post('/api/admin/login')
def admin_login():
    key=(request.get_json() or {}).get('key','')
    if not key or not secrets.compare_digest(key, ADMIN_KEY): return jsonify({'error':'Invalid admin credentials'}),401
    return jsonify({'success':True,'admin_key':key})

@app.get('/api/menu')
def menu():
    conn=get_db(); rows=conn.execute("SELECT * FROM menu_items WHERE status='Available' ORDER BY category,name").fetchall(); conn.close(); return jsonify([dict(r) for r in rows])

@app.get('/api/admin/menu')
def admin_menu():
    err=admin_required()
    if err:return err
    conn=get_db(); rows=conn.execute('SELECT * FROM menu_items ORDER BY id DESC').fetchall(); conn.close(); return jsonify([dict(r) for r in rows])

@app.post('/api/menu')
def create_menu_item():
    err=admin_required()
    if err:return err
    data=request.get_json() or {}
    if not data.get('name') or not data.get('category') or data.get('price') is None:return jsonify({'error':'name, category and price are required'}),400
    try: price=float(data['price'])
    except (TypeError,ValueError): return jsonify({'error':'price must be a number'}),400
    if price<0:return jsonify({'error':'price cannot be negative'}),400
    conn=get_db(); cur=conn.execute('INSERT INTO menu_items (name,category,description,price,image,status,created_at) VALUES (?,?,?,?,?,?,?)',(data['name'].strip(),data['category'],data.get('description',''),price,data.get('image',''),data.get('status','Available'),datetime.utcnow().isoformat())); conn.commit(); item=conn.execute('SELECT * FROM menu_items WHERE id=?',(cur.lastrowid,)).fetchone(); conn.close(); return jsonify(dict(item)),201

@app.patch('/api/menu/<int:item_id>')
def update_menu_item(item_id):
    err=admin_required()
    if err:return err
    data=request.get_json() or {}; allowed={'name','category','description','price','image','status'}; updates={k:data[k] for k in allowed if k in data}
    if 'price' in updates:
        try: updates['price']=float(updates['price']); assert updates['price']>=0
        except (TypeError,ValueError,AssertionError): return jsonify({'error':'price must be a non-negative number'}),400
    if not updates:return jsonify({'error':'no fields to update'}),400
    conn=get_db(); assignments=', '.join(f'{k}=?' for k in updates); cur=conn.execute(f'UPDATE menu_items SET {assignments} WHERE id=?',(*updates.values(),item_id)); conn.commit()
    if not cur.rowcount: conn.close(); return jsonify({'error':'Menu item not found'}),404
    item=conn.execute('SELECT * FROM menu_items WHERE id=?',(item_id,)).fetchone(); conn.close(); return jsonify(dict(item))

@app.delete('/api/menu/<int:item_id>')
def delete_menu_item(item_id):
    err=admin_required()
    if err:return err
    conn=get_db(); cur=conn.execute('DELETE FROM menu_items WHERE id=?',(item_id,)); conn.commit(); conn.close()
    if not cur.rowcount:return jsonify({'error':'Menu item not found'}),404
    return jsonify({'success':True})

@app.get('/api/orders')
def orders():
    conn=get_db(); rows=conn.execute('SELECT * FROM orders ORDER BY id DESC').fetchall(); result=[]
    for order in rows:
        item=dict(order); item['items']=[dict(r) for r in conn.execute('SELECT * FROM order_items WHERE order_id=?',(order['id'],)).fetchall()]; result.append(item)
    conn.close(); return jsonify(result)

@app.post('/api/orders')
def create_order():
    data=request.get_json() or {}; customer,items=data.get('customer',{}),data.get('items',[])
    if not customer.get('name') or not customer.get('phone') or not items:return jsonify({'error':'customer name, phone and items are required'}),400
    subtotal=sum(float(i.get('price',0))*int(i.get('quantity',1)) for i in items); delivery=float(data.get('delivery_fee',49)); total=subtotal+delivery; now=datetime.utcnow().isoformat(); number='TR-'+datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:17]
    conn=get_db(); cur=conn.execute('INSERT INTO orders (order_number,customer_name,phone,address,payment_method,subtotal,delivery_fee,total,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)',(number,customer['name'],customer['phone'],customer.get('address',''),data.get('payment_method','Cash on Delivery'),subtotal,delivery,total,'Pending',now))
    for i in items: conn.execute('INSERT INTO order_items (order_id,menu_item_id,name,price,quantity) VALUES (?,?,?,?,?)',(cur.lastrowid,i.get('id'),i.get('name','Item'),float(i.get('price',0)),int(i.get('quantity',1))))
    conn.commit(); conn.close(); return jsonify({'order_number':number,'status':'Pending','subtotal':subtotal,'delivery_fee':delivery,'total':total}),201

@app.patch('/api/orders/<int:order_id>/status')
def update_order_status(order_id):
    err=admin_required()
    if err:return err
    status=(request.get_json() or {}).get('status')
    if status not in {'Pending','Confirmed','Preparing','Ready','Completed','Cancelled'}:return jsonify({'error':'Invalid order status'}),400
    conn=get_db(); cur=conn.execute('UPDATE orders SET status=? WHERE id=?',(status,order_id)); conn.commit(); conn.close()
    if not cur.rowcount:return jsonify({'error':'Order not found'}),404
    return jsonify({'success':True,'status':status})

@app.get('/api/reservations')
def reservations():
    conn=get_db(); rows=conn.execute('SELECT * FROM reservations ORDER BY date,time').fetchall(); conn.close(); return jsonify([dict(r) for r in rows])

@app.post('/api/reservations')
def create_reservation():
    data=request.get_json() or {}; required=['name','phone','date','time','guests']
    if any(not data.get(f) for f in required):return jsonify({'error':'name, phone, date, time and guests are required'}),400
    number='TB-'+datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:17]; conn=get_db(); conn.execute('INSERT INTO reservations (booking_number,name,phone,date,time,guests,request,status,created_at) VALUES (?,?,?,?,?,?,?,?,?)',(number,data['name'],data['phone'],data['date'],data['time'],int(data['guests']),data.get('request',''),'Pending',datetime.utcnow().isoformat())); conn.commit(); conn.close(); return jsonify({'booking_number':number,'status':'Pending'}),201

@app.patch('/api/reservations/<int:reservation_id>/status')
def update_reservation_status(reservation_id):
    err=admin_required()
    if err:return err
    status=(request.get_json() or {}).get('status')
    if status not in {'Pending','Confirmed','Rejected','Completed'}:return jsonify({'error':'Invalid reservation status'}),400
    conn=get_db(); cur=conn.execute('UPDATE reservations SET status=? WHERE id=?',(status,reservation_id)); conn.commit(); conn.close()
    if not cur.rowcount:return jsonify({'error':'Reservation not found'}),404
    return jsonify({'success':True,'status':status})

init_db()
if __name__=='__main__': app.run(debug=True,port=5000)
