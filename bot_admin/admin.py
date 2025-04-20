from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.urls import reverse, path
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils.safestring import mark_safe

from .models import (
    BotUser, ReferralCode, Plan, UserPlan, Payment, RequestUsage, UserStatistics,
    ReferralHistory, PromoCode, Chat, ChatMessage
)


# Базовый класс для админки с русскими названиями столбцов
class RussianColumnNameAdmin(admin.ModelAdmin):
    """Базовый класс для админки с русскими названиями столбцов"""

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.model = model
        self._column_names = {}  # Словарь с переводами названий столбцов
        
        # Сразу получаем словарь русских названий столбцов
        self._column_names = self.get_column_names()
        
        # Динамически создаем методы для отображения русских названий столбцов
        # для каждого поля из list_display
        for field_name in self.list_display:
            # Для каждого поля создаем метод с соответствующим названием
            if isinstance(field_name, str) and field_name in self._column_names:
                method_name = f"display_{field_name}"
                
                # Создаем динамический метод для отображения поля с русским названием
                def make_display_method(name):
                    def display_method(obj):
                        # Получаем значение поля
                        if hasattr(obj, name):
                            return getattr(obj, name)
                        elif hasattr(self, name) and callable(getattr(self, name)):
                            return getattr(self, name)(obj)
                        return "-"
                    
                    # Устанавливаем атрибуты для метода
                    display_method.short_description = self._column_names.get(name, name)
                    display_method.admin_order_field = name
                    display_method.__name__ = method_name
                    
                    return display_method
                
                # Привязываем метод к классу
                setattr(self, method_name, make_display_method(field_name))

    def get_list_display(self, request):
        """Заменяем list_display на методы с русскими названиями"""
        list_display = super().get_list_display(request)
        
        # Заменяем поля на методы с русскими названиями
        new_list_display = []
        for field_name in list_display:
            if isinstance(field_name, str) and field_name in self._column_names:
                method_name = f"display_{field_name}"
                if hasattr(self, method_name):
                    new_list_display.append(method_name)
                else:
                    new_list_display.append(field_name)
            else:
                new_list_display.append(field_name)
        
        return new_list_display

    def column_name(self, name):
        """Получить русское название столбца для отображения"""
        return self._column_names.get(name, name)

    def get_column_names(self):
        """Должен быть переопределен в дочерних классах для задания русских названий столбцов"""
        return {}

    def changelist_view(self, request, extra_context=None):
        """Переопределяем метод для замены названий столбцов на русские"""
        extra_context = extra_context or {}
        extra_context['title'] = self.model._meta.verbose_name_plural
        
        return super().changelist_view(request, extra_context)
    
    def get_list_display_links(self, request, list_display):
        """Обеспечивает работу ссылок при переопределении заголовков"""
        return super().get_list_display_links(request, list_display)
    
    def get_fieldsets(self, request, obj=None):
        """Переопределяем fieldsets для отображения русских названий полей в форме редактирования"""
        fieldsets = super().get_fieldsets(request, obj)
        
        # Если есть русские названия и определены fieldsets
        if self._column_names and fieldsets:
            new_fieldsets = []
            for name, options in fieldsets:
                # Копируем опции и обновляем названия полей
                new_options = dict(options)
                if 'fields' in new_options:
                    fields = new_options['fields']
                    # Заменяем названия полей только для отображения, не меняя сами поля
                    # Это пока не реализовано полностью, так как требует более глубоких изменений в Django admin
                    new_options['fields'] = fields
                new_fieldsets.append((name, new_options))
            return new_fieldsets
        return fieldsets

