from flask import Flask, request, jsonify
from flask_cors import CORS
from payments_service import PaymentService
from werkzeug.security import check_password_hash
import os
import uuid
import datetime
from functools import wraps
import jwt
from dotenv import load_dotenv
import pymysql
import bcrypt

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)
CORS(app)  # Включаем CORS для всех роутов

# Конфигурация
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'секретный_ключ_по_умолчанию')
app.config['JWT_EXPIRATION_TIME'] = int(os.getenv('JWT_EXPIRATION_TIME', 3600))  # время в секундах

# Инициализация сервиса платежей
payment_service = PaymentService()

# Подключение к БД
def get_db_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        db=os.getenv('DB_NAME', 'ai_bot'),
        charset=os.getenv('DB_CHARSET', 'utf8mb4'),
        cursorclass=pymysql.cursors.DictCursor
    )

# Middleware для проверки JWT токена
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Получаем токен из заголовка
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Токен отсутствует!'}), 401
            
        try:
            # Декодируем токен
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data
            
            # Проверка существования пользователя
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = %s", (current_user['id'],))
            current_user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not current_user:
                return jsonify({'message': 'Пользователь не найден!'}), 401
                
        except Exception as e:
            return jsonify({'message': f'Недействительный токен: {str(e)}'}), 401
            
        # Передаем ID пользователя в функцию
        return f(current_user, *args, **kwargs)
    
    return decorated

# Хелпер для генерации JWT токена
def generate_token(user_id):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=app.config['JWT_EXPIRATION_TIME']),
        'iat': datetime.datetime.utcnow(),
        'user_id': user_id
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

# Аутентификация и авторизация

@app.route('/api/login', methods=['POST'])
def login():
    """Авторизация пользователя"""
    auth = request.json
    
    if not auth or not auth.get('username') or not auth.get('password'):
        return jsonify({'message': 'Неверные данные для входа!'}), 400
        
    username = auth.get('username')
    password = auth.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        return jsonify({'message': 'Пользователь не найден!'}), 404
    
    # Проверка пароля
    if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        # Генерация токена
        token = jwt.encode({
            'user_id': user['id'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=app.config['JWT_EXPIRATION_TIME'])
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'token': token,
            'user_id': user['id'],
            'username': user['username']
        })
    
    cursor.close()
    conn.close()
    return jsonify({'message': 'Неверный пароль!'}), 401

@app.route('/api/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    data = request.json
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Неверные данные для регистрации!'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверка существования пользователя
    cursor.execute("SELECT * FROM users WHERE username = %s", (data.get('username'),))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({'message': 'Пользователь уже существует!'}), 409
    
    # Создание нового пользователя
    user_id = str(uuid.uuid4())
    hashed_password = bcrypt.hashpw(data.get('password').encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    referral_code = ''.join(str(uuid.uuid4()).split('-'))[0:10]
    
    try:
        cursor.execute(
            "INSERT INTO users (id, username, password, email, telegram_id, referral_code, referrer_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                user_id,
                data.get('username'),
                hashed_password,
                data.get('email'),
                data.get('telegram_id'),
                referral_code,
                data.get('referrer_id')
            )
        )
        
        # Назначение базового плана для нового пользователя
        cursor.execute("SELECT id FROM plans WHERE name = 'Базовый' LIMIT 1")
        plan = cursor.fetchone()
        
        if plan:
            start_date = datetime.datetime.now()
            end_date = start_date + datetime.timedelta(days=30)
            
            cursor.execute(
                "INSERT INTO user_plans (user_id, plan_id, start_date, end_date) VALUES (%s, %s, %s, %s)",
                (user_id, plan['id'], start_date, end_date)
            )
        
        conn.commit()
        
        # Создание токена
        token = jwt.encode({
            'user_id': user_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=app.config['JWT_EXPIRATION_TIME'])
        }, app.config['SECRET_KEY'], algorithm="HS256")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'Пользователь успешно зарегистрирован!',
            'token': token,
            'user_id': user_id
        }), 201
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'message': f'Ошибка при регистрации: {str(e)}'}), 500

