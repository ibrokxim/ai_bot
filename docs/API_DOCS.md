# окументация API для бота
# Р”РѕРєСѓРјРµРЅС‚Р°С†РёСЏ API РґР»СЏ Р±РѕС‚Р°

## РћР±С‰Р°СЏ РёРЅС„РѕСЂРјР°С†РёСЏ

API РїРѕСЃС‚СЂРѕРµРЅРѕ РЅР° Django REST Framework Рё РїСЂРµРґРѕСЃС‚Р°РІР»СЏРµС‚ РІРѕР·РјРѕР¶РЅРѕСЃС‚СЊ РІР·Р°РёРјРѕРґРµР№СЃС‚РІРёСЏ СЃ Р±РѕС‚РѕРј С‡РµСЂРµР· HTTP Р·Р°РїСЂРѕСЃС‹.
Р’СЃРµ Р·Р°РїСЂРѕСЃС‹ Рє API РІРѕР·РІСЂР°С‰Р°СЋС‚ РґР°РЅРЅС‹Рµ РІ С„РѕСЂРјР°С‚Рµ JSON СЃ РєР»СЋС‡РѕРј `success`, СѓРєР°Р·С‹РІР°СЋС‰РёРј РЅР° СѓСЃРїРµС€РЅРѕСЃС‚СЊ РІС‹РїРѕР»РЅРµРЅРёСЏ РѕРїРµСЂР°С†РёРё.

## РђСѓС‚РµРЅС‚РёС„РёРєР°С†РёСЏ

Р’ API РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РґРІР° СЃРїРѕСЃРѕР±Р° Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёРё:

1. **TelegramIDAuthentication** - Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёСЏ РїРѕ Telegram ID, РїРµСЂРµРґР°РІР°РµРјРѕРј РІ Р·Р°РіРѕР»РѕРІРєРµ `X-Telegram-ID`. РСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РґР»СЏ Р·Р°С‰РёС‰РµРЅРЅС‹С… СЌРЅРґРїРѕРёРЅС‚РѕРІ.
2. **РџСЂСЏРјРѕР№ РґРѕСЃС‚СѓРї** - РґР»СЏ РЅРµРєРѕС‚РѕСЂС‹С… СЌРЅРґРїРѕРёРЅС‚РѕРІ РґРѕСЃС‚СѓРїРµРЅ РїСЂСЏРјРѕР№ РґРѕСЃС‚СѓРї Р±РµР· Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёРё, РЅРѕ СЃ РїРµСЂРµРґР°С‡РµР№ `telegram_id` РІ РїР°СЂР°РјРµС‚СЂР°С… Р·Р°РїСЂРѕСЃР°.

## РћСЃРЅРѕРІРЅС‹Рµ СЌРЅРґРїРѕРёРЅС‚С‹

### Р РµРіРёСЃС‚СЂР°С†РёСЏ Рё Р°РІС‚РѕСЂРёР·Р°С†РёСЏ

#### POST /api/auth/register/
Р РµРіРёСЃС‚СЂР°С†РёСЏ РЅРѕРІРѕРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ

Р—Р°РїСЂРѕСЃ:
```json
{
    "telegram_id": 123456789,
    "username": "username",
    "first_name": "РРјСЏ",
    "last_name": "Р¤Р°РјРёР»РёСЏ",
    "language_code": "ru",
    "chat_id": 123456789,
    "contact": "+79001234567",
    "referral_code": "CODE123" // РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ
}
```

РЈСЃРїРµС€РЅС‹Р№ РѕС‚РІРµС‚:
```json
{
    "success": true,
    "message": "РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ СѓСЃРїРµС€РЅРѕ Р·Р°СЂРµРіРёСЃС‚СЂРёСЂРѕРІР°РЅ",
    "user_id": 1,
    "telegram_id": 123456789,
    "requests_left": 10
}
```

