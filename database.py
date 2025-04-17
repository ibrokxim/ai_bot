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
DEFAULT_REQUESTS = 10

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
        
        # Создание таблицы пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                language_code VARCHAR(10),
                is_bot BOOLEAN DEFAULT FALSE,
                contact JSON,
                chat_id BIGINT,
                referral_code VARCHAR(20) UNIQUE,
                requests_left INT DEFAULT 10,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        ''')
        
        # Создание таблицы рефералов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                referrer_id BIGINT NOT NULL,
                referred_id BIGINT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_referral (referrer_id, referred_id),
                FOREIGN KEY (referrer_id) REFERENCES users(telegram_id),
                FOREIGN KEY (referred_id) REFERENCES users(telegram_id)
            )
        ''')
        
        # Создание таблицы чатов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                chat_id VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        ''')
        
        # Создание таблицы сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                chat_id INT NOT NULL,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
        ''')
        
        self.conn.commit()
        cursor.close()
        logging.info("Структура базы данных проверена и обновлена")
    
    def save_user(self, telegram_id: int, username: Optional[str] = None, 
                 first_name: Optional[str] = None, last_name: Optional[str] = None, 
                 language_code: Optional[str] = None, is_bot: bool = False,
                 contact: Optional[Any] = None, chat_id: Optional[int] = None) -> None:
        """
        Сохранение информации о пользователе в базе данных
        
        :param telegram_id: ID пользователя в Telegram
        :param username: Имя пользователя
        :param first_name: Имя
        :param last_name: Фамилия
        :param language_code: Код языка
        :param is_bot: Является ли пользователь ботом
        :param contact: Объект контакта пользователя
        :param chat_id: ID чата
        """
        try:
            if not self.conn or not self.conn.is_connected():
                self.connect()
            
            cursor = self.conn.cursor()
            
            # Получаем номер телефона из контакта, если он есть
            phone_number = None
            if contact:
                phone_number = getattr(contact, 'phone_number', None)
            
            # Проверяем, существует ли пользователь
            cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = %s", (telegram_id,))
            user_exists = cursor.fetchone()
            
            if user_exists:
                # Обновляем существующего пользователя
                query = """
                    UPDATE users 
                    SET username = %s, first_name = %s, last_name = %s,
                    language_code = %s, is_bot = %s, contact = %s, chat_id = %s,
                    is_active = 1
                    WHERE telegram_id = %s
                """
                params = [username, first_name, last_name, language_code, is_bot, 
                         phone_number, chat_id, telegram_id]
                
                cursor.execute(query, params)
            else:
                # Создаем нового пользователя
                query = """
                    INSERT INTO users 
                    (telegram_id, username, first_name, last_name, language_code, 
                     is_bot, contact, chat_id, is_active, requests_left, registration_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, 10, CURRENT_TIMESTAMP)
                """
                params = [telegram_id, username, first_name, last_name, language_code, 
                         is_bot, phone_number, chat_id]
                
                cursor.execute(query, params)
            
            self.conn.commit()
            cursor.close()
            logging.info(f"Пользователь {telegram_id} успешно сохранен")
        except mysql.connector.Error as e:
            self.conn.rollback()
            logging.error(f"Ошибка при сохранении пользователя {telegram_id}: {e}")
            raise

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
                SELECT telegram_id FROM users WHERE referral_code = %s
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
            cursor.execute("""
                UPDATE users SET referral_code = %s WHERE telegram_id = %s
            """, (referral_code, telegram_id))
            
            self.conn.commit()
            cursor.close()
            return True
        except mysql.connector.Error as e:
            self.conn.rollback()
            logging.error(f"Ошибка при обновлении реферального кода для {telegram_id}: {e}")
            return False

    def save_referral_history(self, referrer_id: int, referred_id: int) -> bool:
        """
        Сохранение истории реферальной программы
        
        :param referrer_id: ID пользователя-реферера
        :param referred_id: ID приглашенного пользователя
        :return: True, если сохранение успешно, иначе False
        """
        try:
            if not self.conn or not self.conn.is_connected():
                self.connect()
            
            cursor = self.conn.cursor()
            
            # Проверяем, не существует ли уже такая запись
            cursor.execute("""
                SELECT id FROM referrals 
                WHERE referrer_id = %s AND referred_id = %s
            """, (referrer_id, referred_id))
            
            if cursor.fetchone():
                cursor.close()
                return False  # Запись уже существует
            
            cursor.execute("""
                INSERT INTO referrals (referrer_id, referred_id)
                VALUES (%s, %s)
            """, (referrer_id, referred_id))
            
            self.conn.commit()
            cursor.close()
            return True
        except mysql.connector.Error as e:
            self.conn.rollback()
            logging.error(f"Ошибка при сохранении реферальной истории: {e}")
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