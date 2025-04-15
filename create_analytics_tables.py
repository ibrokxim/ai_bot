import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

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

def create_analytics_tables():
    """Создает необходимые таблицы для аналитики в базе данных"""
    try:
        # Установка соединения
        conn = mysql.connector.connect(**config)
        
        if conn.is_connected():
            cursor = conn.cursor()
            
            # 1. Добавляем поля в таблицу user_plans
            cursor.execute("""
                ALTER TABLE user_plans 
                ADD COLUMN IF NOT EXISTS payment_id VARCHAR(255) NULL,
                ADD COLUMN IF NOT EXISTS price_paid DECIMAL(10, 2) NULL,
                ADD COLUMN IF NOT EXISTS is_auto_renewal BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS source VARCHAR(50) NULL,
                ADD COLUMN IF NOT EXISTS requests_added INT DEFAULT 0,
                ADD COLUMN IF NOT EXISTS discount_applied DECIMAL(5, 2) DEFAULT 0,
                ADD COLUMN IF NOT EXISTS notes TEXT NULL
            """)
            print("Поля добавлены в таблицу user_plans")
            
            # 2. Добавляем поля в таблицу plans
            cursor.execute("""
                ALTER TABLE plans 
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS duration_days INT DEFAULT 0,
                ADD COLUMN IF NOT EXISTS description TEXT NULL,
                ADD COLUMN IF NOT EXISTS priority INT DEFAULT 0,
                ADD COLUMN IF NOT EXISTS is_subscription BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS discount_percent DECIMAL(5, 2) DEFAULT 0,
                ADD COLUMN IF NOT EXISTS allowed_models VARCHAR(255) NULL,
                ADD COLUMN IF NOT EXISTS max_tokens_per_request INT NULL,
                ADD COLUMN IF NOT EXISTS features JSON NULL
            """)
            print("Поля добавлены в таблицу plans")
            
            # 3. Создаем таблицу payments
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    user_plan_id INT NULL,
                    amount DECIMAL(10, 2),
                    currency VARCHAR(10) DEFAULT 'RUB',
                    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    payment_system VARCHAR(50),
                    payment_id VARCHAR(255),
                    status VARCHAR(50),
                    details JSON NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_plan_id) REFERENCES user_plans(id) ON DELETE SET NULL
                )
            """)
            print("Таблица payments создана")
            
            # 4. Создаем таблицу request_usage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS request_usage (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    request_type VARCHAR(50),
                    ai_model VARCHAR(100),
                    tokens_used INT DEFAULT 0,
                    request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    response_time FLOAT NULL,
                    was_successful BOOLEAN DEFAULT TRUE,
                    request_text TEXT NULL,
                    response_length INT DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            print("Таблица request_usage создана")
            
            # 5. Создаем таблицу user_statistics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_statistics (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT UNIQUE,
                    total_requests INT DEFAULT 0,
                    total_tokens INT DEFAULT 0,
                    last_active TIMESTAMP NULL,
                    total_payments DECIMAL(10, 2) DEFAULT 0,
                    total_referrals INT DEFAULT 0,
                    favorite_model VARCHAR(100) NULL,
                    account_level VARCHAR(50) DEFAULT 'standard',
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            print("Таблица user_statistics создана")
            
            # 6. Создаем таблицу referral_history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    referrer_id INT,
                    referred_user_id INT,
                    referral_code VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bonus_requests_added INT DEFAULT 0,
                    conversion_status VARCHAR(50) DEFAULT 'registered',
                    converted_at TIMESTAMP NULL,
                    FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (referred_user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            print("Таблица referral_history создана")
            
            # 7. Создаем таблицу promo_codes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    code VARCHAR(50) UNIQUE,
                    discount_type VARCHAR(20),
                    discount_value DECIMAL(10, 2),
                    bonus_requests INT DEFAULT 0,
                    valid_from TIMESTAMP,
                    valid_to TIMESTAMP NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    max_usages INT DEFAULT 0,
                    usages_count INT DEFAULT 0,
                    allowed_plans VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("Таблица promo_codes создана")
            
            # 8. Создаем таблицу promo_code_usages для отслеживания использования промокодов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS promo_code_usages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    promo_code_id INT,
                    user_id INT,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_to_plan_id INT NULL,
                    discount_amount DECIMAL(10, 2) DEFAULT 0,
                    requests_added INT DEFAULT 0,
                    FOREIGN KEY (promo_code_id) REFERENCES promo_codes(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (applied_to_plan_id) REFERENCES plans(id) ON DELETE SET NULL
                )
            """)
            print("Таблица promo_code_usages создана")
            
            conn.commit()
    except Error as e:
        print(f"Ошибка при создании таблиц для аналитики: {e}")
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
    
    create_analytics_tables() 