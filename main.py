import hashlib
import logging
import os
import uuid

from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
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
async def start_handler(message: Message, state: FSMContext):
    user = message.from_user

    # Проверяем, есть ли пользователь в базе и есть ли у него контакт
    user_data = db.get_user(user.id)
    user_exists = user_data is not None
    has_contact = user_exists and 'contact' in user_data and user_data['contact']

    # Сохраняем пользователя в базе данных (обновляем информацию)
    db.save_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        chat_id=message.chat.id,
        is_bot=user.is_bot,
        language_code=user.language_code
    )

    # Обновляем информацию о пользователе
    user_data = db.get_user(user.id)

    # Проверяем реферальный код в команде /start только для новых пользователей
    if not user_exists:
        referral_code = message.text.split()[1] if len(message.text.split()) > 1 else None
        if referral_code:
            referral_info = db.get_referral(referral_code)
            if referral_info and referral_info['telegram_id'] != user.id:
                # Добавляем бонусные запросы пригласившему пользователю
                db.add_requests(referral_info['telegram_id'], REFERRAL_BONUS_REQUESTS)

    # Генерируем реферальный код для пользователя, если его еще нет
    if not db.get_user_referral_code(user.id):
        ref_base = f"{user.id}_{uuid.uuid4()}"
        ref_code = hashlib.md5(ref_base.encode()).hexdigest()[:8]
        db.create_referral(user.id, ref_code)

    # Получаем реферальные данные
    ref_data = db.get_user_referral_code(user.id)
    ref_link = f"https://t.me/testik_ai_bot?start={ref_data}" if ref_data else ""

    # Если пользователь уже есть в базе и у него есть контакт, показываем только баланс и реферальную ссылку
    if has_contact:
        balance_text = (
            f"👋 Здравствуйте, {user.first_name}!\n\n"
            f"🎉 Ваш баланс: {user_data['requests_left']} запросов.\n\n"
            f"Реферальная ссылка:\n{ref_link}\n\n"
            f"Приглашайте друзей и получайте {REFERRAL_BONUS_REQUESTS} бонусных запросов за каждого!"
        )

        # Создаем инлайн клавиатуру
        inline_keyboard = []

        if MINI_APP_URL:
            inline_keyboard.append([
                InlineKeyboardButton(
                    text="🌐 Открыть мини-приложение",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ])

        # Добавляем кнопку копирования реферальной ссылки
        if ref_data:
            inline_keyboard.append([
                InlineKeyboardButton(
                    text="🔗 Скопировать реферальную ссылку",
                    callback_data=f"copy_ref:{ref_data}"
                )
            ])

        # Создаем инлайн разметку, если есть кнопки
        inline_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard) if inline_keyboard else None

        # Отправляем сообщение о балансе и реферальную ссылку
        await message.answer(balance_text, reply_markup=inline_markup)
        return

    # Для новых пользователей или без контакта - стандартный процесс регистрации
    welcome_text = (
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        "Добро пожаловать в наш бот!\n"
        f"У вас есть {user_data['requests_left']} запросов.\n"
    )

    # Создаем инлайн клавиатуру
    inline_keyboard = []

    if MINI_APP_URL:
        inline_keyboard.append([
            InlineKeyboardButton(
                text="🌐 Открыть мини-приложение",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ])

    # Добавляем кнопку реферальной ссылки
    if ref_data:
        inline_keyboard.append([
            InlineKeyboardButton(
                text="🔗 Скопировать реферальную ссылку",
                callback_data=f"copy_ref:{ref_data}"
            )
        ])

        welcome_text += (
            f"\n🔗 Ваша реферальная ссылка:\n"
            f"{ref_link}\n\n"
            f"Приглашайте друзей и получайте {REFERRAL_BONUS_REQUESTS} бонусных запросов за каждого!"
        )

    # Создаем инлайн разметку, если есть кнопки
    inline_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard) if inline_keyboard else None

    # Создаем клавиатуру для запроса контакта
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    # Добавляем текст про контакт
    welcome_text += (
        "\n\n📱 Для продолжения, пожалуйста, поделитесь своим номером телефона.\n"
        "Нажмите на кнопку ниже, чтобы подтвердить контакт.\n\n"
        "🔒 Ваш номер будет использован только для связи и не будет передан третьим лицам."
    )

    # Отправляем сначала сообщение с инлайн кнопками (если есть)
    if inline_markup:
        await message.answer(welcome_text, reply_markup=inline_markup)
    else:
        await message.answer(welcome_text)

    # Отправляем клавиатуру для запроса контакта отдельным сообщением
    await message.answer("Нажмите на кнопку ниже:", reply_markup=contact_keyboard)

    # Устанавливаем состояние ожидания контакта
    await state.set_state(UserState.waiting_for_contact)


@dp.callback_query(F.data.startswith("copy_ref:"))
async def handle_copy_ref(callback: CallbackQuery):
    ref_code = callback.data.split(":")[1]
    ref_link = f"https://t.me/testik_ai_bot?start={ref_code}"

    await callback.message.answer(
        f"🔗 Ваша реферальная ссылка:\n\n{ref_link}\n\n"
        f"Отправьте эту ссылку друзьям и получите {REFERRAL_BONUS_REQUESTS} "
        "бонусных запросов за каждого нового пользователя!"
    )
    await callback.answer()


@dp.message(F.content_type == "contact", UserState.waiting_for_contact)
async def process_contact(message: Message, state: FSMContext):
    if message.contact is not None:
        # Сохраняем контакт в базу данных
        contact = message.contact.phone_number
        db.save_contact(message.from_user.id, contact)

        # Получаем информацию о количестве доступных запросов
        user = db.get_user(message.from_user.id)
        requests_left = user.get('requests_left', 0) if user else 0

        # Получаем реферальные данные
        ref_code = db.get_user_referral_code(message.from_user.id)
        ref_link = f"https://t.me/testik_ai_bot?start={ref_code}" if ref_code else ""

        # Текст сообщения с балансом и реферальной ссылкой
        complete_text = (
            f"✅ Спасибо! Ваш контакт успешно сохранен.\n\n"
            f"🎉 У вас есть {requests_left} доступных запросов.\n\n"
            f"Реферальная ссылка:\n{ref_link}"
        )
        remove_keyboard = types.ReplyKeyboardRemove()
        # Отправляем сообщение
        await message.answer(complete_text, reply_markup=remove_keyboard)

        # Сбрасываем состояние
        await state.clear()
    else:
        await message.answer(
            "❌ Произошла ошибка при получении контакта. Пожалуйста, попробуйте еще раз, "
            "нажав на кнопку 'Поделиться контактом'."
        )


@dp.message(UserState.waiting_for_contact)
async def process_invalid_contact(message: Message):
    """Обработка любых сообщений в состоянии ожидания контакта"""
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "⚠️ Пожалуйста, поделитесь своим контактом, используя специальную кнопку ниже.",
        reply_markup=contact_keyboard
    )


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())