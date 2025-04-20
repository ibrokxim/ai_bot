import os
import pymysql
import pymysql.cursors
import datetime
import uuid
from dotenv import load_dotenv
from config import DB_CONFIG

# Загрузка переменных окружения
load_dotenv()

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

    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', '')
        self.db_name = os.getenv('DB_NAME', 'bot_db')
        self.connection = None

    def connect(self):
        """Подключение к базе данных"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.db_name,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return True
        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
            return False

    def init_db(self):
        """Инициализация базы данных и создание необходимых таблиц"""
        if not self.connect():
            print("Невозможно инициализировать базу данных: ошибка подключения")
            return False

        try:
            with self.connection.cursor() as cursor:
                # Создаем таблицу пользователей, если она не существует
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INT AUTO_INCREMENT PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        username VARCHAR(255),
                        first_name VARCHAR(255),
                        last_name VARCHAR(255),
                        is_bot BOOLEAN DEFAULT FALSE,
                        language_code VARCHAR(10),
                        phone_number VARCHAR(20),
                        chat_id BIGINT,
                        requests_left INT DEFAULT 10,
                        is_active BOOLEAN DEFAULT TRUE,
                        registration_date DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Создаем таблицу для реферальных кодов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS referrals (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        referral_code VARCHAR(50) UNIQUE NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                ''')

                # Создаем таблицу для истории реферальных переходов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS referral_history (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        referrer_id INT NOT NULL,
                        referred_user_id INT NOT NULL,
                        referral_code VARCHAR(50) NOT NULL,
                        bonus_requests_added INT DEFAULT 0,
                        conversion_status VARCHAR(50) DEFAULT 'registered',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        converted_at DATETIME,
                        FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE,
                        FOREIGN KEY (referred_user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                ''')

                # Создаем таблицу запросов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS requests (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        query TEXT NOT NULL,
                        response TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                    )
                ''')

                self.connection.commit()
                return True

        except Exception as e:
            print(f"Ошибка инициализации базы данных: {e}")
            return False
        finally:
            self.connection.close()

    def save_user(self, telegram_id, username=None, first_name=None, last_name=None,
                  is_bot=False, language_code=None, chat_id=None, contact=None, is_active=True):
        """Сохранение информации о пользователе. Возвращает True, если пользователь новый."""
        if not self.connection or self.connection._closed:
            if not self.connect():
                return False

        try:
            with self.connection.cursor() as cursor:
                # Проверяем, существует ли пользователь
                cursor.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
                existing_user = cursor.fetchone()

                if existing_user:
                    # Обновляем информацию о существующем пользователе
                    sql = '''
                        UPDATE users SET 
                        username = %s,
                        first_name = %s,
                        last_name = %s,
                        language_code = %s,
                        is_active = %s
                    '''
                    params = (username, first_name, last_name, language_code, is_active)

                    # Добавляем chat_id, если он предоставлен
                    if chat_id is not None:
                        sql += ", chat_id = %s"
                        params += (chat_id,)

                    # Добавляем phone_number, если он предоставлен
                    if contact is not None and hasattr(contact, 'phone_number'):
                        sql += ", phone_number = %s"
                        params += (contact.phone_number,)

                    sql += " WHERE telegram_id = %s"
                    params += (telegram_id,)

                    cursor.execute(sql, params)
                    self.connection.commit()
                    return False  # Пользователь не новый
                else:
                    # Создаем нового пользователя
                    sql = '''
                        INSERT INTO users 
                        (telegram_id, username, first_name, last_name, is_bot, language_code, 
                        chat_id, phone_number, is_active, registration_date) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    '''

                    phone_number = None
                    if contact is not None and hasattr(contact, 'phone_number'):
                        phone_number = contact.phone_number

                    cursor.execute(sql, (
                        telegram_id, username, first_name, last_name, is_bot, language_code,
                        chat_id, phone_number, is_active, datetime.datetime.now()
                    ))
                    self.connection.commit()
                    return True  # Пользователь новый

        except Exception as e:
            print(f"Ошибка при сохранении пользователя: {e}")
            return False

    def get_user(self, telegram_id):
        """Получение информации о пользователе по telegram_id"""
        if not self.connection or self.connection._closed:
            if not self.connect():
                return None

        try:
            with self.connection.cursor() as cursor:
                cursor.execute('''
                    SELECT * FROM users WHERE telegram_id = %s
                ''', (telegram_id,))

                return cursor.fetchone()

        except Exception as e:
            print(f"Ошибка при получении пользователя: {e}")
            return None

    def create_referral(self, user_id, referral_code):
        """Создание реферальной ссылки для пользователя"""
        if not self.connection or self.connection._closed:
            if not self.connect():
                return False

        try:
            with self.connection.cursor() as cursor:
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

                self.connection.commit()
                return True

        except Exception as e:
            print(f"Ошибка при создании реферальной ссылки: {e}")
            return False

    def get_referral(self, referral_code):
        """Получение информации о реферальном коде"""
        if not self.connection or self.connection._closed:
            if not self.connect():
                return None

        try:
            with self.connection.cursor() as cursor:
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

    def get_user_referral(self, user_id):
        """Получение реферального кода пользователя"""
        if not self.connection or self.connection._closed:
            if not self.connect():
                return None

        try:
            with self.connection.cursor() as cursor:
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

    def add_requests(self, user_id, num_requests):
        """Добавление запросов пользователю"""
        if not self.connection or self.connection._closed:
            if not self.connect():
                return False

        try:
            with self.connection.cursor() as cursor:
                cursor.execute('''
                    UPDATE users 
                    SET requests_left = requests_left + %s 
                    WHERE user_id = %s
                ''', (num_requests, user_id))

                self.connection.commit()
                return True

        except Exception as e:
            print(f"Ошибка при добавлении запросов: {e}")
            return False

    def check_referral_used(self, telegram_id, referrer_id):
        """Проверка, использовал ли пользователь уже реферальную ссылку данного реферрера"""
        if not self.connection or self.connection._closed:
            if not self.connect():
                return False

        try:
            with self.connection.cursor() as cursor:
                # Получаем user_id по telegram_id
                cursor.execute("SELECT user_id FROM users WHERE telegram_id = %s", (telegram_id,))
                user = cursor.fetchone()

                if not user:
                    return False

                # Проверяем наличие записи в истории реферралов
                cursor.execute('''
                    SELECT id FROM referral_history 
                    WHERE referred_user_id = %s AND referrer_id = %s
                ''', (user['user_id'], referrer_id))

                return cursor.fetchone() is not None

        except Exception as e:
            print(f"Ошибка при проверке использования реферальной ссылки: {e}")
            return False

    def save_referral_history(self, referrer_id, referred_user_id, referral_code, bonus_requests=5):
        """Сохранение информации о реферальном переходе"""
        if not self.connection or self.connection._closed:
            if not self.connect():
                return False

        try:
            with self.connection.cursor() as cursor:
                # Проверяем, есть ли уже запись для этой пары пользователей
                cursor.execute('''
                    SELECT id FROM referral_history 
                    WHERE referrer_id = %s AND referred_user_id = %s
                ''', (referrer_id, referred_user_id))

                existing_record = cursor.fetchone()

                if existing_record:
                    # Обновляем существующую запись
                    cursor.execute('''
                        UPDATE referral_history 
                        SET bonus_requests_added = bonus_requests_added + %s,
                            conversion_status = 'used_bot',
                            converted_at = %s
                        WHERE id = %s
                    ''', (bonus_requests, datetime.datetime.now(), existing_record['id']))
                else:
                    # Создаем новую запись
                    cursor.execute('''
                        INSERT INTO referral_history 
                        (referrer_id, referred_user_id, referral_code, bonus_requests_added, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (referrer_id, referred_user_id, referral_code, bonus_requests, datetime.datetime.now()))

                self.connection.commit()

                # Обновляем счетчик рефералов в статистике пользователя (если есть таблица user_statistics)
                try:
                    cursor.execute('''
                        UPDATE user_statistics 
                        SET total_referrals = total_referrals + 1
                        WHERE user_id = %s
                    ''', (referrer_id,))
                    self.connection.commit()
                except:
                    # Таблица user_statistics может отсутствовать, игнорируем ошибку
                    pass

                return True

        except Exception as e:
            print(f"Ошибка при сохранении информации о реферальном переходе: {e}")
            return False

    def get_user_referrals(self, user_id):
        """Получение списка рефералов пользователя"""
        if not self.connection or self.connection._closed:
            if not self.connect():
                return []

        try:
            with self.connection.cursor() as cursor:
                cursor.execute('''
                    SELECT rh.*, u.username, u.first_name, u.last_name, u.telegram_id
                    FROM referral_history rh
                    JOIN users u ON rh.referred_user_id = u.user_id
                    WHERE rh.referrer_id = %s
                    ORDER BY rh.created_at DESC
                ''', (user_id,))

                return cursor.fetchall()

        except Exception as e:
            print(f"Ошибка при получении списка рефералов: {e}")
            return []

    def use_request(self, user_id, query, response=None):
        """Использование запроса пользователем и сохранение его в истории"""
        if not self.connection or self.connection._closed:
            if not self.connect():
                return False, "Недостаточно доступных запросов"

        try:
            with self.connection.cursor() as cursor:
                # Проверяем, есть ли у пользователя доступные запросы
                cursor.execute("SELECT requests_left FROM users WHERE user_id = %s", (user_id,))
                user = cursor.fetchone()

                if not user or user['requests_left'] <= 0:
                    return False, "Недостаточно доступных запросов"

                # Уменьшаем количество доступных запросов
                cursor.execute('''
                    UPDATE users 
                    SET requests_left = requests_left - 1 
                    WHERE user_id = %s
                ''', (user_id,))

                # Сохраняем запрос в истории
                cursor.execute('''
                    INSERT INTO requests (user_id, query, response, created_at)
                    VALUES (%s, %s, %s, %s)
                ''', (user_id, query, response, datetime.datetime.now()))

                self.connection.commit()
                return True, "Запрос успешно использован"

        except Exception as e:
            print(f"Ошибка при использовании запроса: {e}")
            return False, f"Ошибка: {str(e)}" 