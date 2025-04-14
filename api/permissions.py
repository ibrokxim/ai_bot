from rest_framework import permissions


class IsTelegramUser(permissions.BasePermission):
    """
    Проверка прав доступа для пользователей Telegram
    Если в запросе есть параметр telegram_id, то проверка пропускается
    """
    
    def has_permission(self, request, view):
        # Если передан telegram_id в параметрах запроса, пропускаем проверку
        if request.query_params.get('telegram_id') or request.data.get('telegram_id'):
            return True
        
        # Проверяем, аутентифицирован ли пользователь и является ли он экземпляром BotUser
        return bool(request.user and hasattr(request.user, 'telegram_id'))


class CustomIsAuthenticated(permissions.BasePermission):
    """
    Замена стандартного IsAuthenticated, работающий с BotUser
    Пропускает запросы с telegram_id в параметрах запроса
    """
    def has_permission(self, request, view):
        # Если есть telegram_id в параметрах, пропускаем проверку
        if request.query_params.get('telegram_id') or request.data.get('telegram_id'):
            return True
        
        # Проверяем наличие пользователя, не используя is_authenticated
        return bool(request.user and hasattr(request.user, 'telegram_id'))


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Доступ на запись только владельцам объекта
    """
    
    def has_object_permission(self, request, view, obj):
        # Чтение разрешено для всех запросов
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Запись доступна только владельцу объекта
        return obj.user_id == request.user.user_id 