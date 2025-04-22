import os
import uuid
import hashlib
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from database import Database

# Загрузка переменных окружения
load_dotenv()

# Конфигурация базы данных
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

# Токен бота и URL мини-приложения
TOKEN = os.getenv('BOT_TOKEN')
MINI_APP_URL = os.getenv('MINI_APP_URL')
REFERRAL_BONUS_REQUESTS = int(os.getenv('REFERRAL_BONUS_REQUESTS', 5))

# Инициализация
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
db = Database(config=DB_CONFIG)


@dp.message(CommandStart())
async def start_handler(message: Message):
    user = message.from_user

    if not db.connect():
        await message.answer("Извините, произошла ошибка при подключении к базе данных")
        return

    user_data = db.get_user(user.id)
    is_new_user = user_data is None

    referral_code = message.text.split(" ")[1] if len(message.text.split(" ")) > 1 else None
    referral_info = None

    if referral_code:
        referral_info = db.get_referral(referral_code)

        if referral_info and referral_info['user_id'] != user.id:
            if is_new_user or not db.check_referral_used(user.id, referral_info['user_id']):
                db.add_requests(referral_info['user_id'], REFERRAL_BONUS_REQUESTS)
                if not is_new_user:
                    db.save_referral_history(
                        referrer_id=referral_info['user_id'],
                        referred_user_id=user.id,
                        referral_code=referral_code,
                        bonus_requests=REFERRAL_BONUS_REQUESTS
                    )

    db.save_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_bot=user.is_bot,
        language_code=user.language_code,
        chat_id=message.chat.id,
        contact=None,
        is_active=True
    )

    user_data = db.get_user(user.id)
    user_ref_code = db.get_user_referral(user_data['user_id']) if user_data else None

    if user_data and not user_ref_code:
        ref_base = f"{user.id}_{uuid.uuid4()}"
        ref_code = hashlib.md5(ref_base.encode()).hexdigest()[:8]
        db.create_referral(user_data['user_id'], ref_code)
        user_ref_code = ref_code

        if referral_code and referral_info:
            db.save_referral_history(
                referrer_id=referral_info['user_id'],
                referred_user_id=user_data['user_id'],
                referral_code=referral_code,
                bonus_requests=REFERRAL_BONUS_REQUESTS
            )

    requests_left = user_data.get('requests_left', 0) if user_data else 0

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

    if user_ref_code:
        bot_username = (await bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_ref_code}"

        welcome_text += (
            "\n🔗 Ваша реферальная ссылка:\n"
            f"{ref_link}\n\n"
            f"Приглашайте друзей и получайте {REFERRAL_BONUS_REQUESTS} бонусных запросов за каждого!"
        )

    # Создаем клавиатуру с помощью билдера
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопку мини-приложения только если URL задан
    if MINI_APP_URL:
        builder.add(InlineKeyboardButton(
            text="🌐 Открыть мини-приложение",
            web_app=WebAppInfo(url=MINI_APP_URL)
        ))

    if user_ref_code:
        builder.add(InlineKeyboardButton(
            text="🔗 Скопировать реферальную ссылку",
            callback_data=f"copy_ref:{user_ref_code}"
        ))
    
    builder.adjust(1)  # Размещаем кнопки по одной в ряд

    # Отправляем сообщение с клавиатурой только если есть хотя бы одна кнопка
    if builder.buttons:
        await message.answer(welcome_text, reply_markup=builder.as_markup())
    else:
        await message.answer(welcome_text)


@dp.callback_query(F.data.startswith("copy_ref:"))
async def handle_callback(query: CallbackQuery):
    ref_code = query.data.split(":")[1]
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={ref_code}"

    await query.message.answer(
        f"🔗 Ваша реферальная ссылка:\n\n{ref_link}\n\n"
        f"Отправьте эту ссылку друзьям и получите {REFERRAL_BONUS_REQUESTS} бонусных запросов "
        "за каждого нового пользователя!"
    )
    await query.answer()


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
