import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройки приложения
SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
JWT_EXPIRATION_TIME = int(os.getenv('JWT_EXPIRATION_TIME', 3600))  # время в секундах

# Настройки базы данных
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'db': os.getenv('DB_NAME'),
    'charset': 'utf8mb4',
}

# Настройки API
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 5000))
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')

def get_db_config() -> dict[str, str]:
    """
    Получает конфигурацию базы данных из переменных окружения
    """
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', 'root'),
        'database': os.getenv('DB_NAME', 'ai_bot')
    }

def get_bot_token() -> str:
    """
    Получает токен бота из переменных окружения
    """
    return os.getenv('BOT_TOKEN', '') 