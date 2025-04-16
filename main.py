import asyncio
import os
import uuid
import hashlib
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import Database
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройки базы данных
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'db': os.getenv('DB_NAME'),
}

# Отладочная информация
print(f"Параметры подключения к БД: {DB_CONFIG['host']}, {DB_CONFIG['user']}, {DB_CONFIG['db']}")

# Инициализация бота
bot = Bot(token=os.getenv('BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Константы
MINI_APP_URL = os.getenv('MINI_APP_URL')
REFERRAL_BONUS_REQUESTS = int(os.getenv('REFERRAL_BONUS_REQUESTS', 5))

# Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user = message.from_user
    chat = message.chat
    
    # Инициализация соединения с базой данных
    db = Database()
    
    # Проверка подключения к базе данных с выводом отладочной информации
    if not db.connection or db.connection._closed:
        print(f"Ошибка подключения к БД. Параметры: {DB_CONFIG}")
        await message.reply("Извините, произошла ошибка при подключении к базе данных")
        return
    
    # Инициализация БД (создание таблиц, если их нет)
    db.init_db()
    
    # Получаем данные о пользователе
    user_data = db.get_user(user.id)
    is_new_user = user_data is None
    
    # Реферальная система: проверяем реферальный код, если он есть в аргументах команды
    referral_code = None
    command_args = message.text.split()
    if len(command_args) > 1:
        referral_code = command_args[1]
        
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
        bot_username = (await bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_ref_code}"
        
        welcome_text += (
            "\n🔗 Ваша реферальная ссылка:\n"
            f"{ref_link}\n\n"
            f"Приглашайте друзей и получайте {REFERRAL_BONUS_REQUESTS} бонусных запросов за каждого!"
        )
    
    # Создаем кнопки для мини-приложения
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="🌐 Открыть мини-приложение", 
        web_app=types.WebAppInfo(url=MINI_APP_URL)
    ))
    
    # Добавляем кнопку для копирования реферальной ссылки
    if user_ref_code:
        builder.add(types.InlineKeyboardButton(
            text="🔗 Скопировать реферальную ссылку", 
            callback_data=f"copy_ref:{user_ref_code}"
        ))
    
    builder.adjust(1)  # По одной кнопке в каждом ряду
    
    # Отправляем сообщение
    await message.reply(
        welcome_text,
        reply_markup=builder.as_markup()
    )

# Обработчик callback запросов от inline кнопок
@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    """Обработчик callback запросов от inline кнопок"""
    await callback.answer()
    
    if callback.data.startswith("copy_ref:"):
        ref_code = callback.data.split(":")[1]
        bot_username = (await bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={ref_code}"
        
        # Отправляем сообщение с возможностью копирования
        await callback.message.reply(
            f"🔗 Ваша реферальная ссылка:\n\n{ref_link}\n\n"
            f"Отправьте эту ссылку друзьям и получите {REFERRAL_BONUS_REQUESTS} бонусных запросов "
            "за каждого нового пользователя!"
        )

# Основная функция
async def main():
    print("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    # Проверяем наличие всех необходимых переменных окружения
    required_vars = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'BOT_TOKEN']
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"Отсутствуют необходимые переменные окружения: {', '.join(missing)}")
        exit(1)
        
    asyncio.run(main())
