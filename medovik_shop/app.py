from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from database import Database
from functools import wraps
import hashlib
import secrets
import os
import requests
from PIL import Image
from io import BytesIO
from werkzeug.utils import secure_filename
import datetime
import threading
import asyncio
import time
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'avatars'), exist_ok=True)

db = Database()

# ===== ТЕЛЕГРАМ БОТ =====
TELEGRAM_TOKEN = "8827095918:AAG9mg1eNRGKSsx2aXrfTNaw90D6x98wcrI"
bot_app = None
bot_running = False
pending_links = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_minecraft_avatar(username):
    try:
        skin_url = f"https://crafatar.com/skins/{username}"
        response = requests.get(skin_url, timeout=10)
        
        if response.status_code == 200:
            skin_image = Image.open(BytesIO(response.content))
            head = skin_image.crop((8, 8, 16, 16))
            head = head.resize((100, 100), Image.NEAREST)
            
            avatar_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'avatars')
            os.makedirs(avatar_dir, exist_ok=True)
            
            avatar_path = os.path.join(avatar_dir, f'avatar_{username}.png')
            head.save(avatar_path, 'PNG')
            return f'uploads/avatars/avatar_{username}.png'
    except Exception as e:
        print(f"Ошибка загрузки скина: {e}")
        return None

# ===== БОТ КОМАНДЫ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📦 Мои заказы"), KeyboardButton("🔗 Привязать аккаунт")],
        [KeyboardButton("🛍️ Стать продавцом"), KeyboardButton("❓ Помощь")],
        [KeyboardButton("🏠 Главная страница")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🐝 <b>Добро пожаловать в Медовик!</b>\n\n"
        "🍯 Бот работает! Выбери действие:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍯 <b>Помощь по боту</b>\n\n"
        "📌 Команды:\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/orders - Мои заказы\n"
        "/link - Привязать аккаунт\n"
        "/seller - Стать продавцом\n\n"
        "🔗 Привязка аккаунта:\n"
        "1. Зайдите на сайт\n"
        "2. В профиле укажите Telegram\n"
        "3. Нажмите /link в боте\n\n"
        "📦 Статусы заказов:\n"
        "🔵 Собираем - заказ собирается\n"
        "🟡 Доставляем - заказ в пути\n"
        "✅ Доставлен - заказ получен",
        parse_mode='HTML'
    )

async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 <b>Ваши заказы</b>\n\n"
        "Для просмотра заказов:\n"
        "1. Зайдите на сайт\n"
        "2. Войдите в профиль\n"
        "3. Посмотрите историю заказов\n\n"
        f"🔗 https://medovik-shop.relaxdev.ru/profile",
        parse_mode='HTML'
    )

async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.from_user.username or "ваш_username"
    await update.message.reply_text(
        f"🔗 <b>Привязка аккаунта</b>\n\n"
        f"1. Зайдите на сайт: https://medovik-shop.relaxdev.ru\n"
        f"2. Войдите в свой профиль\n"
        f"3. В поле Telegram введите: @{username}\n"
        f"4. Сохраните изменения\n\n"
        f"После этого вы будете получать уведомления о заказах!",
        parse_mode='HTML'
    )

async def seller_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛍️ <b>Стать продавцом</b>\n\n"
        "Чтобы стать продавцом:\n"
        "1. Зайдите на сайт\n"
        "2. Зарегистрируйтесь\n"
        "3. Напишите администратору\n\n"
        f"🌐 https://medovik-shop.relaxdev.ru/register",
        parse_mode='HTML'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "📦 Мои заказы":
        await orders_command(update, context)
    elif text == "🔗 Привязать аккаунт":
        await link_command(update, context)
    elif text == "🛍️ Стать продавцом":
        await seller_command(update, context)
    elif text == "❓ Помощь":
        await help_command(update, context)
    elif text == "🏠 Главная страница":
        await update.message.reply_text(
            f"🌐 <b>Наш сайт:</b>\nhttps://medovik-shop.relaxdev.ru\n\n"
            "Здесь вы можете:\n"
            "• Просматривать товары\n"
            "• Покупать за 🍯 Мед коины\n"
            "• Управлять профилем",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"✅ Вы написали: {text}\n\nИспользуйте кнопки или /start."
        )

