import logging
import os
import random
import string
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

from database import Database

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение токена бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не указан BOT_TOKEN в .env файле")

# Получение конфигурации БД из переменных окружения
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'db': os.getenv('DB_NAME', 'chatbot_db'),
    'charset': os.getenv('DB_CHARSET', 'utf8mb4')
}

# Отладочная информация
print(f"Параметры подключения к БД: {DB_CONFIG['host']}, {DB_CONFIG['user']}, {DB_CONFIG['db']}")

# Инициализация бота и базы данных
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db = Database(DB_CONFIG)

# Константы
MINI_APP_URL = os.getenv('MINI_APP_URL')
REFERRAL_BONUS_REQUESTS = int(os.getenv('REFERRAL_BONUS_REQUESTS', 5))

# Определение состояний для FSM (машины состояний)
class UserState(StatesGroup):
    waiting_for_contact = State()
    registered = State()

# Обработчик команды /start
@dp.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    language_code = message.from_user.language_code
    is_bot = message.from_user.is_bot
    chat_id = message.chat.id
    
    # Проверяем, если пришел реферальный код
    referral_code = None
    args = message.text.split()[1:] if message.text and len(message.text.split()) > 1 else []
    if args:
        referral_code = args[0]
    
    # Получаем информацию о пользователе из БД
    user_data = db.get_user(user_id)
    
    # Проверяем, есть ли у пользователя сохраненный контакт
    if user_data and user_data.get('contact'):
        # Пользователь уже отправил контакт, переводим в состояние registered
        await state.set_state(UserState.registered)
        
        # Показываем приветственное сообщение
        await show_welcome_message(message, user_id)
    else:
        # Создаем или обновляем только базовую информацию пользователя в БД
        if not user_data:  # Создаем нового пользователя только если его нет в БД
            db.save_user(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                chat_id=chat_id,
                is_bot=is_bot,
                language_code=language_code,
                is_active=True
            )
        
        if referral_code:
            # Сохраняем реферальный код для последующего использования
            await state.update_data(referral_code=referral_code)
        
        # Запрашиваем контакт у пользователя
        contact_button = KeyboardButton(text="📱 Отправить контакт", request_contact=True)
        markup = ReplyKeyboardMarkup(
            keyboard=[[contact_button]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.reply(
            "👋 Добро пожаловать в бота!\n\n"
            "Для продолжения, пожалуйста, поделитесь вашим контактом, "
            "нажав кнопку ниже:",
            reply_markup=markup
        )
        
        await state.set_state(UserState.waiting_for_contact)

# Добавляем новую команду для обновления контакта
@dp.message(Command("update_contact"))
async def update_contact_cmd(message: Message, state: FSMContext):
    """Обработчик команды обновления контакта"""
    user_id = message.from_user.id
    
    # Создаем клавиатуру с кнопкой отправки контакта
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    contact_button = KeyboardButton("📱 Отправить контакт", request_contact=True)
    markup.add(contact_button)
    
    await message.reply(
        "Пожалуйста, поделитесь вашим контактом для обновления. "
        "Нажмите кнопку ниже:",
        reply_markup=markup
    )
    
    await UserState.waiting_for_contact.set()

# Улучшаем обработчик получения контакта
@dp.message(F.contact, UserState.waiting_for_contact)
async def process_contact(message: Message, state: FSMContext):
    """Обработчик получения контакта от пользователя"""
    user_id = message.from_user.id
    contact = message.contact
    chat_id = message.chat.id
    
    try:
        # Валидация номера телефона
        if not contact.phone_number:
            await message.reply("❌ Номер телефона не указан. Пожалуйста, попробуйте еще раз.")
            return
            
        # Проверяем формат номера телефона
        phone_number = contact.phone_number
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
            
        # Получаем данные из состояния
        state_data = await state.get_data()
        referral_code = state_data.get('referral_code')
        
        # Сохраняем контакт пользователя в базе данных
        db.save_user(
            user_id=user_id, 
            username=message.from_user.username, 
            first_name=message.from_user.first_name, 
            last_name=message.from_user.last_name,
            chat_id=chat_id,
            contact=phone_number,  # Передаем сам номер телефона, а не объект contact
            is_bot=message.from_user.is_bot,
            language_code=message.from_user.language_code,
            is_active=True
        )
        
        # Генерируем реферальный код для нового пользователя
        new_ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        db.update_user_referral_code(user_id, new_ref_code)
        
        # Обработка реферального кода, если пользователь пришел по ссылке
        if referral_code:
            referrer_id = db.get_user_by_referral_code(referral_code)
            if referrer_id and referrer_id != user_id:
                # Сохраняем информацию о реферале
                db.save_referral_history(referrer_id, user_id, referral_code, REFERRAL_BONUS_REQUESTS)
                # Добавляем бонусные запросы только реферреру
                success = db.increase_user_requests(referrer_id, REFERRAL_BONUS_REQUESTS)
                
                if success:
                    logging.info(f"Успешно добавлены бонусные запросы {REFERRAL_BONUS_REQUESTS} пользователю {referrer_id}")
                else:
                    logging.error(f"Не удалось добавить бонусные запросы пользователю {referrer_id}")
                
                # Уведомляем реферера
                try:
                    await bot.send_message(
                        referrer_id,
                        f"🎉 По вашей реферальной ссылке зарегистрировался новый пользователь!\n"
                        f"Вам начислено {REFERRAL_BONUS_REQUESTS} дополнительных запросов."
                    )
                except Exception as e:
                    logging.error(f"Ошибка при отправке уведомления реферреру: {e}")
            else:
                logging.warning(f"Не удалось найти реферера для кода {referral_code} или пользователь пытается использовать свой код")
        else:
            logging.info("Нет реферального кода при регистрации пользователя")

        # Удаляем клавиатуру и отправляем сообщение об успехе
        await message.reply(
            "✅ Ваш контакт успешно сохранен!",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Переводим пользователя в статус зарегистрированного
        await state.set_state(UserState.registered)
        
        # Показываем приветственное сообщение
        await show_welcome_message(message, user_id)
        
    except Exception as e:
        logging.error(f"Ошибка при сохранении контакта: {e}")
        logging.exception("Полный стек ошибки:")
        await message.reply(
            "❌ Произошла ошибка при сохранении контакта. Пожалуйста, попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
        )

# Функция для отображения приветственного сообщения
async def show_welcome_message(message: Message, user_id: int):
    """Показывает приветственное сообщение пользователю"""
    # Получаем данные пользователя
    user_data = db.get_user(user_id)
    
    if not user_data:
        logging.error(f"Пользователь {user_id} не найден в базе данных")
        return
    
    # Получаем реферальный код пользователя
    referral_code = db.get_user_referral_code(user_id)
    if not referral_code:
        # Если по какой-то причине код не был сгенерирован ранее
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        db.update_user_referral_code(user_id, referral_code)
    
    # Формируем реферальную ссылку
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    # Создаем клавиатуру
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Начать чат", callback_data="start_chat")],
        [InlineKeyboardButton(text="👥 Пригласить друга", callback_data="invite_friend")],
        [InlineKeyboardButton(text="📊 Мой профиль", callback_data="profile")]
    ])
    
    # Отправляем приветственное сообщение
    await message.reply(
        f"👋 Добро пожаловать в бот!\n\n"
        f"У вас осталось {user_data.get('requests_left', 0)} запросов.\n\n"
        f"🔗 Ваша реферальная ссылка:\n{referral_link}\n\n"
        f"Приглашайте друзей и получайте дополнительные запросы!\n"
        f"За каждого приглашенного друга вы получите {REFERRAL_BONUS_REQUESTS} бонусных запросов.\n\n"
        f"Выберите действие:",
        reply_markup=markup
    )

# Обработчики callback-запросов от inline-кнопок
@dp.callback_query(F.data == 'start_chat', UserState.registered)
async def process_start_chat(callback_query: types.CallbackQuery):
    """Обработчик начала чата"""
    await callback_query.answer()
    await bot.send_message(
        callback_query.from_user.id,
        "Введите ваш запрос и я постараюсь на него ответить."
    )

@dp.callback_query(F.data == 'invite_friend', UserState.registered)
async def process_invite_friend(callback_query: types.CallbackQuery):
    """Обработчик приглашения друга"""
    user_id = callback_query.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await callback_query.answer("Ошибка получения данных пользователя")
        return
    
    # Получаем реферальный код
    referral_code = db.get_user_referral_code(user_id)
    
    if not referral_code:
        # Генерируем новый код, если его нет
        referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        success = db.update_user_referral_code(user_id, referral_code)
        
        if not success:
            logging.error(f"Не удалось создать реферальный код для пользователя {user_id}")
            await callback_query.answer("Произошла ошибка при создании реферальной ссылки")
            return
        
        # Проверяем, был ли код действительно создан
        referral_code = db.get_user_referral_code(user_id)
        if not referral_code:
            logging.error(f"Реферальный код не был сохранен для пользователя {user_id}")
            await callback_query.answer("Произошла ошибка при создании реферальной ссылки")
            return
    
    # Формируем реферальную ссылку
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    await callback_query.answer()
    await bot.send_message(
        user_id,
        f"Поделитесь этой ссылкой с друзьями и получите бонусные запросы:\n\n"
        f"[Ваша реферальная ссылка]({referral_link})\n\n"
        f"За каждого приглашенного друга вы получите {REFERRAL_BONUS_REQUESTS} дополнительных запросов!",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == 'profile', UserState.registered)
async def process_profile(callback_query: types.CallbackQuery):
    """Обработчик просмотра профиля"""
    user_id = callback_query.from_user.id
    user_data = db.get_user(user_id)
    
    if not user_data:
        await callback_query.answer("Ошибка получения данных профиля")
        return
    
    await callback_query.answer()
    await bot.send_message(
        user_id,
        f"📊 Ваш профиль:\n\n"
        f"👤 ID: {user_id}\n"
        f"📱 Телефон: {user_data.get('contact', 'Не указан')}\n"
        f"🔢 Осталось запросов: {user_data.get('requests_left', 0)}\n"
        f"📅 Дата регистрации: {user_data.get('created_at', 'Неизвестно')}"
    )

# Основная функция
async def main():
    print("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    # Проверяем наличие всех необходимых переменных окружения
    required_env_vars = ['BOT_TOKEN', 'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Отсутствуют следующие переменные окружения: {', '.join(missing_vars)}")
        print("Пожалуйста, укажите все необходимые переменные в файле .env")
        exit(1)
    
    print("Бот запущен!")
    # Запускаем бота
    import asyncio
    asyncio.run(main())
