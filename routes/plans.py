"""
Маршруты для управления планами подписки
"""

from flask import Blueprint, request, jsonify, g
from database import Database
from middleware.auth import token_required
import os
import datetime

# Создаем блюпринт для планов подписки
plans_bp = Blueprint('plans', __name__)

@plans_bp.route('/', methods=['GET'])
def get_all_plans():
    """
    Получение всех доступных планов подписки
    """
    query = """
    SELECT id, name, description, request_limit, price, validity_days, 
           is_active, created_at, updated_at
    FROM plans
    WHERE is_active = 1
    ORDER BY price ASC
    """
    plans = Database.fetch_all(query)
    
    return jsonify({
        'success': True,
        'plans': plans
    })

@plans_bp.route('/<int:plan_id>', methods=['GET'])
def get_plan_details(plan_id):
    """
    Получение детальной информации о конкретном плане
    """
    query = """
    SELECT id, name, description, request_limit, price, validity_days, 
           is_active, created_at, updated_at
    FROM plans
    WHERE id = %s AND is_active = 1
    """
    plan = Database.fetch_one(query, (plan_id,))
    
    if not plan:
        return jsonify({
            'success': False,
            'message': 'План не найден или не активен'
        }), 404
    
    return jsonify({
        'success': True,
        'plan': plan
    })

