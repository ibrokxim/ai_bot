# API Документация

## Установка и запуск

1. Установите необходимые зависимости:
```bash
pip install -r api_requirements.txt
```

2. Запустите API-сервер:
```bash
python api_server.py
```

По умолчанию сервер запускается на порту 5000. Если вы хотите изменить порт, отредактируйте строку `app.run(debug=True, host='0.0.0.0', port=5000)` в файле `api_server.py`.

## Аутентификация

API использует JWT-токены для аутентификации. Чтобы получить токен, нужно отправить запрос на `/api/auth/login` с telegram_id пользователя.

### Получение токена

#### Запрос:
```
POST /api/auth/login
Content-Type: application/json

{
    "telegram_id": 123456789
}
```

#### Ответ:
```json
{
    "success": true,
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user_id": 1,
    "telegram_id": 123456789
}
```

### Использование токена

Включите полученный токен в заголовок Authorization всех запросов, требующих аутентификации:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Информация о пользователе

### Получение информации о пользователе

#### Запрос:
```
GET /api/user/info
Authorization: Bearer {token}
```

#### Ответ:
```json
{
    "success": true,
    "user": {
        "user_id": 1,
        "telegram_id": 123456789,
        "username": "user123",
        "first_name": "Имя",
        "last_name": "Фамилия",
        "requests_left": 10,
        "registration_date": "2023-04-23T12:00:00",
        "total_requests": 25,
        "total_tokens": 1500,
        "total_payments": 999.0,
        "total_referrals": 3,
        "account_level": "standard",
        "last_active": "2023-04-23T12:00:00",
        "referral_code": "abcd1234",
        "referral_url": "https://t.me/your_bot_username?start=abcd1234"
    },
    "active_plan": {
        "id": 1,
        "user_id": 1,
        "plan_id": 2,
        "activated_at": "2023-04-23T12:00:00",
        "expired_at": null,
        "is_active": true,
        "plan_name": "Стандарт",
        "requests": 200,
        "price": 999.0,
        "description": "Стандартный план с 200 запросами"
    }
}
```

## Управление запросами

### Проверка доступных запросов

#### Запрос:
```
GET /api/user/requests/check
Authorization: Bearer {token}
```

#### Ответ:
```json
{
    "success": true,
    "requests_left": 10,
    "can_make_request": true
}
```

### Использование запроса

#### Запрос:
```
POST /api/user/requests/use
Authorization: Bearer {token}
Content-Type: application/json

{
    "request_type": "text",
    "ai_model": "GPT-4",
    "tokens_used": 150,
    "request_text": "Как работает искусственный интеллект?",
    "response_length": 500,
    "response_time": 2.5
}
```

#### Ответ:
```json
{
    "success": true,
    "requests_left": 9,
    "message": "Запрос успешно использован."
}
```

### Получение истории запросов

#### Запрос:
```
GET /api/user/requests/history?limit=10&offset=0
Authorization: Bearer {token}
```

#### Ответ:
```json
{
    "success": true,
    "total": 25,
    "limit": 10,
    "offset": 0,
    "history": [
        {
            "id": 25,
            "user_id": 1,
            "request_type": "text",
            "ai_model": "GPT-4",
            "tokens_used": 150,
            "request_date": "2023-04-23T12:00:00",
            "response_time": 2.5,
            "was_successful": true,
            "request_text": "Как работает искусственный интеллект?",
            "response_length": 500
        },
        // ...остальные записи...
    ]
}
```

## Тарифные планы

### Получение списка тарифных планов

#### Запрос:
```
GET /api/plans
```

