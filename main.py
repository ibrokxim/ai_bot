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
import asyncio

from database import Database

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Изменяем уровень логирования на DEBUG для большей детализации
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),  # Добавляем запись в файл
        logging.StreamHandler()  # Оставляем вывод в консоль
    ]
)

# Создаем логгер для нашего приложения
logger = logging.getLogger('bot')
logger.setLevel(logging.DEBUG)

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
async def process_contact(message):
    """Обрабатывает полученный контакт пользователя"""
    try:
        user_id = message.from_user.id
        contact = message.contact
        logger.info(f"Получен контакт от пользователя {user_id}: {contact.phone_number}")
        
        # Сохраняем данные пользователя
        username = message.from_user.username or ""
        user_data = {
            'username': username,
            'phone': contact.phone_number
        }
        logger.debug(f"Данные пользователя для сохранения: {user_data}")
        
        # Получаем реферальный код из сессии, если есть
        referral_code = user_sessions.get(user_id, {}).get('referral_code', None)
        logger.debug(f"Найден реферальный код {referral_code} для пользователя {user_id}")
        
        # Сохраняем пользователя и получаем результат операции
        user_saved = db.save_user(user_id, user_data)
        logger.info(f"Пользователь {user_id} сохранен: {user_saved}")
        
        if user_saved:
            # Обрабатываем реферальный код, если есть
            if referral_code:
                logger.info(f"Обрабатываем реферальный код {referral_code} для пользователя {user_id}")
                process_referral_code(user_id, referral_code)
            
            # Автоматически генерируем реферальный код, если его еще нет
            user_referral_code = db.get_user_referral_code(user_id)
            if not user_referral_code:
                logger.info(f"Генерируем новый реферальный код для пользователя {user_id}")
                user_referral_code = db.generate_referral_code(user_id)
                logger.debug(f"Сгенерирован код {user_referral_code}")
            
            # Отправляем сообщение об успешной регистрации
            await message.reply(
                "✅ Контакт успешно сохранен!\n"
                "Теперь вы можете использовать бота в полном объеме.",
                reply_markup=types.ReplyKeyboardRemove()
            )
            
            # Отправляем приветственное сообщение с инструкциями
            await send_welcome_message(user_id)
        else:
            await message.reply(
                "❌ Произошла ошибка при сохранении контакта.\n"
                "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
                reply_markup=types.ReplyKeyboardRemove()
            )
    except Exception as e:
        logger.error(f"Ошибка при обработке контакта: {str(e)}")
        logger.exception("Полный стек ошибки:")
        await message.reply(
            "❌ Произошла ошибка при обработке контакта.\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            reply_markup=types.ReplyKeyboardRemove()
        )

