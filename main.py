import os
import uuid
import hashlib
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from database_bot import BotDatabase

# Загрузка переменных окружения
load_dotenv()

# Инициализация бота и диспетчера
TOKEN = os.getenv('BOT_TOKEN')
MINI_APP_URL = os.getenv('MINI_APP_URL')
REFERRAL_BONUS_REQUESTS = int(os.getenv('REFERRAL_BONUS_REQUESTS', 3))

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
db = BotDatabase(
    host=os.getenv('DB_HOST'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME')
)

@dp.message(CommandStart())
async def start_handler(message: Message):
    user = message.from_user
    
    # Сохраняем пользователя в базе данных
    db.save_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        chat_id=message.chat.id,
        is_bot=user.is_bot,
        language_code=user.language_code
    )
    
    # Получаем информацию о пользователе
    user_data = db.get_user(user.id)
    
    # Проверяем реферальный код в команде /start
    referral_code = message.text.split()[1] if len(message.text.split()) > 1 else None
    
    if referral_code:
        referral_info = db.get_referral(referral_code)
        if referral_info and referral_info['telegram_id'] != user.id:
            # Добавляем бонусные запросы пригласившему пользователю
            db.add_requests(referral_info['telegram_id'], REFERRAL_BONUS_REQUESTS)
    
    # Генерируем реферальный код для пользователя
    if not db.get_referral(user.id):
        ref_base = f"{user.id}_{uuid.uuid4()}"
        ref_code = hashlib.md5(ref_base.encode()).hexdigest()[:8]
        db.create_referral(user.id, ref_code)
    
    # Создаем приветственное сообщение
    welcome_text = (
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        "Добро пожаловать в наш бот!\n"
        f"У вас есть {user_data['requests_left']} запросов.\n"
    )
    
    # Создаем клавиатуру
    keyboard = []
    
    if MINI_APP_URL:
        keyboard.append([
            InlineKeyboardButton(
                text="🌐 Открыть мини-приложение",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ])
    
    # Добавляем кнопку реферальной ссылки
    ref_data = db.get_referral(user.id)
    if ref_data:
        bot_info = await bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={ref_data['referral_code']}"
        keyboard.append([
            InlineKeyboardButton(
                text="🔗 Скопировать реферальную ссылку",
                callback_data=f"copy_ref:{ref_data['referral_code']}"
            )
        ])
        
        welcome_text += (
            f"\n🔗 Ваша реферальная ссылка:\n"
            f"{ref_link}\n\n"
            f"Приглашайте друзей и получайте {REFERRAL_BONUS_REQUESTS} бонусных запросов за каждого!"
        )
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    await message.answer(welcome_text, reply_markup=markup)

@dp.callback_query(F.data.startswith("copy_ref:"))
async def handle_copy_ref(callback: CallbackQuery):
    ref_code = callback.data.split(":")[1]
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={ref_code}"
    
    await callback.message.answer(
        f"🔗 Ваша реферальная ссылка:\n\n{ref_link}\n\n"
        f"Отправьте эту ссылку друзьям и получите {REFERRAL_BONUS_REQUESTS} "
        "бонусных запросов за каждого нового пользователя!"
    )
    await callback.answer()

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