# Информация о пользователе

@app.route('/api/user', methods=['GET'])
@token_required
def get_user_info(current_user):
    """Получение информации о пользователе"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Получаем данные пользователя
    cursor.execute('''
        SELECT u.*, 
               COALESCE(us.total_requests, 0) as total_requests,
               COALESCE(us.total_tokens, 0) as total_tokens,
               COALESCE(us.total_payments, 0) as total_payments,
               COALESCE(us.total_referrals, 0) as total_referrals,
               us.account_level,
               us.last_active
        FROM users u
        LEFT JOIN user_statistics us ON u.id = us.user_id
        WHERE u.id = %s
    ''', (current_user['id'],))
    
    user = cursor.fetchone()
    
    # Получаем активный план пользователя
    cursor.execute('''
        SELECT up.*, p.name as plan_name, p.requests_allowed, p.price, p.description
        FROM user_plans up
        JOIN plans p ON up.plan_id = p.id
        WHERE up.user_id = %s AND up.end_date >= NOW()
        ORDER BY up.start_date DESC
        LIMIT 1
    ''', (current_user['id'],))
    
    active_plan = cursor.fetchone()
    
    # Получаем реферальный код пользователя
    cursor.execute('SELECT referral_code FROM users WHERE id = %s', (current_user['id'],))
    referral = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'success': True,
        'user': {
            'user_id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'telegram_id': user['telegram_id'],
            'requests_left': user.get('requests_left', 0),
            'created_at': user['created_at'].isoformat() if user.get('created_at') else None,
            'total_requests': user.get('total_requests', 0),
            'total_tokens': user.get('total_tokens', 0),
            'total_payments': float(user.get('total_payments', 0)) if user.get('total_payments') else 0,
            'total_referrals': user.get('total_referrals', 0),
            'account_level': user.get('account_level', 'standard'),
            'last_active': user.get('last_active').isoformat() if user.get('last_active') else None,
            'referral_code': referral['referral_code'] if referral else None
        },
        'active_plan': active_plan
    })

# Новый маршрут для получения количества оставшихся запросов
@app.route('/api/user/requests_left', methods=['GET'])
@token_required
def get_requests_left(current_user):
    """Получение количества оставшихся запросов пользователя"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Получаем количество оставшихся запросов
    cursor.execute('''
        SELECT requests_left FROM users WHERE id = %s
    ''', (current_user['id'],))
    
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'Пользователь не найден'
        }), 404
    
    return jsonify({
        'success': True,
        'user_id': current_user['id'],
        'requests_left': user.get('requests_left', 0)
    })

# Управление запросами

@app.route('/api/user/requests/check', methods=['GET'])
@token_required
def check_requests(current_user):
    """
    Проверка доступных запросов пользователя
    """
    requests_left = payment_service.get_user_requests_left(current_user['id'])
    
    return jsonify({
        'success': True,
        'requests_left': requests_left,
        'can_make_request': requests_left > 0
    })

@app.route('/api/user/requests/use', methods=['POST'])
@token_required
def use_request(current_user):
    """
    Использование запроса пользователем
    
    POST-параметры:
    - request_type: тип запроса (text, image, audio)
    - ai_model: используемая модель ИИ
    - tokens_used: количество использованных токенов
    - request_text: текст запроса (опционально)
    - response_length: длина ответа (опционально)
    - response_time: время ответа в секундах (опционально)
    """
    data = request.json
    
    if not data:
        return jsonify({'message': 'Отсутствуют данные запроса!', 'success': False}), 400
    
    # Проверяем наличие запросов
    requests_left = payment_service.get_user_requests_left(current_user['id'])
    
    if requests_left <= 0:
        return jsonify({
            'success': False,
            'message': 'У вас закончились запросы. Пожалуйста, пополните баланс.',
            'requests_left': 0
        }), 403
    
    # Уменьшаем счетчик запросов
    new_count = payment_service.decrement_user_requests(current_user['id'])
    
    # Добавляем запись об использовании
    payment_service.add_usage_record(
        user_id=current_user['id'],
        request_type=data.get('request_type', 'text'),
        ai_model=data.get('ai_model', 'unknown'),
        tokens_used=data.get('tokens_used', 0),
        was_successful=True,
        request_text=data.get('request_text'),
        response_length=data.get('response_length', 0),
        response_time=data.get('response_time')
    )
    
    return jsonify({
        'success': True,
        'requests_left': new_count,
        'message': 'Запрос успешно использован.'
    })