# Функция для отображения приветственного сообщения
async def show_welcome_message(message: Message, user_id: int):
    """Показывает приветственное сообщение пользователю"""
    try:
        logger.debug(f"Начало выполнения функции show_welcome_message для пользователя {user_id}")
        
        # Получаем данные пользователя
        user_data = db.get_user(user_id)
        
        logger.debug(f"Получены данные пользователя: {user_data}")
        
        if not user_data:
            logger.error(f"Пользователь {user_id} не найден в базе данных")
            await message.reply(
                "❌ Произошла ошибка при получении данных. Пожалуйста, попробуйте позже.",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        logger.info(f"Формируем приветственное сообщение для пользователя {user_id}")
        
        # Получаем реферальный код пользователя с автоматическим созданием
        logger.debug(f"Пытаемся получить реферальный код для пользователя {user_id} с автосозданием")
        referral_code = db.get_user_referral_code(user_id, auto_create=True)
        logger.debug(f"Получен реферальный код: {referral_code}")
        
        # Проверяем, получен ли код в итоге
        if not referral_code:
            logger.error(f"Не удалось получить или создать реферальный код для пользователя {user_id}")
            referral_link = "Не удалось сгенерировать ссылку"
        else:
            # Формируем реферальную ссылку
            logger.debug(f"Получаем имя пользователя бота для создания ссылки")
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            logger.debug(f"Имя пользователя бота: {bot_username}")
            
            referral_link = f"https://t.me/{bot_username}?start={referral_code}"
            logger.info(f"Реферальная ссылка для пользователя {user_id}: {referral_link}")
        
        # Создаем клавиатуру
        logger.debug(f"Создаем клавиатуру для пользователя {user_id}")
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Начать чат", callback_data="start_chat")],
            [InlineKeyboardButton(text="👥 Пригласить друга", callback_data="invite_friend")],
            [InlineKeyboardButton(text="📊 Мой профиль", callback_data="profile")]
        ])
        
        # Отправляем приветственное сообщение
        logger.debug(f"Отправляем приветственное сообщение пользователю {user_id}")
        await message.reply(
            f"👋 Добро пожаловать в бот!\n\n"
            f"У вас осталось {user_data.get('requests_left', 0)} запросов.\n\n"
            f"🔗 Ваша реферальная ссылка:\n{referral_link}\n\n"
            f"Приглашайте друзей и получайте дополнительные запросы!\n"
            f"За каждого приглашенного друга вы получите {REFERRAL_BONUS_REQUESTS} бонусных запросов.\n\n"
            f"Выберите действие:",
            reply_markup=markup
        )
        logger.info(f"Приветственное сообщение отправлено пользователю {user_id}")
    
    except Exception as e:
        logger.error(f"Ошибка при отображении приветственного сообщения: {str(e)}")
        logger.exception("Полный стек ошибки:")
        await message.reply(
            "❌ Произошла ошибка. Пожалуйста, попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
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

# Добавляем команду для отладки базы данных
@dp.message(Command("debug"))
async def debug_command(message: Message):
    """Команда для отладки базы данных"""
    user_id = message.from_user.id
    
    logger.info(f"Запущена отладочная команда пользователем {user_id}")
    
    try:
        # Проверяем соединение с базой данных
        logger.debug("Проверка соединения с базой данных")
        if not db.conn or not db.conn.is_connected():
            logger.warning("Соединение с базой данных отсутствует или закрыто, пытаемся переподключиться")
            db.connect()
        
        if not db.conn or not db.conn.is_connected():
            logger.error("Не удалось подключиться к базе данных")
            await message.reply("❌ Ошибка подключения к базе данных")
            return
        
        # Проверяем наличие таблиц
        cursor = db.conn.cursor()
        
        # Проверяем таблицу пользователей
        cursor.execute("SHOW TABLES LIKE 'users'")
        users_exists = cursor.fetchone() is not None
        
        # Проверяем таблицу реферальных кодов
        cursor.execute("SHOW TABLES LIKE 'referral_codes'")
        ref_codes_exists = cursor.fetchone() is not None
        
        # Проверяем таблицу истории рефералов
        cursor.execute("SHOW TABLES LIKE 'referral_history'")
        ref_history_exists = cursor.fetchone() is not None
        
        # Пытаемся получить информацию о пользователе
        user_exists = False
        try:
            user_data = db.get_user(user_id)
            user_exists = user_data is not None
            logger.debug(f"Данные пользователя {user_id}: {user_data}")
        except Exception as e:
            logger.error(f"Ошибка при получении данных пользователя: {str(e)}")
        
        # Отправляем результаты проверки
        status_message = (
            "📊 Результаты диагностики:\n\n"
            f"🔌 Соединение с БД: {'✅ Активно' if db.conn and db.conn.is_connected() else '❌ Отсутствует'}\n"
            f"👤 Таблица users: {'✅ Существует' if users_exists else '❌ Отсутствует'}\n"
            f"🔑 Таблица referral_codes: {'✅ Существует' if ref_codes_exists else '❌ Отсутствует'}\n"
            f"📝 Таблица referral_history: {'✅ Существует' if ref_history_exists else '❌ Отсутствует'}\n"
            f"👤 Данные пользователя: {'✅ Найдены' if user_exists else '❌ Не найдены'}\n"
        )
        
        if user_exists:
            # Проверяем реферальный код пользователя
            ref_code = db.get_user_referral_code(user_id)
            has_ref_code = ref_code is not None
            
            status_message += f"🔗 Реферальный код: {'✅ Найден - ' + ref_code if has_ref_code else '❌ Не найден'}\n"
            
            # Если реферальный код не найден, пробуем создать новый
            if not has_ref_code:
                new_ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                ref_saved = db.update_user_referral_code(user_id, new_ref_code)
                
                status_message += f"🆕 Создание нового кода: {'✅ Успешно - ' + new_ref_code if ref_saved else '❌ Ошибка'}\n"
        
        if not users_exists or not ref_codes_exists or not ref_history_exists:
            # Перезапускаем создание таблиц
            logger.info("Запуск принудительного создания таблиц")
            db._create_tables()
            status_message += "\n⚙️ Была выполнена попытка создания отсутствующих таблиц.\n"
            status_message += "Пожалуйста, повторите команду /debug для проверки результатов.\n"
        
        cursor.close()
        await message.reply(status_message)
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении диагностики: {str(e)}")
        logger.exception("Полный стек ошибки:")
        await message.reply("❌ Произошла ошибка при выполнении диагностики. Подробности в логах.")

def process_referral_code(user_id, referral_code):
    """Обрабатывает реферальный код при регистрации пользователя"""
    try:
        logger.info(f"Обработка реферального кода {referral_code} для пользователя {user_id}")
        
        # Получаем ID пользователя, создавшего реферальную ссылку
        referrer_id = db.get_user_by_referral_code(referral_code)
        logger.debug(f"Найден реферер с ID: {referrer_id}")
        
        # Проверяем, что реферер существует и не является текущим пользователем
        if referrer_id and referrer_id != user_id:
            logger.info(f"Валидный реферер {referrer_id} для кода {referral_code}")
            
            # Сохраняем информацию о реферале
            ref_saved = db.save_referral_history(
                referrer_id=referrer_id,
                referred_id=user_id,
                referral_code=referral_code,
                bonus_amount=REFERRAL_BONUS_REQUESTS
            )
            logger.debug(f"Результат сохранения реферальной истории: {ref_saved}")
            
            if ref_saved:
                # Добавляем бонусные запросы реферреру
                logger.info(f"Добавляем {REFERRAL_BONUS_REQUESTS} бонусных запросов пользователю {referrer_id}")
                bonus_added = db.increase_user_requests(referrer_id, REFERRAL_BONUS_REQUESTS)
                logger.debug(f"Результат добавления бонусов: {bonus_added}")
                
                if bonus_added:
                    # Асинхронно отправляем уведомление реферреру
                    asyncio.create_task(send_referral_notification(referrer_id))
                    return True
                else:
                    logger.error(f"Не удалось добавить бонусные запросы пользователю {referrer_id}")
            else:
                logger.error(f"Не удалось сохранить историю реферала для {user_id} и {referrer_id}")
        else:
            if referrer_id == user_id:
                logger.warning(f"Пользователь {user_id} пытается использовать свой собственный реферальный код")
            else:
                logger.warning(f"Не найден реферер для кода {referral_code}")
    except Exception as e:
        logger.error(f"Ошибка при обработке реферального кода: {str(e)}")
        logger.exception("Полный стек ошибки:")
    
    return False

async def send_referral_notification(referrer_id):
    """Отправляет уведомление о новом реферале"""
    try:
        logger.info(f"Отправка уведомления о новом реферале пользователю {referrer_id}")
        await bot.send_message(
            referrer_id,
            f"🎉 По вашей реферальной ссылке зарегистрировался новый пользователь!\n"
            f"Вам начислено {REFERRAL_BONUS_REQUESTS} дополнительных запросов."
        )
        logger.info(f"Уведомление о реферале успешно отправлено пользователю {referrer_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о реферале: {str(e)}")
        logger.exception("Полный стек ошибки:")

async def send_welcome_message(user_id):
    """Отправляет приветственное сообщение с инструкциями новому пользователю"""
    try:
        logger.info(f"Отправка приветственного сообщения пользователю {user_id}")
        
        # Получаем реферальный код пользователя
        referral_code = db.get_user_referral_code(user_id)
        bot_username = (await bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"
        
        # Создаем клавиатуру с основными функциями
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("💰 Мой баланс", callback_data="show_balance"),
            types.InlineKeyboardButton("👨‍👩‍👧‍👦 Мои рефералы", callback_data="show_referrals"),
            types.InlineKeyboardButton("🎁 Бонусы", callback_data="show_bonuses"),
            types.InlineKeyboardButton("❓ Помощь", callback_data="show_help")
        )
        
        # Отправляем сообщение с информацией
        await bot.send_message(
            user_id,
            f"🎉 *Добро пожаловать в наш Реферальный Бот!*\n\n"
            f"Теперь вы можете приглашать друзей и получать бонусы.\n\n"
            f"*Ваша реферальная ссылка:*\n{referral_link}\n\n"
            f"За каждого приглашенного друга вы получите бонусные баллы!\n\n"
            f"Используйте меню ниже для управления вашим аккаунтом:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        logger.debug(f"Приветственное сообщение успешно отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке приветственного сообщения: {str(e)}")
        logger.exception("Полный стек ошибки:")

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
    asyncio.run(main())
