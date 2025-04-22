import hashlib
import logging
import os
import uuid

from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

from database_bot import BotDatabase

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


class UserState(StatesGroup):
    waiting_for_contact = State()


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
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📱 Поделиться контактом", request_contact=True)
    keyboard.add(button)

    # Добавляем текст про контакт
    welcome_text += (
        "\n\n📱 Для продолжения, пожалуйста, поделитесь своим номером телефона.\n"
        "Нажмите на кнопку ниже, чтобы подтвердить контакт.\n\n"
        "🔒 Ваш номер будет использован только для связи и не будет передан третьим лицам."
    )
    await message.answer(welcome_text, reply_markup=markup)
    await UserState.waiting_for_contact.set()


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


@dp.message_handler(commands=['start'])
async def cmd_start(message: Message):
    # Сохраняем базовую информацию о пользователе
    db.save_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        chat_id=message.chat.id,
        is_bot=message.from_user.is_bot,
        language_code=message.from_user.language_code
    )

    # Создаем клавиатуру с кнопкой запроса контакта
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton("📱 Поделиться контактом", request_contact=True)
    keyboard.add(button)

    # Отправляем приветственное сообщение
    await message.answer(
        f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
        "Для начала работы с ботом, пожалуйста, поделитесь своим контактным номером, "
        "нажав на кнопку ниже.\n\n"
        "🔒 Ваш номер будет использоваться только для связи с вами и не будет передан третьим лицам.",
        reply_markup=keyboard
    )

    # Устанавливаем состояние ожидания контакта
    await UserState.waiting_for_contact.set()


@dp.message_handler(content_types=['contact'], state=UserState.waiting_for_contact)
async def process_contact(message: Message, state: FSMContext):
    if message.contact is not None:
        # Сохраняем контакт в базу данных
        contact = message.contact.phone_number
        db.save_contact(message.from_user.id, contact)

        # Получаем информацию о количестве доступных запросов
        user = db.get_user(message.from_user.id)
        requests_left = user.get('requests_left', 0) if user else 0

        # Создаем обычную клавиатуру для дальнейшего взаимодействия
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("🔍 Начать поиск"))
        keyboard.add(types.KeyboardButton("💫 Мои запросы"))
        keyboard.add(types.KeyboardButton("ℹ️ Помощь"))

        # Отправляем сообщение об успешной регистрации
        await message.answer(
            f"✅ Спасибо! Ваш контакт успешно сохранен.\n\n"
            f"🎉 У вас есть {requests_left} доступных запросов.\n\n"
            f"Выберите действие из меню ниже:",
            reply_markup=keyboard
        )

        # Сбрасываем состояние
        await state.finish()
    else:
        await message.answer(
            "❌ Произошла ошибка при получении контакта. Пожалуйста, попробуйте еще раз, "
            "нажав на кнопку 'Поделиться контактом'."
        )


@dp.message_handler(state=UserState.waiting_for_contact)
async def process_invalid_contact(message: Message):
    """Обработка любых сообщений в состоянии ожидания контакта"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton("📱 Поделиться контактом", request_contact=True)
    keyboard.add(button)

    await message.answer(
        "⚠️ Пожалуйста, поделитесь своим контактом, используя специальную кнопку ниже.",
        reply_markup=keyboard
    )


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
