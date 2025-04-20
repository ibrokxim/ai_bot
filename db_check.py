#!/usr/bin/env python3
"""
Скрипт для проверки и восстановления базы данных.
Используется для диагностики проблем с реферальной системой.
"""

import logging
import sys
import random
import string
from dotenv import load_dotenv

from database import Database
from config import DB_CONFIG

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('db_check.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('db_check')

def check_tables(db):
    """Проверка существования необходимых таблиц"""
    logger.info("Проверка существования таблиц...")
    
    try:
        cursor = db.conn.cursor()
        
        # Проверка таблицы users
        cursor.execute("SHOW TABLES LIKE 'users'")
        users_exists = cursor.fetchone() is not None
        logger.info(f"Таблица users: {'существует' if users_exists else 'не существует'}")
        
        # Проверка таблицы referral_codes
        cursor.execute("SHOW TABLES LIKE 'referral_codes'")
        ref_codes_exists = cursor.fetchone() is not None
        logger.info(f"Таблица referral_codes: {'существует' if ref_codes_exists else 'не существует'}")
        
        # Проверка таблицы referral_history
        cursor.execute("SHOW TABLES LIKE 'referral_history'")
        ref_history_exists = cursor.fetchone() is not None
        logger.info(f"Таблица referral_history: {'существует' if ref_history_exists else 'не существует'}")
        
        cursor.close()
        
        return {
            'users': users_exists,
            'referral_codes': ref_codes_exists,
            'referral_history': ref_history_exists
        }
        
    except Exception as e:
        logger.error(f"Ошибка при проверке таблиц: {str(e)}")
        return None

def check_users_referral_codes(db):
    """Проверка наличия реферальных кодов у пользователей"""
    logger.info("Проверка реферальных кодов пользователей...")
    
    try:
        cursor = db.conn.cursor(dictionary=True)
        
        # Получаем всех пользователей
        cursor.execute("SELECT telegram_id FROM users")
        users = cursor.fetchall()
        
        if not users:
            logger.warning("Пользователи не найдены в базе данных")
            cursor.close()
            return
        
        logger.info(f"Найдено {len(users)} пользователей")
        
        # Проверяем реферальные коды для каждого пользователя
        users_without_code = []
        
        for user in users:
            telegram_id = user['telegram_id']
            
            # Проверяем наличие реферального кода
            cursor.execute("SELECT code FROM referral_codes WHERE user_id = %s", (telegram_id,))
            ref_code = cursor.fetchone()
            
            if not ref_code:
                logger.warning(f"Пользователь {telegram_id} не имеет реферального кода")
                users_without_code.append(telegram_id)
        
        cursor.close()
        
        # Исправляем отсутствующие реферальные коды
        if users_without_code:
            logger.info(f"Найдено {len(users_without_code)} пользователей без реферальных кодов")
            fixed_count = 0
            
            for user_id in users_without_code:
                # Генерируем новый реферальный код
                new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                
                # Сохраняем новый код
                result = db.update_user_referral_code(user_id, new_code)
                
                if result:
                    fixed_count += 1
                    logger.info(f"Создан новый реферальный код {new_code} для пользователя {user_id}")
                else:
                    logger.error(f"Не удалось создать реферальный код для пользователя {user_id}")
            
            logger.info(f"Исправлено {fixed_count} из {len(users_without_code)} отсутствующих реферальных кодов")
        else:
            logger.info("Все пользователи имеют реферальные коды")
    
    except Exception as e:
        logger.error(f"Ошибка при проверке реферальных кодов: {str(e)}")

def main():
    """Основная функция для проверки и восстановления базы данных"""
    logger.info("Начало проверки базы данных")
    
    # Создаем подключение к базе данных
    try:
        db = Database(DB_CONFIG)
        logger.info("Подключение к базе данных установлено")
    except Exception as e:
        logger.error(f"Ошибка при подключении к базе данных: {str(e)}")
        return
    
    # Проверяем наличие необходимых таблиц
    tables = check_tables(db)
    
    if not tables:
        logger.error("Не удалось проверить таблицы")
        return
    
    # Если какая-то из таблиц отсутствует, запускаем создание таблиц
    if not all(tables.values()):
        logger.warning("Некоторые таблицы отсутствуют, запускаем создание")
        try:
            db._create_tables()
            logger.info("Таблицы успешно созданы")
            
            # Проверяем, что таблицы действительно созданы
            new_tables = check_tables(db)
            if not new_tables or not all(new_tables.values()):
                logger.error("Не удалось создать все необходимые таблицы")
                return
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {str(e)}")
            return
    
    # Проверяем наличие реферальных кодов у пользователей
    check_users_referral_codes(db)
    
    # Закрываем соединение с базой данных
    try:
        db.close()
        logger.info("Соединение с базой данных закрыто")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединения с базой данных: {str(e)}")
    
    logger.info("Проверка и восстановление базы данных завершены")

if __name__ == "__main__":
    main() 