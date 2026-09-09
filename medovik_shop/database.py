import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'medovik.db')

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = self.get_connection()
        cur = conn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                balance INTEGER DEFAULT 100,
                role TEXT DEFAULT 'user',
                banned INTEGER DEFAULT 0,
                telegram TEXT,
                discord TEXT,
                avatar TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                price INTEGER NOT NULL,
                stock INTEGER DEFAULT 0,
                image TEXT
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                address TEXT,
                pickup_point TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')

        import hashlib
        admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
        cur.execute("SELECT * FROM users WHERE username='admin'")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (username, password, role, balance) VALUES (?, ?, ?, ?)",
                ('admin', admin_pass, 'admin', 9999)
            )

        cur.execute("SELECT * FROM products")
        if not cur.fetchone():
            items = [
                ('⛏️ Алмазная кирка', 'Прочная алмазная кирка', 'инструменты', 50, 20, ''),
                ('🪓 Алмазный топор', 'Острый алмазный топор', 'инструменты', 45, 15, ''),
                ('🧹 Алмазная лопата', 'Удобная алмазная лопата', 'инструменты', 30, 25, ''),
                ('⛏️ Железная кирка', 'Надёжная железная кирка', 'инструменты', 20, 40, ''),
                ('🧱 Каменный блок', 'Прочный каменный блок', 'блоки', 5, 100, ''),
                ('🪵 Древесный блок', 'Натуральный древесный блок', 'блоки', 3, 150, ''),
                ('🪟 Стеклянный блок', 'Прозрачный стеклянный блок', 'блоки', 4, 80, ''),
                ('🧱 Кирпичный блок', 'Красивый кирпичный блок', 'блоки', 8, 60, ''),
                ('🍞 Хлеб', 'Свежий пшеничный хлеб', 'еда', 2, 200, ''),
                ('🍰 Торт', 'Вкусный торт с кремом', 'еда', 15, 30, ''),
                ('🍪 Печенье', 'Хрустящее печенье', 'еда', 3, 150, ''),
                ('🍲 Суп', 'Горячий грибной суп', 'еда', 6, 50, ''),
                ('🏹 Стрелы', 'Острые стрелы для лука', 'разное', 10, 100, ''),
                ('🔥 Факел', 'Яркий факел для освещения', 'разное', 2, 200, ''),
                ('📖 Книга', 'Книга с древними знаниями', 'разное', 25, 20, ''),
                ('🧪 Зелье', 'Волшебное зелье', 'разное', 30, 15, ''),
            ]
            for name, desc, cat, price, stock, img in items:
                cur.execute(
                    "INSERT INTO products (name, description, category, price, stock, image) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, desc, cat, price, stock, img)
                )

        conn.commit()
        conn.close()

    def create_user(self, username, password):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()

    def get_user(self, user_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
        user = cur.fetchone()
        conn.close()
        if user:
            return {
                'id': user[0], 'username': user[1], 'password': user[2],
                'balance': int(user[3] or 0), 'role': user[4],
                'banned': user[5] if len(user) > 5 else 0,
                'telegram': user[6] if len(user) > 6 else '',
                'discord': user[7] if len(user) > 7 else '',
                'avatar': user[8] if len(user) > 8 else '',
                'created_at': user[9] if len(user) > 9 else ''
            }
        return None

    def get_user_by_username(self, username):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        conn.close()
        if user:
            return {
                'id': user[0], 'username': user[1], 'password': user[2],
                'balance': int(user[3] or 0), 'role': user[4],
                'banned': user[5] if len(user) > 5 else 0,
                'telegram': user[6] if len(user) > 6 else '',
                'discord': user[7] if len(user) > 7 else '',
                'avatar': user[8] if len(user) > 8 else '',
                'created_at': user[9] if len(user) > 9 else ''
            }
        return None

    def get_user_by_telegram(self, telegram_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE telegram=?", (f"@{telegram_id}",))
        user = cur.fetchone()
        conn.close()
        if user:
            return {
                'id': user[0], 'username': user[1], 'password': user[2],
                'balance': int(user[3] or 0), 'role': user[4],
                'banned': user[5] if len(user) > 5 else 0,
                'telegram': user[6] if len(user) > 6 else '',
                'discord': user[7] if len(user) > 7 else '',
                'avatar': user[8] if len(user) > 8 else '',
                'created_at': user[9] if len(user) > 9 else ''
            }
        return None

    def update_user_socials(self, user_id, telegram, discord):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET telegram=?, discord=? WHERE id=?", (telegram, discord, user_id))
        conn.commit()
        conn.close()

    def update_user_avatar(self, username, avatar_path):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET avatar=? WHERE username=?", (avatar_path, username))
        conn.commit()
        conn.close()

    def ban_user(self, user_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET banned=1 WHERE id=?", (user_id,))
        conn.commit()
        conn.close()

    def unban_user(self, user_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET banned=0 WHERE id=?", (user_id,))
        conn.commit()
        conn.close()

    def change_password(self, user_id, new_password):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET password=? WHERE id=?", (new_password, user_id))
        conn.commit()
        conn.close()

    def update_balance(self, user_id, amount):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET balance = balance + ? WHERE id=?", (amount, user_id))
        conn.commit()
        conn.close()

    def get_all_users(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, balance, role, banned, telegram, discord, avatar, created_at FROM users")
        users = cur.fetchall()
        conn.close()
        return [
            {
                'id': u[0], 'username': u[1], 'balance': int(u[2] or 0),
                'role': u[3], 'banned': u[4] if len(u) > 4 else 0,
                'telegram': u[5] if len(u) > 5 else '',
                'discord': u[6] if len(u) > 6 else '',
                'avatar': u[7] if len(u) > 7 else '',
                'created_at': u[8] if len(u) > 8 else ''
            }
            for u in users
        ]

    def add_product(self, name, description, category, price, stock, image):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, description, category, price, stock, image) VALUES (?, ?, ?, ?, ?, ?)",
            (name, description, category, price, stock, image)
        )
        conn.commit()
        conn.close()

    def get_product(self, product_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE id=?", (product_id,))
        p = cur.fetchone()
        conn.close()
        if p:
            return {
                'id': p[0], 'name': p[1], 'description': p[2],
                'category': p[3], 'price': int(p[4] or 0),
                'stock': int(p[5] or 0), 'image': p[6]
            }
        return None

    def get_all_products(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM products ORDER BY id DESC")
        products = cur.fetchall()
        conn.close()
        return [
            {
                'id': p[0], 'name': p[1], 'description': p[2],
                'category': p[3], 'price': int(p[4] or 0),
                'stock': int(p[5] or 0), 'image': p[6]
            }
            for p in products
        ]

    def get_products_by_category(self, category):
        conn = self.get_connection()
        cur = conn.cursor()
        if category == 'все':
            cur.execute("SELECT * FROM products ORDER BY id DESC")
        else:
            cur.execute("SELECT * FROM products WHERE category=? ORDER BY id DESC", (category,))
        products = cur.fetchall()
        conn.close()
        return [
            {
                'id': p[0], 'name': p[1], 'description': p[2],
                'category': p[3], 'price': int(p[4] or 0),
                'stock': int(p[5] or 0), 'image': p[6]
            }
            for p in products
        ]

    def delete_product(self, product_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        conn.close()

    def create_order(self, user_id, total, address, pickup_point):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO orders (user_id, total, address, pickup_point, status) VALUES (?, ?, ?, ?, ?)",
            (user_id, total, address, pickup_point, 'collecting')
        )
        order_id = cur.lastrowid
        conn.commit()
        conn.close()
        return order_id

    def add_order_item(self, order_id, product_id, quantity, price):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
            (order_id, product_id, quantity, price)
        )
        conn.commit()
        conn.close()

    def get_order(self, order_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        order = cur.fetchone()
        conn.close()
        if order:
            return {
                'id': order[0], 'user_id': order[1], 'total': int(order[2] or 0),
                'status': order[3], 'address': order[4] if len(order) > 4 else '',
                'pickup_point': order[5] if len(order) > 5 else '',
                'created_at': order[6] if len(order) > 6 else ''
            }
        return None

    def update_order_status(self, order_id, status):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        conn.commit()
        conn.close()

    def get_user_orders(self, user_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user_id,))
        orders = cur.fetchall()
        conn.close()
        return [
            {
                'id': o[0], 'user_id': o[1], 'total': int(o[2] or 0),
                'status': o[3], 'address': o[4] if len(o) > 4 else '',
                'pickup_point': o[5] if len(o) > 5 else '',
                'created_at': o[6] if len(o) > 6 else ''
            }
            for o in orders
        ]

    def get_all_orders(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT o.*, u.username FROM orders o JOIN users u ON o.user_id = u.id ORDER BY o.id DESC"
        )
        orders = cur.fetchall()
        conn.close()
        return [
            {
                'id': o[0], 'user_id': o[1], 'total': int(o[2] or 0),
                'status': o[3], 'address': o[4] if len(o) > 4 else '',
                'pickup_point': o[5] if len(o) > 5 else '',
                'created_at': o[6] if len(o) > 6 else '',
                'username': o[7] if len(o) > 7 else ''
            }
            for o in orders
        ]
