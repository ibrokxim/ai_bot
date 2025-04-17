import asyncio
import os
import uuid
import hashlib
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
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

# Определение состояний для FSM (машины состояний)
class UserStates(StatesGroup):
    waiting_for_contact = State()
    registered = State()

# Обработчик команды /start
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
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
    
    # Если пользователь уже отправил контакт ранее, показываем приветственное сообщение
    if user_data and user_data.get('phone_number'):
        await show_welcome_message(message, user_data, db)
        await state.set_state(UserStates.registered)
        return
    
    # Сохраняем реферальный код в состоянии, если он есть в аргументах команды
    command_args = message.text.split()
    if len(command_args) > 1:
        referral_code = command_args[1]
        await state.update_data(referral_code=referral_code)
    
    # Создаем клавиатуру для отправки контакта
    keyboard = ReplyKeyboardBuilder()
    keyboard.add(types.KeyboardButton(
        text="📱 Отправить контакт",
        request_contact=True
    ))
    keyboard.adjust(1)
    
    # Запрашиваем контакт
    await message.reply(
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        "Для продолжения работы с ботом, пожалуйста, поделитесь своим номером телефона, "
        "нажав на кнопку ниже.",
        reply_markup=keyboard.as_markup(resize_keyboard=True)
    )
    
    # Устанавливаем состояние ожидания контакта
    await state.set_state(UserStates.waiting_for_contact)

# Обработчик получения контакта
@dp.message(UserStates.waiting_for_contact, F.contact)
async def process_contact(message: types.Message, state: FSMContext):
    user = message.from_user
    chat = message.chat
    contact = message.contact
    
    print(f"Получен контакт от пользователя {user.id}: {contact.phone_number}")
    
    # Проверяем, что контакт принадлежит пользователю
    if contact.user_id != user.id:
        print(f"Контакт не принадлежит пользователю: {contact.user_id} != {user.id}")
        await message.reply(
            "Пожалуйста, отправьте свой собственный контакт, используя кнопку ниже.",
            reply_markup=ReplyKeyboardBuilder().add(
                types.KeyboardButton(text="📱 Отправить контакт", request_contact=True)
            ).as_markup(resize_keyboard=True)
        )
        return
    
    # Инициализация соединения с базой данных
    db = Database()
    
    # Проверка подключения к базе данных
    if not db.connection or db.connection._closed:
        print(f"Ошибка подключения к БД при обработке контакта. Параметры: {DB_CONFIG}")
        await message.reply("Извините, произошла ошибка при подключении к базе данных")
        return
    
    # Получаем данные о пользователе
    user_data = db.get_user(user.id)
    is_new_user = user_data is None
    print(f"Пользователь {'новый' if is_new_user else 'существующий'}, id={user.id}")
    
    # Получаем реферальный код из состояния
    data = await state.get_data()
    referral_code = data.get('referral_code')
    
    # Обрабатываем реферальный код если он есть
    if referral_code:
        print(f"Обрабатываем реферальный код: {referral_code}")
        referral_info = db.get_referral(referral_code)
        
        if referral_info and referral_info['user_id'] != user.id:
            print(f"Найдена реферальная информация: {referral_info}")
            if is_new_user or not db.check_referral_used(user.id, referral_info['user_id']):
                print(f"Добавляем {REFERRAL_BONUS_REQUESTS} бонусных запросов пользователю {referral_info['user_id']}")
                db.add_requests(referral_info['user_id'], REFERRAL_BONUS_REQUESTS)
                
                if not is_new_user:
                    print(f"Сохраняем историю реферала")
                    db.save_referral_history(
                        referrer_id=referral_info['user_id'],
                        referred_user_id=user.id,
                        referral_code=referral_code,
                        bonus_requests=REFERRAL_BONUS_REQUESTS
                    )
    
    # Сохраняем пользователя с контактом
    print(f"Сохраняем пользователя с контактом: {user.id}, {contact.phone_number}")
    save_result = db.save_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_bot=user.is_bot,
        language_code=user.language_code,
        chat_id=chat.id,
        contact=contact,
        is_active=True
    )
    print(f"Результат сохранения пользователя: {'новый' if save_result else 'обновлен существующий'}")
    
    # Обновляем данные пользователя
    user_data = db.get_user(user.id)
    print(f"Получены данные пользователя после сохранения: {user_data}")
    
    # Убираем клавиатуру с кнопкой отправки контакта
    remove_keyboard = types.ReplyKeyboardRemove()
    await message.reply("Спасибо! Ваш контакт успешно сохранен.", reply_markup=remove_keyboard)
    
    # Показываем приветственное сообщение
    await show_welcome_message(message, user_data, db)
    
    # Устанавливаем состояние "зарегистрирован"
    await state.set_state(UserStates.registered)

# Функция для отображения приветственного сообщения
async def show_welcome_message(message, user_data, db):
    user = message.from_user
    
    # Если это новый пользователь или у него еще нет реферального кода, создаем для него реферальную ссылку
    user_ref_code = db.get_user_referral(user_data['user_id']) if user_data else None
    
    if user_data and not user_ref_code:
        # Создаем уникальный код на основе ID пользователя и случайного UUID
        ref_base = f"{user.id}_{uuid.uuid4()}"
        ref_code = hashlib.md5(ref_base.encode()).hexdigest()[:8]
        
        # Сохраняем реферальную ссылку
        db.create_referral(user_data['user_id'], ref_code)
        user_ref_code = ref_code

    # Получаем информацию о пользователе, включая оставшиеся запросы
    requests_left = user_data.get('requests_left', 0) if user_data else 0
    
    # Создаем приветственное сообщение
    welcome_text = (
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        "Добро пожаловать в наш бот!\n"
        f"У вас есть {requests_left} запросов.\n"
    )
    
    # Создаем кнопки для мини-приложения
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="🌐 Открыть мини-приложение", 
        web_app=types.WebAppInfo(url=MINI_APP_URL)
    ))
    
    # Формируем реферальную ссылку, если она есть
    if user_ref_code:
        bot_username = (await message.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_ref_code}"
        
        welcome_text += "\n🔗 [Ваша реферальная ссылка](" + ref_link + ")\n\n"
        welcome_text += f"Приглашайте друзей и получайте {REFERRAL_BONUS_REQUESTS} бонусных запросов за каждого!"
        
        # Добавляем кнопку для копирования реферальной ссылки
        builder.add(types.InlineKeyboardButton(
            text="🔗 Скопировать реферальную ссылку", 
            callback_data=f"copy_ref:{user_ref_code}"
        ))
    
    builder.adjust(1)  # По одной кнопке в каждом ряду
    
    # Отправляем сообщение с поддержкой Markdown
    await message.reply(
        welcome_text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
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
