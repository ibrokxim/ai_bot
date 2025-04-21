import logging
from typing import Optional, Dict, Any
import datetime

import mysql.connector
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

from config import DB_CONFIG

# Загрузка переменных окружения
load_dotenv()

# Создаем логгер для модуля database
logger = logging.getLogger('bot.database')

# Константы
DEFAULT_REQUESTS = 10  # Начальное количество запросов для нового пользователя

def get_db_connection():
    """
    Создает и возвращает соединение с базой данных
    """
    logger.debug("Создаем новое соединение с базой данных")
    return pymysql.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        db=DB_CONFIG['db'],
        charset=DB_CONFIG['charset'],
        cursorclass=pymysql.cursors.DictCursor
    )

class Database:
    """
    Класс для работы с базой данных
    """
    def __init__(self):
        """Инициализация класса Database"""
        self.conn = None
        self.connect()

    def connect(self) -> bool:
        """
        Устанавливает соединение с базой данных
        
        Returns:
            bool: True если соединение установлено успешно, False в противном случае
        """
        try:
            self.conn = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                db=DB_CONFIG['db'],
                charset=DB_CONFIG['charset'],
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("Соединение с базой данных установлено успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка при подключении к базе данных: {str(e)}")
            return False

    def close(self):
        """Закрывает соединение с базой данных"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Соединение с базой данных закрыто")

    def __del__(self):
        """Деструктор класса"""
        self.close()

    @staticmethod
    def execute_query(query, params=None, fetch_one=False, commit=False):
        """
        Выполняет SQL-запрос к базе данных
        
        Args:
            query (str): SQL-запрос
            params (tuple, optional): Параметры для SQL-запроса
            fetch_one (bool): Вернуть один результат или все
            commit (bool): Нужно ли фиксировать изменения
            
        Returns:
            dict or list: Результат запроса
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        result = None
        
        try:
            cursor.execute(query, params or ())
            
            if fetch_one:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()
                
            if commit:
                conn.commit()
                
        except Exception as e:
            if commit:
                conn.rollback()
            raise e
            
        finally:
            cursor.close()
            conn.close()
            
        return result
    
    @staticmethod
    def get_user_by_id(user_id):
        """
        Получает пользователя по ID
        
        Args:
            user_id (str): ID пользователя
            
        Returns:
            dict: Информация о пользователе
        """
        query = "SELECT * FROM users WHERE id = %s"
        return Database.execute_query(query, (user_id,), fetch_one=True)
    
    @staticmethod
    def get_user_by_username(username):
        """
        Получает пользователя по имени пользователя
        
        Args:
            username (str): Имя пользователя
            
        Returns:
            dict: Информация о пользователе
        """
        query = "SELECT * FROM users WHERE username = %s"
        return Database.execute_query(query, (username,), fetch_one=True)
    
    @staticmethod
    def get_user_requests_left(user_id):
        """
        Получает количество оставшихся запросов пользователя
        
        Args:
            user_id (str): ID пользователя
            
        Returns:
            int: Количество оставшихся запросов
        """
        query = "SELECT requests_left FROM users WHERE id = %s"
        result = Database.execute_query(query, (user_id,), fetch_one=True)
        return result.get('requests_left', 0) if result else 0
    
    @staticmethod
    def get_user_detailed_info(user_id):
        """
        Получает детальную информацию о пользователе
        
        Args:
            user_id (str): ID пользователя
            
        Returns:
            dict: Детальная информация о пользователе
        """
        query = '''
            SELECT u.*, 
                   COALESCE(us.total_requests, 0) as total_requests,
                   COALESCE(us.total_tokens, 0) as total_tokens,
                   COALESCE(us.total_payments, 0) as total_payments,
                   COALESCE(us.total_referrals, 0) as total_referrals,
                   us.account_level,
                   us.last_active
            FROM users u
            LEFT JOIN user_statistics us ON u.id = us.user_id
            WHERE u.id = %s
        '''
        return Database.execute_query(query, (user_id,), fetch_one=True)
    
    @staticmethod
    def get_active_plan(user_id):
        """
        Получает активный тарифный план пользователя
        
        Args:
            user_id (str): ID пользователя
            
        Returns:
            dict: Информация о тарифном плане
        """
        query = '''
            SELECT up.*, p.name as plan_name, p.requests_allowed, p.price, p.description
            FROM user_plans up
            JOIN plans p ON up.plan_id = p.id
            WHERE up.user_id = %s AND up.end_date >= NOW()
            ORDER BY up.start_date DESC
            LIMIT 1
        '''
        return Database.execute_query(query, (user_id,), fetch_one=True)
    
    @staticmethod
    def decrease_user_requests(user_id):
        """
        Уменьшает количество оставшихся запросов пользователя
        
        Args:
            user_id (str): ID пользователя
            
        Returns:
            int: Новое количество оставшихся запросов
        """
        query = """
            UPDATE users 
            SET requests_left = GREATEST(requests_left - 1, 0) 
            WHERE id = %s
        """
        Database.execute_query(query, (user_id,), commit=True)
        
        # Получаем обновленное значение
        return Database.get_user_requests_left(user_id)
    
    @staticmethod
    def get_all_active_plans():
        """
        Получает все активные тарифные планы
        
        Returns:
            list: Список активных тарифных планов
        """
        query = '''
            SELECT *
            FROM plans
            WHERE is_active = TRUE
            ORDER BY priority, price
        '''
        return Database.execute_query(query)
    
    @staticmethod
    def get_plan_by_id(plan_id):
        """
        Получает тарифный план по ID
        
        Args:
            plan_id (int): ID тарифного плана
            
        Returns:
            dict: Информация о тарифном плане
        """
        query = "SELECT * FROM plans WHERE id = %s"
        return Database.execute_query(query, (plan_id,), fetch_one=True)
    
    @staticmethod
    def add_usage_record(user_id, request_type, ai_model, tokens_used, was_successful=True, 
                        request_text=None, response_length=0, response_time=None):
        """
        Добавляет запись об использовании запроса
        
        Args:
            user_id (str): ID пользователя
            request_type (str): Тип запроса
            ai_model (str): Название модели ИИ
            tokens_used (int): Количество использованных токенов
            was_successful (bool): Успешно ли выполнен запрос
            request_text (str): Текст запроса (опционально)
            response_length (int): Длина ответа (опционально)
            response_time (float): Время ответа в секундах (опционально)
            
        Returns:
            bool: Успешно ли добавлена запись
        """
        query = """
            INSERT INTO request_usage 
            (user_id, request_type, ai_model, tokens_used, was_successful, request_text, response_length, response_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            user_id, request_type, ai_model, tokens_used, 
            was_successful, request_text, response_length, response_time
        )
        Database.execute_query(query, params, commit=True)
        
        # Обновляем статистику пользователя
        query = """
            INSERT INTO user_statistics (user_id, total_requests, total_tokens, last_active)
            VALUES (%s, 1, %s, NOW())
            ON DUPLICATE KEY UPDATE
                total_requests = total_requests + 1,
                total_tokens = total_tokens + %s,
                last_active = NOW()
        """
        params = (user_id, tokens_used, tokens_used)
        Database.execute_query(query, params, commit=True)
        
        return True

    def save_user(self, user_id: int, username: str = None, first_name: str = None, 
                  last_name: str = None, chat_id: Optional[int] = None, 
                  referral_code: Optional[str] = None, is_bot: bool = False,
                  language_code: str = None, contact: str = None, is_active: bool = True) -> bool:
        """
        Сохраняет или обновляет информацию о пользователе
        
        Args:
            user_id (int): Telegram ID пользователя
            username (str, optional): Имя пользователя
            first_name (str, optional): Имя
            last_name (str, optional): Фамилия
            chat_id (int, optional): ID чата
            referral_code (str, optional): Реферальный код
            is_bot (bool): Является ли пользователь ботом
            language_code (str, optional): Код языка
            contact (str, optional): Контактные данные
            is_active (bool): Активен ли пользователь
            
        Returns:
            bool: True если успешно, False если произошла ошибка
        """
        try:
            logger.info(f"Попытка сохранения пользователя: ID={user_id}, username={username}, "
                       f"contact={contact}, language_code={language_code}, is_bot={is_bot}, "
                       f"chat_id={chat_id}, is_active={is_active}")
            
            if not self.conn or not self.conn.open:
                logger.debug("Соединение с БД отсутствует, пытаемся создать новое")
                if not self.connect():
                    logger.error("Не удалось подключиться к базе данных")
                    return False
            
            cursor = self.conn.cursor()
            
            try:
                # Проверяем, существует ли пользователь
                cursor.execute("""
                    SELECT telegram_id FROM users WHERE telegram_id = %s
                """, (user_id,))
                user_exists = cursor.fetchone()
                
                if user_exists:
                    # Обновляем существующего пользователя
                    sql = """
                        UPDATE users 
                        SET username = %s,
                            first_name = %s,
                            last_name = %s,
                            chat_id = %s,
                            is_bot = %s,
                            language_code = %s,
                            contact = %s,
                            is_active = %s
                        WHERE telegram_id = %s
                    """
                    params = (
                        username, first_name, last_name, chat_id,
                        is_bot, language_code, contact, is_active,
                        user_id
                    )
                    logger.info(f"Обновление пользователя {user_id}")
                    cursor.execute(sql, params)
                else:
                    # Создаем нового пользователя
                    sql = """
                        INSERT INTO users (
                            telegram_id, username, first_name, last_name,
                            chat_id, is_bot, language_code, contact,
                            requests_left, is_active
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """
                    params = (
                        user_id, username, first_name, last_name,
                        chat_id, is_bot, language_code, contact,
                        DEFAULT_REQUESTS, is_active
                    )
                    logger.info(f"Создание нового пользователя {user_id}")
                    cursor.execute(sql, params)

                # Генерируем и сохраняем реферальный код, если его нет
                if not referral_code:
                    referral_code = self.generate_referral_code(user_id)
                
                if referral_code:
                    cursor.execute("""
                        INSERT INTO referrals (user_id, referral_code, created_at)
                        VALUES (%s, %s, NOW())
                        ON DUPLICATE KEY UPDATE referral_code = VALUES(referral_code)
                    """, (user_id, referral_code))

                self.conn.commit()
                
                # Проверяем, что данные действительно сохранились
                cursor.execute("SELECT contact FROM users WHERE telegram_id = %s", (user_id,))
                result = cursor.fetchone()
                logger.info(f"Текущее значение контакта в БД: {result['contact'] if result else None}")
                
                return True

            except Exception as e:
                self.conn.rollback()
                logger.error(f"Ошибка при сохранении пользователя: {str(e)}")
                return False
            
            finally:
                cursor.close()

        except Exception as e:
            logger.error(f"Общая ошибка при сохранении пользователя: {str(e)}")
            logger.exception("Полный стек ошибки:")
            return False

    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение информации о пользователе по telegram_id
        
        :param telegram_id: ID пользователя в Telegram
        :return: Словарь с данными пользователя или None, если пользователь не найден
        """
        try:
            logger.debug(f"Получение данных пользователя {telegram_id} из базы данных")
            
            if not self.conn or not self.conn.is_connected():
                logger.debug(f"Соединение с БД отсутствует или закрыто, открываем новое соединение")
                self.connect()
            
            if not self.conn or not self.conn.is_connected():
                logger.error(f"Не удалось установить соединение с базой данных")
                return None
            
            cursor = self.conn.cursor(dictionary=True, buffered=True)
            
            try:
                logger.debug(f"Выполняем запрос к БД для получения данных пользователя {telegram_id}")
                cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
            
            user = cursor.fetchone()
                if user:
                    logger.info(f"Пользователь {telegram_id} найден в базе данных")
                    logger.debug(f"Полученные данные: {user}")
                else:
                    logger.warning(f"Пользователь {telegram_id} не найден в базе данных")

            return user
                
            except Exception as e:
                logger.error(f"Ошибка при выполнении запроса: {str(e)}")
                return None
                
            finally:
                cursor.close()
            
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя {telegram_id}: {str(e)}")
            logger.exception("Полный стек ошибки:")
            return None

    def get_user_by_referral_code(self, referral_code: str) -> Optional[int]:
        """
        Получение ID пользователя по реферальному коду
        
        :param referral_code: Реферальный код
        :return: telegram_id пользователя или None, если код не найден
        """
        try:
            logger.info(f"Ищем пользователя по реферальному коду: {referral_code}")
            
            if not self.conn or not self.conn.is_connected():
                self.connect()
            
            cursor = self.conn.cursor(dictionary=True)
            found_user_id = None
            
            # Сначала пробуем найти в таблице referral_codes (основная таблица)
            try:
                cursor.execute("""
                    SELECT user_id FROM referral_codes WHERE code = %s
                """, (referral_code,))
                
                result = cursor.fetchone()
                
                if result:
                    found_user_id = result['user_id']
                    logger.info(f"Найден пользователь {found_user_id} в таблице referral_codes")
            except Exception as e:
                logger.warning(f"Ошибка при поиске в таблице referral_codes: {e}")
            
            # Если не нашли, пробуем поискать в таблице users (если там хранятся коды)
            if not found_user_id:
                try:
            cursor.execute("""
                SELECT telegram_id FROM users WHERE referral_code = %s
            """, (referral_code,))
            
            result = cursor.fetchone()
                    
                    if result:
                        found_user_id = result['telegram_id']
                        logger.info(f"Найден пользователь {found_user_id} в таблице users")
                except Exception as e:
                    logger.warning(f"Ошибка при поиске в таблице users: {e}")
            
            # Если и тут не нашли, пробуем в таблице referrals 
            if not found_user_id:
                try:
                    cursor.execute("""
                        SELECT user_id FROM referrals WHERE referral_code = %s
                    """, (referral_code,))
                    
                    result = cursor.fetchone()
                    if result:
                        found_user_id = result['user_id']
                        logger.info(f"Найден пользователь {found_user_id} в таблице referrals")
                except Exception as e:
                    logger.warning(f"Таблица referrals не найдена или другая ошибка: {e}")
            
            cursor.close()
            
            if not found_user_id:
                logger.warning(f"Не найден пользователь для реферального кода {referral_code}")
            
            return found_user_id
            
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя по коду {referral_code}: {e}")
            return None

    def update_user_referral_code(self, telegram_id: int, referral_code: str) -> bool:
        """
        Обновление или создание реферального кода пользователя
        
        :param telegram_id: ID пользователя в Telegram
        :param referral_code: Новый реферальный код
        :return: True, если обновление успешно, иначе False
        """
        try:
            logger.info(f"Обновление реферального кода для пользователя {telegram_id}: {referral_code}")
            
            if not self.conn or not self.conn.is_connected():
                logger.debug(f"Соединение с БД отсутствует или закрыто, пытаемся переподключиться")
                self.connect()
            
            cursor = self.conn.cursor()
            
            # Проверяем, существует ли пользователь
            cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = %s", (telegram_id,))
            user_exists = cursor.fetchone()
            
            if not user_exists:
                logger.warning(f"Пользователь {telegram_id} не найден в базе данных, но мы все равно попытаемся сохранить код")
                # Для отладки запросим все строки из таблицы users
                try:
                    cursor.execute("SELECT telegram_id FROM users LIMIT 10")
                    existing_users = cursor.fetchall()
                    user_ids = [user[0] for user in existing_users] if existing_users else []
                    logger.debug(f"Существующие пользователи в базе: {user_ids}")
                except Exception as e:
                    logger.error(f"Ошибка при получении списка пользователей: {str(e)}")
            else:
                logger.debug(f"Пользователь {telegram_id} найден в базе данных")
            
            # Проверяем, есть ли уже код у пользователя
            cursor.execute("""
                SELECT id FROM referral_codes WHERE user_id = %s
            """, (telegram_id,))
            
            existing_code = cursor.fetchone()
            
            if existing_code:
                # Обновляем существующий код
                logger.info(f"Обновляем существующий реферальный код для {telegram_id}")
                cursor.execute("""
                    UPDATE referral_codes 
                    SET code = %s 
                    WHERE user_id = %s
            """, (referral_code, telegram_id))
            else:
                # Создаем новый код
                logger.info(f"Создаем новый реферальный код для {telegram_id}")
                
                # Проверяем, существует ли таблица
                cursor.execute("SHOW TABLES LIKE 'referral_codes'")
                table_exists = cursor.fetchone() is not None
                
                if not table_exists:
                    logger.warning("Таблица referral_codes не существует, создаем")
                    self._create_tables()
                
                try:
                    cursor.execute("""
                        INSERT INTO referral_codes (user_id, code)
                        VALUES (%s, %s)
                    """, (telegram_id, referral_code))
                except Exception as e:
                    logger.error(f"Ошибка при вставке кода: {str(e)}")
                    
                    # Проверяем ограничения внешнего ключа
                    if "foreign key constraint fails" in str(e).lower():
                        logger.warning("Ошибка внешнего ключа. Пробуем создать запись в users")
                        try:
                            # Пытаемся создать запись пользователя, если она отсутствует
                            cursor.execute("""
                                INSERT IGNORE INTO users (telegram_id, requests_left)
                                VALUES (%s, 10)
                            """, (telegram_id,))
            self.conn.commit()
                            
                            # Пробуем снова вставить код
                            cursor.execute("""
                                INSERT INTO referral_codes (user_id, code)
                                VALUES (%s, %s)
                            """, (telegram_id, referral_code))
                        except Exception as inner_e:
                            logger.error(f"Ошибка при повторной попытке: {str(inner_e)}")
                            raise inner_e
            
            self.conn.commit()
            
            # Проверяем, сохранился ли код
            cursor.execute("""
                SELECT code FROM referral_codes WHERE user_id = %s
            """, (telegram_id,))
            
            saved_code = cursor.fetchone()
            cursor.close()
            
            if saved_code and saved_code[0] == referral_code:
                logger.info(f"Реферальный код {referral_code} успешно сохранен для пользователя {telegram_id}")
            return True
            else:
                logger.error(f"Ошибка при сохранении реферального кода: код в БД не соответствует запрошенному")
                return False
            
        except Exception as e:
            if self.conn:
            self.conn.rollback()
            logger.error(f"Ошибка при обновлении реферального кода для {telegram_id}: {str(e)}")
            return False

    def get_user_referral_code(self, telegram_id: int, auto_create: bool = False) -> Optional[str]:
        """
        Получает реферальный код пользователя. Может автоматически создать новый, если он отсутствует.
        
        Args:
            telegram_id (int): ID пользователя в Telegram
            auto_create (bool): Автоматически создать код, если отсутствует
            
        Returns:
            str or None: Реферальный код пользователя или None в случае ошибки
        """
        try:
            if not self.conn or self.conn._closed:
                if not self.connect():
                    logger.error("Не удалось подключиться к базе данных")
                    return None
                
            # Получаем ID пользователя в системе
            user_id = self.get_user_id_by_telegram_id(telegram_id)
            if not user_id:
                logger.warning(f"Пользователь с Telegram ID {telegram_id} не найден в базе")
                return None
            
            # Пытаемся получить существующий код
            with self.conn.cursor() as cursor:
                cursor.execute('''
                    SELECT referral_code 
                    FROM referrals 
                    WHERE user_id = %s
                ''', (user_id,))
                
                result = cursor.fetchone()
                
                if result and result['referral_code']:
                    return result['referral_code']
                
                # Если кода нет и нужно создать новый
                if auto_create:
                    new_code = self.generate_referral_code(telegram_id)
                    self.create_referral(user_id, new_code)
                    logger.info(f"Создан новый реферальный код {new_code} для пользователя {telegram_id}")
                    return new_code
                
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении реферального кода для {telegram_id}: {str(e)}")
            logger.exception("Подробная информация об ошибке:")
            return None
        
    def generate_referral_code(self, telegram_id: int) -> str:
        """
        Генерирует уникальный реферальный код для пользователя
        
        Args:
            telegram_id (int): ID пользователя в Telegram
            
        Returns:
            str: Уникальный реферальный код
        """
        import random
        import string
        
        # Пытаемся получить имя пользователя
        user_data = self.get_user(telegram_id)
        prefix = ""
        
        if user_data and user_data.get('username'):
            # Берем первые 4 символа имени пользователя в верхнем регистре
            prefix = user_data['username'][:4].upper()
        else:
            # Если нет имени, берем первые 4 цифры ID
            prefix = str(telegram_id)[:4]
        
        # Добавляем случайные символы для уникальности
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        
        return f"{prefix}{suffix}"

    def get_user_id_by_telegram_id(self, telegram_id: int) -> Optional[int]:
        """
        Получает ID пользователя в базе данных по его Telegram ID
        
        Args:
            telegram_id (int): ID пользователя в Telegram
            
        Returns:
            int or None: ID пользователя в БД или None в случае ошибки
        """
        try:
            if not self.conn or self.conn._closed:
                if not self.connect():
                    return None
                
            with self.conn.cursor() as cursor:
                cursor.execute('''
                    SELECT user_id 
                    FROM users 
                    WHERE telegram_id = %s
                ''', (telegram_id,))
                
                result = cursor.fetchone()
                
                if result:
                    return result['user_id']
                return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении user_id для {telegram_id}: {str(e)}")
            return None

    def save_referral_history(self, referrer_id, referred_user_id, referral_code=None, bonus_requests=5):
        """
        Сохраняет историю реферала
        
        Args:
            referrer_id (int): ID пригласившего пользователя
            referred_user_id (int): ID приглашенного пользователя
            referral_code (str, optional): Использованный реферальный код
            bonus_requests (int): Количество бонусных запросов
            
        Returns:
            bool: True если успешно, False если произошла ошибка
        """
        try:
            # Проверяем, не использовал ли уже пользователь реферальную систему
            if self.check_referral_used(referred_user_id, referrer_id):
                logger.warning(f"Пользователь {referred_user_id} уже использовал реферальную систему")
                return False

            # Получаем реферальный код если не был передан
            if not referral_code:
                ref_code = self.get_user_referral_code(referrer_id)
                referral_code = ref_code if ref_code else "UNKNOWN"
                
            logger.info(f"Сохраняем историю реферала: реферер {referrer_id}, приглашенный {referred_user_id}, код {referral_code}")

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    try:
                        # Сначала проверяем наличие таблицы
                        cursor.execute("SHOW TABLES LIKE 'referral_history'")
                        table_exists = cursor.fetchone() is not None
                        
                        if not table_exists:
                            logger.error("Таблица referral_history не существует")
                            # Создаем таблицу с полным набором полей
                            self._create_tables()
                        
                        # Пробуем вставить запись со всеми дополнительными полями
                        try:
                            sql = """
                                INSERT INTO referral_history 
                                (referrer_id, referred_id, referral_code, bonus_requests_added, conversion_status, created_at)
                                VALUES (%s, %s, %s, %s, %s, NOW())
                            """
                            cursor.execute(sql, (referrer_id, referred_user_id, referral_code, bonus_requests, 'registered'))
                            conn.commit()
                            logger.info(f"Реферальная история сохранена с полными данными: {referrer_id} пригласил {referred_user_id}, код: {referral_code}")
            return True
                        except Exception as e:
                            conn.rollback()
                            logger.warning(f"Не удалось сохранить полную запись: {e}. Пробуем базовый вариант.")
                            
                            # Пробуем упрощенный запрос с минимальным набором полей
                            sql = """
                                INSERT INTO referral_history 
                                (referrer_id, referred_id, created_at)
                                VALUES (%s, %s, NOW())
                            """
                            cursor.execute(sql, (referrer_id, referred_user_id))
                            conn.commit()
                            logger.info(f"Реферальная история сохранена с базовыми данными: {referrer_id} пригласил {referred_user_id}")
                            return True
                            
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"SQL ошибка при сохранении реферальной истории: {str(e)}")
                        return False

        except Exception as e:
            logger.error(f"Ошибка при сохранении реферальной истории: {e}")
            return False

    def increase_user_requests(self, telegram_id: int, amount: int = 1) -> bool:
        """
        Увеличение количества доступных запросов пользователя
        
        :param telegram_id: ID пользователя в Telegram
        :param amount: Количество запросов для добавления
        :return: True, если обновление успешно, иначе False
        """
        try:
            logger.info(f"Попытка увеличить количество запросов на {amount} для пользователя {telegram_id}")
            
            if not self.conn or not self.conn.is_connected():
                self.connect()
            
            cursor = self.conn.cursor()
            
            # Проверка существования пользователя
            cursor.execute("SELECT telegram_id, requests_left FROM users WHERE telegram_id = %s", (telegram_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                logger.error(f"Пользователь {telegram_id} не найден при попытке увеличить запросы")
                cursor.close()
                return False
                
            current_requests = user_data[1] if len(user_data) > 1 else 0
            logger.info(f"Текущее количество запросов пользователя {telegram_id}: {current_requests}")
            
            # Увеличиваем количество запросов
            cursor.execute("""
                UPDATE users 
                SET requests_left = requests_left + %s 
                WHERE telegram_id = %s
            """, (amount, telegram_id))
            
            self.conn.commit()
            affected_rows = cursor.rowcount
            
            # Проверяем, изменилось ли количество запросов
            cursor.execute("SELECT requests_left FROM users WHERE telegram_id = %s", (telegram_id,))
            new_data = cursor.fetchone()
            new_requests = new_data[0] if new_data else 0
            
            cursor.close()
            
            if affected_rows > 0 and new_requests > current_requests:
                logger.info(f"Успешно добавлено {amount} запросов пользователю {telegram_id}. Новое значение: {new_requests}")
            return True
            else:
                logger.error(f"Не удалось добавить запросы пользователю {telegram_id}. Запросов до: {current_requests}, после: {new_requests}")
                return False
            
        except Exception as e:
            if self.conn:
            self.conn.rollback()
            logger.error(f"Ошибка при увеличении запросов для {telegram_id}: {e}")
            return False

    def decrease_user_requests(self, telegram_id: int, amount: int = 1) -> bool:
        """
        Уменьшение количества доступных запросов пользователя
        
        :param telegram_id: ID пользователя в Telegram
        :param amount: Количество запросов для вычитания
        :return: True, если обновление успешно, иначе False
        """
        try:
            if not self.conn or not self.conn.is_connected():
                self.connect()
            
            cursor = self.conn.cursor()
            
            # Проверяем текущее количество запросов
            cursor.execute("""
                SELECT requests_left FROM users WHERE telegram_id = %s
            """, (telegram_id,))
            
            result = cursor.fetchone()
            if not result or result[0] < amount:
                cursor.close()
                return False  # Недостаточно запросов
            
            cursor.execute("""
                UPDATE users 
                SET requests_left = requests_left - %s 
                WHERE telegram_id = %s
            """, (amount, telegram_id))
            
            self.conn.commit()
            cursor.close()
            return True
        except mysql.connector.Error as e:
            self.conn.rollback()
            logging.error(f"Ошибка при уменьшении запросов для {telegram_id}: {e}")
            return False

    def get_user_referral(self, user_id):
        """Получение реферального кода пользователя"""
        if not self.conn or self.conn._closed:
            if not self.connect():
                return None

        try:
            with self.conn.cursor() as cursor:
                cursor.execute('''
                    SELECT referral_code FROM referrals WHERE user_id = %s
                ''', (user_id,))

                result = cursor.fetchone()
                if result:
                    return result['referral_code']
                return None

        except Exception as e:
            print(f"Ошибка при получении реферального кода пользователя: {e}")
            return None

    def create_referral(self, user_id: int, referral_code: str) -> bool:
        """
        Создает новую запись о реферальном коде пользователя в базе данных
        
        Args:
            user_id (int): ID пользователя в системе
            referral_code (str): Реферальный код
            
        Returns:
            bool: True если операция выполнена успешно, иначе False
        """
        try:
            if not self.conn or self.conn._closed:
                if not self.connect():
                    logger.error("Не удалось подключиться к базе данных")
                    return False
                
            with self.conn.cursor() as cursor:
                # Проверяем, существует ли уже запись для данного пользователя
                cursor.execute('''
                    SELECT id FROM referrals WHERE user_id = %s
                ''', (user_id,))
                
                result = cursor.fetchone()
                
                if result:
                    # Обновляем существующую запись
                    cursor.execute('''
                        UPDATE referrals 
                        SET referral_code = %s, updated_at = NOW()
                        WHERE user_id = %s
                    ''', (referral_code, user_id))
                else:
                    # Создаем новую запись
                    cursor.execute('''
                        INSERT INTO referrals (user_id, referral_code, created_at, updated_at)
                        VALUES (%s, %s, NOW(), NOW())
                    ''', (user_id, referral_code))
                
            self.conn.commit()
            logger.info(f"Успешно сохранен реферальный код {referral_code} для пользователя {user_id}")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Ошибка при сохранении реферального кода: {str(e)}")
            logger.exception("Подробная информация об ошибке:")
            return False

    def get_referral(self, referral_code):
        """Получение информации о реферальном коде"""
        if not self.conn or self.conn._closed:
            if not self.connect():
                return None

        try:
            with self.conn.cursor() as cursor:
                cursor.execute('''
                    SELECT r.*, u.telegram_id
                    FROM referrals r
                    JOIN users u ON r.user_id = u.user_id
                    WHERE r.referral_code = %s
                ''', (referral_code,))

                return cursor.fetchone()

        except Exception as e:
            print(f"Ошибка при получении информации о реферальном коде: {e}")
            return None

    def check_referral_used(self, referred_id: int, referrer_id: int) -> bool:
        """
        Проверяет, использовал ли уже пользователь реферальный код данного пригласившего
        
        Args:
            referred_id (int): ID приглашенного пользователя
            referrer_id (int): ID пригласившего пользователя
            
        Returns:
            bool: True если реферальный код уже был использован, иначе False
        """
        try:
            if not self.conn or self.conn._closed:
                if not self.connect():
                    logger.error("Не удалось подключиться к базе данных при проверке использования реферала")
                    return False
                
            with self.conn.cursor() as cursor:
                cursor.execute('''
                    SELECT id FROM referral_history 
                    WHERE referrer_id = %s AND referred_id = %s
                ''', (referrer_id, referred_id))
                
                result = cursor.fetchone()
                
            return bool(result)
            
        except Exception as e:
            logger.error(f"Ошибка при проверке использования реферального кода: {str(e)}")
            logger.exception("Подробная информация об ошибке:")
            return False

    def add_bonus_requests(self, user_id: int, amount: int) -> bool:
        """Добавляет бонусные запросы пользователю"""
        try:
            with self.conn:
                cursor = self.conn.cursor()
                cursor.execute(
                    'UPDATE users SET requests_left = requests_left + ? WHERE user_id = ?',
                    (amount, user_id)
                )
                return True
        except mysql.connector.Error as e:
            logging.error(f"Ошибка при добавлении бонусных запросов: {e}")
            return False

    def create_tables(self):
        """Создает необходимые таблицы в базе данных"""
        try:
            with self.conn:
                cursor = self.conn.cursor()
                
                # Создание таблицы пользователей
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INT AUTO_INCREMENT PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        chat_id BIGINT,
                        is_bot BOOLEAN DEFAULT FALSE,
                        language_code VARCHAR(10),
                        contact VARCHAR(255),
                        requests_left INT DEFAULT 5,
                        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                ''')
                
                self.conn.commit()
                logging.info("Таблицы успешно созданы")
        except mysql.connector.Error as e:
            logging.error(f"Ошибка при создании таблиц: {e}") 

    def track_referral_usage(self, referrer_id: int, referred_id: int, referral_code: str, bonus_requests: int = 5) -> bool:
        """
        Отслеживает использование реферального кода и начисляет бонусные запросы
        
        Args:
            referrer_id (int): ID пользователя, который пригласил
            referred_id (int): ID пользователя, который был приглашен
            referral_code (str): Использованный реферальный код
            bonus_requests (int, optional): Количество бонусных запросов. По умолчанию 5.
            
        Returns:
            bool: True если операция выполнена успешно, иначе False
        """
        try:
            if not self.conn or self.conn._closed:
                if not self.connect():
                    logger.error("Не удалось подключиться к базе данных при отслеживании реферала")
                    return False
                
            with self.conn.cursor() as cursor:
                # Проверяем, есть ли уже запись для этой пары пользователей
                cursor.execute('''
                    SELECT id FROM referral_history 
                    WHERE referrer_id = %s AND referred_id = %s
                ''', (referrer_id, referred_id))
                
                existing_record = cursor.fetchone()
                
                current_time = datetime.datetime.now()
                
                if existing_record:
                    # Обновляем существующую запись
                    cursor.execute('''
                        UPDATE referral_history 
                        SET bonus_requests_added = bonus_requests_added + %s,
                            conversion_status = 'used_bot',
                            converted_at = %s
                        WHERE id = %s
                    ''', (bonus_requests, current_time, existing_record[0]))
                else:
                    # Создаем новую запись
                    cursor.execute('''
                        INSERT INTO referral_history 
                        (referrer_id, referred_id, referral_code, bonus_requests_added, 
                         conversion_status, created_at, converted_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ''', (referrer_id, referred_id, referral_code, bonus_requests, 
                          'registered', current_time, current_time))
                    
                # Обновляем счетчик использований реферального кода
                cursor.execute('''
                    UPDATE referrals
                    SET total_uses = total_uses + 1, 
                        last_used_at = %s
                    WHERE user_id = %s AND referral_code = %s
                ''', (current_time, referrer_id, referral_code))
                
                # Начисляем бонусные запросы пригласившему пользователю
                cursor.execute('''
                    UPDATE users
                    SET requests_left = COALESCE(requests_left, 0) + %s
                    WHERE id = %s
                ''', (bonus_requests, referrer_id))
                
            self.conn.commit()
            logger.info(f"Успешно отслежено использование реферального кода: {referral_code}. "
                        f"Пользователь {referrer_id} получил {bonus_requests} бонусных запросов.")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Ошибка при отслеживании использования реферального кода: {str(e)}")
            logger.exception("Подробная информация об ошибке:")
            return False 