#### POST /api/auth/login/
РђРІС‚РѕСЂРёР·Р°С†РёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ

Р—Р°РїСЂРѕСЃ:
```json
{
    "telegram_id": 123456789
}
```

РЈСЃРїРµС€РЅС‹Р№ РѕС‚РІРµС‚:
```json
{
    "success": true,
    "user_id": 1,
    "telegram_id": 123456789,
    "username": "username",
    "requests_left": 5
}
```

### Р—Р°РїСЂРѕСЃС‹ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ

#### GET /api/check-requests/
РџСЂРѕРІРµСЂРєР° РґРѕСЃС‚СѓРїРЅС‹С… Р·Р°РїСЂРѕСЃРѕРІ (С‚СЂРµР±СѓРµС‚СЃСЏ Р·Р°РіРѕР»РѕРІРѕРє X-Telegram-ID)

РЈСЃРїРµС€РЅС‹Р№ РѕС‚РІРµС‚:
```json
{
    "success": true,
    "requests_left": 5,
    "can_make_request": true
}
```

#### POST /api/use-request/
РСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ Р·Р°РїСЂРѕСЃР° (С‚СЂРµР±СѓРµС‚СЃСЏ Р·Р°РіРѕР»РѕРІРѕРє X-Telegram-ID)

Р—Р°РїСЂРѕСЃ:
```json
{
    "request_type": "text",
    "ai_model": "gpt-3.5-turbo",
    "tokens_used": 150,
    "request_text": "РџСЂРёРІРµС‚, РєР°Рє РґРµР»Р°?",
    "response_length": 100,
    "response_time": 1.5,
    "was_successful": true
}
```

РЈСЃРїРµС€РЅС‹Р№ РѕС‚РІРµС‚:
```json
{
    "success": true,
    "requests_left": 4,
    "message": "Р—Р°РїСЂРѕСЃ СѓСЃРїРµС€РЅРѕ РёСЃРїРѕР»СЊР·РѕРІР°РЅ"
}
```

### РџСЂРѕРјРѕРєРѕРґС‹

#### POST /api/validate-promo/
РџСЂРѕРІРµСЂРєР° РІР°Р»РёРґРЅРѕСЃС‚Рё РїСЂРѕРјРѕРєРѕРґР° (С‚СЂРµР±СѓРµС‚СЃСЏ Р·Р°РіРѕР»РѕРІРѕРє X-Telegram-ID)

Р—Р°РїСЂРѕСЃ:
```json
{
    "code": "PROMO2023",
    "plan_id": 1 // РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ
}
```

РЈСЃРїРµС€РЅС‹Р№ РѕС‚РІРµС‚:
```json
{
    "success": true,
    "promo": {
        "id": 1,
        "code": "PROMO2023",
        "discount_type": "percent",
        "discount_value": 10.0,
        "bonus_requests": 5
    },
    "discount_amount": 100.0,
    "price_after_discount": 900.0
}
```

### РРЅС„РѕСЂРјР°С†РёСЏ Рѕ РїРѕР»СЊР·РѕРІР°С‚РµР»Рµ

#### GET /api/me/
РџРѕР»СѓС‡РµРЅРёРµ РёРЅС„РѕСЂРјР°С†РёРё Рѕ С‚РµРєСѓС‰РµРј РїРѕР»СЊР·РѕРІР°С‚РµР»Рµ (С‚СЂРµР±СѓРµС‚СЃСЏ Р·Р°РіРѕР»РѕРІРѕРє X-Telegram-ID)

