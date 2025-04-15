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

def alter_users_table():
    """Добавляет столбец requests_left в таблицу users"""
    try:
        # Установка соединения
        conn = mysql.connector.connect(**config)
        
        if conn.is_connected():
            cursor = conn.cursor()
            
            # Проверяем, существует ли уже столбец requests_left
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE 
                    TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'users' 
                    AND COLUMN_NAME = 'requests_left'
            """, (config['database'],))
            
            if cursor.fetchone()[0] == 0:
                # Столбец не существует, добавляем его
                cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN requests_left INT DEFAULT 10
                """)
                print("Столбец requests_left успешно добавлен в таблицу users")
            else:
                print("Столбец requests_left уже существует в таблице users")
            
            conn.commit()
    except Error as e:
        print(f"Ошибка при изменении таблицы: {e}")
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