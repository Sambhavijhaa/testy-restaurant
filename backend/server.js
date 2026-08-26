const express = require('express');
const cors = require('cors');
const crypto = require('crypto');
const Database = require('better-sqlite3');
require('dotenv').config();

const app = express();
const PORT = Number(process.env.PORT || 5000);
const ADMIN_KEY = process.env.TESTY_ADMIN_KEY || 'change-this-admin-key';
const FRONTEND_ORIGIN = process.env.TESTY_FRONTEND_ORIGIN || '*';
const db = new Database(process.env.TESTY_DB_PATH || 'testy.db');

app.use(cors({ origin: FRONTEND_ORIGIN === '*' ? true : FRONTEND_ORIGIN }));
app.use(express.json({ limit: '1mb' }));

const now = () => new Date().toISOString();
const adminRequired = (req, res, next) => {
  const key = req.get('X-Admin-Key') || '';
  if (!key || !crypto.timingSafeEqual(Buffer.from(key), Buffer.from(ADMIN_KEY))) return res.status(401).json({ error: 'Admin authentication required' });
  next();
};

function initDb() {
  db.exec(`CREATE TABLE IF NOT EXISTS menu_items(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT NOT NULL,description TEXT DEFAULT '',price REAL NOT NULL,image TEXT DEFAULT '',status TEXT NOT NULL DEFAULT 'Available',created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,order_number TEXT UNIQUE NOT NULL,customer_name TEXT NOT NULL,phone TEXT NOT NULL,address TEXT DEFAULT '',payment_method TEXT DEFAULT 'Cash on Delivery',subtotal REAL NOT NULL,delivery_fee REAL NOT NULL DEFAULT 0,total REAL NOT NULL,status TEXT NOT NULL DEFAULT 'Pending',created_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER NOT NULL,menu_item_id INTEGER NOT NULL,name TEXT NOT NULL,price REAL NOT NULL,quantity INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS reservations(id INTEGER PRIMARY KEY AUTOINCREMENT,booking_number TEXT UNIQUE NOT NULL,name TEXT NOT NULL,phone TEXT NOT NULL,date TEXT NOT NULL,time TEXT NOT NULL,guests INTEGER NOT NULL,request TEXT DEFAULT '',status TEXT NOT NULL DEFAULT 'Pending',created_at TEXT NOT NULL);
  CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number); CREATE INDEX IF NOT EXISTS idx_res_date_time ON reservations(date,time);`);
}
const makeNumber = prefix => `${prefix}-${Date.now()}-${crypto.randomBytes(3).toString('hex')}`;

app.get('/api/health', (req,res)=>res.json({status:'ok',service:'Testy Restaurant API'}));
app.post('/api/admin/login',(req,res)=>{const key=(req.body||{}).key||'';if(!key || key!==ADMIN_KEY)return res.status(401).json({error:'Invalid admin credentials'});res.json({success:true});});

app.get('/api/menu',(req,res)=>res.json(db.prepare("SELECT * FROM menu_items WHERE status='Available' ORDER BY category,name").all()));
app.get('/api/admin/menu',adminRequired,(req,res)=>res.json(db.prepare('SELECT * FROM menu_items ORDER BY id DESC').all()));
app.post('/api/menu',adminRequired,(req,res)=>{const d=req.body||{};const p=Number(d.price);if(!d.name||!d.category||!Number.isFinite(p)||p<0)return res.status(400).json({error:'Valid name, category and price are required'});if(!['Available','Unavailable'].includes(d.status||'Available'))return res.status(400).json({error:'Invalid status'});const info=db.prepare('INSERT INTO menu_items(name,category,description,price,image,status,created_at) VALUES(?,?,?,?,?,?,?)').run(d.name.trim(),d.category,(d.description||'').trim(),p,d.image||'',d.status||'Available',now());res.status(201).json(db.prepare('SELECT * FROM menu_items WHERE id=?').get(info.lastInsertRowid));});
app.patch('/api/menu/:id',adminRequired,(req,res)=>{const allowed=['name','category','description','price','image','status'];const d=req.body||{};const fields=allowed.filter(k=>d[k]!==undefined);if(!fields.length)return res.status(400).json({error:'No fields to update'});if(d.price!==undefined&&(!Number.isFinite(Number(d.price))||Number(d.price)<0))return res.status(400).json({error:'Invalid price'});if(d.status!==undefined&&!['Available','Unavailable'].includes(d.status))return res.status(400).json({error:'Invalid status'});const sets=fields.map(k=>`${k}=@${k}`).join(',');const params={id:Number(req.params.id)};fields.forEach(k=>params[k]=k==='price'?Number(d[k]):d[k]);const info=db.prepare(`UPDATE menu_items SET ${sets} WHERE id=@id`).run(params);if(!info.changes)return res.status(404).json({error:'Menu item not found'});res.json(db.prepare('SELECT * FROM menu_items WHERE id=?').get(params.id));});
app.delete('/api/menu/:id',adminRequired,(req,res)=>{const info=db.prepare('DELETE FROM menu_items WHERE id=?').run(Number(req.params.id));if(!info.changes)return res.status(404).json({error:'Menu item not found'});res.json({success:true});});