@admin.register(BotUser)
class BotUserAdmin(RussianColumnNameAdmin):
    list_display = ('telegram_id', 'username', 'first_name', 'last_name', 'referral_code', 'is_bot', 'language_code', 'chat_id', 'contact', 'is_active', 'requests_left', 'registration_date')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name', 'referral_code')
    list_filter = ('is_bot', 'is_active', 'language_code')
    readonly_fields = ('telegram_id', 'referral_code')
    ordering = ('-registration_date',)
    actions = ['delete_user_with_data']
    
    def has_delete_permission(self, request, obj=None):
        """Разрешить удаление пользователей"""
        return True
    
    def get_column_names(self):
        """Русские названия столбцов для отображения"""
        return {
            'telegram_id': 'ID в Telegram',
            'username': 'Имя пользователя',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'is_bot': 'Бот',
            'language_code': 'Язык',
            'chat_id': 'ID чата',
            'contact': 'Контакт',
            'is_active': 'Активен',
            'requests_left': 'Осталось запросов',
            'registration_date': 'Дата регистрации',
            'referral_code': 'Реферальный код'
        }
    
    @admin.display(description='Контакт')
    def user_contact(self, obj):
        """Метод для отображения контакта пользователя"""
        if obj.contact:
            return format_html('<a href="tel:{0}">{0}</a>', obj.contact)
        return '-'
    
    @admin.action(description='Удалить пользователя вместе со всеми данными')
    def delete_user_with_data(self, request, queryset):
        """Метод для удаления пользователя вместе со всеми его данными"""
        from django.db import transaction
        total_deleted = 0
        
        try:
            with transaction.atomic():
                for user in queryset:
                    # Сначала удаляем все связанные сообщения чатов
                    ChatMessage.objects.filter(chat__user=user).delete()
                    
                    # Затем удаляем сами чаты
                    Chat.objects.filter(user=user).delete()
                    
                    # Удаляем остальные связанные объекты
                    UserPlan.objects.filter(user=user).delete()
                    Payment.objects.filter(user=user).delete()
                    RequestUsage.objects.filter(user=user).delete()
                    UserStatistics.objects.filter(user=user).delete()
                    ReferralHistory.objects.filter(referrer=user).delete()
                    ReferralHistory.objects.filter(referred=user).delete()
                    
                    # Удаляем реферальные ссылки
                    ReferralCode.objects.filter(user=user).delete()
                    
                    # Наконец удаляем самого пользователя
                    user.delete()
                    total_deleted += 1
                
                self.message_user(
                    request,
                    f'Успешно удалено пользователей: {total_deleted}',
                    messages.SUCCESS
                )
        except Exception as e:
            self.message_user(
                request,
                f'Ошибка при удалении пользователей: {str(e)}',
                messages.ERROR
            )

@admin.register(Plan)
class PlanAdmin(RussianColumnNameAdmin):
    list_display = ('id', 'name', 'requests', 'price', 'is_active', 'is_subscription', 'duration_days', 'discount_percent', 'priority')
    search_fields = ('name',)
    list_filter = ('is_active', 'is_subscription', 'created_at')
    ordering = ('priority', 'price',)
    
    def get_column_names(self):
        """Русские названия столбцов для отображения"""
        return {
            'id': 'ID',
            'name': 'Название',
            'requests': 'Запросов',
            'price': 'Цена',
            'is_active': 'Активен',
            'is_subscription': 'Подписка',
            'duration_days': 'Длительность (дней)',
            'discount_percent': 'Скидка (%)',
            'priority': 'Приоритет'
        }

@admin.register(UserPlan)
class UserPlanAdmin(RussianColumnNameAdmin):
    list_display = ('id', 'user', 'plan', 'activated_at', 'expired_at', 'is_active', 'price_paid', 'requests_added', 'discount_applied', 'is_auto_renewal')
    search_fields = ('user__username', 'user__telegram_id', 'plan__name')
    list_filter = ('is_active', 'is_auto_renewal', 'activated_at', 'expired_at')
    readonly_fields = ('activated_at',)
    ordering = ('-activated_at',)
    
    def get_column_names(self):
        """Русские названия столбцов для отображения"""
        return {
            'id': 'ID',
            'user': 'Пользователь',
            'plan': 'Тариф',
            'activated_at': 'Дата активации',
            'expired_at': 'Дата истечения',
            'is_active': 'Активен',
            'price_paid': 'Оплачено',
            'requests_added': 'Добавлено запросов',
            'discount_applied': 'Скидка (%)',
            'is_auto_renewal': 'Автопродление'
        }