@plans_bp.route('/subscribe', methods=['POST'])
@token_required
def subscribe_to_plan():
    """
    Подписка пользователя на план
    """
    user_id = g.user_id
    data = request.get_json()
    
    if not data or 'plan_id' not in data:
        return jsonify({
            'success': False,
            'message': 'Необходимо указать ID плана'
        }), 400
    
    plan_id = data['plan_id']
    
    # Проверяем существование плана
    plan_query = """
    SELECT id, name, request_limit, price, validity_days
    FROM plans
    WHERE id = %s AND is_active = 1
    """
    plan = Database.fetch_one(plan_query, (plan_id,))
    
    if not plan:
        return jsonify({
            'success': False,
            'message': 'План не найден или не активен'
        }), 404
    
    # Проверяем, есть ли у пользователя активная подписка на этот план
    active_sub_query = """
    SELECT id, end_date
    FROM user_subscriptions
    WHERE user_id = %s AND plan_id = %s AND is_active = 1 AND end_date >= CURDATE()
    """
    active_sub = Database.fetch_one(active_sub_query, (user_id, plan_id))
    
    # Применяем промокод, если указан
    discount = 0
    promo_id = None
    
    if 'promo_code' in data and data['promo_code']:
        promo_query = """
        SELECT id, discount_percent, max_usage, current_usage
        FROM promo_codes
        WHERE code = %s AND expiry_date >= CURDATE() AND is_active = 1
        """
        promo = Database.fetch_one(promo_query, (data['promo_code'],))
        
        if promo and (promo['max_usage'] == 0 or promo['current_usage'] < promo['max_usage']):
            discount = promo['discount_percent']
            promo_id = promo['id']
            
            # Увеличиваем счетчик использования промокода
            update_promo_query = """
            UPDATE promo_codes
            SET current_usage = current_usage + 1
            WHERE id = %s
            """
            Database.execute_query(update_promo_query, (promo_id,), commit=True)
    
    # Рассчитываем стоимость с учетом скидки
    final_price = plan['price'] * (1 - discount / 100)
    
    try:
        # Начинаем транзакцию
        Database.start_transaction()
        
        # Создаем запись о платеже (в реальном приложении здесь была бы интеграция с платежной системой)
        payment_query = """
        INSERT INTO payments (user_id, amount, status, payment_method, description)
        VALUES (%s, %s, %s, %s, %s)
        """
        payment_description = f"Подписка на план: {plan['name']}"
        payment_params = (user_id, final_price, 'completed', 'card', payment_description)
        payment_id = Database.execute_query(payment_query, payment_params, get_last_id=True)
        
        # Определяем даты начала и окончания подписки
        start_date = datetime.date.today()
        
        # Если у пользователя уже есть активная подписка на этот план, продлеваем ее
        if active_sub:
            end_date = active_sub['end_date'] + datetime.timedelta(days=plan['validity_days'])
            
            # Обновляем существующую подписку
            update_sub_query = """
            UPDATE user_subscriptions
            SET end_date = %s, updated_at = NOW()
            WHERE id = %s
            """
            Database.execute_query(update_sub_query, (end_date, active_sub['id']), commit=False)
        else:
            # Создаем новую подписку
            end_date = start_date + datetime.timedelta(days=plan['validity_days'])
            
            sub_query = """
            INSERT INTO user_subscriptions (user_id, plan_id, start_date, end_date, is_active, payment_id, promo_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            sub_params = (user_id, plan_id, start_date, end_date, 1, payment_id, promo_id)
            Database.execute_query(sub_query, sub_params, commit=False)
        
        # Фиксируем транзакцию
        Database.commit_transaction()
        
        return jsonify({
            'success': True,
            'message': 'Подписка успешно оформлена',
            'subscription': {
                'plan_id': plan_id,
                'plan_name': plan['name'],
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'price': final_price,
                'original_price': plan['price'],
                'discount': discount
            }
        })
        
    except Exception as e:
        # Откатываем транзакцию в случае ошибки
        Database.rollback_transaction()
        return jsonify({
            'success': False,
            'message': f'Ошибка при оформлении подписки: {str(e)}'
        }), 500

@plans_bp.route('/my', methods=['GET'])
@token_required
def get_user_subscriptions():
    """
    Получение всех подписок пользователя
    """
    user_id = g.user_id
    
    # Получаем все подписки пользователя
    query = """
    SELECT us.id, us.user_id, us.plan_id, us.start_date, us.end_date, 
           us.is_active, us.created_at, us.updated_at,
           p.name as plan_name, p.description, p.request_limit, p.price, p.validity_days
    FROM user_subscriptions us
    JOIN plans p ON us.plan_id = p.id
    WHERE us.user_id = %s
    ORDER BY us.end_date DESC
    """
    subscriptions = Database.fetch_all(query, (user_id,))
    
    # Разделяем подписки на активные и истекшие
    active_subs = []
    expired_subs = []
    today = datetime.date.today()
    
    for sub in subscriptions:
        sub['start_date'] = sub['start_date'].isoformat() if sub['start_date'] else None
        sub['end_date'] = sub['end_date'].isoformat() if sub['end_date'] else None
        sub['created_at'] = sub['created_at'].isoformat() if sub['created_at'] else None
        sub['updated_at'] = sub['updated_at'].isoformat() if sub['updated_at'] else None
        
        if sub['is_active'] and sub['end_date'] and datetime.date.fromisoformat(sub['end_date']) >= today:
            active_subs.append(sub)
        else:
            expired_subs.append(sub)
    
    return jsonify({
        'success': True,
        'active_subscriptions': active_subs,
        'expired_subscriptions': expired_subs
    })

@plans_bp.route('/cancel/<int:subscription_id>', methods=['POST'])
@token_required
def cancel_subscription(subscription_id):
    """
    Отмена подписки пользователя
    """
    user_id = g.user_id
    
    # Проверяем существование подписки и принадлежность пользователю
    query = """
    SELECT id, user_id, is_active
    FROM user_subscriptions
    WHERE id = %s
    """
    subscription = Database.fetch_one(query, (subscription_id,))
    
    if not subscription:
        return jsonify({
            'success': False,
            'message': 'Подписка не найдена'
        }), 404
    
    if subscription['user_id'] != user_id:
        return jsonify({
            'success': False,
            'message': 'У вас нет прав для отмены этой подписки'
        }), 403
    
    if not subscription['is_active']:
        return jsonify({
            'success': False,
            'message': 'Подписка уже отменена'
        }), 400
    
    # Отменяем подписку
    update_query = """
    UPDATE user_subscriptions
    SET is_active = 0, updated_at = NOW()
    WHERE id = %s
    """
    
    try:
        Database.execute_query(update_query, (subscription_id,), commit=True)
        return jsonify({
            'success': True,
            'message': 'Подписка успешно отменена'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка при отмене подписки: {str(e)}'
        }), 500

# Регистрируем блюпринт
from . import api_blueprint
api_blueprint.register_blueprint(plans_bp, url_prefix='/plans') 