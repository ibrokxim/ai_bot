import logging
from typing import Optional, Dict, Any

import mysql.connector
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

from config import DB_CONFIG

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Константы
DEFAULT_REQUESTS = 10  # Начальное количество запросов для нового пользователя

def get_db_connection():
    """
    Создает и возвращает соединение с базой данных
    """
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

    def __init__(self, config: Dict[str, str]):
        """
        Инициализация подключения к базе данных
        
        :param config: Словарь с параметрами подключения к базе данных
        """
        self.config = config
        self.conn = None
        self.connect()
        self._create_tables()
    
    def get_connection(self):
        """
        Создает и возвращает новое соединение с базой данных
        
        :return: Соединение с базой данных
        """
        return mysql.connector.connect(**self.config)

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            self.conn = mysql.connector.connect(**self.config)
            logging.info("Успешное подключение к базе данных")
        except mysql.connector.Error as e:
            logging.error(f"Ошибка подключения к базе данных: {e}")
            raise
    
    def _create_tables(self):
        """Создание необходимых таблиц, если они не существуют"""
        cursor = self.conn.cursor()
        
        # Удаляем существующие таблицы в правильном порядке
        try:
            cursor.execute('DROP TABLE IF EXISTS referral_history')
            cursor.execute('DROP TABLE IF EXISTS referral_codes')
            cursor.execute('DROP TABLE IF EXISTS users')
            self.conn.commit()
        except mysql.connector.Error as e:
            logging.error(f"Ошибка при удалении таблиц: {e}")
            self.conn.rollback()
        
        # Создание таблицы пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                chat_id BIGINT,
                is_bot BOOLEAN DEFAULT FALSE,
                language_code VARCHAR(10),
                contact VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                requests_left INT DEFAULT 5,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        
        # Создание таблицы реферальных кодов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_codes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                code VARCHAR(20) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        
        # Создание таблицы реферальной истории
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referral_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                referrer_id BIGINT NOT NULL,
                referred_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_referral (referrer_id, referred_id),
                FOREIGN KEY (referrer_id) REFERENCES users(telegram_id)
                ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (referred_id) REFERENCES users(telegram_id)
                ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        ''')
        
        self.conn.commit()
        cursor.close()
        logging.info("Структура базы данных проверена и обновлена")
    
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
                       f"is_active={is_active}, chat_id={chat_id}")
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
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
                        logger.info(f"Обновление пользователя {user_id}. SQL: {sql}")
                        logger.info(f"Параметры запроса: {params}")
                        cursor.execute(sql, params)
                        logger.info(f"Запрос выполнен. Проверяем результат...")
                        
                        # Проверяем, что данные действительно обновились
                        cursor.execute("SELECT contact FROM users WHERE telegram_id = %s", (user_id,))
                        result = cursor.fetchone()
                        logger.info(f"Текущее значение контакта в БД: {result[0] if result else None}")
                    else:
                        # Создаем нового пользователя
                        sql = """
                            INSERT INTO users (
                                telegram_id, username, first_name, last_name,
                                chat_id, is_bot, language_code, contact,
                                is_active, requests_left, registration_date
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                            )
                        """
                        params = (
                            user_id, username, first_name, last_name,
                            chat_id, is_bot, language_code, contact,
                            is_active, DEFAULT_REQUESTS
                        )
                        logger.info(f"Создание нового пользователя. SQL: {sql}")
                        logger.info(f"Параметры запроса: {params}")
                        cursor.execute(sql, params)
                        logger.info(f"Запрос выполнен. Проверяем результат...")
                        
                        # Проверяем, что данные действительно сохранились
                        cursor.execute("SELECT contact FROM users WHERE telegram_id = %s", (user_id,))
                        result = cursor.fetchone()
                        logger.info(f"Текущее значение контакта в БД: {result[0] if result else None}")

                    # Если есть реферальный код, обрабатываем его
                    if referral_code:
                        referrer_id = self.get_referrer_by_code(referral_code)
                        if referrer_id and referrer_id != user_id:
                            self.save_referral_history(referrer_id, user_id, referral_code)

                    conn.commit()
                    logger.info(f"Пользователь {user_id} успешно сохранен/обновлен")
                    return True

        except Exception as e:
            logger.error(f"Ошибка при сохранении пользователя: {e}")
            logger.exception("Полный стек ошибки:")
            return False

    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение информации о пользователе по telegram_id
        
        :param telegram_id: ID пользователя в Telegram
        :return: Словарь с данными пользователя или None, если пользователь не найден
        """
        try:
            if not self.conn or not self.conn.is_connected():
                self.connect()
            
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM users WHERE telegram_id = %s
            """, (telegram_id,))
            
            user = cursor.fetchone()
            cursor.close()
            return user
        except mysql.connector.Error as e:
            logging.error(f"Ошибка при получении пользователя {telegram_id}: {e}")
            return None

    def get_user_by_referral_code(self, referral_code: str) -> Optional[int]:
        """
        Получение ID пользователя по реферальному коду
        
        :param referral_code: Реферальный код
        :return: telegram_id пользователя или None, если код не найден
        """
        try:
            if not self.conn or not self.conn.is_connected():
                self.connect()
            
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT user_id FROM referral_codes WHERE code = %s
            """, (referral_code,))
            
            result = cursor.fetchone()
            cursor.close()
            
            return result[0] if result else None
            
        except mysql.connector.Error as e:
            logging.error(f"Ошибка при поиске пользователя по коду {referral_code}: {e}")
            return None

    def update_user_referral_code(self, telegram_id: int, referral_code: str) -> bool:
        """
        Обновление реферального кода пользователя
        
        :param telegram_id: ID пользователя в Telegram
        :param referral_code: Новый реферальный код
        :return: True, если обновление успешно, иначе False
        """
        try:
            if not self.conn or not self.conn.is_connected():
                self.connect()
            
            cursor = self.conn.cursor()
            
            # Проверяем, есть ли уже код у пользователя
            cursor.execute("""
                SELECT id FROM referral_codes WHERE user_id = %s
            """, (telegram_id,))
            
            existing_code = cursor.fetchone()
            
            if existing_code:
                # Обновляем существующий код
                cursor.execute("""
                    UPDATE referral_codes 
                    SET code = %s 
                    WHERE user_id = %s
                """, (referral_code, telegram_id))
            else:
                # Создаем новый код
                cursor.execute("""
                    INSERT INTO referral_codes (user_id, code)
                    VALUES (%s, %s)
                """, (telegram_id, referral_code))
            
            self.conn.commit()
            cursor.close()
            return True
            
        except mysql.connector.Error as e:
            self.conn.rollback()
            logging.error(f"Ошибка при обновлении реферального кода для {telegram_id}: {e}")
            return False

    def get_user_referral_code(self, telegram_id: int) -> Optional[str]:
        """Получает реферальный код пользователя"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute('''
                        SELECT code FROM referral_codes 
                        WHERE user_id = %s
                    ''', (telegram_id,))
                    result = cursor.fetchone()
                    return result['code'] if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении реферального кода: {e}")
            return None

    def save_referral_history(self, referrer_id, referred_user_id, referral_code=None, bonus_requests=5):
        """
        Сохраняет историю реферала
        
        Args:
            referrer_id (int): ID пригласившего пользователя
            referred_user_id (int): ID приглашенного пользователя
            referral_code (str, optional): Использованный реферальный код
            bonus_requests (int): Количество бонусных запросов (не используется)
            
        Returns:
            bool: True если успешно, False если произошла ошибка
        """
        try:
            # Проверяем, не использовал ли уже пользователь реферальную систему
            if self.check_referral_used(referred_user_id, referrer_id):
                logger.warning(f"Пользователь {referred_user_id} уже использовал реферальную систему")
                return False

            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Сохраняем историю реферала
                    sql = """
                        INSERT INTO referral_history (referrer_id, referred_id, created_at)
                        VALUES (%s, %s, NOW())
                    """
                    cursor.execute(sql, (referrer_id, referred_user_id))
                    conn.commit()

                    logger.info(f"Реферальная история сохранена: {referrer_id} пригласил {referred_user_id}")
                    return True

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
            if not self.conn or not self.conn.is_connected():
                self.connect()
            
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET requests_left = requests_left + %s 
                WHERE telegram_id = %s
            """, (amount, telegram_id))
            
            self.conn.commit()
            cursor.close()
            logging.info(f"Добавлено {amount} запросов пользователю {telegram_id}")
            return True
            
        except mysql.connector.Error as e:
            self.conn.rollback()
            logging.error(f"Ошибка при увеличении запросов для {telegram_id}: {e}")
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

    def close(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()
            logging.info("Соединение с базой данных закрыто")
    
    def __del__(self):
        """Деструктор для закрытия соединения при уничтожении объекта"""
        self.close()

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

    def create_referral(self, user_id, referral_code):
        """Создание реферальной ссылки для пользователя"""
        if not self.conn or self.conn._closed:
            if not self.connect():
                return False

        try:
            with self.conn.cursor() as cursor:
                # Проверяем, есть ли уже реферальный код у пользователя
                cursor.execute("SELECT id FROM referrals WHERE user_id = %s", (user_id,))
                existing_ref = cursor.fetchone()

                if existing_ref:
                    # Обновляем существующий код
                    cursor.execute('''
                        UPDATE referrals 
                        SET referral_code = %s 
                        WHERE user_id = %s
                    ''', (referral_code, user_id))
                else:
                    # Создаем новый реферальный код
                    cursor.execute('''
                        INSERT INTO referrals (user_id, referral_code)
                        VALUES (%s, %s)
                    ''', (user_id, referral_code))

                self.conn.commit()
                return True

        except Exception as e:
            print(f"Ошибка при создании реферальной ссылки: {e}")
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

    def check_referral_used(self, telegram_id, referrer_id):
        """Проверка, использовал ли пользователь уже реферальную ссылку данного реферрера"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(dictionary=True) as cursor:
                    # Проверяем наличие записи в истории реферралов
                    cursor.execute('''
                        SELECT id FROM referral_history 
                        WHERE referred_id = %s AND referrer_id = %s
                    ''', (telegram_id, referrer_id))
                    
                    return cursor.fetchone() is not None

        except Exception as e:
            logger.error(f"Ошибка при проверке использования реферальной ссылки: {e}")
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
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        chat_id INTEGER,
                        requests_left INTEGER DEFAULT 10,
                        referral_code TEXT UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                self.conn.commit()
                logging.info("Таблицы успешно созданы")
        except mysql.connector.Error as e:
            logging.error(f"Ошибка при создании таблиц: {e}") 