"""
Маршруты для аутентификации и регистрации пользователей
"""

import datetime
import jwt
import secrets
import hashlib
from flask import Blueprint, request, jsonify
from database import Database
import os

# Создаем блюпринт для аутентификации
auth_bp = Blueprint('auth', __name__)

# Секретный ключ для JWT из переменных окружения
JWT_SECRET = os.environ.get('JWT_SECRET', 'default_secret_key')
JWT_EXPIRES = int(os.environ.get('JWT_EXPIRES', 86400))  # 24 часа по умолчанию

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Авторизация пользователя и выдача JWT токена
    """
    data = request.get_json()
    
    # Проверяем наличие обязательных полей
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({
            'success': False,
            'message': 'Необходимо указать имя пользователя и пароль'
        }), 400
    
    username = data['username']
    password = data['password']
    
    # Хешируем пароль для сравнения
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    # Получаем пользователя из БД
    user = Database.get_user_by_username(username)
    
    if not user or user['password'] != hashed_password:
        return jsonify({
            'success': False,
            'message': 'Неверное имя пользователя или пароль'
        }), 401
    
    # Генерируем JWT токен
    token_payload = {
        'user_id': user['id'],
        'username': user['username'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRES)
    }
    
    token = jwt.encode(token_payload, JWT_SECRET, algorithm='HS256')
    
    return jsonify({
        'success': True,
        'token': token,
        'user_id': user['id'],
        'expires_in': JWT_EXPIRES
    })

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Регистрация нового пользователя
    """
    data = request.get_json()
    
    # Проверяем наличие обязательных полей
    required_fields = ['username', 'password', 'email', 'phone']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return jsonify({
            'success': False,
            'message': f'Отсутствуют обязательные поля: {", ".join(missing_fields)}'
        }), 400
    
    username = data['username']
    password = data['password']
    email = data['email']
    phone = data['phone']
    
    # Проверяем, существует ли пользователь с таким же именем
    existing_user = Database.get_user_by_username(username)
    if existing_user:
        return jsonify({
            'success': False,
            'message': 'Пользователь с таким именем уже существует'
        }), 409
    
    # Хешируем пароль для хранения
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    # Генерируем реферальный код
    referral_code = secrets.token_hex(3).upper()
    
    # Создаем пользователя
    query = """
    INSERT INTO users (username, password, email, phone, referral_code, created_at)
    VALUES (%s, %s, %s, %s, %s, NOW())
    """
    params = (username, hashed_password, email, phone, referral_code)
    
    try:
        user_id = Database.execute_query(query, params, commit=True)
        
        # Создаем запись в статистике пользователя
        stats_query = """
        INSERT INTO user_stats (user_id, total_requests, created_at)
        VALUES (%s, 0, NOW())
        """
        Database.execute_query(stats_query, (user_id,), commit=True)
        
        # Генерируем JWT токен для нового пользователя
        token_payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRES)
        }
        
        token = jwt.encode(token_payload, JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            'success': True,
            'message': 'Пользователь успешно зарегистрирован',
            'user_id': user_id,
            'token': token,
            'expires_in': JWT_EXPIRES
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка при регистрации: {str(e)}'
        }), 500
    
@auth_bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    """
    Обновление JWT токена
    """
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({
            'success': False,
            'message': 'Отсутствует или некорректный токен авторизации'
        }), 401
    
    token = auth_header.split(' ')[1]
    
    try:
        # Пытаемся декодировать токен
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        user_id = payload['user_id']
        username = payload['username']
        
        # Проверяем существование пользователя
        user = Database.get_user_by_id(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'Пользователь не найден'
            }), 404
        
        # Генерируем новый JWT токен
        new_token_payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRES)
        }
        
        new_token = jwt.encode(new_token_payload, JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            'success': True,
            'token': new_token,
            'expires_in': JWT_EXPIRES
        })
    except jwt.ExpiredSignatureError:
        return jsonify({
            'success': False,
            'message': 'Срок действия токена истек'
        }), 401
    except (jwt.InvalidTokenError, Exception) as e:
        return jsonify({
            'success': False,
            'message': f'Некорректный токен: {str(e)}'
        }), 401

# Импортируем этот блюпринт в основной модуль routes/__init__.py
from . import api_blueprint
api_blueprint.register_blueprint(auth_bp) 