import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8827095918:AAEcl15umAZe3LGNKJ1mhqm_eZmPY55Gzrs"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📦 Мои заказы"), KeyboardButton("🔗 Привязать аккаунт")],
        [KeyboardButton("🛍️ Стать продавцом"), KeyboardButton("❓ Помощь")],
        [KeyboardButton("🏠 Главная страница")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🐝 <b>Добро пожаловать в Медовик!</b>\n\n"
        "🍯 Бот работает! Нажми любую кнопку.",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот работает! Команда /help выполнена.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"✅ Вы написали: {text}\n\nБот работает!")

def main():
    print("🤖 Запускаю бота...")
    print(f"📌 Токен: {TELEGRAM_TOKEN[:10]}...")
    
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ Бот запущен! Напиши /start в Telegram.")
        application.run_polling()
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    main()
