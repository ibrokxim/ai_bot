import sqlite3
import datetime
import os
from dotenv import load_dotenv
from app.config import DATABASE_NAME

# Загрузка переменных окружения
load_dotenv()

# Получение имени базы данных из переменных окружения или использование значения по умолчанию
DATABASE_NAME = os.getenv('SQLITE_DATABASE_NAME', 'app/database/bot.db')

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_bot BOOLEAN,
            language_code TEXT,
            phone_number TEXT,
            registration_date TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_user_data(user_id: int, username: str, first_name: str, last_name: str, 
                  is_bot: bool, language_code: str, phone_number: str = None):
    """Сохранение данных пользователя в базу"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name, is_bot, language_code, 
         phone_number, registration_date) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, is_bot, language_code, 
          phone_number, datetime.datetime.now()))
    conn.commit()
    conn.close()

def update_user_phone(user_id: int, phone_number: str):
    """Обновление номера телефона пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET phone_number = ? 
        WHERE user_id = ?
    ''', (phone_number, user_id))
    conn.commit()
    conn.close()

def get_user(user_id: int):
    """Получение данных пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user 