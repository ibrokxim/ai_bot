from rest_framework import serializers
from bot_admin.models import BotUser, Plan, UserPlan, RequestUsage, UserStatistics, PromoCode, Payment, Chat, ChatMessage


class BotUserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя бота"""
    
    class Meta:
        model = BotUser
        fields = ['user_id', 'telegram_id', 'username', 'first_name', 'last_name', 
                  'language_code', 'contact', 'is_active', 'requests_left', 'registration_date']
        read_only_fields = ['user_id', 'telegram_id', 'registration_date', 'requests_left']


class PlanSerializer(serializers.ModelSerializer):
    """Сериализатор для тарифного плана"""
    
    class Meta:
        model = Plan
        fields = '__all__'


class UserPlanSerializer(serializers.ModelSerializer):
    """Сериализатор для плана пользователя"""
    plan_details = PlanSerializer(source='plan', read_only=True)
    
    class Meta:
        model = UserPlan
        fields = ['id', 'user', 'plan', 'plan_details', 'activated_at', 'expired_at', 
                  'is_active', 'price_paid', 'is_auto_renewal', 'requests_added']
        read_only_fields = ['id', 'activated_at']


class RequestUsageSerializer(serializers.ModelSerializer):
    """Сериализатор для использования запросов"""
    
    class Meta:
        model = RequestUsage
        fields = ['id', 'user', 'request_type', 'ai_model', 'tokens_used', 
                  'request_date', 'response_time', 'was_successful', 
                  'request_text', 'response_length']
        read_only_fields = ['id', 'request_date']


class UserStatisticsSerializer(serializers.ModelSerializer):
    """Сериализатор для статистики пользователя"""
    
    class Meta:
        model = UserStatistics
        fields = ['id', 'user', 'total_requests', 'total_tokens', 'last_active', 
                  'total_payments', 'total_referrals', 'favorite_model', 'account_level']
        read_only_fields = ['id', 'total_requests', 'total_tokens', 'last_active', 
                           'total_payments', 'total_referrals']


class PromoCodeSerializer(serializers.ModelSerializer):
    """Сериализатор для промокодов"""
    
    class Meta:
        model = PromoCode
        fields = ['id', 'code', 'discount_type', 'discount_value', 'bonus_requests', 
                  'valid_from', 'valid_to', 'is_active', 'max_usages', 'usages_count', 
                  'allowed_plans', 'created_at']
        read_only_fields = ['id', 'created_at', 'usages_count']


class PaymentSerializer(serializers.ModelSerializer):
    """Сериализатор для платежей"""
    
    class Meta:
        model = Payment
        fields = ['id', 'user', 'user_plan', 'amount', 'currency', 'payment_date', 
                  'payment_system', 'payment_id', 'status', 'details']
        read_only_fields = ['id', 'payment_date']


class UserRegistrationSerializer(serializers.Serializer):
    """Сериализатор для регистрации пользователя"""
    telegram_id = serializers.IntegerField(required=True)
    username = serializers.CharField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    is_bot = serializers.BooleanField(required=False, default=False)
    language_code = serializers.CharField(required=False, default='ru')
    chat_id = serializers.IntegerField(required=True)
    contact = serializers.CharField(required=False, allow_blank=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)


class UserContactSerializer(serializers.ModelSerializer):
    """Сериализатор для получения и обновления контакта пользователя"""
    class Meta:
        model = BotUser
        fields = ['contact']
        # Добавляем параметры, если нужно разрешить пустое значение или null
        extra_kwargs = {
            'contact': {'required': False, 'allow_blank': True, 'allow_null': True}
        }


class UserLoginSerializer(serializers.Serializer):
    """Сериализатор для авторизации пользователя"""
    telegram_id = serializers.IntegerField(required=True)
    
    
class PromoValidationSerializer(serializers.Serializer):
    """Сериализатор для проверки промокода"""
    code = serializers.CharField(required=True)
    plan_id = serializers.IntegerField(required=False)


class UseRequestSerializer(serializers.Serializer):
    """Сериализатор для использования запроса"""
    request_type = serializers.CharField(required=True)
    ai_model = serializers.CharField(required=True)
    tokens_used = serializers.IntegerField(required=True)
    request_text = serializers.CharField(required=False, allow_blank=True)
    response_length = serializers.IntegerField(required=False, default=0)
    response_time = serializers.FloatField(required=False)
    was_successful = serializers.BooleanField(required=False, default=True)


# Сериализаторы для чатов

class ChatSerializer(serializers.ModelSerializer):
    """Сериализатор для чата"""
    ai_model_display = serializers.CharField(source='get_ai_model_display', read_only=True)
    
    class Meta:
        model = Chat
        fields = ['id', 'user', 'title', 'ai_model', 'ai_model_display', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

class ChatMessageSerializer(serializers.ModelSerializer):
    """Сериализатор для сообщения в чате"""
    class Meta:
        model = ChatMessage
        fields = ['id', 'chat', 'role', 'content', 'model_used', 'tokens_used', 'timestamp']
        read_only_fields = ['timestamp']
        extra_kwargs = {
            'chat': {'write_only': True}, # Не показываем ID чата при чтении сообщений
            'model_used': {'read_only': True}, # Заполняется сервером
            'tokens_used': {'read_only': True}, # Заполняется сервером
            'role': {'read_only': True} # Заполняется сервером
        } 