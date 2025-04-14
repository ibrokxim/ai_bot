import mysql.connector
from mysql.connector import Error
import os

def create_tables():
    """Создает необходимые таблицы в базе данных"""
    config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'root'),
        'database': os.getenv('DB_NAME', 'ai_bot')
    }
    
    try:
        # Создаем соединение с базой данных
        conn = mysql.connector.connect(**config)
        if conn is None:
            print("Ошибка при подключении к базе данных")
            return
        
        cursor = conn.cursor()
        
        # Таблица реферальных ссылок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                referral_code VARCHAR(255) UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        print("Таблица referrals создана или уже существует")
        
        # Таблица тарифных планов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                requests INT,
                price DECIMAL(10, 2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("Таблица plans создана или уже существует")
        
        # Таблица связи пользователей с тарифными планами
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_plans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                plan_id INT,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expired_at TIMESTAMP NULL,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
            )
        ''')
        print("Таблица user_plans создана или уже существует")
        
        # Добавляем базовые тарифные планы, если они еще не существуют
        cursor.execute("SELECT COUNT(*) FROM plans")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO plans (name, requests, price) VALUES 
                ('Базовый', 50, 299.00),
                ('Стандарт', 200, 999.00),
                ('Премиум', 500, 1999.00)
            ''')
            print("Базовые тарифные планы добавлены")
        else:
            print("Тарифные планы уже существуют")
        
        conn.commit()
    except Error as e:
        print(f"Ошибка при создании таблиц: {e}")
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
        
    create_tables() 