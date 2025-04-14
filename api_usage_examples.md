# Примеры использования API

## Установка и запуск API

### Шаг 1: Установка зависимостей
```bash
pip install -r api_requirements.txt
```

### Шаг 2: Создание базы данных
```bash
# Создаем базу данных (MySQL/MariaDB)
mysql -u root -p
```

```sql
CREATE DATABASE bot_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Шаг 3: Импорт схемы базы данных
```bash
mysql -u root -p bot_db < schema.sql
```

### Шаг 4: Настройка переменных окружения
Скопируйте файл `.env.example` в `.env` и отредактируйте его, указав свои настройки:

```bash
cp .env.example .env
```

### Шаг 5: Запуск API сервера
```bash
python api_server.py
```

## Примеры вызовов API с использованием `curl`

### 1. Регистрация нового пользователя

```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "password": "secure_password",
    "email": "user@example.com"
  }'
```

Ответ:
```json
{
  "message": "Пользователь успешно зарегистрирован!",
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 2. Авторизация пользователя

```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "password": "secure_password"
  }'
```

Ответ:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "test_user"
}
```

### 3. Получение информации о пользователе

```bash
curl -X GET http://localhost:5000/api/user \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### 4. Получение списка тарифных планов

```bash
curl -X GET http://localhost:5000/api/plans
```

### 5. Получение информации о конкретном плане

```bash
curl -X GET http://localhost:5000/api/plans/1
```

### 6. Валидация промокода

```bash
curl -X POST http://localhost:5000/api/promo/validate \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "code": "WELCOME20",
    "plan_id": 1
  }'
```

### 7. Покупка тарифного плана

```bash
curl -X POST http://localhost:5000/api/payment \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": 1,
    "amount": 299.00,
    "payment_details": "{\"payment_method\":\"card\",\"card_last4\":\"4242\"}",
    "promo_code": "WELCOME20"
  }'
```

### 8. Создание запроса к боту

```bash
curl -X POST http://localhost:5000/api/requests \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Что такое искусственный интеллект?"
  }'
```

### 9. Получение истории запросов

```bash
curl -X GET http://localhost:5000/api/requests \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### 10. Получение информации о рефералах

```bash
curl -X GET http://localhost:5000/api/referrals \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

## Примеры использования API в Python

### Настройка
```python
import requests
import json

BASE_URL = "http://localhost:5000"
TOKEN = None
```

### 1. Регистрация и получение токена

```python
def register_user(username, password, email=None):
    data = {
        "username": username,
        "password": password
    }
    
    if email:
        data["email"] = email
        
    response = requests.post(f"{BASE_URL}/api/register", json=data)
    return response.json()

# Пример использования
result = register_user("new_user", "secure_password", "user@example.com")
print(result)
```

### 2. Авторизация

```python
def login(username, password):
    global TOKEN
    
    data = {
        "username": username,
        "password": password
    }
    
    response = requests.post(f"{BASE_URL}/api/login", json=data)
    result = response.json()
    
    if response.status_code == 200:
        TOKEN = result.get("token")
    
    return result

# Пример использования
result = login("new_user", "secure_password")
print(result)
```

### 3. Получение информации о пользователе

```python
def get_user_info():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(f"{BASE_URL}/api/user", headers=headers)
    return response.json()

# Пример использования
user_info = get_user_info()
print(user_info)
```

### 4. Получение списка тарифных планов

```python
def get_plans():
    response = requests.get(f"{BASE_URL}/api/plans")
    return response.json()

# Пример использования
plans = get_plans()
print(plans)
```

### 5. Покупка тарифного плана

```python
def purchase_plan(plan_id, amount, promo_code=None):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    data = {
        "plan_id": plan_id,
        "amount": amount,
        "payment_details": json.dumps({"payment_method": "card", "card_last4": "4242"})
    }
    
    if promo_code:
        data["promo_code"] = promo_code
        
    response = requests.post(f"{BASE_URL}/api/payment", json=data, headers=headers)
    return response.json()

# Пример использования
result = purchase_plan(1, 299.00, "WELCOME20")
print(result)
```

### 6. Создание запроса к боту

