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
async def process_contact(message: Message, state: FSMContext):
    """Обработчик получения контакта от пользователя"""
    user_id = message.from_user.id
    contact = message.contact
    chat_id = message.chat.id
    
    try:
        logger.debug(f"Начало обработки контакта для пользователя {user_id}")
        
        # Валидация номера телефона
        if not contact.phone_number:
            logger.warning(f"Пользователь {user_id} отправил контакт без номера телефона")
            await message.reply("❌ Номер телефона не указан. Пожалуйста, попробуйте еще раз.")
            return
            
        # Проверяем формат номера телефона
        phone_number = contact.phone_number
        if not phone_number.startswith('+'):
            logger.debug(f"Добавляем префикс '+' к номеру телефона {phone_number}")
            phone_number = '+' + phone_number
        
        logger.info(f"Получен контакт от пользователя {user_id}: {phone_number}")
            
        # Получаем данные из состояния
        state_data = await state.get_data()
        referral_code = state_data.get('referral_code')
        logger.info(f"Реферальный код из состояния: {referral_code}")
        
        # Сохраняем контакт пользователя в базе данных
        logger.debug(f"Сохраняем данные пользователя {user_id} в базу данных")
        user_saved = db.save_user(
            user_id=user_id, 
            username=message.from_user.username, 
            first_name=message.from_user.first_name, 
            last_name=message.from_user.last_name,
            chat_id=chat_id,
            contact=phone_number,
            is_bot=message.from_user.is_bot,
            language_code=message.from_user.language_code,
            is_active=True
        )
        
        if not user_saved:
            logger.error(f"Не удалось сохранить пользователя {user_id}")
            await message.reply(
                "❌ Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        else:
            logger.info(f"Пользователь {user_id} успешно сохранен в базе данных")
        
        # Генерируем реферальный код для нового пользователя
        new_ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        logger.info(f"Сгенерирован новый реферальный код для пользователя {user_id}: {new_ref_code}")
        
        logger.debug(f"Сохраняем реферальный код для пользователя {user_id}")
        ref_code_saved = db.update_user_referral_code(user_id, new_ref_code)
        if not ref_code_saved:
            logger.error(f"Не удалось сохранить реферальный код {new_ref_code} для пользователя {user_id}")
        else:
            logger.info(f"Реферальный код успешно сохранен для пользователя {user_id}")
        
        # Обработка реферального кода, если пользователь пришел по ссылке
        if referral_code:
            logger.info(f"Обрабатываем реферальный код: {referral_code}")
            
            logger.debug(f"Ищем реферера по коду {referral_code}")
            referrer_id = db.get_user_by_referral_code(referral_code)
            logger.debug(f"Результат поиска реферера: {referrer_id}")
            
            if referrer_id and referrer_id != user_id:
                logger.info(f"Найден реферер {referrer_id} для кода {referral_code}")
                
                # Сохраняем информацию о реферале и добавляем бонусные запросы
                logger.debug(f"Сохраняем историю реферала между {referrer_id} и {user_id}")
                ref_history_saved = db.save_referral_history(referrer_id, user_id, referral_code, REFERRAL_BONUS_REQUESTS)
                logger.debug(f"Результат сохранения истории реферала: {ref_history_saved}")
                
                if ref_history_saved:
                    # Добавляем бонусные запросы только реферреру
                    logger.debug(f"Добавляем {REFERRAL_BONUS_REQUESTS} бонусных запросов пользователю {referrer_id}")
                    success = db.increase_user_requests(referrer_id, REFERRAL_BONUS_REQUESTS)
                    logger.debug(f"Результат добавления бонусных запросов: {success}")
                    
                    if success:
                        logger.info(f"Успешно добавлены бонусные запросы {REFERRAL_BONUS_REQUESTS} пользователю {referrer_id}")
                        
                        # Уведомляем реферера
                        try:
                            logger.debug(f"Отправляем уведомление реферреру {referrer_id}")
                            await bot.send_message(
                                referrer_id,
                                f"🎉 По вашей реферальной ссылке зарегистрировался новый пользователь!\n"
                                f"Вам начислено {REFERRAL_BONUS_REQUESTS} дополнительных запросов."
                            )
                            logger.info(f"Отправлено уведомление реферреру {referrer_id}")
                        except Exception as e:
                            logger.error(f"Ошибка при отправке уведомления реферреру: {str(e)}")
                    else:
                        logger.error(f"Не удалось добавить бонусные запросы пользователю {referrer_id}")
                else:
                    logger.error(f"Не удалось сохранить историю реферала между {referrer_id} и {user_id}")
            else:
                logger.warning(f"Не удалось найти реферера для кода {referral_code} или пользователь пытается использовать свой код")
        else:
            logger.info("Нет реферального кода при регистрации пользователя")

        # Удаляем клавиатуру и отправляем сообщение об успехе
        logger.debug(f"Отправляем сообщение об успешном сохранении контакта пользователю {user_id}")
        await message.reply(
            "✅ Ваш контакт успешно сохранен!",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Переводим пользователя в статус зарегистрированного
        logger.debug(f"Устанавливаем статус registered для пользователя {user_id}")
        await state.set_state(UserState.registered)
        
        # Показываем приветственное сообщение
        logger.debug(f"Вызываем функцию отображения приветственного сообщения для пользователя {user_id}")
        await show_welcome_message(message, user_id)
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении контакта: {str(e)}")
        logger.exception("Полный стек ошибки:")
        await message.reply(
            "❌ Произошла ошибка при сохранении контакта. Пожалуйста, попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
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
        
        # Получаем реферальный код пользователя
        logger.debug(f"Пытаемся получить реферальный код для пользователя {user_id}")
        referral_code = db.get_user_referral_code(user_id)
        logger.debug(f"Получен реферальный код: {referral_code}")
        
        if not referral_code:
            # Если по какой-то причине код не был сгенерирован ранее
            logger.warning(f"Реферальный код не найден для пользователя {user_id}, генерируем новый")
            referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            logger.debug(f"Сгенерирован новый код: {referral_code}")
            
            logger.debug(f"Пытаемся сохранить реферальный код для пользователя {user_id}")
            result = db.update_user_referral_code(user_id, referral_code)
            logger.debug(f"Результат сохранения реферального кода: {result}")
            
            if not result:
                logger.error(f"Не удалось сохранить реферальный код для пользователя {user_id}")
                # Пробуем получить код снова после попытки сохранения
                logger.debug(f"Повторная попытка получить реферальный код для пользователя {user_id}")
                referral_code = db.get_user_referral_code(user_id)
                logger.debug(f"Получен реферальный код после повторной попытки: {referral_code}")
                
                if not referral_code:
                    logger.error(f"Не удалось получить реферальный код даже после попытки создания")
        
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
