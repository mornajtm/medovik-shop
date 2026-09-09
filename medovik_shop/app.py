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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'avatars'), exist_ok=True)

db = Database()

# ===== ТЕЛЕГРАМ БОТ =====
TELEGRAM_TOKEN = "8827095918:AAEcl15umAZe3LGNKJ1mhqm_eZmPY55Gzrs"
bot_app = None
bot_running = False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_minecraft_avatar(username):
    """Скачивает голову скина Minecraft"""
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

def send_telegram_notification(order_id, user_id, total, address, pickup_point):
    """Отправляет уведомление в Telegram при создании заказа"""
    global bot_app, bot_running
    
    if not bot_app or not bot_running:
        print("⚠️ Бот не запущен, уведомление не отправлено")
        return
    
    try:
        user = db.get_user(user_id)
        if not user or not user.get('telegram'):
            print(f"⚠️ У пользователя {user_id} нет Telegram")
            return
        
        telegram_id = user['telegram'].replace('@', '')
        if not telegram_id:
            return
        
        message = f"""
🛒 <b>НОВЫЙ ЗАКАЗ!</b>

📦 Заказ #{order_id}
👤 Покупатель: {user['username']}
💰 Сумма: {total} Ар

📍 <b>Адрес доставки:</b>
{address}

🏪 <b>ПВЗ:</b>
{pickup_point}

📅 Дата: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}

Статус: 🔵 <b>Собираем</b>
"""
        keyboard = [
            [
                InlineKeyboardButton("📦 Собираем", callback_data=f"order_status_{order_id}_collecting"),
                InlineKeyboardButton("🚚 Доставляем", callback_data=f"order_status_{order_id}_delivering"),
                InlineKeyboardButton("✅ Доставлен", callback_data=f"order_status_{order_id}_delivered")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        asyncio.run_coroutine_threadsafe(
            bot_app.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode='HTML',
                reply_markup=reply_markup
            ),
            bot_app.loop
        )
        print(f"✅ Уведомление о заказе #{order_id} отправлено в Telegram")
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")

def update_telegram_order_status(order_id, status_text):
    """Обновляет статус заказа в Telegram"""
    global bot_app, bot_running
    
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
        
        status_emoji = {
            'collecting': '🔵',
            'delivering': '🟡',
            'delivered': '✅'
        }
        status_names = {
            'collecting': 'Собираем',
            'delivering': 'Доставляем',
            'delivered': 'Доставлен'
        }
        
        message = f"""
📦 <b>Заказ #{order_id} обновлён!</b>

Статус: {status_emoji.get(status_text, '🔵')} <b>{status_names.get(status_text, status_text)}</b>

👤 Покупатель: {user['username']}
💰 Сумма: {order['total']} Ар
📅 Обновлён: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
        asyncio.run_coroutine_threadsafe(
            bot_app.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode='HTML'
            ),
            bot_app.loop
        )
        print(f"✅ Статус заказа #{order_id} обновлён в Telegram")
    except Exception as e:
        print(f"❌ Ошибка обновления статуса в Telegram: {e}")

# ===== БОТ КОМАНДЫ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐝 <b>Добро пожаловать в Медовик!</b>\n\n"
        "Здесь вы можете:\n"
        "• Отслеживать свои заказы\n"
        "• Получать уведомления о статусе\n"
        "• Управлять доставкой\n\n"
        "Свяжите ваш Telegram с аккаунтом на сайте, чтобы получать уведомления!",
        parse_mode='HTML'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍯 <b>Помощь по боту</b>\n\n"
        "1. Зарегистрируйтесь на сайте Медовик\n"
        "2. В профиле укажите ваш Telegram (@username)\n"
        "3. При создании заказа вы получите уведомление\n"
        "4. Статус заказа можно отслеживать в боте\n\n"
        "Статусы:\n"
        "🔵 Собираем - заказ собирается\n"
        "🟡 Доставляем - заказ в пути\n"
        "✅ Доставлен - заказ получен",
        parse_mode='HTML'
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = db.get_user_by_telegram(update.message.from_user.username)
    if not user:
        await update.message.reply_text(
            "❌ Аккаунт не найден.\nПривяжите Telegram в профиле на сайте!"
        )
        return
    
    orders = db.get_user_orders(user['id'])
    if not orders:
        await update.message.reply_text("📭 У вас пока нет заказов.")
        return
    
    status_emoji = {
        'pending': '🆕',
        'collecting': '🔵',
        'delivering': '🟡',
        'delivered': '✅'
    }
    
    message = "📦 <b>Ваши заказы:</b>\n\n"
    for order in orders[:5]:
        emoji = status_emoji.get(order['status'], '🆕')
        message += f"{emoji} Заказ #{order['id']}: {order['total']} Ар\n"
    
    await update.message.reply_text(message, parse_mode='HTML')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    if data[0] == 'order' and data[1] == 'status':
        order_id = int(data[2])
        status = data[3]
        
        db.update_order_status(order_id, status)
        
        status_emoji = {
            'collecting': '🔵',
            'delivering': '🟡',
            'delivered': '✅'
        }
        status_names = {
            'collecting': 'Собираем',
            'delivering': 'Доставляем',
            'delivered': 'Доставлен'
        }
        
        new_text = query.message.text.replace(
            f"Статус: {status_emoji.get(status, '🔵')} <b>{status_names.get(status, status)}</b>",
            f"Статус: {status_emoji.get(status, '🔵')} <b>{status_names.get(status, status)}</b> ✅"
        )
        
        await query.edit_message_text(new_text, parse_mode='HTML')
        await query.message.reply_text(
            f"✅ Статус заказа #{order_id} обновлён на: {status_names.get(status, status)}"
        )

def run_bot():
    """Запуск Telegram бота"""
    global bot_app, bot_running
    
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "YOUR_BOT_TOKEN":
        print("⚠️ Telegram бот не запущен: токен не указан!")
        return
    
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).connect_timeout(30).read_timeout(30).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        bot_app = application
        bot_running = True
        
        print("🤖 Telegram бот запущен!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        bot_running = False

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
        if not user or user['role'] != 'admin':
            flash('Доступ запрещён', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    products = db.get_all_products()
    return render_template('index.html', products=products)

@app.route('/category/<category>')
def category(category):
    products = db.get_products_by_category(category)
    return render_template('index.html', products=products, category=category)

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
        pickup_point = request.form.get('pickup_point')
        
        if not address or not pickup_point:
            flash('Заполните все поля доставки!', 'danger')
            return redirect(url_for('checkout'))
        
        user = db.get_user(session['user_id'])
        total = 0
        for item in cart_items:
            product = db.get_product(item['id'])
            if product:
                total += product['price'] * item['quantity']
        
        if user['balance'] < total:
            flash(f'Недостаточно Ар! Нужно {total}, у вас {user["balance"]}', 'danger')
            return redirect(url_for('cart'))
        
        order_id = db.create_order(session['user_id'], total, address, pickup_point)
        for item in cart_items:
            product = db.get_product(item['id'])
            db.add_order_item(order_id, item['id'], item['quantity'], product['price'])
        
        db.update_balance(session['user_id'], -total)
        
        # Отправка в Telegram (если бот работает)
        send_telegram_notification(order_id, session['user_id'], total, address, pickup_point)
        
        session['cart'] = []
        flash(f'Заказ #{order_id} оформлен! -{total} Ар', 'success')
        return redirect(url_for('profile'))
    
    user = db.get_user(session['user_id'])
    total = 0
    products_in_cart = []
    for item in cart_items:
        product = db.get_product(item['id'])
        if product:
            products_in_cart.append({
                'product': product,
                'quantity': item['quantity']
            })
            total += product['price'] * item['quantity']
    
    return render_template('checkout.html', 
                         total=total, 
                         user=user, 
                         cart_items=products_in_cart)

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
    flash(f'Добавлено {amount} Ар', 'success')
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
        
        if price <= 0:
            flash('Цена должна быть больше 0', 'danger')
            return redirect(url_for('admin_products'))
        
        file = request.files.get('image')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        db.add_product(name, desc, category, price, stock, filename)
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
    # Запускаем бота в отдельном потоке с обработкой ошибок
    try:
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        time.sleep(3)  # Даём время на запуск
    except Exception as e:
        print(f"⚠️ Бот не запущен: {e}")
        print("✅ Сайт продолжит работу без бота!")
 
    # Запускаем Flask
    print("🚀 Запуск сайта Медовик...")
    app.run(debug=True, host='0.0.0.0', port=5000)

app.debug = False

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