#### Ответ:
```json
{
    "success": true,
    "plans": [
        {
            "id": 1,
            "name": "Базовый",
            "requests": 50,
            "price": 299.0,
            "created_at": "2023-04-23T12:00:00",
            "is_active": true,
            "duration_days": 30,
            "description": "Базовый план с 50 запросами",
            "priority": 1,
            "is_subscription": false,
            "discount_percent": 0.0,
            "allowed_models": "GPT-3.5,DALLE",
            "max_tokens_per_request": 2000
        },
        {
            "id": 2,
            "name": "Стандарт",
            "requests": 200,
            "price": 999.0,
            "created_at": "2023-04-23T12:00:00",
            "is_active": true,
            "duration_days": 30,
            "description": "Стандартный план с 200 запросами",
            "priority": 2,
            "is_subscription": false,
            "discount_percent": 0.0,
            "allowed_models": "GPT-3.5,GPT-4,DALLE",
            "max_tokens_per_request": 4000
        },
        {
            "id": 3,
            "name": "Премиум",
            "requests": 500,
            "price": 1999.0,
            "created_at": "2023-04-23T12:00:00",
            "is_active": true,
            "duration_days": 30,
            "description": "Премиум план с 500 запросами",
            "priority": 3,
            "is_subscription": false,
            "discount_percent": 0.0,
            "allowed_models": "GPT-3.5,GPT-4,DALLE,Claude",
            "max_tokens_per_request": 8000
        }
    ]
}
```

### Получение информации о конкретном плане

#### Запрос:
```
GET /api/plans/2
```

#### Ответ:
```json
{
    "success": true,
    "plan": {
        "id": 2,
        "name": "Стандарт",
        "requests": 200,
        "price": 999.0,
        "created_at": "2023-04-23T12:00:00",
        "is_active": true,
        "duration_days": 30,
        "description": "Стандартный план с 200 запросами",
        "priority": 2,
        "is_subscription": false,
        "discount_percent": 0.0,
        "allowed_models": "GPT-3.5,GPT-4,DALLE",
        "max_tokens_per_request": 4000
    }
}
```

## Покупки и платежи

### Покупка тарифного плана

#### Запрос:
```
POST /api/payment/purchase
Authorization: Bearer {token}
Content-Type: application/json

{
    "plan_id": 2,
    "payment_details": {
        "payment_id": "payment_123456",
        "amount": 999.0,
        "payment_system": "stripe",
        "status": "completed",
        "details": {
            "card_last4": "4242",
            "payment_method": "card"
        }
    },
    "promo_code": "WELCOME20"
}
```

#### Ответ:
```json
{
    "success": true,
    "message": "Тарифный план успешно приобретен!",
    "plan_details": {
        "plan": "Стандарт",
        "price_paid": 799.2,
        "requests_added": 200,
        "expired_at": "2023-05-23T12:00:00",
        "plan_id": 2,
        "user_plan_id": 5
    },
    "requests_left": 210
}
```

## Промокоды

### Проверка валидности промокода

#### Запрос:
```
POST /api/promo/validate
Authorization: Bearer {token}
Content-Type: application/json

{
    "promo_code": "WELCOME20",
    "plan_id": 2
}
```

#### Ответ:
```json
{
    "success": true,
    "promo": {
        "id": 1,
        "code": "WELCOME20",
        "discount_type": "percent",
        "discount_value": 20.0,
        "bonus_requests": 10
    },
    "discount_amount": 199.8,
    "price_after_discount": 799.2,
    "bonus_requests": 10
}
```

## Реферальная система

### Получение статистики по реферальной программе

#### Запрос:
```
GET /api/referrals/stats
Authorization: Bearer {token}
```

