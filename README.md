# Документация по API ChatBot

## Структура API

API построено с использованием Flask и организовано по следующей структуре:

```
app/
└── api/
    ├── __init__.py           # Инициализация API и регистрация блюпринтов
    ├── app.py                # Основное приложение Flask
    ├── middleware/           # Промежуточное ПО (middleware)
    │   ├── __init__.py
    │   └── auth.py           # Аутентификация через JWT
    └── routes/               # Маршруты API
        ├── __init__.py
        ├── auth.py           # Авторизация и регистрация
        ├── plans.py          # Планы подписки
        ├── requests.py       # Управление запросами
        └── users.py          # Управление пользователями
```

## Доступные эндпоинты

### Аутентификация

- `POST /api/login` - Авторизация пользователя
- `POST /api/register` - Регистрация нового пользователя

### Пользователи

- `GET /api/users/profile` - Получение профиля пользователя
- `POST /api/users/update-phone` - Обновление номера телефона
- `GET /api/users/stats` - Получение статистики пользователя

### Планы подписки

- `GET /api/plans` - Получение всех доступных планов
- `GET /api/plans/<plan_id>` - Получение информации о конкретном плане
- `POST /api/plans/subscribe` - Подписка на план

### Запросы

- `GET /api/requests/check` - Проверка доступных запросов
- `POST /api/requests/use` - Использование запроса
- `GET /api/requests/history` - Получение истории запросов

## Настройки окружения

Для работы API необходимо настроить следующие переменные окружения в файле `.env`:

```
# Настройки бота
BOT_TOKEN=ваш_токен_от_botfather

# URL мини-приложения
MINI_APP_URL=https://example.com

# Настройки базы данных
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=ваш_пароль
DB_NAME=bot_db

# Настройки API
API_HOST=0.0.0.0
API_PORT=5000
DEBUG=True

# Настройки JWT
SECRET_KEY=ваш_секретный_ключ_для_jwt
JWT_EXPIRATION_TIME=3600
```

## Запуск API

```bash
python -m app.api.app
``` 