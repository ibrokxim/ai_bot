import logging
from typing import Optional, Dict, Any

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
        logger.debug("Инициализация объекта Database")
        self.config = config
        self.conn = None
        try:
            self.connect()
            self._create_tables()
            logger.info("Инициализация Database завершена успешно")
        except Exception as e:
            logger.error(f"Ошибка при инициализации Database: {str(e)}")
            logger.exception("Полный стек ошибки:")
    
    def get_connection(self):
        """
        Создает и возвращает новое соединение с базой данных
        
        :return: Соединение с базой данных
        """
        logger.debug("Создание нового соединения с базой данных")
        try:
            conn = mysql.connector.connect(**self.config)
            logger.debug("Соединение с базой данных успешно создано")
            return conn
        except Exception as e:
            logger.error(f"Ошибка при создании соединения с БД: {str(e)}")
            raise

    def connect(self):
        """Установка соединения с базой данных"""
        try:
            logger.debug("Попытка установить соединение с базой данных")
            self.conn = mysql.connector.connect(**self.config)
            logger.info("Успешное подключение к базе данных")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {str(e)}")
            logger.exception("Полный стек ошибки:")
            return False
    
    def _create_tables(self):
        """Создание необходимых таблиц, если они не существуют"""
        logger.debug("Начало создания необходимых таблиц")
        
        try:
            if not self.conn or not self.conn.is_connected():
                logger.warning("Соединение с БД отсутствует, пытаемся создать новое")
                if not self.connect():
                    logger.error("Не удалось установить соединение с базой данных")
                    return
            
            cursor = self.conn.cursor()
            
            # Создание таблицы пользователей (без удаления существующих таблиц)
            logger.debug("Создание таблицы users")
            try:
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
                logger.debug("Таблица users создана успешно")
            except Exception as e:
                logger.error(f"Ошибка при создании таблицы users: {str(e)}")
                return
            
            # Создание таблицы реферальных кодов
            logger.debug("Создание таблицы referral_codes")
            try:
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
                logger.debug("Таблица referral_codes создана успешно")
            except Exception as e:
                logger.error(f"Ошибка при создании таблицы referral_codes: {str(e)}")
                return
            
            # Проверяем наличие таблицы реферальной истории
            logger.debug("Проверка наличия таблицы referral_history")
            try:
                cursor.execute("SHOW TABLES LIKE 'referral_history'")
                referral_history_exists = cursor.fetchone() is not None
                
                if referral_history_exists:
                    logger.debug("Таблица referral_history существует, проверяем структуру")
                    # Проверяем структуру таблицы
                    cursor.execute("DESCRIBE referral_history")
                    columns = cursor.fetchall()
                    column_names = [row[0] for row in columns]
                    logger.debug(f"Найденные столбцы таблицы referral_history: {column_names}")
                    
                    # Добавляем отсутствующие столбцы, если нужно
                    if 'referral_code' not in column_names:
                        logger.debug("Добавляем столбец referral_code в таблицу referral_history")
                        cursor.execute('''
                            ALTER TABLE referral_history 
                            ADD COLUMN referral_code VARCHAR(50) NULL AFTER referred_id
                        ''')
                        logger.info("Добавлен столбец referral_code в таблицу referral_history")
                        
                    if 'bonus_requests_added' not in column_names:
                        logger.debug("Добавляем столбец bonus_requests_added в таблицу referral_history")
                        cursor.execute('''
                            ALTER TABLE referral_history 
                            ADD COLUMN bonus_requests_added INT DEFAULT 0 AFTER referral_code
                        ''')
                        logger.info("Добавлен столбец bonus_requests_added в таблицу referral_history")
                        
                    if 'conversion_status' not in column_names:
                        logger.debug("Добавляем столбец conversion_status в таблицу referral_history")
                        cursor.execute('''
                            ALTER TABLE referral_history 
                            ADD COLUMN conversion_status VARCHAR(50) DEFAULT 'registered' AFTER bonus_requests_added
                        ''')
                        logger.info("Добавлен столбец conversion_status в таблицу referral_history")
                        
                    if 'converted_at' not in column_names:
                        logger.debug("Добавляем столбец converted_at в таблицу referral_history")
                        cursor.execute('''
                            ALTER TABLE referral_history 
                            ADD COLUMN converted_at TIMESTAMP NULL AFTER conversion_status
                        ''')
                        logger.info("Добавлен столбец converted_at в таблицу referral_history")
                else:
                    # Создание таблицы реферальной истории с полным набором полей
                    logger.debug("Таблица referral_history не существует, создаем новую")
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS referral_history (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            referrer_id BIGINT NOT NULL,
                            referred_id BIGINT NOT NULL,
                            referral_code VARCHAR(50) NULL,
                            bonus_requests_added INT DEFAULT 0,
                            conversion_status VARCHAR(50) DEFAULT 'registered',
                            converted_at TIMESTAMP NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE KEY unique_referral (referrer_id, referred_id),
                            FOREIGN KEY (referrer_id) REFERENCES users(telegram_id)
                            ON DELETE CASCADE ON UPDATE CASCADE,
                            FOREIGN KEY (referred_id) REFERENCES users(telegram_id)
                            ON DELETE CASCADE ON UPDATE CASCADE
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    ''')
                    logger.info("Создана таблица referral_history")
            except Exception as e:
                logger.error(f"Ошибка при обработке таблицы referral_history: {str(e)}")
                
            try:
                self.conn.commit()
                logger.info("Все изменения структуры базы данных успешно сохранены")
            except Exception as e:
                logger.error(f"Ошибка при фиксации изменений структуры базы данных: {str(e)}")
                self.conn.rollback()
            
            cursor.close()
            logger.info("Структура базы данных проверена и обновлена")
        
        except Exception as e:
            logger.error(f"Общая ошибка при создании таблиц: {str(e)}")
            logger.exception("Полный стек ошибки:")
    
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
            logger.debug(f"Получение данных пользователя {telegram_id} из базы данных")
            
            if not self.conn or not self.conn.is_connected():
                logger.debug(f"Соединение с БД отсутствует или закрыто, открываем новое соединение")
                self.connect()
                
            if not self.conn or not self.conn.is_connected():
                logger.error(f"Не удалось установить соединение с базой данных")
                return None
            
            cursor = self.conn.cursor(dictionary=True)
            
            logger.debug(f"Выполняем запрос к БД для получения данных пользователя {telegram_id}")
            query = "SELECT * FROM users WHERE telegram_id = %s"
            logger.debug(f"SQL запрос: {query}, параметры: ({telegram_id},)")
            
            cursor.execute(query, (telegram_id,))
            
            user = cursor.fetchone()
            cursor.close()
            
            if user:
                logger.info(f"Пользователь {telegram_id} найден в базе данных")
                logger.debug(f"Полученные данные: {user}")
            else:
                logger.warning(f"Пользователь {telegram_id} не найден в базе данных")
            
            return user
            
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
                self.connect()
            
            cursor = self.conn.cursor()
            
            # Проверяем, существует ли пользователь
            cursor.execute("SELECT telegram_id FROM users WHERE telegram_id = %s", (telegram_id,))
            if not cursor.fetchone():
                logger.error(f"Пользователь {telegram_id} не найден в базе данных")
                cursor.close()
                return False
            
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
                cursor.execute("""
                    INSERT INTO referral_codes (user_id, code)
                    VALUES (%s, %s)
                """, (telegram_id, referral_code))
            
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
            logger.error(f"Ошибка при обновлении реферального кода для {telegram_id}: {e}")
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
            logger.info(f"Проверяем, использовал ли пользователь {telegram_id} реферальную ссылку {referrer_id}")
            
            if not self.conn or not self.conn.is_connected():
                self.connect()
            
            cursor = self.conn.cursor(dictionary=True)
            
            # Проверяем наличие таблицы
            cursor.execute("SHOW TABLES LIKE 'referral_history'")
            if not cursor.fetchone():
                logger.error("Таблица referral_history не существует")
                cursor.close()
                return False
            
            # Проверяем наличие записи в истории реферралов
            cursor.execute('''
                SELECT id FROM referral_history 
                WHERE referred_id = %s AND referrer_id = %s
            ''', (telegram_id, referrer_id))
            
            result = cursor.fetchone()
            is_used = result is not None
            cursor.close()
            
            if is_used:
                logger.info(f"Пользователь {telegram_id} уже использовал реферальную ссылку от {referrer_id}")
            else:
                logger.info(f"Пользователь {telegram_id} еще не использовал реферальную ссылку от {referrer_id}")
            
            return is_used

        except Exception as e:
            logger.error(f"Ошибка при проверке использования реферальной ссылки: {e}")
            return False  # В случае ошибки считаем, что код не использовался

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