app.get('/api/orders',adminRequired,(req,res)=>{const rows=db.prepare('SELECT * FROM orders ORDER BY id DESC').all();const items=db.prepare('SELECT * FROM order_items WHERE order_id=?');res.json(rows.map(o=>({...o,items:items.all(o.id)})));});
app.get('/api/orders/:number',(req,res)=>{const o=db.prepare('SELECT id,order_number,customer_name,subtotal,delivery_fee,total,status,created_at FROM orders WHERE order_number=?').get(req.params.number);if(!o)return res.status(404).json({error:'Order not found'});o.items=db.prepare('SELECT name,price,quantity FROM order_items WHERE order_id=?').all(o.id);delete o.id;res.json(o);});
app.post('/api/orders',(req,res)=>{const d=req.body||{},customer=d.customer||{},items=d.items||[];if(!customer.name||!customer.phone||!Array.isArray(items)||!items.length)return res.status(400).json({error:'customer name, phone and items are required'});let subtotal=0;const valid=[];const get=db.prepare("SELECT id,name,price,status FROM menu_items WHERE id=?");for(const i of items){const id=Number(i.id),q=Number(i.quantity);if(!Number.isInteger(id)||!Number.isInteger(q)||q<1||q>20)return res.status(400).json({error:'Invalid item quantity'});const row=get.get(id);if(!row||row.status!=='Available')return res.status(409).json({error:`${row?.name||'Item'} is unavailable`});subtotal+=row.price*q;valid.push([row,q]);}const fee=49,total=subtotal+fee,number=makeNumber('TR');const tx=db.transaction(()=>{const info=db.prepare('INSERT INTO orders(order_number,customer_name,phone,address,payment_method,subtotal,delivery_fee,total,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)').run(number,customer.name.trim(),customer.phone.trim(),customer.address||'',d.payment_method||'Cash on Delivery',subtotal,fee,total,'Pending',now());const add=db.prepare('INSERT INTO order_items(order_id,menu_item_id,name,price,quantity) VALUES(?,?,?,?,?)');valid.forEach(([r,q])=>add.run(info.lastInsertRowid,r.id,r.name,r.price,q));});tx();res.status(201).json({order_number:number,status:'Pending',subtotal,delivery_fee:fee,total});});
app.patch('/api/orders/:id/status',adminRequired,(req,res)=>{const allowed=['Pending','Confirmed','Preparing','Ready','Completed','Cancelled'];if(!allowed.includes(req.body?.status))return res.status(400).json({error:'Invalid order status'});const info=db.prepare('UPDATE orders SET status=? WHERE id=?').run(req.body.status,Number(req.params.id));if(!info.changes)return res.status(404).json({error:'Order not found'});res.json({success:true,status:req.body.status});});

app.get('/api/reservations',adminRequired,(req,res)=>res.json(db.prepare('SELECT * FROM reservations ORDER BY date,time').all()));
app.post('/api/reservations',(req,res)=>{const d=req.body||{};if(!d.name||!d.phone||!d.date||!d.time||!d.guests)return res.status(400).json({error:'name, phone, date, time and guests are required'});const guests=Number(d.guests);if(!Number.isInteger(guests)||guests<1||guests>20)return res.status(400).json({error:'Guests must be 1-20'});const count=db.prepare("SELECT COUNT(*) AS n FROM reservations WHERE date=? AND time=? AND status IN ('Pending','Confirmed')").get(d.date,d.time).n;if(count>=20)return res.status(409).json({error:'No tables available at this time'});const number=makeNumber('TB');db.prepare('INSERT INTO reservations(booking_number,name,phone,date,time,guests,request,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)').run(number,d.name.trim(),d.phone.trim(),d.date,d.time,guests,d.request||'','Pending',now());res.status(201).json({booking_number:number,status:'Pending'});});
app.patch('/api/reservations/:id/status',adminRequired,(req,res)=>{if(!['Pending','Confirmed','Rejected','Completed'].includes(req.body?.status))return res.status(400).json({error:'Invalid reservation status'});const info=db.prepare('UPDATE reservations SET status=? WHERE id=?').run(req.body.status,Number(req.params.id));if(!info.changes)return res.status(404).json({error:'Reservation not found'});res.json({success:true,status:req.body.status});});

initDb();app.listen(PORT,()=>console.log(`Testy Restaurant API running on port ${PORT}`));
