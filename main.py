from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from database import Database
import os
import uuid
import hashlib
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# Загрузка переменных окружения
load_dotenv()

# Конфигурация базы данных
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'root'),
    'database': os.getenv('DB_NAME', 'ai_bot')
}

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv('BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных с конфигурацией MySQL
db = Database()
db.init_db()  # Инициализируем базу данных и создаем таблицы

# Токен бота
TOKEN = os.getenv('BOT_TOKEN')
# URL мини-приложения
MINI_APP_URL = os.getenv('MINI_APP_URL')
# Количество бонусных запросов за реферала
REFERRAL_BONUS_REQUESTS = int(os.getenv('REFERRAL_BONUS_REQUESTS', 5))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.message.from_user
    chat = update.message.chat
    
    # Подключаемся к базе данных
    if not db.connect():
        await update.message.reply_text("Извините, произошла ошибка при подключении к базе данных")
        return
    
    # Получаем информацию о пользователе из базы данных
    user_data = db.get_user(user.id)
    is_new_user = user_data is None
    
    # Реферальная система: проверяем реферальный код, если он есть в аргументах команды
    referral_code = None
    if context.args and len(context.args) > 0:
        referral_code = context.args[0]
        
        # Получаем информацию о владельце реферального кода
        referral_info = db.get_referral(referral_code)
        
        if referral_info and referral_info['user_id'] != user.id:  # Проверяем, что это не собственный код пользователя
            # Проверяем, является ли пользователь новым или уже переходил по реф. ссылке
            if is_new_user or not db.check_referral_used(user.id, referral_info['user_id']):
                # Даем бонусные запросы пригласившему пользователю
                db.add_requests(referral_info['user_id'], REFERRAL_BONUS_REQUESTS)
                
                # Сохраняем информацию о реферальном переходе
                if not is_new_user:  # Если пользователь уже существует
                    db.save_referral_history(
                        referrer_id=referral_info['user_id'],
                        referred_user_id=user.id,
                        referral_code=referral_code,
                        bonus_requests=REFERRAL_BONUS_REQUESTS
                    )
    
    # Пытаемся сохранить пользователя и получаем результат операции
    db.save_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_bot=user.is_bot,
        language_code=user.language_code,
        chat_id=chat.id,
        contact=None,
        is_active=True
    )
    
    # Если это новый пользователь или у него еще нет реферального кода, создаем для него реферальную ссылку
    user_data = db.get_user(user.id)  # Обновляем данные пользователя после сохранения
    user_ref_code = db.get_user_referral(user_data['user_id']) if user_data else None
    
    if user_data and not user_ref_code:
        # Создаем уникальный код на основе ID пользователя и случайного UUID
        ref_base = f"{user.id}_{uuid.uuid4()}"
        ref_code = hashlib.md5(ref_base.encode()).hexdigest()[:8]
        
        # Сохраняем реферальную ссылку
        db.create_referral(user_data['user_id'], ref_code)
        user_ref_code = ref_code
        
        # Если был передан реферальный код при регистрации, сохраняем историю
        if referral_code and referral_info:
            db.save_referral_history(
                referrer_id=referral_info['user_id'],
                referred_user_id=user_data['user_id'],
                referral_code=referral_code,
                bonus_requests=REFERRAL_BONUS_REQUESTS
            )

    # Получаем информацию о пользователе, включая оставшиеся запросы
    requests_left = user_data.get('requests_left', 0) if user_data else 0
    
    # Создаем приветственное сообщение
    if is_new_user:
        welcome_text = (
            f"👋 Здравствуйте, {user.first_name}!\n\n"
            "Добро пожаловать в наш бот!\n"
            f"У вас есть {requests_left} запросов.\n"
        )
    else:
        welcome_text = (
            f"👋 С возвращением, {user.first_name}!\n\n"
            "Вы уже зарегистрированы в нашем боте.\n"
            f"У вас осталось {requests_left} запросов.\n"
        )
    
    # Добавляем информацию о реферальной программе
    if user_ref_code:
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start={user_ref_code}"
        
        welcome_text += (
            "\n🔗 Ваша реферальная ссылка:\n"
            f"{ref_link}\n\n"
            f"Приглашайте друзей и получайте {REFERRAL_BONUS_REQUESTS} бонусных запросов за каждого!"
        )
    
    # Создаем кнопки для мини-приложения
    keyboard = [
        [InlineKeyboardButton("🌐 Открыть мини-приложение", web_app=WebAppInfo(url=MINI_APP_URL))]
    ]
    
    # Добавляем кнопку для копирования реферальной ссылки
    if user_ref_code:
        keyboard.append([InlineKeyboardButton("🔗 Скопировать реферальную ссылку", callback_data=f"copy_ref:{user_ref_code}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback запросов от inline кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("copy_ref:"):
        ref_code = query.data.split(":")[1]
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start={ref_code}"
        
        # Отправляем сообщение с возможностью копирования
        await query.message.reply_text(
            f"🔗 Ваша реферальная ссылка:\n\n{ref_link}\n\n"
            f"Отправьте эту ссылку друзьям и получите {REFERRAL_BONUS_REQUESTS} бонусных запросов "
            "за каждого нового пользователя!"
        )

def main():
    """Основная функция"""
    # Создаем приложение бота
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler('start', start))
    
    # Добавляем обработчик для callback_query (для кнопок)
    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Запускаем бота
    print("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
