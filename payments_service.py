import mysql.connector
from mysql.connector import Error
import os
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

class PaymentService:
    def __init__(self):
        """Инициализация сервиса платежей"""
        self.config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'ai_bot'),
            'charset': os.getenv('DB_CHARSET', 'utf8mb4')
        }
        self.connection = None
            
    def connect(self):
        """Установка соединения с базой данных"""
        try:
            connection = mysql.connector.connect(**self.config)
            if connection.is_connected():
                return connection
        except Error as e:
            print(f"Ошибка при подключении к MySQL: {e}")
        return None
    
    def process_plan_purchase(self, user_id: int, plan_id: int, payment_details=None, promo_code=None, source='bot'):
        """
        Обрабатывает покупку тарифного плана и обновляет количество запросов пользователя
        
        Args:
            user_id: ID пользователя
            plan_id: ID тарифного плана
            payment_details: Детали платежа (словарь с payment_id, amount, payment_system, status)
            promo_code: Код промокода (если использовался)
            source: Источник покупки (bot, web, admin)
            
        Returns:
            bool: Успешность операции
            dict: Детали операции
        """
        conn = self.connect()
        if conn is None:
            return False, {"error": "Ошибка подключения к базе данных"}
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Получаем информацию о тарифном плане
            cursor.execute("SELECT * FROM plans WHERE id = %s", (plan_id,))
            plan = cursor.fetchone()
            
            if not plan:
                return False, {"error": "Тарифный план не найден"}
            
            # Применяем промокод, если он указан
            discount_amount = 0
            bonus_requests = 0
            promo_id = None
            
            if promo_code:
                promo_details = self._apply_promo_code(cursor, promo_code, user_id, plan_id)
                if promo_details:
                    discount_amount = promo_details.get('discount_amount', 0)
                    bonus_requests = promo_details.get('bonus_requests', 0)
                    promo_id = promo_details.get('promo_id')
            
            # Рассчитываем фактическую стоимость
            price_paid = float(plan['price']) - discount_amount
            if price_paid < 0:
                price_paid = 0
                
            # Рассчитываем количество запросов для добавления
            requests_to_add = plan['requests'] + bonus_requests
            
            # Создаем запись о платеже, если предоставлены детали платежа
            payment_id = None
            if payment_details:
                payment_system = payment_details.get('payment_system', 'unknown')
                external_payment_id = payment_details.get('payment_id', '')
                amount = payment_details.get('amount', price_paid)
                status = payment_details.get('status', 'completed')
                
                cursor.execute("""
                    INSERT INTO payments 
                    (user_id, amount, currency, payment_system, payment_id, status, details) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id, 
                    amount, 
                    'RUB', 
                    payment_system, 
                    external_payment_id, 
                    status,
                    json.dumps(payment_details)
                ))
                payment_id = cursor.lastrowid
            
            # Рассчитываем дату истечения, если у плана есть длительность
            expired_at = None
            if plan['duration_days'] > 0:
                expired_at = (datetime.now() + timedelta(days=plan['duration_days'])).strftime('%Y-%m-%d %H:%M:%S')
            
            # Делаем все предыдущие планы пользователя неактивными
            if plan['is_subscription']:
                cursor.execute("""
                    UPDATE user_plans 
                    SET is_active = FALSE
                    WHERE user_id = %s AND is_active = TRUE
                """, (user_id,))
            
            # Добавляем новый план пользователю
            cursor.execute("""
                INSERT INTO user_plans 
                (user_id, plan_id, expired_at, is_active, payment_id, price_paid, is_auto_renewal, source, requests_added, discount_applied) 
                VALUES (%s, %s, %s, TRUE, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, 
                plan_id,
                expired_at,
                payment_id,
                price_paid,
                plan['is_subscription'],
                source,
                requests_to_add,
                discount_amount
            ))
            user_plan_id = cursor.lastrowid
            
            # Обновляем платеж с id созданного плана
            if payment_id:
                cursor.execute("UPDATE payments SET user_plan_id = %s WHERE id = %s", (user_plan_id, payment_id))
            
            # Регистрируем использование промокода
            if promo_id:
                cursor.execute("""
                    INSERT INTO promo_code_usages 
                    (promo_code_id, user_id, applied_to_plan_id, discount_amount, requests_added) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (promo_id, user_id, plan_id, discount_amount, bonus_requests))
                
                # Увеличиваем счетчик использований промокода
                cursor.execute("UPDATE promo_codes SET usages_count = usages_count + 1 WHERE id = %s", (promo_id,))
            
            # Обновляем количество запросов пользователя
            cursor.execute("""
                UPDATE users 
                SET requests_left = requests_left + %s
                WHERE user_id = %s
            """, (requests_to_add, user_id))
            
            # Обновляем статистику пользователя
            self._update_user_statistics(cursor, user_id, payment_amount=price_paid)
            
            conn.commit()
            
            return True, {
                "plan": plan['name'],
                "price_paid": price_paid,
                "requests_added": requests_to_add,
                "expired_at": expired_at,
                "plan_id": plan_id,
                "user_plan_id": user_plan_id
            }
            
        except Error as e:
            print(f"Ошибка при обработке покупки: {e}")
            return False, {"error": str(e)}
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def _apply_promo_code(self, cursor, promo_code, user_id, plan_id):
        """Применяет промокод и возвращает скидку и бонусные запросы"""
        try:
            # Получаем информацию о промокоде
            cursor.execute("""
                SELECT * FROM promo_codes 
                WHERE code = %s 
                AND is_active = TRUE 
                AND (valid_to IS NULL OR valid_to > NOW())
                AND (max_usages = 0 OR usages_count < max_usages)
            """, (promo_code,))
            
            promo = cursor.fetchone()
            if not promo:
                return None
                
            # Проверяем, что промокод применим к данному плану
            if promo['allowed_plans']:
                allowed_plans = promo['allowed_plans'].split(',')
                if str(plan_id) not in allowed_plans:
                    return None
            
            # Проверяем, использовал ли пользователь этот промокод ранее
            cursor.execute("""
                SELECT COUNT(*) as count FROM promo_code_usages 
                WHERE promo_code_id = %s AND user_id = %s
            """, (promo['id'], user_id))
            
            usage_count = cursor.fetchone()['count']
            if usage_count > 0:
                return None
            
            # Получаем информацию о плане
            cursor.execute("SELECT price FROM plans WHERE id = %s", (plan_id,))
            plan = cursor.fetchone()
            
            # Рассчитываем скидку
            discount_amount = 0
            if promo['discount_type'] == 'percent':
                discount_amount = float(plan['price']) * (float(promo['discount_value']) / 100)
            elif promo['discount_type'] == 'fixed':
                discount_amount = float(promo['discount_value'])
                if discount_amount > float(plan['price']):
                    discount_amount = float(plan['price'])
            
            return {
                'promo_id': promo['id'],
                'discount_amount': discount_amount,
                'bonus_requests': promo['bonus_requests']
            }
            
        except Error as e:
            print(f"Ошибка при применении промокода: {e}")
            return None
    
    def _update_user_statistics(self, cursor, user_id, payment_amount=0):
        """Обновляет статистику пользователя"""
        try:
            # Проверяем, существует ли запись статистики для пользователя
            cursor.execute("SELECT id FROM user_statistics WHERE user_id = %s", (user_id,))
            stats = cursor.fetchone()
            
            if stats:
                # Обновляем существующую запись
                cursor.execute("""
                    UPDATE user_statistics 
                    SET total_payments = total_payments + %s,
                        last_active = NOW()
                    WHERE user_id = %s
                """, (payment_amount, user_id))
            else:
                # Создаем новую запись
                cursor.execute("""
                    INSERT INTO user_statistics 
                    (user_id, total_payments, last_active) 
                    VALUES (%s, %s, NOW())
                """, (user_id, payment_amount))
                
        except Error as e:
            print(f"Ошибка при обновлении статистики: {e}")
            
    def get_user_requests_left(self, user_id):
        """Получает количество оставшихся запросов у пользователя"""
        conn = self.connect()
        if conn is None:
            return 0
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT requests_left FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Error as e:
            print(f"Ошибка при получении количества запросов: {e}")
            return 0
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
                
    def decrement_user_requests(self, user_id):
        """Уменьшает количество оставшихся запросов пользователя на 1"""
        conn = self.connect()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET requests_left = requests_left - 1
                WHERE user_id = %s AND requests_left > 0
            """, (user_id,))
            conn.commit()
            
            # Получаем обновленное количество запросов
            cursor.execute("SELECT requests_left FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            
            return result[0] if result else 0
        except Error as e:
            print(f"Ошибка при уменьшении количества запросов: {e}")
            return -1
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def add_usage_record(self, user_id, request_type, ai_model, tokens_used=0, was_successful=True, 
                         request_text=None, response_length=0, response_time=None):
        """Добавляет запись об использовании API"""
        conn = self.connect()
        if conn is None:
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO request_usage 
                (user_id, request_type, ai_model, tokens_used, was_successful, request_text, response_length, response_time) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, 
                request_type, 
                ai_model, 
                tokens_used, 
                was_successful, 
                request_text[:100] if request_text else None,  # Сохраняем только первые 100 символов
                response_length,
                response_time
            ))
            
            # Обновляем статистику пользователя
            cursor.execute("""
                UPDATE user_statistics 
                SET total_requests = total_requests + 1,
                    total_tokens = total_tokens + %s,
                    last_active = NOW()
                WHERE user_id = %s
            """, (tokens_used, user_id))
            
            # Если запись статистики еще не существует, создаем ее
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO user_statistics 
                    (user_id, total_requests, total_tokens, last_active) 
                    VALUES (%s, 1, %s, NOW())
                """, (user_id, tokens_used))
            
            conn.commit()
            return True
        except Error as e:
            print(f"Ошибка при добавлении записи использования: {e}")
            return False
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close() 