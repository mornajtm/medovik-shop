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

        # УДАЛЯЕМ СТАРЫЕ ТАБЛИЦЫ
        cur.execute("DROP TABLE IF EXISTS products")
        cur.execute("DROP TABLE IF EXISTS users")
        cur.execute("DROP TABLE IF EXISTS orders")
        cur.execute("DROP TABLE IF EXISTS order_items")
        cur.execute("DROP TABLE IF EXISTS ads")

        # ===== СОЗДАЁМ ВСЁ ЗАНОВО =====

        # Таблица пользователей
        cur.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                balance INTEGER DEFAULT 100,
                role TEXT DEFAULT 'user',
                banned INTEGER DEFAULT 0,
                avatar TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица товаров
        cur.execute('''
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                price INTEGER NOT NULL,
                stock INTEGER DEFAULT 0,
                image TEXT,
                discount INTEGER DEFAULT 0
            )
        ''')

        # Таблица заказов
        cur.execute('''
            CREATE TABLE orders (
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

        # Таблица товаров в заказе
        cur.execute('''
            CREATE TABLE order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')

        # Таблица рекламы
        cur.execute('''
            CREATE TABLE ads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                text TEXT,
                link TEXT,
                image TEXT,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ===== АДМИН =====
        import hashlib
        admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
        cur.execute("INSERT INTO users (username, password, role, balance) VALUES (?, ?, ?, ?)",
                    ('admin', admin_pass, 'admin', 9999))

        # ===== ТОВАРЫ =====
        items = [
            # 🔧 ИНСТРУМЕНТЫ
            ('⛏️ Алмазная кирка', 'Прочная алмазная кирка', 'инструменты', 50, 20, '', 10),
            ('🪓 Алмазный топор', 'Острый алмазный топор', 'инструменты', 45, 15, '', 5),
            ('🧹 Алмазная лопата', 'Удобная алмазная лопата', 'инструменты', 30, 25, '', 0),
            ('⛏️ Железная кирка', 'Надёжная железная кирка', 'инструменты', 20, 40, '', 0),

            # 🧱 БЛОКИ
            ('🧱 Каменный блок', 'Прочный каменный блок', 'блоки', 5, 100, '', 0),
            ('🪵 Древесный блок', 'Натуральный древесный блок', 'блоки', 3, 150, '', 0),
            ('🪟 Стеклянный блок', 'Прозрачный стеклянный блок', 'блоки', 4, 80, '', 0),
            ('🧱 Кирпичный блок', 'Красивый кирпичный блок', 'блоки', 8, 60, '', 0),
            ('🔮 Обсидиановый блок', 'Чёрный обсидиановый блок', 'блоки', 12, 30, '', 0),

            # 🍔 ЕДА
            ('🍞 Хлеб', 'Свежий пшеничный хлеб', 'еда', 2, 200, '', 0),
            ('🍪 Печенье', 'Хрустящее печенье', 'еда', 3, 150, '', 0),

            # 📦 РАЗНОЕ
            ('🏹 Стрелы', 'Острые стрелы для лука', 'разное', 10, 100, '', 0),
            ('🔥 Факел', 'Яркий факел для освещения', 'разное', 2, 200, '', 0),
        ]
        for name, desc, cat, price, stock, img, discount in items:
            cur.execute(
                "INSERT INTO products (name, description, category, price, stock, image, discount) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, desc, cat, price, stock, img, discount)
            )

        # ===== РЕКЛАМА =====
        ads = [
            ('🍯 Добро пожаловать в Медовик!', 'Здесь вы найдёте лучшие товары за Мед коины', '', ''),
            ('🎉 Скидки до 50%!', 'Только сегодня на все товары!', '', ''),
            ('🚀 Новинки каждую неделю', 'Следите за обновлениями!', '', ''),
            ('💎 Пополни баланс и получи бонус!', '+10% при пополнении от 1000 🍯', '', ''),
        ]
        for title, text, link, img in ads:
            cur.execute(
                "INSERT INTO ads (title, text, link, image) VALUES (?, ?, ?, ?)",
                (title, text, link, img)
            )

        conn.commit()
        conn.close()

    # ===== ПОЛЬЗОВАТЕЛИ =====
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
                'avatar': user[6] if len(user) > 6 else '',
                'created_at': user[7] if len(user) > 7 else ''
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
                'avatar': user[6] if len(user) > 6 else '',
                'created_at': user[7] if len(user) > 7 else ''
            }
        return None

    def update_user_avatar(self, username, avatar_path):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET avatar=? WHERE username=?", (avatar_path, username))
        conn.commit()
        conn.close()

    def update_user_avatar_by_id(self, user_id, avatar_path):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET avatar=? WHERE id=?", (avatar_path, user_id))
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

    def make_seller(self, user_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET role='seller' WHERE id=?", (user_id,))
        conn.commit()
        conn.close()

    def get_all_users(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, balance, role, banned, avatar, created_at FROM users")
        users = cur.fetchall()
        conn.close()
        return [
            {
                'id': u[0], 'username': u[1], 'balance': int(u[2] or 0),
                'role': u[3], 'banned': u[4] if len(u) > 4 else 0,
                'avatar': u[5] if len(u) > 5 else '',
                'created_at': u[6] if len(u) > 6 else ''
            }
            for u in users
        ]

    # ===== ТОВАРЫ =====
    def add_product(self, name, description, category, price, stock, image, discount=0):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO products (name, description, category, price, stock, image, discount) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, description, category, price, stock, image, discount)
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
                'stock': int(p[5] or 0), 'image': p[6],
                'discount': int(p[7] or 0) if len(p) > 7 else 0
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
                'stock': int(p[5] or 0), 'image': p[6],
                'discount': int(p[7] or 0) if len(p) > 7 else 0
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
                'stock': int(p[5] or 0), 'image': p[6],
                'discount': int(p[7] or 0) if len(p) > 7 else 0
            }
            for p in products
        ]

    def delete_product(self, product_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        conn.close()

    # ===== ЗАКАЗЫ =====
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

    # ===== РЕКЛАМА =====
    def get_all_ads(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM ads WHERE active=1 ORDER BY id ASC")
        ads = cur.fetchall()
        conn.close()
        return [
            {
                'id': a[0], 'title': a[1], 'text': a[2],
                'link': a[3], 'image': a[4],
                'active': a[5] if len(a) > 5 else 1,
                'created_at': a[6] if len(a) > 6 else ''
            }
            for a in ads
        ]

    def get_ad(self, ad_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM ads WHERE id=?", (ad_id,))
        ad = cur.fetchone()
        conn.close()
        if ad:
            return {
                'id': ad[0], 'title': ad[1], 'text': ad[2],
                'link': ad[3], 'image': ad[4],
                'active': ad[5] if len(ad) > 5 else 1,
                'created_at': ad[6] if len(ad) > 6 else ''
            }
        return None

    def toggle_ad(self, ad_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE ads SET active = CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?", (ad_id,))
        conn.commit()
        conn.close()

    def add_ad(self, title, text, link, image):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ads (title, text, link, image) VALUES (?, ?, ?, ?)",
            (title, text, link, image)
        )
        conn.commit()
        conn.close()

    def delete_ad(self, ad_id):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM ads WHERE id=?", (ad_id,))
        conn.commit()
        conn.close()