@admin.register(Payment)
class PaymentAdmin(RussianColumnNameAdmin):
    list_display = ('id', 'user', 'amount', 'currency', 'payment_date', 'payment_system', 'status')
    search_fields = ('user__username', 'user__telegram_id', 'payment_id')
    list_filter = ('status', 'payment_system', 'payment_date')
    readonly_fields = ('payment_date',)
    ordering = ('-payment_date',)
    
    def get_column_names(self):
        """Русские названия столбцов для отображения"""
        return {
            'id': 'ID',
            'user': 'Пользователь',
            'amount': 'Сумма',
            'currency': 'Валюта',
            'payment_date': 'Дата платежа',
            'payment_system': 'Платежная система',
            'status': 'Статус'
        }

@admin.register(RequestUsage)
class RequestUsageAdmin(RussianColumnNameAdmin):
    list_display = ('id', 'user', 'request_type', 'ai_model', 'tokens_used', 'request_date', 'was_successful')
    search_fields = ('user__username', 'user__telegram_id', 'request_type', 'ai_model')
    list_filter = ('request_type', 'ai_model', 'was_successful', 'request_date')
    readonly_fields = ('request_date',)
    ordering = ('-request_date',)
    
    def get_column_names(self):
        """Русские названия столбцов для отображения"""
        return {
            'id': 'ID',
            'user': 'Пользователь',
            'request_type': 'Тип запроса',
            'ai_model': 'Модель ИИ',
            'tokens_used': 'Использовано токенов',
            'request_date': 'Дата запроса',
            'was_successful': 'Успешно'
        }

@admin.register(UserStatistics)
class UserStatisticsAdmin(RussianColumnNameAdmin):
    list_display = ('user', 'total_requests', 'total_tokens', 'last_active', 'total_payments', 'total_referrals', 'account_level')
    search_fields = ('user__username', 'user__telegram_id')
    list_filter = ('account_level', 'last_active')
    readonly_fields = ('total_requests', 'total_tokens', 'last_active')
    ordering = ('-total_requests',)
    
    def get_column_names(self):
        """Русские названия столбцов для отображения"""
        return {
            'user': 'Пользователь',
            'total_requests': 'Всего запросов',
            'total_tokens': 'Всего токенов',
            'last_active': 'Последняя активность',
            'total_payments': 'Всего платежей',
            'total_referrals': 'Всего рефералов',
            'account_level': 'Уровень аккаунта'
        }

@admin.register(ReferralCode)
class ReferralCodeAdmin(RussianColumnNameAdmin):
    list_display = ('code', 'user', 'created_at', 'is_active', 'total_uses', 'last_used_at')
    search_fields = ('code', 'user__username', 'user__telegram_id')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('code', 'total_uses', 'last_used_at')
    
    def get_column_names(self):
        """Русские названия столбцов для отображения"""
        return {
            'code': 'Реферальный код',
            'user': 'Пользователь',
            'created_at': 'Дата создания',
            'is_active': 'Активен',
            'total_uses': 'Использований',
            'last_used_at': 'Последнее использование'
        }

@admin.register(ReferralHistory)
class ReferralHistoryAdmin(RussianColumnNameAdmin):
    list_display = ('referrer', 'referred', 'referral_code', 'created_at', 'bonus_requests_added', 'conversion_status', 'converted_at')
    search_fields = ('referrer__username', 'referred__username', 'referral_code__code')
    list_filter = ('conversion_status', 'created_at')
    readonly_fields = ('created_at', 'converted_at')
    
    def get_column_names(self):
        """Русские названия столбцов для отображения"""
        return {
            'referrer': 'Реферер',
            'referred': 'Приглашенный',
            'referral_code': 'Реферальный код',
            'created_at': 'Дата создания',
            'bonus_requests_added': 'Добавлено бонусных запросов',
            'conversion_status': 'Статус конверсии',
            'converted_at': 'Дата конверсии'
        }

