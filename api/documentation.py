"""
Этот модуль содержит документацию по API бота.
Документация используется в административной панели Django.
"""

class ApiDocumentation:
    """
    Класс для генерации HTML-документации API.
    """
    
    @staticmethod
    def get_documentation():
        """
        Возвращает HTML-документацию API.
        """
        return """
        <div class="api-documentation">
            <h1>Документация API Чат-бота</h1>
            
            <section>
                <h2>Общая информация</h2>
                <p>API используется для взаимодействия с чат-ботом и управления пользователями, подписками и запросами.</p>
                <p>Базовый URL: <code>/api/</code></p>
                <p>Формат ответа: JSON</p>
                <p>Все ответы имеют следующую структуру:</p>
                <pre>
{
    "success": true/false,
    "data": { ... },  // опционально
    "error": "Сообщение об ошибке"  // только если success=false
}
                </pre>
            </section>
            
            <section>
                <h2>Аутентификация</h2>
                <p>Аутентификация в API происходит с использованием Telegram ID пользователя.</p>
                <p>Telegram ID может быть передан одним из следующих способов:</p>
                <ul>
                    <li>В заголовке запроса: <code>X-Telegram-ID: 123456789</code></li>
                    <li>В параметре URL: <code>?telegram_id=123456789</code></li>
                    <li>В теле запроса JSON для POST-запросов: <code>{"telegram_id": 123456789, ...}</code></li>
                </ul>
            </section>
            
            <section>
                <h2>Основные эндпоинты</h2>
                
                <div class="endpoint">
                    <h3>Регистрация пользователя</h3>
                    <p><strong>URL:</strong> <code>/api/register/</code></p>
                    <p><strong>Метод:</strong> POST</p>
                    <p><strong>Описание:</strong> Регистрирует нового пользователя в системе.</p>
                    <p><strong>Тело запроса:</strong></p>
                    <pre>
{
    "telegram_id": 123456789,
    "username": "example_user",
    "first_name": "John",
    "last_name": "Doe",
    "is_bot": false,
    "language_code": "ru",
    "chat_id": 123456789,
    "contact": "+79001234567",  // опционально
    "referral_code": "ABC123"   // опционально
}
                    </pre>
                    <p><strong>Ответ:</strong></p>
                    <pre>
{
    "success": true,
    "data": {
        "telegram_id": 123456789,
        "username": "example_user",
        "first_name": "John",
        "last_name": "Doe",
        "requests_left": 10
        // другие поля пользователя
    }
}
                    </pre>
                </div>
                
                <div class="endpoint">
                    <h3>Авторизация пользователя</h3>
                    <p><strong>URL:</strong> <code>/api/login/</code></p>
                    <p><strong>Метод:</strong> POST</p>
                    <p><strong>Описание:</strong> Авторизует существующего пользователя и возвращает информацию о нем.</p>
                    <p><strong>Тело запроса:</strong></p>
                    <pre>
{
    "telegram_id": 123456789
}
                    </pre>
                    <p><strong>Ответ:</strong></p>
                    <pre>
{
    "success": true,
    "data": {
        "telegram_id": 123456789,
        "username": "example_user",
        "first_name": "John",
        "last_name": "Doe",
        "requests_left": 5
        // другие поля пользователя
    }
}
                    </pre>
                </div>
                
                <div class="endpoint">
                    <h3>Проверка доступных запросов</h3>
                    <p><strong>URL:</strong> <code>/api/check-requests/</code></p>
                    <p><strong>Метод:</strong> GET</p>
                    <p><strong>Описание:</strong> Проверяет количество доступных запросов для пользователя.</p>
                    <p><strong>Заголовки:</strong> <code>X-Telegram-ID: 123456789</code></p>
                    <p><strong>Ответ:</strong></p>
                    <pre>
{
    "success": true,
    "data": {
        "requests_left": 5,
        "user_plan": {
            "name": "Стандарт",
            "requests": 200,
            "expired_at": "2023-12-31T23:59:59Z",
            "is_active": true
        }
    }
}
                    </pre>
                </div>
                
                <div class="endpoint">
                    <h3>Использование запроса</h3>
                    <p><strong>URL:</strong> <code>/api/use-request/</code></p>
                    <p><strong>Метод:</strong> POST</p>
                    <p><strong>Описание:</strong> Регистрирует использование запроса и уменьшает счетчик доступных запросов.</p>
                    <p><strong>Заголовки:</strong> <code>X-Telegram-ID: 123456789</code></p>
                    <p><strong>Тело запроса:</strong></p>
                    <pre>
{
    "request_type": "text",
    "ai_model": "gpt-4",
    "tokens_used": 150,
    "request_text": "Привет, как дела?",
    "response_length": 250,
    "response_time": 2.5
}
                    </pre>
                    <p><strong>Ответ:</strong></p>
                    <pre>
{
    "success": true,
    "data": {
        "requests_left": 4
    }
}
                    </pre>
                </div>
                
                <div class="endpoint">
                    <h3>Валидация промокода</h3>
                    <p><strong>URL:</strong> <code>/api/validate-promo/</code></p>
                    <p><strong>Метод:</strong> POST</p>
                    <p><strong>Описание:</strong> Проверяет валидность промокода и возвращает информацию о скидке.</p>
                    <p><strong>Заголовки:</strong> <code>X-Telegram-ID: 123456789</code></p>
                    <p><strong>Тело запроса:</strong></p>
                    <pre>
{
    "promo_code": "SUMMER2023",
    "plan_id": 1  // опционально, если применяется к конкретному плану
}
                    </pre>
                    <p><strong>Ответ:</strong></p>
                    <pre>
{
    "success": true,
    "data": {
        "discount_type": "percent",
        "discount_value": 20.00,
        "bonus_requests": 0,
        "valid_from": "2023-06-01T00:00:00Z",
        "valid_to": "2023-08-31T23:59:59Z"
    }
}
                    </pre>
                </div>
                
                <div class="endpoint">
                    <h3>Информация о текущем пользователе</h3>
                    <p><strong>URL:</strong> <code>/api/me/</code></p>
                    <p><strong>Метод:</strong> GET</p>
                    <p><strong>Описание:</strong> Возвращает полную информацию о текущем пользователе, включая активные планы и статистику.</p>
                    <p><strong>Заголовки:</strong> <code>X-Telegram-ID: 123456789</code></p>
                    <p><strong>Ответ:</strong></p>
                    <pre>
{
    "success": true,
    "data": {
        "user": {
            "telegram_id": 123456789,
            "username": "example_user",
            "first_name": "John",
            "last_name": "Doe",
            "requests_left": 4
        },
        "active_plan": {
            "name": "Стандарт",
            "requests": 200,
            "expired_at": "2023-12-31T23:59:59Z",
            "is_active": true
        },
        "statistics": {
            "total_requests": 196,
            "total_tokens": 29400,
            "last_active": "2023-07-15T14:30:45Z",
            "total_payments": 999.00,
            "total_referrals": 2
        }
    }
}
                    </pre>
                </div>
            </section>
            
            <section>
                <h3>Управление чатами</h3>
                
                <div class="endpoint">
                    <h3>Создание нового чата</h3>
                    <p><strong>URL:</strong> <code>/api/chats/</code></p>
                    <p><strong>Метод:</strong> POST</p>
                    <p><strong>Описание:</strong> Создает новый чат для пользователя.</p>
                    <p><strong>Заголовки:</strong> <code>X-Telegram-ID: 123456789</code></p>
                    <p><strong>Тело запроса:</strong></p>
                    <pre>
{
    "title": "Новый чат",
    "ai_model": "gpt-4o-mini"
}
                    </pre>
                    <p><strong>Ответ:</strong></p>
                    <pre>
{
    "success": true,
    "data": {
        "id": 42,
        "title": "Новый чат",
        "ai_model": "gpt-4o-mini",
        "created_at": "2023-07-15T15:30:00Z",
        "updated_at": "2023-07-15T15:30:00Z"
    }
}
                    </pre>
                </div>
                
                <div class="endpoint">
                    <h3>Получение списка чатов</h3>
                    <p><strong>URL:</strong> <code>/api/chats/</code></p>
                    <p><strong>Метод:</strong> GET</p>
                    <p><strong>Описание:</strong> Возвращает список всех чатов пользователя.</p>
                    <p><strong>Заголовки:</strong> <code>X-Telegram-ID: 123456789</code></p>
                    <p><strong>Ответ:</strong></p>
                    <pre>
{
    "success": true,
    "data": {
        "chats": [
            {
                "id": 42,
                "title": "Новый чат",
                "ai_model": "gpt-4o-mini",
                "created_at": "2023-07-15T15:30:00Z",
                "updated_at": "2023-07-15T15:30:00Z"
            },
            {
                "id": 41,
                "title": "О погоде",
                "ai_model": "claude-3-5",
                "created_at": "2023-07-14T10:15:00Z",
                "updated_at": "2023-07-14T11:20:00Z"
            }
        ]
    }
}
                    </pre>
                </div>
                
                <div class="endpoint">
                    <h3>Получение сообщений чата</h3>
                    <p><strong>URL:</strong> <code>/api/chats/{chat_id}/messages/</code></p>
                    <p><strong>Метод:</strong> GET</p>
                    <p><strong>Описание:</strong> Возвращает список сообщений в чате.</p>
                    <p><strong>Заголовки:</strong> <code>X-Telegram-ID: 123456789</code></p>
                    <p><strong>Ответ:</strong></p>
                    <pre>
{
    "success": true,
    "data": {
        "messages": [
            {
                "id": 101,
                "role": "user",
                "content": "Привет, как дела?",
                "timestamp": "2023-07-15T15:31:00Z"
            },
            {
                "id": 102,
                "role": "assistant",
                "content": "Привет! У меня всё отлично. Чем я могу тебе помочь сегодня?",
                "timestamp": "2023-07-15T15:31:05Z",
                "model_used": "gpt-4o-mini",
                "tokens_used": 150
            }
        ]
    }
}
                    </pre>
                </div>
                
                <div class="endpoint">
                    <h3>Отправка сообщения в чат</h3>
                    <p><strong>URL:</strong> <code>/api/chats/{chat_id}/messages/</code></p>
                    <p><strong>Метод:</strong> POST</p>
                    <p><strong>Описание:</strong> Отправляет новое сообщение в чат и получает ответ от ИИ.</p>
                    <p><strong>Заголовки:</strong> <code>X-Telegram-ID: 123456789</code></p>
                    <p><strong>Тело запроса:</strong></p>
                    <pre>
{
    "content": "Расскажи мне о погоде в Москве"
}
                    </pre>
                    <p><strong>Ответ:</strong></p>
                    <pre>
{
    "success": true,
    "data": {
        "user_message": {
            "id": 103,
            "role": "user",
            "content": "Расскажи мне о погоде в Москве",
            "timestamp": "2023-07-15T15:40:00Z"
        },
        "assistant_message": {
            "id": 104,
            "role": "assistant",
            "content": "В Москве сегодня ожидается переменная облачность, температура около 25°C...",
            "timestamp": "2023-07-15T15:40:05Z",
            "model_used": "gpt-4o-mini",
            "tokens_used": 200
        },
        "requests_left": 3
    }
}
                    </pre>
                </div>
            </section>
            
            <section>
                <h2>Коды ошибок</h2>
                <table>
                    <tr>
                        <th>Код</th>
                        <th>Описание</th>
                    </tr>
                    <tr>
                        <td>400</td>
                        <td>Неверный запрос (Bad Request)</td>
                    </tr>
                    <tr>
                        <td>401</td>
                        <td>Не авторизован (Unauthorized)</td>
                    </tr>
                    <tr>
                        <td>403</td>
                        <td>Доступ запрещен (Forbidden)</td>
                    </tr>
                    <tr>
                        <td>404</td>
                        <td>Не найдено (Not Found)</td>
                    </tr>
                    <tr>
                        <td>429</td>
                        <td>Слишком много запросов (Too Many Requests)</td>
                    </tr>
                    <tr>
                        <td>500</td>
                        <td>Внутренняя ошибка сервера (Internal Server Error)</td>
                    </tr>
                </table>
                
                <h3>Специфические коды ошибок API</h3>
                <table>
                    <tr>
                        <th>Код</th>
                        <th>Описание</th>
                    </tr>
                    <tr>
                        <td>1001</td>
                        <td>Пользователь не найден</td>
                    </tr>
                    <tr>
                        <td>1002</td>
                        <td>Недостаточно запросов</td>
                    </tr>
                    <tr>
                        <td>1003</td>
                        <td>Недействительный промокод</td>
                    </tr>
                    <tr>
                        <td>1004</td>
                        <td>Истек срок действия плана</td>
                    </tr>
                    <tr>
                        <td>1005</td>
                        <td>Ошибка при обработке запроса ИИ</td>
                    </tr>
                </table>
            </section>
            
            <section>
                <h2>Модели данных</h2>
                
                <h3>Пользователь (BotUser)</h3>
                <pre>
{
    "user_id": Int,            // первичный ключ
    "telegram_id": BigInt,     // уникальный ID из Telegram
    "username": String,        // имя пользователя в Telegram
    "first_name": String,      // имя
    "last_name": String,       // фамилия
    "is_bot": Boolean,         // является ли бот
    "language_code": String,   // код языка
    "chat_id": BigInt,         // ID чата в Telegram
    "contact": String,         // контактная информация
    "is_active": Boolean,      // активен ли пользователь
    "requests_left": Int,      // осталось запросов
    "registration_date": DateTime // дата регистрации
}
                </pre>
                
                <h3>Тарифный план (Plan)</h3>
                <pre>
{
    "id": Int,                 // первичный ключ
    "name": String,            // название плана
    "requests": Int,           // количество запросов
    "price": Decimal,          // цена
    "created_at": DateTime,    // дата создания
    "is_active": Boolean,      // активен ли план
    "duration_days": Int,      // длительность в днях (0 = бессрочно)
    "description": String,     // описание
    "priority": Int,           // приоритет для сортировки
    "is_subscription": Boolean, // подписка или разовая покупка
    "discount_percent": Decimal, // скидка в процентах
    "allowed_models": String,  // доступные модели ИИ
    "max_tokens_per_request": Int, // максимум токенов на запрос
    "features": JSON           // дополнительные возможности
}
                </pre>
                
                <h3>Подписка пользователя (UserPlan)</h3>
                <pre>
{
    "user_id": Int,            // внешний ключ на пользователя
    "plan_id": Int,            // внешний ключ на план
    "activated_at": DateTime,  // дата активации
    "expired_at": DateTime,    // дата истечения
    "is_active": Boolean,      // активна ли подписка
    "payment_id": String,      // ID платежа
    "price_paid": Decimal,     // фактически оплаченная сумма
    "is_auto_renewal": Boolean, // автопродление
    "source": String,          // источник (веб, бот, админка)
    "requests_added": Int,     // добавлено запросов
    "discount_applied": Decimal, // применённая скидка
    "notes": String            // примечания
}
                </pre>
                
                <h3>Использование запроса (RequestUsage)</h3>
                <pre>
{
    "id": Int,                 // первичный ключ
    "user_id": Int,            // внешний ключ на пользователя
    "request_type": String,    // тип запроса
    "ai_model": String,        // используемая модель
    "tokens_used": Int,        // использовано токенов
    "request_date": DateTime,  // дата запроса
    "response_time": Float,    // время ответа в секундах
    "was_successful": Boolean, // был ли запрос успешным
    "request_text": String,    // текст запроса
    "response_length": Int     // длина ответа
}
                </pre>
                
                <h3>Чат (Chat)</h3>
                <pre>
{
    "id": Int,                 // первичный ключ
    "user_id": Int,            // внешний ключ на пользователя
    "title": String,           // название чата
    "ai_model": String,        // модель ИИ
    "created_at": DateTime,    // дата создания
    "updated_at": DateTime     // дата обновления
}
                </pre>
                
                <h3>Сообщение чата (ChatMessage)</h3>
                <pre>
{
    "id": Int,                 // первичный ключ
    "chat_id": Int,            // внешний ключ на чат
    "role": String,            // роль (user/assistant)
    "content": String,         // содержимое сообщения
    "model_used": String,      // используемая модель
    "tokens_used": Int,        // использовано токенов
    "timestamp": DateTime      // время сообщения
}
                </pre>
            </section>
            
            <style>
                .api-documentation {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                
                h1 {
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }
                
                h2 {
                    color: #2980b9;
                    margin-top: 30px;
                    border-bottom: 1px solid #ddd;
                    padding-bottom: 5px;
                }
                
                h3 {
                    color: #3498db;
                    margin-top: 20px;
                }
                
                section {
                    margin-bottom: 40px;
                }
                
                .endpoint {
                    background-color: #f9f9f9;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 15px;
                    margin-bottom: 20px;
                }
                
                code {
                    background-color: #f8f8f8;
                    padding: 2px 5px;
                    border-radius: 3px;
                    font-family: Consolas, monospace;
                    color: #e74c3c;
                }
                
                pre {
                    background-color: #f8f8f8;
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                    font-family: Consolas, monospace;
                    border: 1px solid #ddd;
                }
                
                table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }
                
                th, td {
                    text-align: left;
                    padding: 8px;
                    border: 1px solid #ddd;
                }
                
                th {
                    background-color: #f2f2f2;
                }
                
                tr:nth-child(even) {
                    background-color: #f9f9f9;
                }
            </style>
        </div>
        """ 