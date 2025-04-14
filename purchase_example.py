from payments_service import PaymentService
import sys
import datetime

def main():
    """Пример использования сервиса платежей"""
    
    # Проверка аргументов командной строки
    if len(sys.argv) < 4:
        print("Использование: python purchase_example.py user_id plan_id [promo_code]")
        return
    
    # Получение аргументов
    user_id = int(sys.argv[1])
    plan_id = int(sys.argv[2])
    promo_code = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Создание сервиса платежей
    payment_service = PaymentService()
    
    # Получение текущего количества запросов
    current_requests = payment_service.get_user_requests_left(user_id)
    print(f"Текущее количество запросов: {current_requests}")
    
    # Эмуляция данных о платеже
    payment_details = {
        'payment_id': f"test_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        'amount': 0,  # Будет установлено автоматически
        'payment_system': 'test',
        'status': 'completed',
        'details': {
            'test': True,
            'method': 'example'
        }
    }
    
    # Обработка покупки
    success, details = payment_service.process_plan_purchase(
        user_id=user_id, 
        plan_id=plan_id, 
        payment_details=payment_details,
        promo_code=promo_code,
        source='script'
    )
    
    # Вывод результата
    if success:
        print("Покупка успешно обработана!")
        print(f"Тарифный план: {details['plan']}")
        print(f"Оплаченная сумма: {details['price_paid']} руб.")
        print(f"Добавлено запросов: {details['requests_added']}")
        if details['expired_at']:
            print(f"Срок действия до: {details['expired_at']}")
        
        # Получение обновленного количества запросов
        new_requests = payment_service.get_user_requests_left(user_id)
        print(f"Новое количество запросов: {new_requests}")
    else:
        print("Ошибка при обработке покупки:")
        print(details)

if __name__ == "__main__":
    main() 