@admin.register(PromoCode)
class PromoCodeAdmin(RussianColumnNameAdmin):
    list_display = ('id', 'code', 'discount_type', 'discount_value', 'valid_from', 'valid_to', 'is_active', 'usages_count', 'max_usages')
    search_fields = ('code',)
    list_filter = ('is_active', 'discount_type', 'valid_from', 'valid_to')
    ordering = ('-created_at',)
    
    def get_column_names(self):
        """Русские названия столбцов для отображения"""
        return {
            'id': 'ID',
            'code': 'Код',
            'discount_type': 'Тип скидки',
            'discount_value': 'Значение скидки',
            'valid_from': 'Действует с',
            'valid_to': 'Действует до',
            'is_active': 'Активен',
            'usages_count': 'Количество использований',
            'max_usages': 'Максимум использований'
        }

# Админка для чатов и сообщений

class ChatMessageInline(admin.TabularInline):
    """Инлайн для отображения сообщений прямо в админке чата"""
    model = ChatMessage
    fields = ('role', 'content', 'model_used', 'tokens_used', 'timestamp')
    readonly_fields = ('role', 'content', 'model_used', 'tokens_used', 'timestamp')
    extra = 0  # Не показывать пустые строки для добавления
    can_delete = False # Запретить удаление сообщений из чата
    ordering = ('timestamp',) # Сортировка по времени
    
    def has_add_permission(self, request, obj=None):
        return False # Запретить добавление сообщений из чата


@admin.register(Chat)
class ChatAdmin(RussianColumnNameAdmin):
    list_display = ('id', 'user', 'title', 'created_at', 'updated_at')
    search_fields = ('title', 'user__username', 'user__telegram_id')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('user', 'created_at', 'updated_at')
    ordering = ('-updated_at',)
    inlines = [ChatMessageInline] # Отображаем сообщения внутри чата
    
    def get_column_names(self):
        """Русские названия столбцов для отображения"""
        return {
            'id': 'ID Чата',
            'user': 'Пользователь',
            'title': 'Название чата',
            'created_at': 'Создан',
            'updated_at': 'Обновлен'
        }
    
    def has_add_permission(self, request):
        return False # Запретить создание чатов из админки


@admin.register(ChatMessage)
class ChatMessageAdmin(RussianColumnNameAdmin):
    list_display = ('id', 'chat_link', 'role', 'short_content', 'model_used', 'tokens_used', 'timestamp')
    search_fields = ('content', 'chat__user__username', 'chat__user__telegram_id', 'chat__title')
    list_filter = ('role', 'model_used', 'timestamp')
    readonly_fields = ('chat', 'role', 'content', 'model_used', 'tokens_used', 'timestamp')
    ordering = ('-timestamp',)
    
    def get_column_names(self):
        """Русские названия столбцов для отображения"""
        return {
            'id': 'ID Сообщ.',
            'chat_link': 'Чат',
            'role': 'Роль',
            'short_content': 'Содержание',
            'model_used': 'Модель ИИ',
            'tokens_used': 'Токены',
            'timestamp': 'Время'
        }
    
    @admin.display(description='Чат', ordering='chat__title')
    def chat_link(self, obj):
        """Ссылка на связанный чат"""
        from django.urls import reverse
        link = reverse("admin:bot_admin_chat_change", args=[obj.chat.id])
        return format_html('<a href="{}">{}</a>', link, obj.chat.title)
        
    @admin.display(description='Содержание', ordering='content')
    def short_content(self, obj):
        """Обрезанное содержание сообщения"""
        return (obj.content[:75] + '...') if len(obj.content) > 75 else obj.content
    
    def has_add_permission(self, request):
        return False # Запретить создание сообщений из админки
