import functools  # Импортируем functools для wraps
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable

import pymysql
import pymysql.cursors

# Настройка логирования
# Убедитесь, что базовая конфигурация вызывается только один раз в вашем приложении
# logging.basicConfig(level=logging.INFO) # Можно убрать отсюда, если настраивается в основном файле бота
logger = logging.getLogger('bot.database') # Используем 'bot.database' как имя логгера

# --- ДЕКОРАТОР для проверки соединения ---
def ensure_db_connection(func: Callable):
    """
    Декоратор для методов BotDatabase, который проверяет
    и восстанавливает соединение перед вызовом метода.
    Также обрабатывает базовые ошибки pymysql и откатывает транзакции.
    """
    @functools.wraps(func) # Сохраняет метаданные оригинальной функции
    def wrapper(self: 'BotDatabase', *args, **kwargs):
        # 'self' здесь - это экземпляр BotDatabase
        if not isinstance(self, BotDatabase):
            logger.error("Декоратор ensure_db_connection применен не к методу BotDatabase")
            # Возвращаем None/False в зависимости от ожидаемого типа возврата
            return False if func.__name__.startswith(('save', 'add', 'create', 'record')) else None

        # 1. Проверка и восстановление соединения
        if not self._ensure_connection():
            logger.error(f"Не удалось установить/проверить соединение перед вызовом {func.__name__}")
            # Возвращаем значение, соответствующее ошибке соединения
            return False if func.__name__.startswith(('save', 'add', 'create', 'record')) else None

        # 2. Вызов оригинального метода с обработкой ошибок
        try:
            result = func(self, *args, **kwargs)
            # Для методов записи/изменения, подтверждаем транзакцию, если не было ошибок
            # (Предполагаем, что commit() вызывается внутри метода, если нужен)
            # Декоратор сам не делает commit, т.к. метод может быть частью большей транзакции.
            # Оставляем commit() внутри методов save_*, add_*, etc.
            return result
        except pymysql.Error as e:
            # Ловим ошибки pymysql, которые могли произойти ВНУТРИ обернутого метода
            logger.error(f"Ошибка pymysql в методе {func.__name__}: ({type(e).__name__}) {e}")
            # Пытаемся откатить транзакцию
            try:
                if self.conn: self.conn.rollback()
                logger.warning(f"Транзакция отменена из-за ошибки pymysql в {func.__name__}")
            except Exception as roll_err:
                logger.error(f"Ошибка отката после ошибки pymysql в {func.__name__}: {roll_err}")
            # Возвращаем значение, соответствующее ошибке
            return False if func.__name__.startswith(('save', 'add', 'create', 'record')) else None
        except Exception as e:
            # Ловим другие неожиданные ошибки
            logger.error(f"Неожиданная ошибка в методе {func.__name__}: ({type(e).__name__}) {e}")
            # Также пытаемся откатить
            try:
                if self.conn: self.conn.rollback()
                logger.warning(f"Транзакция отменена из-за неожиданной ошибки в {func.__name__}")
            except Exception as roll_err:
                logger.error(f"Ошибка отката после неожиданной ошибки в {func.__name__}: {roll_err}")
            # Возвращаем значение, соответствующее ошибке
            return False if func.__name__.startswith(('save', 'add', 'create', 'record')) else None

    return wrapper
# --- КОНЕЦ ДЕКОРАТОРА ---


