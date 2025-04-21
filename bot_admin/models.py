from django.db import models
from django.utils import timezone

# Create your models here.

class BotUser(models.Model):
    user_id = models.AutoField(primary_key=True)
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    is_bot = models.BooleanField()
    language_code = models.CharField(max_length=10, null=True, blank=True)
    chat_id = models.BigIntegerField()
    contact = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    requests_left = models.IntegerField(null=True, blank=True)
    registration_date = models.DateTimeField(default=timezone.now)

    @property
    def referral_code(self):
        """Получить активный реферальный код пользователя"""
        try:
            return self.referral_codes.filter(is_active=True).first().code
        except AttributeError:
            return None

    # Добавляем свойства для поддержки аутентификации в DRF
    @property
    def is_authenticated(self):
        """Метод требуется для работы с DRF"""
        return True
    
    @property
    def is_anonymous(self):
        """Метод требуется для работы с DRF"""
        return False
    
    # Добавляем дополнительные атрибуты для DRF auth
    @property
    def is_staff(self):
        return False
    
    def get_username(self):
        return str(self.telegram_id)
    
    def has_perm(self, perm, obj=None):
        return False
    
    def has_module_perms(self, app_label):
        return False

    class Meta:
        managed = True
        db_table = 'users'
        verbose_name = 'Пользователь бота'
        verbose_name_plural = 'Пользователи бота'
        ordering = ['-registration_date']

    def __str__(self):
        return f"{self.first_name} {self.last_name} (@{self.username})"

class ReferralCode(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, db_column='user_id', related_name='referral_codes')
    code = models.CharField(max_length=255, unique=True)
    registration_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    total_uses = models.IntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            # Генерируем код на основе имени пользователя или telegram_id
            base = self.user.username or str(self.user.telegram_id)
            # Берем первые 4 символа из base (в верхнем регистре) и добавляем 4 случайные цифры
            import random
            import string
            prefix = base[:4].upper()
            suffix = ''.join(random.choices(string.digits, k=4))
            self.code = f"{prefix}{suffix}"
        super().save(*args, **kwargs)

    class Meta:
        managed = True
        db_table = 'referral_codes'
        verbose_name = 'Реферальный код'
        verbose_name_plural = 'Реферальные коды'

    def __str__(self):
        return f"{self.code} ({self.user})"

class ReferralHistory(models.Model):
    id = models.AutoField(primary_key=True)
    referrer = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='referrals_sent', db_column='referrer_id')
    referred = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='referral_source', db_column='referred_id', null=True, blank=True)
    referral_code = models.ForeignKey(ReferralCode, on_delete=models.CASCADE, related_name='usage_history')
    created_at = models.DateTimeField(auto_now_add=True)
    bonus_requests_added = models.IntegerField(default=0)
    conversion_status = models.CharField(max_length=50, default='registered')
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = True
        db_table = 'referral_history'
        verbose_name = 'История реферралов'
        verbose_name_plural = 'История реферралов'
        ordering = ['-created_at']

    def __str__(self):
        referred_str = f" → {self.referred}" if self.referred else ""
        return f"{self.referrer}{referred_str} ({self.created_at})"

    def save(self, *args, **kwargs):
        # Увеличиваем счетчик использований реферального кода
        if self.referral_code:
            self.referral_code.total_uses += 1
            self.referral_code.last_used_at = self.created_at
            self.referral_code.save()
        super().save(*args, **kwargs)

class Plan(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    requests = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # Активен ли план для покупки
    duration_days = models.IntegerField(default=0)  # Длительность в днях (0 = бессрочно)
    description = models.TextField(null=True, blank=True)  # Описание плана
    priority = models.IntegerField(default=0)  # Приоритет для сортировки
    is_subscription = models.BooleanField(default=False)  # Это подписка или разовая покупка
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Скидка в %
    allowed_models = models.CharField(max_length=255, null=True, blank=True)  # Доступные модели ИИ (через запятую)
    max_tokens_per_request = models.IntegerField(null=True, blank=True)  # Максимум токенов на запрос
    features = models.JSONField(null=True, blank=True)  # Дополнительные возможности в формате JSON

    class Meta:
        managed = True  # Django будет управлять таблицей
        db_table = 'plans'
        verbose_name = 'Тарифный план'
        verbose_name_plural = 'Тарифные планы'
        ordering = ['priority', 'price']

    def __str__(self):
        return f"{self.name} ({self.requests} запросов, {self.price} руб.)"

class UserPlan(models.Model):
    """Модель связи пользователя с тарифным планом"""
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, db_column='user_id')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, db_column='plan_id')
    activated_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    payment_id = models.CharField(max_length=255, null=True, blank=True)  # ID платежа из платежной системы
    price_paid = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Фактически оплаченная сумма
    is_auto_renewal = models.BooleanField(default=False)  # Флаг автопродления подписки
    source = models.CharField(max_length=50, null=True, blank=True)  # Источник приобретения (веб, бот, админка)
    requests_added = models.IntegerField(default=0)  # Количество добавленных запросов
    discount_applied = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Применённая скидка в %
    notes = models.TextField(null=True, blank=True)  # Дополнительная информация
    
    class Meta:
        db_table = 'user_plans'
        verbose_name = 'Подписка пользователя'
        verbose_name_plural = 'Подписки пользователей'

    def __str__(self):
        return f"{self.user} - {self.plan}"

