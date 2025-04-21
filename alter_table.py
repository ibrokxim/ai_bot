import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Параметры подключения
config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'ai_bot'),
    'charset': os.getenv('DB_CHARSET', 'utf8mb4')
}

def create_referrals_table():
    """Создает таблицу referrals если она не существует"""
    try:
        conn = mysql.connector.connect(**config)
        if conn.is_connected():
            cursor = conn.cursor()
            
            # Удаляем старую таблицу если она существует
            cursor.execute("DROP TABLE IF EXISTS referrals")
            
            # Создаем таблицу referrals с правильным внешним ключом
            cursor.execute("""
                CREATE TABLE referrals (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    referral_code VARCHAR(50) UNIQUE NOT NULL,
                    total_uses INT DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP NULL,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("Таблица referrals успешно создана")
            
    except Error as e:
        logger.error(f"Ошибка при создании таблицы referrals: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def alter_users_table():
    """Обновляет структуру таблицы users"""
    try:
        conn = mysql.connector.connect(**config)
        
        if conn.is_connected():
            cursor = conn.cursor()
            
            # Проверяем и добавляем столбец requests_left
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE 
                    TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'users' 
                    AND COLUMN_NAME = 'requests_left'
            """, (config['database'],))
            
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN requests_left INT DEFAULT 10
                """)
                logger.info("Столбец requests_left успешно добавлен в таблицу users")
            
            # Обновляем registration_date
            cursor.execute("""
                ALTER TABLE users 
                MODIFY COLUMN registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            logger.info("Столбец registration_date обновлен")
            
            # Добавляем значение по умолчанию для is_active
            cursor.execute("""
                ALTER TABLE users 
                MODIFY COLUMN is_active BOOLEAN DEFAULT TRUE
            """)
            logger.info("Добавлено значение по умолчанию для is_active")
            
            # Создаем таблицу users если она не существует
            cursor.execute("""
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
                    requests_left INT DEFAULT 10,
                    is_active BOOLEAN DEFAULT TRUE,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            conn.commit()
            logger.info("Структура таблицы users успешно обновлена")
            
    except Error as e:
        logger.error(f"Ошибка при изменении таблицы users: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    # Получение параметров подключения из командной строки, если они предоставлены
    import sys
    
    if len(sys.argv) >= 5:
        os.environ['DB_HOST'] = sys.argv[1]
        os.environ['DB_USER'] = sys.argv[2]
        os.environ['DB_PASSWORD'] = sys.argv[3]
        os.environ['DB_NAME'] = sys.argv[4]
    
    alter_users_table()
    create_referrals_table() 