```python
def create_request(query):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    data = {
        "query": query
    }
        
    response = requests.post(f"{BASE_URL}/api/requests", json=data, headers=headers)
    return response.json()

# Пример использования
result = create_request("Что такое машинное обучение?")
print(result)
```

### 7. Получение истории запросов

```python
def get_request_history():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(f"{BASE_URL}/api/requests", headers=headers)
    return response.json()

# Пример использования
history = get_request_history()
print(history)
```

## Пример интеграции API в веб-приложение (JavaScript)

```javascript
// Базовый URL API
const API_BASE_URL = 'http://localhost:5000';

// Получение токена из localStorage
const getToken = () => localStorage.getItem('token');

// Установка токена в localStorage
const setToken = (token) => localStorage.setItem('token', token);

// Базовая функция для выполнения запросов к API
async function apiRequest(endpoint, method = 'GET', data = null) {
  const headers = {
    'Content-Type': 'application/json'
  };
  
  // Добавление токена авторизации, если он есть
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const options = {
    method,
    headers
  };
  
  if (data && (method === 'POST' || method === 'PUT')) {
    options.body = JSON.stringify(data);
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
    const responseData = await response.json();
    
    if (!response.ok) {
      throw new Error(responseData.message || 'Произошла ошибка при выполнении запроса');
    }
    
    return responseData;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// API Функции
const API = {
  // Аутентификация
  async login(username, password) {
    const result = await apiRequest('/api/login', 'POST', { username, password });
    if (result.token) {
      setToken(result.token);
    }
    return result;
  },
  
  async register(username, password, email) {
    const result = await apiRequest('/api/register', 'POST', { 
      username, 
      password,
      email
    });
    if (result.token) {
      setToken(result.token);
    }
    return result;
  },
  
  // Информация о пользователе
  async getUserInfo() {
    return await apiRequest('/api/user');
  },
  
  // Тарифные планы
  async getPlans() {
    return await apiRequest('/api/plans');
  },
  
  async getPlan(planId) {
    return await apiRequest(`/api/plans/${planId}`);
  },
  
  // Запросы
  async createRequest(query) {
    return await apiRequest('/api/requests', 'POST', { query });
  },
  
  async getRequestHistory() {
    return await apiRequest('/api/requests');
  },
  
  // Платежи
  async purchasePlan(planId, amount, promoCode = null) {
    const data = {
      plan_id: planId,
      amount,
      payment_details: JSON.stringify({
        payment_method: 'card',
        card_last4: '4242'
      })
    };
    
    if (promoCode) {
      data.promo_code = promoCode;
    }
    
    return await apiRequest('/api/payment', 'POST', data);
  },
  
  // Промокоды
  async validatePromo(code, planId) {
    return await apiRequest('/api/promo/validate', 'POST', {
      code,
      plan_id: planId
    });
  },
  
  // Рефералы
  async getReferrals() {
    return await apiRequest('/api/referrals');
  }
};

// Пример использования в компоненте React
function App() {
  const [user, setUser] = useState(null);
  const [plans, setPlans] = useState([]);
  
  useEffect(() => {
    // Получение информации о пользователе, если есть токен
    if (getToken()) {
      API.getUserInfo()
        .then(data => setUser(data))
        .catch(err => {
          // Если ошибка авторизации, сбрасываем токен
          if (err.message.includes('токен')) {
            localStorage.removeItem('token');
          }
        });
    }
    
    // Получение списка тарифных планов
    API.getPlans()
      .then(data => setPlans(data.plans || []))
      .catch(err => console.error('Ошибка получения планов:', err));
  }, []);
  
  // Функция для авторизации
  const handleLogin = async (username, password) => {
    try {
      const result = await API.login(username, password);
      setUser(result);
      return true;
    } catch (error) {
      console.error('Ошибка входа:', error);
      return false;
    }
  };
  
  // Функция для отправки запроса к боту
  const handleCreateRequest = async (query) => {
    try {
      const result = await API.createRequest(query);
      return result;
    } catch (error) {
      console.error('Ошибка создания запроса:', error);
      return null;
    }
  };
  
  // ... остальной код компонента
}
``` 