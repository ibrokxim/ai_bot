# AI Bot - Телеграм бот с OpenAI API

Этот проект представляет собой Telegram бота с интеграцией API OpenAI, управлением запросами пользователей, системой планов подписки и реферальной программой.

## Структура проекта

- `admin_panel/` - Основное Django приложение
- `api/` - API для взаимодействия с фронтендом и ботом
- `bot_admin/` - Модели и админка Django
- `app/` - Основная логика телеграм бота

## Требования

- Python 3.10+ (3.12 рекомендуется)
- MySQL 5.7+ или MariaDB 10.3+
- Доступ к API OpenAI
- Токен Telegram Bot API

## Установка и настройка

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/ai_bot.git
cd ai_bot
```

### 2. Настройка проекта

#### На Linux/macOS:

```bash
# Дать права на выполнение скрипту
chmod +x server_setup.sh

# Запустить скрипт настройки
./server_setup.sh
```

#### На Windows:

```cmd
# Запустить скрипт настройки
setup_server.bat
```

### 3. Настройка .env файла

Скопируйте `.env.example` в `.env` и установите все необходимые переменные окружения:

```
# Основные настройки
BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key

# База данных
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=ai_bot
```

### 4. Запуск сервера разработки

```bash
# Активация виртуального окружения
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Запуск сервера разработки
python manage.py runserver
```

### 5. Запуск в продакшн

Для запуска в продакшн используйте Gunicorn:

```bash
gunicorn -c gunicorn_config.py admin_panel.wsgi:application
```

Или установите и активируйте systemd сервис (Linux):

```bash
sudo systemctl start ai_bot
sudo systemctl enable ai_bot
```

## Структура API

Основные эндпоинты API:

- `/api/register/` - Регистрация пользователя
- `/api/login/` - Авторизация пользователя
- `/api/user/info/` - Информация о пользователе
- `/api/plans/` - Список доступных планов подписки
- `/api/requests/check/` - Проверка доступных запросов
- `/api/requests/use/` - Использование запроса

Полная документация доступна в Django Admin панели по адресу `/admin/api/documentation/`.

## Разработка

### Миграции базы данных

```bash
python manage.py makemigrations
python manage.py migrate
```

### Создание суперпользователя

```bash
python manage.py createsuperuser
```

## Лицензия

Проект распространяется под лицензией MIT. 