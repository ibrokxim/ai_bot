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
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.exceptions import TelegramAPIError
from dotenv import load_dotenv


from database_bot import BotDatabase

log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
log_file_path = os.path.join(log_directory, "bot.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=log_file_path,
    filemode='a'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Инициализация бота и диспетчера
TOKEN = os.getenv('BOT_TOKEN')
MINI_APP_URL = os.getenv('MINI_APP_URL')
REFERRAL_BONUS_REQUESTS = int(os.getenv('REFERRAL_BONUS_REQUESTS', 3))

# Проверка наличия токена
if not TOKEN:
    logger.critical("Не найден BOT_TOKEN в переменных окружения!")
    exit("Ошибка: BOT_TOKEN не установлен.")

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
try:
    db = BotDatabase(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    # Проверяем соединение при старте
    if not db.conn or not db.conn.open:
        if not db.connect():
            logger.critical("Не удалось подключиться к базе данных при инициализации.")
            exit("Критическая ошибка: Не удалось подключиться к БД.")
except Exception as e:
    logger.critical(f"Критическая ошибка при инициализации базы данных: {e}")
    exit("Критическая ошибка: Не удалось инициализировать БД.")


class UserState(StatesGroup):
    waiting_for_contact = State()


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user = message.from_user
    referrer_info = None # Информация о пригласившем
    referral_code_used = None # Использованный реф. код

    logger.info(f"Получена команда /start от пользователя {user.id} ({user.username})")

    # 1. Проверяем, существует ли пользователь ДО его сохранения
    try:
        user_data_before_save = db.get_user(user.id)
        user_exists = user_data_before_save is not None
    except Exception as e:
        logger.error(f"Ошибка при проверке существования пользователя {user.id}: {e}")
        await message.answer("Произошла ошибка при обработке вашего запроса. Попробуйте позже.")
        return

    logger.info(f"Пользователь {user.id} {'существует' if user_exists else 'новый'}")

    # 2. Если пользователь НОВЫЙ, проверяем реферальный код
    if not user_exists:
        args = message.text.split()
        if len(args) > 1:
            potential_referral_code = args[1]
            logger.info(f"Пользователь {user.id} пришел с аргументом (потенциальный реф.код): {potential_referral_code}")
            try:
                # Пытаемся найти реферера по коду
                referrer_info = db.get_referral(potential_referral_code)

                if referrer_info:
                    # Проверяем, что пользователь не сам себя пригласил
                    if referrer_info['referrer_telegram_id'] == user.id:
                        logger.warning(f"Пользователь {user.id} попытался использовать свой реферальный код.")
                        referrer_info = None # Сбрасываем информацию, self-реферал не засчитываем
                    else:
                        logger.info(f"Найден реферер {referrer_info['referrer_telegram_id']} для нового пользователя {user.id} по коду {potential_referral_code}")
                        referral_code_used = potential_referral_code
                else:
                    logger.info(f"Реферальный код '{potential_referral_code}' не найден или неактивен.")
            except Exception as e:
                logger.error(f"Ошибка при поиске реферального кода '{potential_referral_code}' для пользователя {user.id}: {e}")
                # Продолжаем без реферала, но логируем ошибку

    # 3. Сохраняем или обновляем пользователя (теперь точно знаем, новый он или нет)
    try:
        save_success = db.save_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            chat_id=message.chat.id, # Сохраняем chat_id для уведомлений
            is_bot=user.is_bot,
            language_code=user.language_code
        )
        if not save_success:
            logger.error(f"Не удалось сохранить/обновить пользователя {user.id}")
            await message.answer("Произошла ошибка при регистрации. Попробуйте позже.")
            return

        # Получаем актуальные данные пользователя ПОСЛЕ сохранения/обновления
        user_data = db.get_user(user.id)
        if not user_data:
            logger.error(f"Не удалось получить данные пользователя {user.id} после сохранения!")
            await message.answer("Произошла ошибка при получении данных. Попробуйте позже.")
            return
    except Exception as e:
        logger.error(f"Критическая ошибка при сохранении или получении пользователя {user.id}: {e}")
        await message.answer("Произошла критическая ошибка. Пожалуйста, свяжитесь с поддержкой.")
        return

    # 4. Если был УСПЕШНЫЙ реферальный переход (новый пользователь + валидный код другого юзера)
    if referrer_info and referral_code_used and not user_exists:
        referrer_telegram_id = referrer_info['referrer_telegram_id']
        referrer_user_id = referrer_info['referrer_user_id'] # ID реферера в таблице users
        referral_code_id = referrer_info['referral_code_id'] # ID кода в таблице referral_codes
        new_user_db_id = user_data['user_id'] # ID нового пользователя в таблице users

        try:
            # Начисляем бонусы рефереру
            if db.add_requests(referrer_telegram_id, REFERRAL_BONUS_REQUESTS):
                logger.info(f"Начислено {REFERRAL_BONUS_REQUESTS} запросов рефереру {referrer_telegram_id}")

                # Записываем в историю
                record_success = db.record_referral(
                    referrer_id=referrer_user_id,
                    referred_id=new_user_db_id,
                    referral_code_id=referral_code_id,
                    referral_code=referral_code_used,
                    bonus_requests_added=REFERRAL_BONUS_REQUESTS
                )
                if not record_success:
                    logger.error(f"Не удалось записать реферальный переход в историю: {referrer_user_id} -> {new_user_db_id}")

                # Отправляем уведомление рефереру
                referrer_chat_id = db.get_user_chat_id(referrer_telegram_id)
                if referrer_chat_id:
                    try:
                        await bot.send_message(
                            referrer_chat_id,
                            f"🎉 По вашей реферальной ссылке присоединился новый пользователь "
                            f"{user.first_name or user.username or f'ID:{user.id}'}!\n"
                            f"Вам начислено +{REFERRAL_BONUS_REQUESTS} бонусных запросов."
                        )
                        logger.info(f"Уведомление отправлено рефереру {referrer_telegram_id}")
                    except TelegramAPIError as e:
                        # Частая ошибка - пользователь заблокировал бота
                        if "bot was blocked by the user" in str(e):
                            logger.warning(f"Не удалось отправить уведомление рефереру {referrer_telegram_id}: бот заблокирован.")
                        else:
                            logger.error(f"Не удалось отправить уведомление рефереру {referrer_telegram_id} (chat_id: {referrer_chat_id}): {e}")
                else:
                    logger.warning(f"Не найден chat_id для реферера {referrer_telegram_id}, уведомление не отправлено.")
            else:
                logger.error(f"Не удалось начислить бонусы рефереру {referrer_telegram_id}")
        except Exception as e:
            logger.error(f"Ошибка при обработке реферального начисления/уведомления для реферера {referrer_telegram_id}: {e}")


    # 5. Генерируем реферальный код для пользователя (нового или старого), если его нет
    user_ref_code = None
    try:
        user_ref_code = db.get_user_referral_code(user.id)
        if not user_ref_code:
            logger.info(f"У пользователя {user.id} нет реферального кода, генерируем новый.")
            ref_base = f"{user.id}_{uuid.uuid4()}"
            ref_code_new = hashlib.md5(ref_base.encode()).hexdigest()[:8] # Длина кода 8 символов
            if db.create_referral(user.id, ref_code_new):
                user_ref_code = ref_code_new
                logger.info(f"Сгенерирован и сохранен реферальный код '{user_ref_code}' для пользователя {user.id}")
            else:
                logger.error(f"Не удалось создать реферальный код для пользователя {user.id}")
        else:
            logger.info(f"У пользователя {user.id} уже есть реферальный код: {user_ref_code}")
    except Exception as e:
        logger.error(f"Ошибка при получении/генерации реферального кода для {user.id}: {e}")

    ref_link = ""
    if user_ref_code:
        try:
            # Получаем имя бота динамически
            bot_info = await bot.get_me()
            ref_link = f"https://t.me/{bot_info.username}?start={user_ref_code}"
        except Exception as e:
            logger.error(f"Не удалось получить имя бота для реферальной ссылки: {e}")
            # Фоллбэк на статичное имя, если известно, или пустая строка
            # ref_link = f"https://t.me/YOUR_BOT_USERNAME?start={user_ref_code}"

    # 6. Определяем, нужно ли запрашивать контакт
    # Используем user_data, полученные ПОСЛЕ сохранения/обновления
    has_contact = 'contact' in user_data and user_data['contact'] is not None and user_data['contact'] != ''
    logger.info(f"Пользователь {user.id} {'имеет' if has_contact else 'не имеет'} сохраненный контакт.")

    # 7. Показываем сообщение в зависимости от наличия контакта
    user_display_name = user_data.get('first_name') or user.username or f"Пользователь {user.id}"
    requests_left = user_data.get('requests_left', 0)

    if has_contact:
        # Пользователь уже зарегистрирован и поделился контактом
        balance_text = (
            f"👋 Здравствуйте, {user_display_name}!\n\n"
            f"🎉 Ваш баланс: {requests_left} запросов.\n\n"
        )
        if ref_link:
            balance_text += (
                f"Приглашайте друзей и получайте +{REFERRAL_BONUS_REQUESTS} запросов за каждого!\n"
                f"Ваша реферальная ссылка для приглашений:\n`{ref_link}`" # Markdown для копирования
            )
        else:
            balance_text += "Не удалось сгенерировать вашу реферальную ссылку. Попробуйте позже."

        inline_keyboard = []
        if MINI_APP_URL:
            inline_keyboard.append([
                InlineKeyboardButton(
                    text="🌐 Открыть мини-приложение",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ])

        inline_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard) if inline_keyboard else None
        try:
            await message.answer(balance_text, reply_markup=inline_markup, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения 'баланс' пользователю {user.id}: {e}")

    else:
        # Новый пользователь ИЛИ старый, но без контакта
        welcome_text = (
            f"👋 Здравствуйте, {user_display_name}!\n\n"
            "Добро пожаловать в наш бот!\n"
            f"Стартовый баланс: {requests_left} запросов.\n"
        )
        if ref_link:
            welcome_text += (
                f"\nПриглашайте друзей и получайте +{REFERRAL_BONUS_REQUESTS} запросов за каждого!\n"
                f"🔗 Ваша реферальная ссылка:\n`{ref_link}`\n" # Markdown для копирования
            )

        welcome_text += (
            "\n\n📱 Для полноценного использования бота, пожалуйста, поделитесь своим номером телефона.\n"
            "Нажмите на кнопку ниже 👇\n\n"
            "🔒 Ваш номер будет использован только для идентификации и не будет передан третьим лицам."
        )

        inline_keyboard = []
        if MINI_APP_URL:
            inline_keyboard.append([
                InlineKeyboardButton(
                    text="🌐 Открыть мини-приложение",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ])
        inline_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard) if inline_keyboard else None

        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True # Кнопка исчезнет после нажатия
        )

        try:
            # Сначала текст и инлайн-кнопки (если есть)
            await message.answer(welcome_text, reply_markup=inline_markup, parse_mode="Markdown")
            # Затем запрос контакта с реплай-кнопкой
            await message.answer("Пожалуйста, нажмите кнопку ниже, чтобы поделиться контактом:", reply_markup=contact_keyboard)

            # Устанавливаем состояние ожидания контакта
            await state.set_state(UserState.waiting_for_contact)
            logger.info(f"Установлено состояние 'waiting_for_contact' для пользователя {user.id}")

        except Exception as e:
            logger.error(f"Ошибка отправки приветственного сообщения / запроса контакта пользователю {user.id}: {e}")


# Обработчик для колбэка копирования ссылки больше не нужен,
# так как ссылка в тексте и легко копируется с помощью Markdown.

@dp.message(F.content_type == types.ContentType.CONTACT, UserState.waiting_for_contact)
async def process_contact(message: Message, state: FSMContext):
    """Обработка получения контакта"""
    user = message.from_user
    logger.info(f"Получен контакт от пользователя {user.id}")

    # Проверяем, что контакт принадлежит отправителю сообщения
    if message.contact is not None and message.contact.user_id == user.id:
        contact_phone = message.contact.phone_number
        logger.info(f"Контакт {contact_phone} получен от пользователя {user.id} (ID совпадает)")
        try:
            # Сохраняем контакт в базу данных
            if db.save_contact(user.id, contact_phone):
                logger.info(f"Контакт {contact_phone} успешно сохранен для пользователя {user.id}")

                # Получаем обновленную информацию о пользователе
                user_data = db.get_user(user.id)
                requests_left = user_data.get('requests_left', 0) if user_data else 0
                ref_code = db.get_user_referral_code(user.id)

                ref_link = ""
                if ref_code:
                    try:
                        bot_info = await bot.get_me()
                        ref_link = f"https://t.me/{bot_info.username}?start={ref_code}"
                    except Exception as e:
                        logger.error(f"Не удалось получить имя бота для реферальной ссылки в process_contact: {e}")

                complete_text = (
                    f"✅ Спасибо! Ваш контакт ({contact_phone}) успешно сохранен.\n\n"
                    f"🎉 У вас {requests_left} доступных запросов.\n\n"
                )
                if ref_link:
                    complete_text += f"Ваша реферальная ссылка:\n`{ref_link}`" # Markdown

                # Отправляем сообщение и убираем клавиатуру запроса контакта
                await message.answer(complete_text, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")

                # Сбрасываем состояние
                await state.clear()
                logger.info(f"Состояние сброшено для пользователя {user.id} после сохранения контакта.")

            else:
                logger.error(f"Ошибка при сохранении контакта {contact_phone} для пользователя {user.id} в БД.")
                await message.answer(
                    "❌ Произошла ошибка при сохранении вашего контакта. Пожалуйста, попробуйте позже или обратитесь в поддержку.",
                    reply_markup=ReplyKeyboardRemove() # Убираем кнопку в случае ошибки БД
                )
                await state.clear() # Сбрасываем состояние при ошибке

        except Exception as e:
            logger.error(f"Критическая ошибка при обработке контакта от {user.id}: {e}")
            await message.answer("Произошла внутренняя ошибка. Попробуйте позже.", reply_markup=ReplyKeyboardRemove())
            await state.clear()

    else:
        # Ситуация, когда прислали не контакт или чужой контакт
        logger.warning(f"Пользователь {user.id} прислал некорректный контакт или не через кнопку.")
        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(
            "❌ Пожалуйста, нажмите на кнопку '📱 Поделиться контактом' ниже, чтобы отправить именно свой номер телефона.",
            reply_markup=contact_keyboard # Показываем кнопку еще раз
        )
        # Состояние не сбрасываем, ждем правильный контакт


@dp.message(UserState.waiting_for_contact)
async def process_invalid_input_while_waiting_contact(message: Message):
    """Обработка любых других сообщений (не контактов) в состоянии ожидания контакта"""
    logger.warning(f"Пользователь {message.from_user.id} прислал не контакт '{message.text}' в состоянии waiting_for_contact.")
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "⚠️ Пожалуйста, не присылайте текст или другие файлы. Нажмите на кнопку '📱 Поделиться контактом', чтобы продолжить.",
        reply_markup=contact_keyboard
    )


async def main():
    """Главная функция запуска бота"""
    # Проверка соединения с БД перед запуском опроса
    if not db.conn or not db.conn.open:
        logger.warning("Соединение с БД отсутствует перед запуском. Попытка переподключения...")
        if not db.connect():
            logger.critical("Не удалось восстановить соединение с БД. Запуск бота отменен.")
            return # Не запускаем бот без БД

    logger.info("Запуск бота (polling)...")
    # Запуск long polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Критическая ошибка во время работы бота: {e}", exc_info=True)
    finally:
        # Корректное закрытие сессии бота и соединения с БД
        await bot.session.close()
        db.close()
        logger.info("Бот остановлен, ресурсы освобождены.")


if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал KeyboardInterrupt. Завершение работы...")
    except Exception as main_error:
        logger.critical(f"Неперехваченная ошибка в main цикле: {main_error}", exc_info=True)