# Тарифные планы

@app.route('/api/plans', methods=['GET'])
def get_plans():
    """
    Получение списка доступных тарифных планов
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT *
        FROM plans
        WHERE is_active = TRUE
        ORDER BY priority, price
    ''')
    
    plans = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Преобразуем Decimal в float для JSON сериализации
    for plan in plans:
        plan['price'] = float(plan['price'])
        if plan.get('discount_percent'):
            plan['discount_percent'] = float(plan['discount_percent'])
        # Преобразуем datetime объекты в строки
        plan['created_at'] = plan['created_at'].isoformat() if plan['created_at'] else None
    
    return jsonify({
        'success': True,
        'plans': plans
    })

@app.route('/api/plans/<int:plan_id>', methods=['GET'])
def get_plan(plan_id):
    """
    Получение информации о конкретном тарифном плане
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT * FROM plans WHERE id = %s', (plan_id,))
    
    plan = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not plan:
        return jsonify({'message': 'Тарифный план не найден!', 'success': False}), 404
    
    # Преобразуем Decimal в float для JSON сериализации
    plan['price'] = float(plan['price'])
    if plan.get('discount_percent'):
        plan['discount_percent'] = float(plan['discount_percent'])
    # Преобразуем datetime объекты в строки
    plan['created_at'] = plan['created_at'].isoformat() if plan['created_at'] else None
    
    return jsonify({
        'success': True,
        'plan': plan
    })

# Покупка тарифного плана

@app.route('/api/payment', methods=['POST'])
@token_required
def process_payment(current_user):
    """Обработка оплаты тарифного плана"""
    data = request.json
    
    if not data or not data.get('plan_id') or not data.get('amount'):
        return jsonify({'message': 'Неверные данные для оплаты!'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверка существования плана
    cursor.execute("SELECT * FROM plans WHERE id = %s", (data.get('plan_id'),))
    plan = cursor.fetchone()
    
    if not plan:
        cursor.close()
        conn.close()
        return jsonify({'message': 'Тарифный план не найден!'}), 404
    
    # Здесь будет код для обработки платежа через внешний платежный сервис
    # В данном примере просто имитируем успешную оплату
    
    payment_id = str(uuid.uuid4())
    
    try:
        # Запись информации о платеже
        cursor.execute(
            "INSERT INTO payments (id, user_id, plan_id, amount, payment_details, promo_code) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                payment_id,
                current_user['id'],
                data.get('plan_id'),
                data.get('amount'),
                data.get('payment_details', '{}'),
                data.get('promo_code')
            )
        )
        
        # Обновление или добавление плана пользователя
        start_date = datetime.datetime.now()
        end_date = start_date + datetime.timedelta(days=plan['duration_days'])
        
        cursor.execute(
            """
            INSERT INTO user_plans (user_id, plan_id, start_date, end_date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                plan_id = VALUES(plan_id),
                start_date = VALUES(start_date),
                end_date = VALUES(end_date)
            """,
            (current_user['id'], data.get('plan_id'), start_date, end_date)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'Оплата успешно обработана!',
            'payment_id': payment_id,
            'plan': plan['name'],
            'end_date': end_date.isoformat()
        })
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({'message': f'Ошибка при обработке оплаты: {str(e)}'}), 500

# Промокоды

