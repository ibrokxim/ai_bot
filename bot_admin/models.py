from django.db import models

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
    is_active = models.BooleanField(null=True, blank=True)
    requests_left = models.IntegerField(default=10, null=True, blank=True)
    registration_date = models.DateTimeField()

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
        managed = False  # Говорим Django не управлять таблицей
        db_table = 'users'  # Указываем имя существующей таблицы
        verbose_name = 'Пользователь бота'
        verbose_name_plural = 'Пользователи бота'
        ordering = ['-registration_date']  # Сортировка по дате регистрации (сначала новые)

    def __str__(self):
        return f"{self.first_name} {self.last_name} (@{self.username})"

class Referral(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, db_column='user_id')
    referral_code = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False  # Django не управляет таблицей
        db_table = 'referrals'
        verbose_name = 'Реферальная ссылка'
        verbose_name_plural = 'Реферальные ссылки'

    def __str__(self):
        return f"{self.referral_code} ({self.user})"

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
        managed = False  # Django не управляет таблицей
        db_table = 'plans'
        verbose_name = 'Тарифный план'
        verbose_name_plural = 'Тарифные планы'
        ordering = ['priority', 'price']

    def __str__(self):
        return f"{self.name} ({self.requests} запросов, {self.price} руб.)"

class UserPlan(models.Model):
    id = models.AutoField(primary_key=True)
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
        managed = False  # Django не управляет таблицей
        db_table = 'user_plans'
        verbose_name = 'Тарифный план пользователя'
        verbose_name_plural = 'Тарифные планы пользователей'

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
        managed = False  # Django не управляет таблицей
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
        managed = False  # Django не управляет таблицей
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
        managed = False  # Django не управляет таблицей
        db_table = 'user_statistics'
        verbose_name = 'Статистика пользователя'
        verbose_name_plural = 'Статистика пользователей'

    def __str__(self):
        return f"Статистика: {self.user}"

class ReferralHistory(models.Model):
    id = models.AutoField(primary_key=True)
    referrer = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='referrals_sent', db_column='referrer_id')
    referred_user = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='referral_source', db_column='referred_user_id')
    referral_code = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    bonus_requests_added = models.IntegerField(default=0)  # Сколько бонусных запросов добавлено реферреру
    conversion_status = models.CharField(max_length=50, default='registered')  # Статус конверсии (registered, used_bot, purchased)
    converted_at = models.DateTimeField(null=True, blank=True)  # Дата конверсии (например, первая покупка)

    class Meta:
        managed = False  # Django не управляет таблицей
        db_table = 'referral_history'
        verbose_name = 'История реферралов'
        verbose_name_plural = 'История реферралов'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.referrer} → {self.referred_user} ({self.created_at})"

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
        managed = False  # Django не управляет таблицей
        db_table = 'promo_codes'
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.discount_value} {self.get_discount_type_display()})"

# Модели для чатов

class Chat(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, db_column='user_id')
    title = models.CharField(max_length=255, default='Новый чат')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False # Или True, если хотите, чтобы Django создал таблицу
        db_table = 'chats'
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.user.username})"

class ChatMessage(models.Model):
    id = models.AutoField(primary_key=True)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, db_column='chat_id')
    role = models.CharField(max_length=10) # 'user' или 'assistant'
    content = models.TextField()
    model_used = models.CharField(max_length=100, null=True, blank=True)
    tokens_used = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False # Или True
        db_table = 'chat_messages'
        verbose_name = 'Сообщение чата'
        verbose_name_plural = 'Сообщения чата'
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