class Payment(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, db_column='user_id')
    user_plan = models.ForeignKey(UserPlan, on_delete=models.SET_NULL, null=True, blank=True, db_column='user_plan_id')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='RUB')
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_system = models.CharField(max_length=50)  # Название платежной системы
    payment_id = models.CharField(max_length=255)  # ID транзакции в платежной системе
    status = models.CharField(max_length=50)  # Статус платежа (успешно, ошибка, отмена)
    details = models.JSONField(null=True, blank=True)  # Детали платежа в JSON

    class Meta:
        managed = True  # Django будет управлять таблицей
        db_table = 'payments'
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.user} - {self.amount} {self.currency} ({self.status})"

class RequestUsage(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, db_column='user_id')
    request_type = models.CharField(max_length=50)  # Тип запроса (текст, изображение, голос и т.д.)
    ai_model = models.CharField(max_length=100)  # Используемая модель (GPT, Claude, и т.д.)
    tokens_used = models.IntegerField(default=0)  # Количество использованных токенов
    request_date = models.DateTimeField(auto_now_add=True)
    response_time = models.FloatField(null=True, blank=True)  # Время ответа в секундах
    was_successful = models.BooleanField(default=True)  # Был ли запрос успешным
    request_text = models.TextField(null=True, blank=True)  # Первые 100 символов запроса
    response_length = models.IntegerField(default=0)  # Длина ответа в символах

    class Meta:
        managed = True  # Django будет управлять таблицей
        db_table = 'request_usage'
        verbose_name = 'Использование запроса'
        verbose_name_plural = 'Использование запросов'
        ordering = ['-request_date']

    def __str__(self):
        return f"{self.user} - {self.request_type} ({self.request_date})"

class UserStatistics(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(BotUser, on_delete=models.CASCADE, db_column='user_id')
    total_requests = models.IntegerField(default=0)  # Общее количество запросов
    total_tokens = models.IntegerField(default=0)  # Общее количество использованных токенов
    last_active = models.DateTimeField(null=True, blank=True)  # Последняя активность
    total_payments = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Сумма всех платежей
    total_referrals = models.IntegerField(default=0)  # Количество приглашенных пользователей
    favorite_model = models.CharField(max_length=100, null=True, blank=True)  # Предпочитаемая модель ИИ
    account_level = models.CharField(max_length=50, default='standard')  # Уровень аккаунта

    class Meta:
        managed = True  # Django будет управлять таблицей
        db_table = 'user_statistics'
        verbose_name = 'Статистика пользователя'
        verbose_name_plural = 'Статистика пользователей'

    def __str__(self):
        return f"Статистика: {self.user}"

class PromoCode(models.Model):
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=[('percent', 'Процент'), ('fixed', 'Фиксированная сумма'), ('requests', 'Бонусные запросы')])
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)  # Значение скидки (в % или в рублях)
    bonus_requests = models.IntegerField(default=0)  # Бонусные запросы
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    max_usages = models.IntegerField(default=0)  # 0 = неограниченно
    usages_count = models.IntegerField(default=0)
    allowed_plans = models.CharField(max_length=255, null=True, blank=True)  # ID планов, к которым применим промокод (через запятую)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True  # Django будет управлять таблицей
        db_table = 'promo_codes'
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.discount_value} {self.get_discount_type_display()})"

class PromoCodeUsage(models.Model):
    """Модель для отслеживания использования промокодов"""
    id = models.AutoField(primary_key=True)
    promo_code = models.ForeignKey(PromoCode, on_delete=models.CASCADE, db_column='promo_code_id')
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, db_column='user_id')
    used_at = models.DateTimeField(auto_now_add=True)
    applied_to_plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, db_column='applied_to_plan_id')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    requests_added = models.IntegerField(default=0)

    class Meta:
        managed = True
        db_table = 'promo_code_usages'
        verbose_name = 'Использование промокода'
        verbose_name_plural = 'Использования промокодов'
        ordering = ['-used_at']

    def __str__(self):
        return f"{self.user} использовал {self.promo_code} ({self.used_at})"

# Модели для чатов

class Chat(models.Model):
    # Типы моделей ИИ
    AI_MODEL_CHOICES = [
        ('gpt-4o-mini', 'GPT-4o Mini'),
        ('claude-3-5', 'Claude 3.5'),
        ('claude-3-7', 'Claude 3.7'),
        ('gemini-2-flash', 'Gemini 2.0 Flash'),
        ('gpt-4', 'GPT-4'),
        ('gpt3-mini', 'GPT-3 Mini'),
        ('dall-e', 'DALL-E'),
        ('midjourney', 'Midjourney'),
    ]
    
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, db_column='user_id')
    title = models.CharField(max_length=255, default='Новый чат')
    ai_model = models.CharField(max_length=50, choices=AI_MODEL_CHOICES, default='gpt-4o-mini')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        managed = True # Или True, если хотите, чтобы Django создал таблицу
        db_table = 'chats'
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.user.username}) - {self.get_ai_model_display()}"

class ChatMessage(models.Model):
    id = models.AutoField(primary_key=True)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, db_column='chat_id')
    role = models.CharField(max_length=10) # 'user' или 'assistant'
    content = models.TextField()
    model_used = models.CharField(max_length=100, null=True, blank=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True # Или True
        db_table = 'chat_messages'
        verbose_name = 'Сообщение чата'
        verbose_name_plural = 'Сообщения чата'
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

class Request(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, db_column='user_id')
    query = models.TextField()
    response = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'requests'
        verbose_name = 'Запрос'
        verbose_name_plural = 'Запросы'

    def __str__(self):
        return f"{self.user}: {self.query[:50]}..."
