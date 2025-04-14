"""
Маршруты для управления пользовательской информацией
"""

from flask import Blueprint, request, jsonify, g
from database import Database
from middleware.auth import token_required
import os
import hashlib

# Создаем блюпринт для пользователей
users_bp = Blueprint('users', __name__)

@users_bp.route('/profile', methods=['GET'])
@token_required
def get_user_profile():
    """
    Получение профиля текущего пользователя
    """
    user_id = g.user_id
    
    # Получаем данные пользователя
    query = """
    SELECT u.id, u.username, u.email, u.phone, u.referral_code,
           u.referrer_id, u.created_at, us.total_requests
    FROM users u
    JOIN user_stats us ON u.id = us.user_id
    WHERE u.id = %s
    """
    user = Database.fetch_one(query, (user_id,))
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'Пользователь не найден'
        }), 404
    
    # Получаем активные подписки пользователя
    active_plans_query = """
    SELECT p.id, p.name, p.description, p.request_limit, p.price, 
           p.validity_days, us.start_date, us.end_date
    FROM user_subscriptions us
    JOIN plans p ON us.plan_id = p.id
    WHERE us.user_id = %s AND us.is_active = 1 AND us.end_date >= CURDATE()
    """
    active_plans = Database.fetch_all(active_plans_query, (user_id,))
    
    # Получаем количество рефералов
    referrals_query = """
    SELECT COUNT(*) as referral_count
    FROM users
    WHERE referrer_id = %s
    """
    referral_result = Database.fetch_one(referrals_query, (user_id,))
    referral_count = referral_result['referral_count'] if referral_result else 0
    
    # Формируем ответ
    response = {
        'success': True,
        'profile': {
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'phone': user['phone'],
            'referral_code': user['referral_code'],
            'referrer_id': user['referrer_id'],
            'created_at': user['created_at'].isoformat() if user['created_at'] else None,
            'total_requests': user['total_requests'],
            'referral_count': referral_count,
            'active_plans': active_plans
        }
    }
    
    return jsonify(response)

@users_bp.route('/profile', methods=['PUT'])
@token_required
def update_user_profile():
    """
    Обновление профиля пользователя
    """
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'Отсутствуют данные для обновления'
        }), 400
    
    # Получаем текущие данные пользователя
    user = Database.get_user_by_id(user_id)
    if not user:
        return jsonify({
            'success': False,
            'message': 'Пользователь не найден'
        }), 404
    
    # Поля, которые можно обновить
    allowed_fields = ['email', 'phone']
    update_fields = []
    params = []
    
    for field in allowed_fields:
        if field in data and data[field] != user[field]:
            update_fields.append(f"{field} = %s")
            params.append(data[field])
    
    # Проверяем смену пароля
    if 'password' in data and 'current_password' in data:
        current_hashed = hashlib.sha256(data['current_password'].encode()).hexdigest()
        
        if current_hashed != user['password']:
            return jsonify({
                'success': False,
                'message': 'Текущий пароль указан неверно'
            }), 400
        
        new_hashed = hashlib.sha256(data['password'].encode()).hexdigest()
        update_fields.append("password = %s")
        params.append(new_hashed)
    
    if not update_fields:
        return jsonify({
            'success': False,
            'message': 'Нет данных для обновления'
        }), 400
    
    # Выполняем обновление
    query = f"""
    UPDATE users 
    SET {', '.join(update_fields)}, updated_at = NOW()
    WHERE id = %s
    """
    params.append(user_id)
    
    try:
        Database.execute_query(query, params, commit=True)
        return jsonify({
            'success': True,
            'message': 'Профиль успешно обновлен'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка при обновлении профиля: {str(e)}'
        }), 500

@users_bp.route('/stats', methods=['GET'])
@token_required
def get_user_stats():
    """
    Получение статистики пользователя
    """
    user_id = g.user_id
    
    # Получаем статистику пользователя
    query = """
    SELECT total_requests, last_request_date, created_at, updated_at
    FROM user_stats
    WHERE user_id = %s
    """
    stats = Database.fetch_one(query, (user_id,))
    
    if not stats:
        return jsonify({
            'success': False,
            'message': 'Статистика не найдена'
        }), 404
    
    # Подсчитываем количество запросов за текущий месяц
    month_query = """
    SELECT COUNT(*) as monthly_requests
    FROM requests
    WHERE user_id = %s AND MONTH(created_at) = MONTH(CURRENT_DATE()) 
    AND YEAR(created_at) = YEAR(CURRENT_DATE())
    """
    month_result = Database.fetch_one(month_query, (user_id,))
    monthly_requests = month_result['monthly_requests'] if month_result else 0
    
    # Получаем историю запросов (последние 10)
    requests_query = """
    SELECT id, prompt, created_at, status
    FROM requests
    WHERE user_id = %s
    ORDER BY created_at DESC
    LIMIT 10
    """
    recent_requests = Database.fetch_all(requests_query, (user_id,))
    
    return jsonify({
        'success': True,
        'stats': {
            'total_requests': stats['total_requests'],
            'monthly_requests': monthly_requests,
            'last_request_date': stats['last_request_date'].isoformat() if stats['last_request_date'] else None,
            'created_at': stats['created_at'].isoformat() if stats['created_at'] else None,
            'updated_at': stats['updated_at'].isoformat() if stats['updated_at'] else None,
            'recent_requests': recent_requests
        }
    })

# Регистрируем блюпринт
from . import api_blueprint
api_blueprint.register_blueprint(users_bp, url_prefix='/users') 