#### Ответ:
```json
{
    "success": true,
    "referral_code": "abcd1234",
    "referral_url": "https://t.me/your_bot_username?start=abcd1234",
    "stats": {
        "total_referrals": 3,
        "total_bonus_requests": 15,
        "converted_referrals": 1
    },
    "referrals": [
        {
            "id": 3,
            "referred_user_id": 4,
            "username": "friend3",
            "first_name": "Друг",
            "last_name": "Третий",
            "created_at": "2023-04-23T12:00:00",
            "bonus_requests_added": 5,
            "conversion_status": "registered",
            "converted_at": null
        },
        {
            "id": 2,
            "referred_user_id": 3,
            "username": "friend2",
            "first_name": "Друг",
            "last_name": "Второй",
            "created_at": "2023-04-22T10:00:00",
            "bonus_requests_added": 5,
            "conversion_status": "registered",
            "converted_at": null
        },
        {
            "id": 1,
            "referred_user_id": 2,
            "username": "friend1",
            "first_name": "Друг",
            "last_name": "Первый",
            "created_at": "2023-04-21T09:00:00",
            "bonus_requests_added": 5,
            "conversion_status": "purchased",
            "converted_at": "2023-04-21T10:30:00"
        }
    ]
}
```

## Примеры использования в Postman

### 1. Создание коллекции

1. Откройте Postman и создайте новую коллекцию, назвав её "AI Bot API"
2. В настройках коллекции, перейдите на вкладку "Variables" и добавьте переменную:
   - `base_url`: `http://localhost:5000`
   - `token`: оставьте пустым (заполним после первого вызова)

### 2. Аутентификация

1. Создайте новый запрос "Login" в коллекции
   - Метод: POST
   - URL: `{{base_url}}/api/auth/login`
   - Body (raw JSON):
   ```json
   {
       "telegram_id": 123456789
   }
   ```
2. Отправьте запрос и из ответа скопируйте значение `token`
3. Сохраните token в переменную коллекции: правый клик на коллекции → Edit → Variables → установите значение для `token`
4. Добавьте предварительный запрос в настройках коллекции (Pre-request Script) для автоматической установки токена в заголовок:
```javascript
pm.request.headers.add({
    key: 'Authorization',
    value: 'Bearer ' + pm.variables.get('token')
});
```

### 3. Информация о пользователе

1. Создайте новый запрос "Get User Info"
   - Метод: GET
   - URL: `{{base_url}}/api/user/info`
   - Headers: Authorization уже должен подставляться автоматически
   
### 4. Проверка доступных запросов

1. Создайте новый запрос "Check Requests"
   - Метод: GET
   - URL: `{{base_url}}/api/user/requests/check`

### 5. Использование запроса

1. Создайте новый запрос "Use Request"
   - Метод: POST
   - URL: `{{base_url}}/api/user/requests/use`
   - Body (raw JSON):
   ```json
   {
       "request_type": "text",
       "ai_model": "GPT-4",
       "tokens_used": 150,
       "request_text": "Как работает искусственный интеллект?",
       "response_length": 500,
       "response_time": 2.5
   }
   ```

### 6. Получение тарифных планов

1. Создайте новый запрос "Get Plans"
   - Метод: GET
   - URL: `{{base_url}}/api/plans`

### 7. Покупка тарифного плана

1. Создайте новый запрос "Purchase Plan"
   - Метод: POST
   - URL: `{{base_url}}/api/payment/purchase`
   - Body (raw JSON):
   ```json
   {
       "plan_id": 2,
       "payment_details": {
           "payment_id": "payment_123456",
           "amount": 999.0,
           "payment_system": "stripe",
           "status": "completed",
           "details": {
               "card_last4": "4242",
               "payment_method": "card"
           }
       },
       "promo_code": "WELCOME20"
   }
   ```

### 8. Проверка промокода

1. Создайте новый запрос "Validate Promo"
   - Метод: POST
   - URL: `{{base_url}}/api/promo/validate`
   - Body (raw JSON):
   ```json
   {
       "promo_code": "WELCOME20",
       "plan_id": 2
   }
   ```

### 9. Получение статистики рефералов

1. Создайте новый запрос "Referral Stats"
   - Метод: GET
   - URL: `{{base_url}}/api/referrals/stats`

### 10. Получение истории запросов

1. Создайте новый запрос "Request History"
   - Метод: GET
   - URL: `{{base_url}}/api/user/requests/history?limit=10&offset=0` 