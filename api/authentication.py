from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from bot_admin.models import BotUser


class TelegramIDAuthentication(authentication.BaseAuthentication):
    """
    Аутентификация пользователей по Telegram ID.
    Ищет telegram_id в заголовке X-Telegram-ID, параметрах URL, или теле запроса.
    """
    
    def authenticate(self, request):
        # Ищем telegram_id в разных местах
        telegram_id = None
        if 'HTTP_X_TELEGRAM_ID' in request.META:
            telegram_id = request.META.get('HTTP_X_TELEGRAM_ID')
        elif 'telegram_id' in request.query_params:
            telegram_id = request.query_params.get('telegram_id')
        elif request.content_type == 'application/json' and hasattr(request, 'data') and 'telegram_id' in request.data:
             # Проверяем тело запроса (request.data) только для JSON
            telegram_id = request.data.get('telegram_id')

        if not telegram_id:
            # Если telegram_id не найден нигде, аутентификация не удалась для этого метода
            return None 
        
        try:
            user = BotUser.objects.get(telegram_id=telegram_id)
            
            if not user.is_active:
                raise AuthenticationFailed('Пользователь неактивен')
                
            return (user, None) # Успешная аутентификация
        except BotUser.DoesNotExist:
            # Если пользователь не найден, но ID был предоставлен,
            # это явная ошибка аутентификации (кроме случаев, когда это просто проверка ID)
            # Не вызываем ошибку, чтобы представление могло обработать 404
            return None 
        except Exception as e:
            # Другие возможные ошибки (например, с БД)
            raise AuthenticationFailed(f'Ошибка аутентификации: {str(e)}')

    def authenticate_header(self, request):
        return 'TelegramID' 