РЈСЃРїРµС€РЅС‹Р№ РѕС‚РІРµС‚:
```json
{
    "success": true,
    "user": {
        "user_id": 1,
        "telegram_id": 123456789,
        "username": "username",
        "first_name": "РРјСЏ",
        "last_name": "Р¤Р°РјРёР»РёСЏ",
        "language_code": "ru",
        "contact": "+79001234567",
        "is_active": true,
        "requests_left": 4,
        "registration_date": "2023-01-01T12:00:00Z"
    },
    "active_plan": {
        "id": 1,
        "user": 1,
        "plan": 2,
        "plan_details": {
            "id": 2,
            "name": "РџСЂРµРјРёСѓРј",
            "requests": 100,
            "price": 1000.00,
            "created_at": "2023-01-01T00:00:00Z",
            "is_active": true,
            "duration_days": 30,
            "description": "РџСЂРµРјРёСѓРј РїР»Р°РЅ",
            "priority": 10,
            "is_subscription": true,
            "discount_percent": 0.00,
            "allowed_models": "gpt-3.5-turbo,gpt-4",
            "max_tokens_per_request": 4000,
            "features": {
                "priority_support": true,
                "voice_messages": true
            }
        },
        "activated_at": "2023-01-01T12:30:00Z",
        "expired_at": "2023-01-31T12:30:00Z",
        "is_active": true,
        "price_paid": 900.00,
        "is_auto_renewal": false,
        "requests_added": 100
    },
    "statistics": {
        "id": 1,
        "user": 1,
        "total_requests": 10,
        "total_tokens": 1500,
        "last_active": "2023-01-05T15:30:00Z",
        "total_payments": 900.00,
        "total_referrals": 2,
        "favorite_model": "gpt-3.5-turbo",
        "account_level": "premium"
    }
}
```

#### GET /api/me/history/
РџРѕР»СѓС‡РµРЅРёРµ РёСЃС‚РѕСЂРёРё Р·Р°РїСЂРѕСЃРѕРІ (С‚СЂРµР±СѓРµС‚СЃСЏ Р·Р°РіРѕР»РѕРІРѕРє X-Telegram-ID)

РџР°СЂР°РјРµС‚СЂС‹:
- `page` - РЅРѕРјРµСЂ СЃС‚СЂР°РЅРёС†С‹ (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 1)
- `per_page` - РєРѕР»РёС‡РµСЃС‚РІРѕ Р·Р°РїРёСЃРµР№ РЅР° СЃС‚СЂР°РЅРёС†Рµ (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 20)

РЈСЃРїРµС€РЅС‹Р№ РѕС‚РІРµС‚:
```json
{
    "success": true,
    "history": [
        {
            "id": 10,
            "user": 1,
            "request_type": "text",
            "ai_model": "gpt-3.5-turbo",
            "tokens_used": 150,
            "request_date": "2023-01-05T15:30:00Z",
            "response_time": 1.5,
            "was_successful": true,
            "request_text": "РџСЂРёРІРµС‚, РєР°Рє РґРµР»Р°?",
            "response_length": 100
        },
        // ...
    ],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 10,
        "total_pages": 1
    }
}
```

### Р РµС„РµСЂР°Р»С‹

#### GET /api/referrals/
РџРѕР»СѓС‡РµРЅРёРµ РёРЅС„РѕСЂРјР°С†РёРё Рѕ СЂРµС„РµСЂР°Р»Р°С… (С‚СЂРµР±СѓРµС‚СЃСЏ Р·Р°РіРѕР»РѕРІРѕРє X-Telegram-ID)

РЈСЃРїРµС€РЅС‹Р№ РѕС‚РІРµС‚:
```json
{
    "success": true,
    "referrals": [
        {
            "user_id": 2,
            "username": "referral1",
            "first_name": "РРјСЏ",
            "last_name": "Р¤Р°РјРёР»РёСЏ",
            "created_at": "2023-01-02T10:00:00Z",
            "bonus_requests_added": 5,
            "conversion_status": "purchased"
        },
        // ...
    ],
    "total_count": 2,
    "total_earnings": 45.0
}
```

### РџСЂСЏРјРѕР№ РґРѕСЃС‚СѓРї Р±РµР· Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёРё

