from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Создаем роутер для API
router = DefaultRouter()
router.register(r'users', views.BotUserViewSet)
router.register(r'plans', views.PlanViewSet)
router.register(r'user-plans', views.UserPlanViewSet)
router.register(r'requests', views.RequestUsageViewSet)
router.register(r'statistics', views.UserStatisticsViewSet)
router.register(r'payments', views.PaymentViewSet)

urlpatterns = [
    # API с использованием ViewSets
    path('', include(router.urls)),
    
    # Аутентификация и регистрация
    path('auth/register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('auth/login/', views.UserLoginView.as_view(), name='user-login'),
    
    # Проверка запросов
    path('check-requests/', views.CheckRequestsView.as_view(), name='check-requests'),
    # path('use-request/', views.UseRequestView.as_view(), name='use-request'), # Вероятно, больше не нужен
    
    # Промокоды
    path('validate-promo/', views.ValidatePromoView.as_view(), name='validate-promo'),
    
    # Информация о текущем пользователе
    path('me/', views.CurrentUserView.as_view(), name='current-user'),
    path('me/history/', views.UserRequestHistoryView.as_view(), name='user-request-history'),
    path('user/contact/', views.UserContactView.as_view(), name='user-contact'),
    # Реферальная система
    path('referrals/', views.ReferralsView.as_view(), name='referrals'),
    
    # Прямой доступ по telegram_id (без JWT)
    path('telegram/requests/', views.DirectTelegramRequestsView.as_view(), name='telegram-requests'),
    path('telegram/use-request/', views.UseRequestByTelegramIDView.as_view(), name='telegram-use-request'),
    path('telegram/user-info/', views.UserInfoByTelegramIDView.as_view(), name='telegram-user-info'),
    path('telegram/referral-link/', views.ReferralLinkView.as_view(), name='telegram-referral-link'),

    # Новые URL для чатов
    path('chats/', views.ChatListView.as_view(), name='chat-list'),
    path('chats/<int:chat_id>/', views.ChatDetailView.as_view(), name='chat-detail'),
    path('chats/<int:chat_id>/messages/', views.ChatMessageListView.as_view(), name='chat-message-list'),
    path('chats/<int:chat_id>/messages/create/', views.ChatMessageCreateView.as_view(), name='chat-message-create'),
    # URL для создания нового чата и отправки первого сообщения одновременно
    path('messages/create', views.ChatMessageCreateView.as_view(), name='chat-message-create-new'),
] 