# Документация по API для Telegram Chat Bot

## Структура API

API построено с использованием Django REST Framework и организовано по следующей структуре:

```
api/
├── __init__.py            # Инициализация API
├── apps.py                # Конфигурация приложения Django
├── authentication.py      # Классы для аутентификации (JWT)
├── permissions.py         # Классы разрешений доступа
├── serializers.py         # Сериализаторы для моделей
├── urls.py                # URL маршруты API
└── views.py               # Контроллеры API
```

## Доступные эндпоинты

### Аутентификация

- `POST /api/auth/register/` - Регистрация нового пользователя
- `POST /api/auth/login/` - Авторизация пользователя
- `POST /api-token-auth/` - Получение токена авторизации (Django REST Framework)

### Пользователи

- `GET /api/me/` - Получение информации о текущем пользователе
- `GET /api/me/history/` - Получение истории запросов пользователя

### Планы подписки

- `GET /api/plans/` - Получение списка всех тарифных планов
- `GET /api/plans/<id>/` - Получение информации о конкретном плане
- `GET /api/user-plans/` - Получение планов пользователя

### Запросы

- `GET /api/check-requests/` - Проверка доступных запросов
- `POST /api/use-request/` - Использование запроса
- `GET /api/requests/` - Получение истории запросов

### Промокоды

- `POST /api/validate-promo/` - Проверка валидности промокода

### Реферальная система

- `GET /api/referrals/` - Получение информации о приглашенных пользователях

### Прямой доступ по Telegram ID (без JWT)

- `GET /api/telegram/requests/?telegram_id=123456789` - Проверка количества запросов пользователя по telegram_id

## Аутентификация

API поддерживает два способа аутентификации:

### 1. JWT токены

Используйте JWT токены для авторизации через заголовок Authorization. Пример запроса:

```
GET /api/me/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. Telegram ID

Для упрощения интеграции с ботом, API поддерживает аутентификацию по Telegram ID. Вы можете использовать параметр `telegram_id` в запросе:

```
GET /api/check-requests/?telegram_id=123456789
```

Или использовать специальный эндпоинт без аутентификации:

```
GET /api/telegram/requests/?telegram_id=123456789
```

## Модели данных

API использует модели из приложения `bot_admin`:

- `BotUser` - Пользователи бота
- `Plan` - Тарифные планы
- `UserPlan` - Подписки пользователей на планы
- `RequestUsage` - Использование запросов
- `UserStatistics` - Статистика пользователей
- `PromoCode` - Промокоды
- `Payment` - Платежи
- `ReferralHistory` - История реферальной системы

## Примеры запросов

### Регистрация пользователя

```
POST /api/auth/register/

{
  "telegram_id": 123456789,
  "username": "username",
  "first_name": "Имя",
  "last_name": "Фамилия",
  "chat_id": 123456789,
  "referral_code": "abc123"
}
```

### Авторизация и получение токена

```
POST /api/auth/login/

{
  "telegram_id": 123456789
}
```

### Использование запроса

```
POST /api/use-request/

{
  "request_type": "text",
  "ai_model": "gpt-3.5-turbo",
  "tokens_used": 1500,
  "request_text": "Пример запроса",
  "response_length": 500,
  "response_time": 2.5,
  "was_successful": true
}
```

### Проверка запросов по Telegram ID

```
GET /api/telegram/requests/?telegram_id=123456789
```

Ответ:
```json
{
  "success": true,
  "telegram_id": 123456789,
  "username": "username",
  "first_name": "Имя",
  "requests_left": 10,
  "can_make_request": true
}
``` 