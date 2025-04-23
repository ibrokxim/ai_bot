import logging
from datetime import datetime
from typing import Optional, Dict, Any
import pymysql
import pymysql.cursors

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bot.database')


class BotDatabase:
    def __init__(self, host: str, user: str, password: str, database: str):
        """Инициализация подключения к базе данных"""
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        self.conn = None
        self.connect()

    def connect(self) -> bool:
        """Установка соединения с базой данных"""
        try:
            self.conn = pymysql.connect(**self.config)
            logger.info("Соединение с базой данных установлено успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка при подключении к базе данных: {str(e)}")
            return False

    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM users WHERE telegram_id = %s",
                    (telegram_id,)
                )
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {str(e)}")
            return None

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
        try:
            with self.conn.cursor() as cursor:
                # Проверяем существование пользователя
                cursor.execute(
                    "SELECT user_id FROM users WHERE telegram_id = %s",
                    (telegram_id,)
                )
                user_exists = cursor.fetchone() is not None

                if user_exists:
                    # Обновляем существующего пользователя
                    cursor.execute('''
                        UPDATE users 
                        SET username = %s,
                            first_name = %s,
                            last_name = %s,
                            chat_id = %s,
                            is_bot = %s,
                            language_code = %s
                        WHERE telegram_id = %s
                    ''', (
                        username, first_name, last_name,
                        chat_id, is_bot, language_code,
                        telegram_id
                    ))
                else:
                    # Создаем нового пользователя с 3 начальными запросами
                    cursor.execute('''
                        INSERT INTO users (
                            telegram_id, username, first_name, last_name,
                            chat_id, is_bot, language_code, is_active, requests_left
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 3)
                    ''', (
                        telegram_id, username, first_name, last_name,
                        chat_id, is_bot, language_code
                    ))

                self.conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении пользователя: {str(e)}")
            self.conn.rollback()
            return False

    def get_user_chat_id(self, telegram_id: int) -> Optional[int]:
        """Получение chat_id пользователя по его telegram_id"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT chat_id FROM users WHERE telegram_id = %s",
                    (telegram_id,)
                )
                result = cursor.fetchone()
                return result['chat_id'] if result and result['chat_id'] else None
        except Exception as e:
            logger.error(f"Ошибка при получении chat_id пользователя {telegram_id}: {str(e)}")
            return None

    def record_referral(
            self,
            referrer_id: int,  # user_id пригласившего (из users)
            referred_id: int,  # user_id приглашенного (из users)
            referral_code_id: int,  # id реферального кода (из referral_codes)
            referral_code: str,  # сам реферальный код
            bonus_requests_added: int
    ) -> bool:
        """Запись информации о реферальном переходе в историю"""
        try:
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
                self.conn.commit()
                logger.info(f"Реферальный переход записан: {referrer_id} -> {referred_id} (code: {referral_code})")
                return True
        except Exception as e:
            logger.error(f"Ошибка при записи реферального перехода: {str(e)}")
            self.conn.rollback()
            return False

    def create_referral(self, telegram_id: int, referral_code: str) -> bool:
        """Создание реферального кода для пользователя"""
        try:
            with self.conn.cursor() as cursor:
                # Получаем user_id по telegram_id
                cursor.execute(
                    "SELECT user_id FROM users WHERE telegram_id = %s",
                    (telegram_id,)
                )
                user = cursor.fetchone()
                if not user:
                    logger.error(f"Пользователь с telegram_id {telegram_id} не найден")
                    return False

                user_id = user['user_id']

                # Проверяем существующий реферальный код
                cursor.execute(
                    "SELECT id FROM referral_codes WHERE user_id = %s",
                    (user_id,)
                )
                exists = cursor.fetchone()

                if exists:
                    # Обновляем существующий код
                    cursor.execute('''
                        UPDATE referral_codes 
                        SET code = %s,
                            is_active = 1,
                            last_used_at = NOW()
                        WHERE user_id = %s
                    ''', (referral_code, user_id))
                else:
                    # Создаем новый код
                    cursor.execute('''
                        INSERT INTO referral_codes (
                            user_id, code, is_active, total_uses
                        ) VALUES (%s, %s, 1, 0)
                    ''', (user_id, referral_code))

                self.conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при создании реферального кода: {str(e)}")
            self.conn.rollback()
            return False

    def get_user_referral_code(self, telegram_id: int) -> Optional[str]:
        try:
            with self.conn.cursor() as cursor:
                cursor.execute('''
                    SELECT rc.code
                    FROM referral_codes rc
                    JOIN users u ON rc.user_id = u.user_id
                    WHERE u.telegram_id = %s AND rc.is_active = 1
                ''', (telegram_id,))
                result = cursor.fetchone()
                return result['code'] if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении реферального кода пользователя: {str(e)}")
            return None

    # def get_referral(self, referral_code: str) -> Optional[Dict[str, Any]]:
    #     """Получение информации о реферальном коде"""
    #     try:
    #         with self.conn.cursor() as cursor:
    #             cursor.execute('''
    #                 SELECT rc.*, u.telegram_id
    #                 FROM referral_codes rc
    #                 JOIN users u ON rc.user_id = u.user_id
    #                 WHERE rc.code = %s AND rc.is_active = 1
    #             ''', (referral_code,))
    #             return cursor.fetchone()
    #     except Exception as e:
    #         logger.error(f"Ошибка при получении реферального кода: {str(e)}")
    #         return None

    def get_referral(self, referral_code: str) -> Optional[Dict[str, Any]]:
        """Получение информации о реферальном коде (включая user_id и id кода)"""
        try:
            with self.conn.cursor() as cursor:
                # Убедимся, что выбираем user_id и id из referral_codes
                cursor.execute('''
                    SELECT
                        rc.id AS referral_code_id,
                        rc.user_id AS referrer_user_id,
                        rc.code,
                        u.telegram_id AS referrer_telegram_id
                    FROM referral_codes rc
                    JOIN users u ON rc.user_id = u.user_id
                    WHERE rc.code = %s AND rc.is_active = 1
                ''', (referral_code,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при получении реферального кода '{referral_code}': {str(e)}")
            return None

    def get_user_referral(self, telegram_id):
        """Получает реферальный код пользователя по его telegram_id"""
        query = "SELECT * FROM referrals WHERE telegram_id = %s"
        result = self.execute_query(query, (telegram_id,), fetch=True)
        return result[0] if result else None

    def add_requests(self, telegram_id: int, amount: int) -> bool:
        """Добавление бонусных запросов пользователю"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE users 
                    SET requests_left = COALESCE(requests_left, 0) + %s 
                    WHERE telegram_id = %s
                ''', (amount, telegram_id))
                self.conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении запросов: {str(e)}")
            self.conn.rollback()
            return False

    def save_contact(self, telegram_id: int, contact: str) -> bool:
        """Сохранение контакта пользователя"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE users 
                    SET contact = %s
                    WHERE telegram_id = %s
                ''', (contact, telegram_id))

                self.conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении контакта пользователя: {str(e)}")
            self.conn.rollback()
            return False

    def get_user_contact(self, telegram_id: int) -> Optional[str]:
        """Получение контакта пользователя"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT contact FROM users WHERE telegram_id = %s",
                    (telegram_id,)
                )
                result = cursor.fetchone()
                return result['contact'] if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении контакта пользователя: {str(e)}")
            return None

    def close(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()
            self.conn = None