def run_bot():
    global bot_app, bot_running
    
    if not TELEGRAM_TOKEN:
        print("⚠️ Telegram бот не запущен: токен не указан!")
        return
    
    try:
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(connect_timeout=60.0, read_timeout=60.0)
        application = Application.builder().token(TELEGRAM_TOKEN).request(request).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("orders", orders_command))
        application.add_handler(CommandHandler("link", link_command))
        application.add_handler(CommandHandler("seller", seller_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        bot_app = application
        bot_running = True
        print("🤖 Telegram бот запущен!")
        application.run_polling()
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        bot_running = False

def send_telegram_notification(order_id, user_id, total, address, pickup_point):
    if not bot_app or not bot_running:
        return
    try:
        user = db.get_user(user_id)
        if not user or not user.get('telegram'):
            return
        telegram_id = user['telegram'].replace('@', '')
        if not telegram_id:
            return
        message = f"""
🛒 <b>НОВЫЙ ЗАКАЗ!</b>

📦 Заказ #{order_id}
👤 Покупатель: {user['username']}
💰 Сумма: {total} 🍯
📍 Адрес: {address}
📅 Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}
Статус: 🔵 Собираем
"""
        asyncio.run_coroutine_threadsafe(
            bot_app.bot.send_message(chat_id=telegram_id, text=message, parse_mode='HTML'),
            bot_app.loop
        )
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

def update_telegram_order_status(order_id, status_text):
    if not bot_app or not bot_running:
        return
    try:
        order = db.get_order(order_id)
        if not order:
            return
        user = db.get_user(order['user_id'])
        if not user or not user.get('telegram'):
            return
        telegram_id = user['telegram'].replace('@', '')
        status_emoji = {'collecting': '🔵', 'delivering': '🟡', 'delivered': '✅'}
        status_names = {'collecting': 'Собираем', 'delivering': 'Доставляем', 'delivered': 'Доставлен'}
        message = f"""
📦 <b>Заказ #{order_id} обновлён!</b>
Статус: {status_emoji.get(status_text, '🔵')} <b>{status_names.get(status_text, status_text)}</b>
👤 Покупатель: {user['username']}
💰 Сумма: {order['total']} 🍯
"""
        asyncio.run_coroutine_threadsafe(
            bot_app.bot.send_message(chat_id=telegram_id, text=message, parse_mode='HTML'),
            bot_app.loop
        )
    except Exception as e:
        print(f"Ошибка обновления статуса в Telegram: {e}")

# ===== МАРШРУТЫ ФЛЕСК =====
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Войдите в систему', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Войдите в систему', 'warning')
            return redirect(url_for('login'))
        user = db.get_user(session['user_id'])
        if not user or (user['role'] != 'admin' and user['role'] != 'seller'):
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    products = db.get_all_products()
    ads = db.get_all_ads()
    return render_template('index.html', products=products, ads=ads)

@app.route('/category/<category>')
def category(category):
    products = db.get_products_by_category(category)
    ads = db.get_all_ads()
    return render_template('index.html', products=products, category=category, ads=ads)

@app.route('/product/<int:product_id>')
def product_page(product_id):
    product = db.get_product(product_id)
    if not product:
        flash('Товар не найден', 'danger')
        return redirect(url_for('index'))
    similar = db.get_products_by_category(product['category'])
    similar = [p for p in similar if p['id'] != product_id][:4]
    return render_template('product.html', product=product, similar=similar)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if db.get_user_by_username(username):
            flash('Имя занято', 'danger')
            return redirect(url_for('register'))
        hashed = hashlib.sha256(password.encode()).hexdigest()
        db.create_user(username, hashed)
        avatar_path = get_minecraft_avatar(username)
        if avatar_path:
            db.update_user_avatar(username, avatar_path)
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = db.get_user_by_username(username)
        if user and user['password'] == hashlib.sha256(password.encode()).hexdigest():
            if user.get('banned', 0) == 1:
                flash('Ваш аккаунт заблокирован', 'danger')
                return redirect(url_for('login'))
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Добро пожаловать!', 'success')
            return redirect(url_for('index'))
        flash('Неверные данные', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    user = db.get_user(session['user_id'])
    orders = db.get_user_orders(session['user_id'])
    return render_template('profile.html', user=user, orders=orders)

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    telegram = request.form.get('telegram')
    discord = request.form.get('discord')
    db.update_user_socials(session['user_id'], telegram, discord)
    flash('Социальные сети обновлены!', 'success')
    return redirect(url_for('profile'))

@app.route('/cart')
@login_required
def cart():
    cart_items = session.get('cart', [])
    products = []
    total = 0
    for item in cart_items:
        product = db.get_product(item['id'])
        if product:
            products.append({'product': product, 'quantity': item['quantity']})
            total += product['price'] * item['quantity']
    return render_template('cart.html', products=products, total=total)

@app.route('/add_to_cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    cart = session.get('cart', [])
    for item in cart:
        if item['id'] == product_id:
            item['quantity'] += 1
            session['cart'] = cart
            flash('Добавлено в корзину', 'success')
            return redirect(request.referrer or url_for('index'))
    cart.append({'id': product_id, 'quantity': 1})
    session['cart'] = cart
    flash('Добавлено в корзину', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/remove_from_cart/<int:product_id>')
@login_required
def remove_from_cart(product_id):
    cart = session.get('cart', [])
    cart = [item for item in cart if item['id'] != product_id]
    session['cart'] = cart
    flash('Удалено из корзины', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = session.get('cart', [])
    if not cart_items:
        flash('Корзина пуста', 'warning')
        return redirect(url_for('cart'))
    if request.method == 'POST':
        address = request.form.get('address')
        pickup_point = request.form.get('pickup_point', 'ПВЗ в разработке')
        if not address:
            flash('Заполните адрес доставки!', 'danger')
            return redirect(url_for('checkout'))
        user = db.get_user(session['user_id'])
        total = 0
        for item in cart_items:
            product = db.get_product(item['id'])
            if product:
                total += product['price'] * item['quantity']
        if user['balance'] < total:
            flash(f'Недостаточно 🍯! Нужно {total}, у вас {user["balance"]}', 'danger')
            return redirect(url_for('cart'))
        order_id = db.create_order(session['user_id'], total, address, pickup_point)
        for item in cart_items:
            product = db.get_product(item['id'])
            db.add_order_item(order_id, item['id'], item['quantity'], product['price'])
        db.update_balance(session['user_id'], -total)
        send_telegram_notification(order_id, session['user_id'], total, address, pickup_point)
        session['cart'] = []
        flash(f'Заказ #{order_id} оформлен! -{total} 🍯', 'success')
        return redirect(url_for('profile'))
    user = db.get_user(session['user_id'])
    total = 0
    products_in_cart = []
    for item in cart_items:
        product = db.get_product(item['id'])
        if product:
            products_in_cart.append({'product': product, 'quantity': item['quantity']})
            total += product['price'] * item['quantity']
    return render_template('checkout.html', total=total, user=user, cart_items=products_in_cart)

@app.route('/admin')
@admin_required
def admin_dashboard():
    users = db.get_all_users()
    orders = db.get_all_orders()
    products = db.get_all_products()
    stats = {
        'users': len(users),
        'orders': len(orders),
        'products': len(products),
        'revenue': sum(o['total'] for o in orders),
        'banned': sum(1 for u in users if u.get('banned', 0) == 1)
    }
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = db.get_all_orders()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/order/update_status/<int:order_id>/<status>')
@admin_required
def admin_update_order_status(order_id, status):
    db.update_order_status(order_id, status)
    update_telegram_order_status(order_id, status)
    flash(f'Статус заказа #{order_id} обновлён!', 'success')
    return redirect(url_for('admin_orders'))

@app.route('/admin/users')
@admin_required
def admin_users():
    users = db.get_all_users()
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/ban/<int:user_id>')
@admin_required
def admin_ban_user(user_id):
    if user_id == session['user_id']:
        flash('Нельзя забанить самого себя', 'danger')
        return redirect(url_for('admin_users'))
    db.ban_user(user_id)
    flash('Пользователь заблокирован', 'info')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/unban/<int:user_id>')
@admin_required
def admin_unban_user(user_id):
    db.unban_user(user_id)
    flash('Пользователь разблокирован', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/change_password/<int:user_id>', methods=['POST'])
@admin_required
def admin_change_password(user_id):
    new_password = request.form.get('new_password')
    if not new_password or len(new_password) < 4:
        flash('Пароль должен быть минимум 4 символа', 'danger')
        return redirect(url_for('admin_users'))
    hashed = hashlib.sha256(new_password.encode()).hexdigest()
    db.change_password(user_id, hashed)
    flash('Пароль изменён', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/add_balance/<int:user_id>', methods=['POST'])
@admin_required
def admin_add_balance(user_id):
    amount = int(request.form.get('amount', 0))
    if amount <= 0:
        flash('Сумма должна быть больше 0', 'danger')
        return redirect(url_for('admin_users'))
    db.update_balance(user_id, amount)
    flash(f'Добавлено {amount} 🍯', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/products')
@admin_required
def admin_products():
    products = db.get_all_products()
    return render_template('admin/products.html', products=products)

@app.route('/admin/add_product', methods=['POST'])
@admin_required
def add_product():
    try:
        name = request.form.get('name')
        desc = request.form.get('description')
        category = request.form.get('category')
        price = int(request.form.get('price', 0))
        stock = int(request.form.get('stock', 0))
        discount = int(request.form.get('discount', 0))
        if price <= 0:
            flash('Цена должна быть больше 0', 'danger')
            return redirect(url_for('admin_products'))
        file = request.files.get('image')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        db.add_product(name, desc, category, price, stock, filename, discount)
        flash('Товар добавлен', 'success')
    except Exception as e:
        flash(f'Ошибка: {str(e)}', 'danger')
    return redirect(url_for('admin_products'))

@app.route('/admin/delete_product/<int:product_id>')
@admin_required
def delete_product(product_id):
    product = db.get_product(product_id)
    if product and product['image']:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], product['image']))
        except:
            pass
    db.delete_product(product_id)
    flash('Товар удалён', 'info')
    return redirect(url_for('admin_products'))

@app.route('/admin/ads')
@admin_required
def admin_ads():
    ads = db.get_all_ads()
    return render_template('admin/ads.html', ads=ads)

@app.route('/admin/add_ad', methods=['POST'])
@admin_required
def add_ad():
    title = request.form.get('title')
    text = request.form.get('text')
    link = request.form.get('link', '')
    file = request.files.get('image')
    filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    db.add_ad(title, text, link, filename)
    flash('Реклама добавлена!', 'success')
    return redirect(url_for('admin_ads'))

@app.route('/admin/delete_ad/<int:ad_id>')
@admin_required
def admin_delete_ad(ad_id):
    ad = db.get_ad(ad_id)
    if ad and ad.get('image'):
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], ad['image']))
        except:
            pass
    db.delete_ad(ad_id)
    flash('Реклама удалена', 'info')
    return redirect(url_for('admin_ads'))

@app.route('/admin/toggle_ad/<int:ad_id>')
@admin_required
def admin_toggle_ad(ad_id):
    db.toggle_ad(ad_id)
    flash('Статус рекламы изменён', 'info')
    return redirect(url_for('admin_ads'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.context_processor
def inject_user():
    user = None
    if 'user_id' in session:
        user = db.get_user(session['user_id'])
    return {'user': user}

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    time.sleep(2)
    app.run(debug=True, host='0.0.0.0', port=5000)