class BotDatabase:
    def __init__(self, host: str, user: str, password: str, database: str):
        """Инициализация подключения к базе данных"""
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': False # Важно для управления транзакциями
        }
        self.conn = None
        # Убираем connect() из __init__, чтобы не блокировать запуск, если БД недоступна
        # self.connect()
        # Соединение будет установлено при первом вызове метода через декоратор

    def connect(self) -> bool:
        """Установка или переустановка соединения с базой данных"""
        try:
            # Закрываем старое соединение, если оно есть
            if self.conn:
                try:
                    self.conn.close()
                    # logger.info("Закрыто старое соединение с БД перед переподключением.")
                except Exception:
                    pass # Игнорируем ошибки при закрытии старого
            self.conn = None

            # logger.debug("Попытка подключения к БД...")
            self.conn = pymysql.connect(**self.config)
            logger.info("Соединение с базой данных установлено/восстановлено успешно")
            return True
        except pymysql.Error as e:
            logger.error(f"Ошибка pymysql при подключении к базе данных: {e}")
            self.conn = None
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при подключении к базе данных: {e}")
            self.conn = None
            return False

    def _ensure_connection(self) -> bool:
        """Проверяет соединение и пытается переподключиться при необходимости."""
        try:
            if self.conn is None:
                # logger.warning("Соединение отсутствует. Попытка первого подключения...")
                return self.connect()

            # Используем ping для проверки и автоматического переподключения
            # logger.debug("Проверка соединения через ping...")
            self.conn.ping(reconnect=True)
            # logger.debug("Пинг соединения успешен.")
            return True
        except pymysql.Error as e:
            logger.warning(f"Пинг/переподключение не удалось ({type(e).__name__}: {e}). Попытка полного переподключения...")
            return self.connect() # Пробуем полное переподключение
        except AttributeError:
            # Если self.conn стал None между проверками (маловероятно)
            logger.warning("Атрибут self.conn равен None во время проверки. Попытка подключения...")
            return self.connect()
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке соединения: {e}")
            # На всякий случай сбрасываем соединение
            try:
                if self.conn: self.conn.close()
            except: pass
            self.conn = None
            return False

    # --- Методы с примененным декоратором ---

    @ensure_db_connection
    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE telegram_id = %s", # Убедитесь, что таблица users
                (telegram_id,)
            )
            return cursor.fetchone()

    @ensure_db_connection
    def save_user(
            self,
            telegram_id: int,
            username: str = None,
            first_name: str = None,
            last_name: str = None,
            chat_id: int = None,
            is_bot: bool = False,
            language_code: str = None,
    ) -> bool:
        """Сохранение информации о пользователе"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM users WHERE telegram_id = %s",
                (telegram_id,)
            )
            user_exists = cursor.fetchone() is not None

            if user_exists:
                cursor.execute('''
                    UPDATE users SET username = %s, first_name = %s, last_name = %s, chat_id = %s, is_bot = %s, language_code = %s, last_seen = NOW()
                    WHERE telegram_id = %s
                ''', (username, first_name, last_name, chat_id, is_bot, language_code, telegram_id))
                logger.info(f"Обновлен пользователь {telegram_id}")
            else:
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name, chat_id, is_bot, language_code, is_active, requests_left, registration_date, last_seen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 1000, NOW(), NOW())
                ''', (telegram_id, username, first_name, last_name, chat_id, is_bot, language_code))
                logger.info(f"Создан пользователь {telegram_id}")

            self.conn.commit() # Commit здесь
            return True
        # Ошибки и rollback обрабатываются декоратором

    @ensure_db_connection
    def get_user_chat_id(self, telegram_id: int) -> Optional[int]:
        """Получение chat_id пользователя по его telegram_id"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT chat_id FROM users WHERE telegram_id = %s",
                (telegram_id,)
            )
            result = cursor.fetchone()
            return result.get('chat_id') if result else None

    @ensure_db_connection
    def record_referral(
            self,
            referrer_id: int,  # user_id пригласившего (из users)
            referred_id: int,  # user_id приглашенного (из users)
            referral_code_id: int,  # id реферального кода (из referral_codes)
            referral_code: str,  # сам реферальный код
            bonus_requests_added: int
    ) -> bool:
        """Запись информации о реферальном переходе в историю"""
        with self.conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO referral_history (
                    referrer_id, referred_id, referral_code_id, referral_code,
                    bonus_requests_added, conversion_status, created_at, converted_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                referrer_id, referred_id, referral_code_id, referral_code,
                bonus_requests_added, 'completed', datetime.now(), datetime.now()
            ))
            self.conn.commit() # Commit здесь
            logger.info(f"Реферальный переход записан: {referrer_id} -> {referred_id} (code: {referral_code})")
            return True

    @ensure_db_connection
    def create_referral(self, telegram_id: int, referral_code: str) -> bool:
        """Создание реферального кода для пользователя"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT user_id FROM users WHERE telegram_id = %s",
                (telegram_id,)
            )
            user = cursor.fetchone()
            if not user:
                logger.error(f"Пользователь с telegram_id {telegram_id} не найден при создании реф.кода")
                return False # Явная проверка

            user_id = user['user_id']
            cursor.execute(
                "SELECT id FROM referral_codes WHERE user_id = %s",
                (user_id,)
            )
            exists = cursor.fetchone()

            if exists:
                cursor.execute('''
                    UPDATE referral_codes SET code = %s, is_active = 1, last_used_at = NOW()
                    WHERE user_id = %s
                ''', (referral_code, user_id))
                logger.info(f"Обновлен реф.код для user_id {user_id}")
            else:
                cursor.execute('''
                    INSERT INTO referral_codes (user_id, code, is_active, total_uses)
                    VALUES (%s, %s, 1, 0)
                ''', (user_id, referral_code))
                logger.info(f"Создан реф.код для user_id {user_id}")

            self.conn.commit() # Commit здесь
            return True

    @ensure_db_connection
    def get_user_referral_code(self, telegram_id: int) -> Optional[str]:
        """Получение активного реферального кода пользователя"""
        with self.conn.cursor() as cursor:
            cursor.execute('''
                SELECT rc.code FROM referral_codes rc JOIN users u ON rc.user_id = u.user_id
                WHERE u.telegram_id = %s AND rc.is_active = 1
            ''', (telegram_id,))
            result = cursor.fetchone()
            return result.get('code') if result else None

    @ensure_db_connection
    def get_referral(self, referral_code: str) -> Optional[Dict[str, Any]]:
        """Получение информации о реферальном коде (включая user_id и id кода)"""
        with self.conn.cursor() as cursor:
            cursor.execute('''
                SELECT rc.id AS referral_code_id, rc.user_id AS referrer_user_id, rc.code,
                       u.telegram_id AS referrer_telegram_id
                FROM referral_codes rc JOIN users u ON rc.user_id = u.user_id
                WHERE rc.code = %s AND rc.is_active = 1
            ''', (referral_code,))
            return cursor.fetchone()

    # Метод get_user_referral удален, так как он ссылался на несуществующий execute_query
    # Если он вам нужен, его нужно переписать с использованием cursor.execute

    @ensure_db_connection
    def add_requests(self, telegram_id: int, amount: int) -> bool:
        """Добавление бонусных запросов пользователю"""
        with self.conn.cursor() as cursor:
            cursor.execute('''
                UPDATE users SET requests_left = COALESCE(requests_left, 0) + %s
                WHERE telegram_id = %s
            ''', (amount, telegram_id))
            self.conn.commit() # Commit здесь
            logger.info(f"Добавлено {amount} запросов пользователю {telegram_id}")
            return True

    @ensure_db_connection
    def save_contact(self, telegram_id: int, contact: str) -> bool:
        """Сохранение контакта пользователя"""
        with self.conn.cursor() as cursor:
            cursor.execute('''
                UPDATE users SET contact = %s WHERE telegram_id = %s
            ''', (contact, telegram_id))
            self.conn.commit() # Commit здесь
            logger.info(f"Сохранен контакт для пользователя {telegram_id}")
            return True

    @ensure_db_connection
    def get_user_contact(self, telegram_id: int) -> Optional[str]:
        """Получение контакта пользователя"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT contact FROM users WHERE telegram_id = %s",
                (telegram_id,)
            )
            result = cursor.fetchone()
            return result.get('contact') if result else None

    def close(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Соединение с БД закрыто.")
            except Exception as e:
                logger.error(f"Ошибка при закрытии соединения: {e}")
            finally:
                self.conn = None