@app.route('/api/promo/validate', methods=['POST'])
@token_required
def validate_promo(current_user):
    """
    Проверка валидности промокода
    
    POST-параметры:
    - promo_code: промокод
    - plan_id: ID тарифного плана (опционально)
    """
    data = request.json
    
    if not data or not data.get('promo_code'):
        return jsonify({'message': 'Необходим промокод!', 'success': False}), 400
    
    promo_code = data.get('promo_code')
    plan_id = data.get('plan_id')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Проверяем существование и активность промокода
    cursor.execute('''
        SELECT * FROM promo_codes 
        WHERE code = %s 
        AND is_active = TRUE 
        AND (valid_to IS NULL OR valid_to > NOW())
        AND (max_usages = 0 OR usages_count < max_usages)
    ''', (promo_code,))
    
    promo = cursor.fetchone()
    
    if not promo:
        cursor.close()
        conn.close()
        return jsonify({
            'success': False,
            'message': 'Промокод не найден или недействителен'
        }), 404
    
    # Если указан план, проверяем применимость промокода к этому плану
    if plan_id and promo.get('allowed_plans'):
        allowed_plans = promo['allowed_plans'].split(',')
        if str(plan_id) not in allowed_plans:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Промокод не может быть применен к выбранному тарифному плану'
            }), 400
    
    # Проверяем, использовал ли пользователь этот промокод ранее
    cursor.execute('''
        SELECT COUNT(*) as count FROM promo_code_usages 
        WHERE promo_code_id = %s AND user_id = %s
    ''', (promo['id'], current_user['id']))
    
    usage_count = cursor.fetchone()['count']
    
    if usage_count > 0:
        cursor.close()
        conn.close()
        return jsonify({
            'success': False,
            'message': 'Вы уже использовали этот промокод'
        }), 400
    
    # Если указан план, рассчитываем скидку
    discount_amount = 0
    price_after_discount = None
    
    if plan_id:
        cursor.execute('SELECT price FROM plans WHERE id = %s', (plan_id,))
        plan = cursor.fetchone()
        
        if plan:
            price = float(plan['price'])
            
            if promo['discount_type'] == 'percent':
                discount_amount = price * (float(promo['discount_value']) / 100)
            elif promo['discount_type'] == 'fixed':
                discount_amount = float(promo['discount_value'])
                if discount_amount > price:
                    discount_amount = price
            
            price_after_discount = price - discount_amount
            if price_after_discount < 0:
                price_after_discount = 0
    
    cursor.close()
    conn.close()
    
    # Преобразуем Decimal в float для JSON сериализации
    promo_data = {
        'id': promo['id'],
        'code': promo['code'],
        'discount_type': promo['discount_type'],
        'discount_value': float(promo['discount_value']),
        'bonus_requests': promo['bonus_requests']
    }
    
    return jsonify({
        'success': True,
        'promo': promo_data,
        'discount_amount': discount_amount if plan_id else None,
        'price_after_discount': price_after_discount if plan_id else None,
        'bonus_requests': promo['bonus_requests']
    })

# Реферальная система

@app.route('/api/referrals', methods=['GET'])
@token_required
def get_referrals(current_user):
    """Получение списка приглашенных пользователей"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT id, username, created_at
        FROM users 
        WHERE referrer_id = %s
        ORDER BY created_at DESC
        """,
        (current_user['id'],)
    )
    
    referrals = cursor.fetchall()
    
    # Подсчет оплат от приглашенных пользователей
    cursor.execute(
        """
        SELECT SUM(p.amount) as total_amount
        FROM payments p
        JOIN users u ON p.user_id = u.id
        WHERE u.referrer_id = %s
        """,
        (current_user['id'],)
    )
    
    total = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    # Преобразование datetime в строки для JSON
    for ref in referrals:
        ref['created_at'] = ref['created_at'].isoformat() if ref['created_at'] else None
    
    return jsonify({
        'referrals': referrals,
        'total_count': len(referrals),
        'total_earnings': total['total_amount'] if total['total_amount'] else 0
    })

# Запуск сервера
if __name__ == '__main__':
    port = int(os.getenv('API_PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port) 