#### GET /api/telegram/requests/?telegram_id=123456789
РџСЂРѕРІРµСЂРєР° РґРѕСЃС‚СѓРїРЅС‹С… Р·Р°РїСЂРѕСЃРѕРІ РїРѕ telegram_id (РЅРµ С‚СЂРµР±СѓРµС‚ Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёРё)

РЈСЃРїРµС€РЅС‹Р№ РѕС‚РІРµС‚:
```json
{
    "success": true,
    "telegram_id": 123456789,
    "requests_left": 4,
    "can_make_request": true
}
```

#### POST /api/telegram/use-request/
РСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ Р·Р°РїСЂРѕСЃР° РїРѕ telegram_id (РЅРµ С‚СЂРµР±СѓРµС‚ Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёРё)

Р—Р°РїСЂРѕСЃ:
```json
{
    "telegram_id": 123456789,
    "request_type": "text",
    "ai_model": "gpt-3.5-turbo",
    "tokens_used": 150,
    "request_text": "РџСЂРёРІРµС‚, РєР°Рє РґРµР»Р°?",
    "response_length": 100,
    "response_time": 1.5,
    "was_successful": true
}
```

РЈСЃРїРµС€РЅС‹Р№ РѕС‚РІРµС‚:
```json
{
    "success": true,
    "requests_left": 3,
    "message": "Р—Р°РїСЂРѕСЃ СѓСЃРїРµС€РЅРѕ РёСЃРїРѕР»СЊР·РѕРІР°РЅ"
}
```

#### GET /api/telegram/user-info/?telegram_id=123456789
РџРѕР»СѓС‡РµРЅРёРµ РёРЅС„РѕСЂРјР°С†РёРё Рѕ РїРѕР»СЊР·РѕРІР°С‚РµР»Рµ РїРѕ telegram_id (РЅРµ С‚СЂРµР±СѓРµС‚ Р°СѓС‚РµРЅС‚РёС„РёРєР°С†РёРё)

РЈСЃРїРµС€РЅС‹Р№ РѕС‚РІРµС‚:
```json
{
    "success": true,
    "user": {
        "user_id": 1,
        "telegram_id": 123456789,
        "username": "username",
        "first_name": "РРјСЏ",
        "last_name": "Р¤Р°РјРёР»РёСЏ",
        "requests_left": 3,
        "registration_date": "2023-01-01T12:00:00Z"
    },
    "active_plan": {
        "id": 1,
        "plan_id": 2,
        "plan_name": "РџСЂРµРјРёСѓРј",
        "start_date": "2023-01-01T12:30:00Z",
        "end_date": "2023-01-31T12:30:00Z",
        "is_active": true,
        "requests_added": 100
    }
}
```

## РљРѕРґС‹ РѕС€РёР±РѕРє

| РљРѕРґ | РћРїРёСЃР°РЅРёРµ |
|-----|----------|
| 400 | РћС€РёР±РєР° РІ РїР°СЂР°РјРµС‚СЂР°С… Р·Р°РїСЂРѕСЃР° |
| 401 | РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ РЅРµ Р°РІС‚РѕСЂРёР·РѕРІР°РЅ |
| 403 | Р”РѕСЃС‚СѓРї Р·Р°РїСЂРµС‰РµРЅ (РЅР°РїСЂРёРјРµСЂ, РЅРµРґРѕСЃС‚Р°С‚РѕС‡РЅРѕ Р·Р°РїСЂРѕСЃРѕРІ) |
| 404 | Р РµСЃСѓСЂСЃ РЅРµ РЅР°Р№РґРµРЅ |
| 409 | РљРѕРЅС„Р»РёРєС‚ (РЅР°РїСЂРёРјРµСЂ, РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ СѓР¶Рµ СЃСѓС‰РµСЃС‚РІСѓРµС‚) |
| 500 | Р’РЅСѓС‚СЂРµРЅРЅСЏСЏ РѕС€РёР±РєР° СЃРµСЂРІРµСЂР° | 
