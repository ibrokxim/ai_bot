from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
import openai  # Предполагается, что вы будете использовать библиотеку OpenAI

from bot_admin.models import BotUser, Plan, UserPlan, RequestUsage, UserStatistics, PromoCode, Payment, ReferralHistory, Chat, ChatMessage
from .authentication import TelegramIDAuthentication
from .permissions import IsTelegramUser, IsOwnerOrReadOnly, CustomIsAuthenticated
from .serializers import (
    BotUserSerializer, PlanSerializer, UserPlanSerializer, RequestUsageSerializer,
    UserStatisticsSerializer, PaymentSerializer,
    UserRegistrationSerializer, UserLoginSerializer, PromoValidationSerializer,
    UseRequestSerializer, ChatSerializer, ChatMessageSerializer, UserContactSerializer
)

openai.api_key = settings.OPENAI_API_KEY


class BotUserViewSet(viewsets.ModelViewSet):
    """API для пользователей бота"""
    queryset = BotUser.objects.all()
    serializer_class = BotUserSerializer
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """API для тарифных планов (только чтение)"""
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]


class UserPlanViewSet(viewsets.ModelViewSet):
    """API для планов пользователей"""
    queryset = UserPlan.objects.all()
    serializer_class = UserPlanSerializer
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser, IsOwnerOrReadOnly]

    def get_queryset(self):
        """Возвращает только планы текущего пользователя"""
        if self.request.user.is_staff:
            return UserPlan.objects.all()
        return UserPlan.objects.filter(user=self.request.user)


class RequestUsageViewSet(viewsets.ModelViewSet):
    """API для использования запросов"""
    queryset = RequestUsage.objects.all()
    serializer_class = RequestUsageSerializer
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def get_queryset(self):
        """Возвращает только запросы текущего пользователя"""
        if self.request.user.is_staff:
            return RequestUsage.objects.all()
        return RequestUsage.objects.filter(user=self.request.user)


class UserContactView(generics.RetrieveUpdateAPIView):
    """
    API для получения (GET) и обновления (PUT/PATCH)
    контакта текущего аутентифицированного пользователя.
    """
    serializer_class = UserContactSerializer
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser] # Доступ только у самого пользователя

    def get_object(self):
        """
        Возвращает объект текущего пользователя.
        RetrieveUpdateAPIView ожидает получить один объект.
        """
        # self.request.user устанавливается TelegramIDAuthentication
        user = self.request.user
        # Дополнительная проверка, что пользователь действительно найден
        if not isinstance(user, BotUser):
            raise generics.NotFound("Пользователь не найден или не аутентифицирован.")
        # Проверяем права доступа еще раз (хотя permission_classes это делают)
        self.check_object_permissions(self.request, user)
        return user

    def get_queryset(self):
        # Этот метод формально нужен для RetrieveUpdateAPIView,
        # но т.к. мы переопределили get_object, он не будет напрямую использоваться
        # для получения объекта. Вернем queryset с одним пользователем для консистентности.
        if self.request.user.is_authenticated and isinstance(self.request.user, BotUser):
            return BotUser.objects.filter(pk=self.request.user.pk)
        return BotUser.objects.none()


class UserStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    """API для статистики пользователей (только чтение)"""
    queryset = UserStatistics.objects.all()
    serializer_class = UserStatisticsSerializer
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def get_queryset(self):
        """Возвращает только статистику текущего пользователя"""
        if self.request.user.is_staff:
            return UserStatistics.objects.all()
        return UserStatistics.objects.filter(user=self.request.user)


class PaymentViewSet(viewsets.ModelViewSet):
    """API для платежей"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def get_queryset(self):
        """Возвращает только платежи текущего пользователя"""
        if self.request.user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(user=self.request.user)


class UserRegistrationView(APIView):
    """Регистрация нового пользователя"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # Проверяем существование пользователя
            if BotUser.objects.filter(telegram_id=data['telegram_id']).exists():
                return Response({
                    'success': False,
                    'message': 'Пользователь уже существует',
                }, status=status.HTTP_409_CONFLICT)

            # Создаем пользователя
            user = BotUser.objects.create(
                telegram_id=data['telegram_id'],
                username=data['username'],
                first_name=data['first_name'],
                last_name=data.get('last_name', ''),
                is_bot=data.get('is_bot', False),
                language_code=data.get('language_code', 'ru'),
                chat_id=data['chat_id'],
                contact=data.get('contact', ''),
                is_active=True,
                requests_left=10,  # Базовое количество запросов
                registration_date=timezone.now()
            )

            # Обрабатываем реферальный код, если предоставлен
            referral_code = data.get('referral_code')
            if referral_code:
                try:
                    referrer = BotUser.objects.get(referral_code=referral_code)
                    ReferralHistory.objects.create(
                        referrer=referrer,
                        referred_user=user,
                        referral_code=referral_code,
                        bonus_requests_added=int(settings.REFERRAL_BONUS_REQUESTS)
                    )

                    # Добавляем бонусные запросы реферреру
                    referrer.requests_left += int(settings.REFERRAL_BONUS_REQUESTS)
                    referrer.save()
                except BotUser.DoesNotExist:
                    pass

            return Response({
                'success': True,
                'message': 'Пользователь успешно зарегистрирован',
                'user_id': user.user_id,
                'telegram_id': user.telegram_id,
                'requests_left': user.requests_left
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'message': 'Ошибка в данных',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """Получение информации о пользователе по telegram_id"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            telegram_id = serializer.validated_data['telegram_id']

            try:
                user = BotUser.objects.get(telegram_id=telegram_id)

                return Response({
                    'success': True,
                    'user_id': user.user_id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'requests_left': user.requests_left
                })
            except BotUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Пользователь не найден'
                }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'success': False,
            'message': 'Ошибка в данных',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class CheckRequestsView(APIView):
    """Проверка доступных запросов"""
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def get(self, request):
        # Проверяем, если telegram_id передан в параметрах запроса
        telegram_id = request.query_params.get('telegram_id')
        if telegram_id:
            try:
                user = BotUser.objects.get(telegram_id=telegram_id)
            except BotUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Пользователь не найден'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        return Response({
            'success': True,
            'requests_left': user.requests_left,
            'can_make_request': user.requests_left > 0
        })


class UseRequestView(APIView):
    """Использование запроса пользователем"""
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def post(self, request):
        # Проверяем, если telegram_id передан в параметрах запроса
        telegram_id = request.data.get('telegram_id')
        if telegram_id:
            try:
                user = BotUser.objects.get(telegram_id=telegram_id)
            except BotUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Пользователь не найден'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        # Проверяем наличие запросов
        if user.requests_left <= 0:
            return Response({
                'success': False,
                'message': 'У вас закончились запросы. Пожалуйста, пополните баланс.',
                'requests_left': 0
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = UseRequestSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # Уменьшаем счетчик запросов
            user.requests_left -= 1
            user.save()

            # Записываем использование запроса
            RequestUsage.objects.create(
                user=user,
                request_type=data['request_type'],
                ai_model=data['ai_model'],
                tokens_used=data['tokens_used'],
                request_text=data.get('request_text', ''),
                response_length=data.get('response_length', 0),
                response_time=data.get('response_time'),
                was_successful=data.get('was_successful', True)
            )

            # Обновляем статистику пользователя
            stats, created = UserStatistics.objects.get_or_create(user=user)
            stats.total_requests += 1
            stats.total_tokens += data['tokens_used']
            stats.last_active = timezone.now()
            stats.save()

            return Response({
                'success': True,
                'requests_left': user.requests_left,
                'message': 'Запрос успешно использован'
            })

        return Response({
            'success': False,
            'message': 'Ошибка в данных',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ValidatePromoView(APIView):
    """Проверка валидности промокода"""
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def post(self, request):
        # Проверяем, если telegram_id передан в параметрах запроса
        telegram_id = request.data.get('telegram_id')
        if telegram_id:
            try:
                user = BotUser.objects.get(telegram_id=telegram_id)
            except BotUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Пользователь не найден'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        serializer = PromoValidationSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data['code']
            plan_id = serializer.validated_data.get('plan_id')

            try:
                # Проверяем существование и активность промокода
                promo = PromoCode.objects.get(
                    code=code,
                    is_active=True,
                    valid_from__lte=timezone.now()
                )

                # Проверяем срок действия
                if promo.valid_to and promo.valid_to < timezone.now():
                    return Response({
                        'success': False,
                        'message': 'Срок действия промокода истек'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Проверяем количество использований
                if promo.max_usages > 0 and promo.usages_count >= promo.max_usages:
                    return Response({
                        'success': False,
                        'message': 'Промокод уже использован максимальное количество раз'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Если указан план, проверяем применимость промокода к этому плану
                if plan_id and promo.allowed_plans:
                    allowed_plans = promo.allowed_plans.split(',')
                    if str(plan_id) not in allowed_plans:
                        return Response({
                            'success': False,
                            'message': 'Промокод не применим к выбранному плану'
                        }, status=status.HTTP_400_BAD_REQUEST)

                # Если все проверки пройдены, возвращаем данные о промокоде
                response_data = {
                    'success': True,
                    'promo': {
                        'id': promo.id,
                        'code': promo.code,
                        'discount_type': promo.discount_type,
                        'discount_value': float(promo.discount_value),
                        'bonus_requests': promo.bonus_requests
                    }
                }

                # Если указан план, рассчитываем скидку
                if plan_id:
                    try:
                        plan = Plan.objects.get(id=plan_id)
                        price = float(plan.price)

                        if promo.discount_type == 'percent':
                            discount_amount = price * (float(promo.discount_value) / 100)
                        elif promo.discount_type == 'fixed':
                            discount_amount = float(promo.discount_value)
                            if discount_amount > price:
                                discount_amount = price
                        else:
                            discount_amount = 0

                        price_after_discount = max(0, price - discount_amount)

                        response_data.update({
                            'discount_amount': discount_amount,
                            'price_after_discount': price_after_discount
                        })
                    except Plan.DoesNotExist:
                        pass

                return Response(response_data)

            except PromoCode.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Промокод не найден или недействителен'
                }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'success': False,
            'message': 'Ошибка в данных',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    """Получение данных о текущем пользователе"""
    permission_classes = [AllowAny]  # Убираем проверку аутентификации полностью

    def get(self, request):
        # Проверяем, если telegram_id передан в параметрах запроса
        telegram_id = request.query_params.get('telegram_id')
        if not telegram_id:
            return Response({
                'success': False,
                'message': 'Не указан параметр telegram_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = BotUser.objects.get(telegram_id=telegram_id)
        except BotUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Пользователь не найден'
            }, status=status.HTTP_404_NOT_FOUND)

        user_data = BotUserSerializer(user).data

        # Получаем активный план пользователя
        active_plan = UserPlan.objects.filter(
            user=user,
            is_active=True,
            expired_at__gt=timezone.now()
        ).order_by('-activated_at').first()

        active_plan_data = UserPlanSerializer(active_plan).data if active_plan else None

        # Получаем статистику пользователя
        stats, created = UserStatistics.objects.get_or_create(user=user)
        stats_data = UserStatisticsSerializer(stats).data

        return Response({
            'success': True,
            'user': user_data,
            'active_plan': active_plan_data,
            'statistics': stats_data
        })


class UserRequestHistoryView(APIView):
    """Получение истории запросов пользователя"""
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def get(self, request):
        # Проверяем, если telegram_id передан в параметрах запроса
        telegram_id = request.query_params.get('telegram_id')
        if telegram_id:
            try:
                user = BotUser.objects.get(telegram_id=telegram_id)
            except BotUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Пользователь не найден'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        # Получаем параметры пагинации
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))

        # Вычисляем смещение
        offset = (page - 1) * per_page

        # Получаем историю запросов с пагинацией
        history = RequestUsage.objects.filter(user=user).order_by('-request_date')[offset:offset+per_page]
        total = RequestUsage.objects.filter(user=user).count()

        # Сериализуем данные
        history_data = RequestUsageSerializer(history, many=True).data

        return Response({
            'success': True,
            'history': history_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        })


class ReferralsView(APIView):
    """Получение информации о рефералах пользователя"""
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def get(self, request):
        # Проверяем, если telegram_id передан в параметрах запроса
        telegram_id = request.query_params.get('telegram_id')
        if telegram_id:
            try:
                user = BotUser.objects.get(telegram_id=telegram_id)
            except BotUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Пользователь не найден'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        # Получаем список рефералов
        referrals = ReferralHistory.objects.filter(referrer=user).order_by('-created_at')

        # Получаем статистику по оплатам от рефералов
        total_payments = Payment.objects.filter(
            user__in=referrals.values_list('referred_user', flat=True)
        ).aggregate(total=Sum('amount'))

        # Формируем список рефералов с минимальной информацией
        referral_list = []
        for ref in referrals:
            referral_list.append({
                'user_id': ref.referred_user.user_id,
                'username': ref.referred_user.username,
                'first_name': ref.referred_user.first_name,
                'last_name': ref.referred_user.last_name,
                'created_at': ref.created_at.isoformat(),
                'bonus_requests_added': ref.bonus_requests_added,
                'conversion_status': ref.conversion_status
            })

        return Response({
            'success': True,
            'referrals': referral_list,
            'total_count': referrals.count(),
            'total_earnings': float(total_payments['total'] or 0)
        })


# Прямой доступ к API без авторизации
class DirectTelegramRequestsView(APIView):
    """
    Прямой доступ к запросам по telegram_id без авторизации

    GET /api/telegram/requests/?telegram_id=123456789
    """
    permission_classes = [AllowAny]

    def get(self, request):
        telegram_id = request.query_params.get('telegram_id')

        if not telegram_id:
            return Response({
                'success': False,
                'message': 'Не указан параметр telegram_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = BotUser.objects.get(telegram_id=telegram_id)

            return Response({
                'success': True,
                'telegram_id': user.telegram_id,
                'requests_left': user.requests_left,
                'can_make_request': user.requests_left > 0
            })
        except BotUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Пользователь не найден'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Ошибка: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Новые эндпоинты с прямым доступом
class UseRequestByTelegramIDView(APIView):
    """
    Использование запроса по telegram_id без авторизации

    POST /api/telegram/use-request/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        telegram_id = request.data.get('telegram_id')

        if not telegram_id:
            return Response({
                'success': False,
                'message': 'Не указан параметр telegram_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = BotUser.objects.get(telegram_id=telegram_id)

            # Проверяем наличие запросов
            if user.requests_left <= 0:
                return Response({
                    'success': False,
                    'message': 'У вас закончились запросы. Пожалуйста, пополните баланс.',
                    'requests_left': 0
                }, status=status.HTTP_403_FORBIDDEN)

            serializer = UseRequestSerializer(data=request.data)
            if serializer.is_valid():
                data = serializer.validated_data

                # Уменьшаем счетчик запросов
                user.requests_left -= 1
                user.save()

                # Записываем использование запроса
                RequestUsage.objects.create(
                    user=user,
                    request_type=data['request_type'],
                    ai_model=data['ai_model'],
                    tokens_used=data['tokens_used'],
                    request_text=data.get('request_text', ''),
                    response_length=data.get('response_length', 0),
                    response_time=data.get('response_time'),
                    was_successful=data.get('was_successful', True)
                )

                # Обновляем статистику пользователя
                stats, created = UserStatistics.objects.get_or_create(user=user)
                stats.total_requests += 1
                stats.total_tokens += data['tokens_used']
                stats.last_active = timezone.now()
                stats.save()

                return Response({
                    'success': True,
                    'requests_left': user.requests_left,
                    'message': 'Запрос успешно использован'
                })

            return Response({
                'success': False,
                'message': 'Ошибка в данных',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except BotUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Пользователь не найден'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Ошибка: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserInfoByTelegramIDView(APIView):
    """
    Получение информации о пользователе по telegram_id без авторизации

    GET /api/telegram/user-info/?telegram_id=123456789
    """
    permission_classes = [AllowAny]

    def get(self, request):
        telegram_id = request.query_params.get('telegram_id')

        if not telegram_id:
            return Response({
                'success': False,
                'message': 'Не указан параметр telegram_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = BotUser.objects.get(telegram_id=telegram_id)

            # Получаем активный план пользователя
            active_plan = UserPlan.objects.filter(
                user=user,
                is_active=True,
                expired_at__gt=timezone.now()
            ).order_by('-activated_at').first()

            active_plan_data = None
            if active_plan:
                active_plan_data = {
                    'id': active_plan.id,
                    'plan_id': active_plan.plan.id,
                    'plan_name': active_plan.plan.name,
                    'start_date': active_plan.activated_at.isoformat() if active_plan.activated_at else None,
                    'end_date': active_plan.expired_at.isoformat() if active_plan.expired_at else None,
                    'is_active': active_plan.is_active,
                    'requests_added': active_plan.requests_added
                }

            # Формируем ответ
            response_data = {
                'success': True,
                'user': {
                    'user_id': user.user_id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'requests_left': user.requests_left,
                    'registration_date': user.registration_date.isoformat() if user.registration_date else None
                },
                'active_plan': active_plan_data
            }

            return Response(response_data)

        except BotUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Пользователь не найден'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Ошибка: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Представления для чатов

class ChatListView(APIView):
    """Список чатов пользователя и создание нового чата"""
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def get_user(self, request):
        """Вспомогательный метод для получения пользователя"""
        telegram_id = request.query_params.get('telegram_id') or request.data.get('telegram_id')
        if telegram_id:
            try:
                return BotUser.objects.get(telegram_id=telegram_id)
            except BotUser.DoesNotExist:
                return None
        return request.user

    def get(self, request):
        user = self.get_user(request)
        if not user:
            return Response({'success': False, 'message': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

        chats = Chat.objects.filter(user=user)
        serializer = ChatSerializer(chats, many=True)
        return Response({'success': True, 'chats': serializer.data})

    def post(self, request):
        user = self.get_user(request)
        if not user:
            return Response({'success': False, 'message': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ChatSerializer(data=request.data) # Можно передать title в запросе
        if serializer.is_valid():
            # Устанавливаем пользователя и сохраняем
            chat = serializer.save(user=user)
            return Response({'success': True, 'chat': ChatSerializer(chat).data}, status=status.HTTP_201_CREATED)
        return Response({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ChatDetailView(APIView):
    """Удаление и получение чата"""
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def get_user(self, request):
        """Вспомогательный метод для получения пользователя"""
        telegram_id = request.query_params.get(
            'telegram_id') or request.data.get('telegram_id')
        if telegram_id:
            try:
                return BotUser.objects.get(telegram_id=telegram_id)
            except BotUser.DoesNotExist:
                return None
        return request.user

    def get(self, request, chat_id):
        """Получение данных о чате"""
        user = self.get_user(request)
        if not user:
            return Response({'success': False, 'message': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Убедимся, что чат принадлежит пользователю
        chat = get_object_or_404(Chat, id=chat_id, user=user)
        serializer = ChatSerializer(chat)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, chat_id):
        """Удаление чата"""
        user = self.get_user(request)
        if not user:
            return Response({'success': False, 'message': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Убедимся, что чат принадлежит пользователю
        chat = get_object_or_404(Chat, id=chat_id, user=user)
        chat.delete()
        return Response({'success': True, 'message': 'Чат удален'}, status=status.HTTP_204_NO_CONTENT)



class ChatMessageListView(APIView):
    """Получение сообщений чата"""
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def get_user(self, request):
        """Вспомогательный метод для получения пользователя"""
        telegram_id = request.query_params.get('telegram_id') or request.data.get('telegram_id')
        if telegram_id:
            try:
                return BotUser.objects.get(telegram_id=telegram_id)
            except BotUser.DoesNotExist:
                return None
        return request.user

    def get(self, request, chat_id):
        user = self.get_user(request)
        if not user:
            return Response({'success': False, 'message': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Убедимся, что чат принадлежит пользователю
        chat = get_object_or_404(Chat, id=chat_id, user=user)

        messages = ChatMessage.objects.filter(chat=chat)
        serializer = ChatMessageSerializer(messages, many=True)
        return Response({'success': True, 'messages': serializer.data})


class ChatMessageCreateView(APIView):
    """Создание сообщения в чате, взаимодействие с ИИ и списание запроса"""
    authentication_classes = [TelegramIDAuthentication]
    permission_classes = [CustomIsAuthenticated, IsTelegramUser]

    def get_user(self, request):
        """Вспомогательный метод для получения пользователя"""
        telegram_id = request.query_params.get('telegram_id') or request.data.get('telegram_id')
        if telegram_id:
            try:
                return BotUser.objects.get(telegram_id=telegram_id)
            except BotUser.DoesNotExist:
                return None
        return request.user

    def post(self, request, chat_id=None):
        user = self.get_user(request)
        if not user:
            return Response({'success': False, 'message': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Валидация входных данных
        user_message_content = request.data.get('content')
        if not user_message_content:
            return Response({'success': False, 'message': 'Поле content обязательно'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Получаем модель ИИ из запроса или используем значение по умолчанию
        ai_model_to_use = request.data.get('ai_model', 'gpt-4o-mini')

        # Создаем новый чат, если chat_id равен 0, null или не существует
        if not chat_id or chat_id == 0:
            # Создаем новый чат
            # Название чата = первые 30 символов сообщения пользователя
            title = user_message_content[:30] + ('...' if len(user_message_content) > 30 else '')
            chat = Chat.objects.create(
                user=user,
                title=title,
                ai_model=ai_model_to_use
            )
        else:
            # Находим существующий чат
            try:
                chat = Chat.objects.get(id=chat_id, user=user)
                # Обновляем модель, если она была изменена
                if chat.ai_model != ai_model_to_use:
                    chat.ai_model = ai_model_to_use
                    chat.save()
            except Chat.DoesNotExist:
                return Response({'success': False, 'message': 'Чат не найден'}, status=status.HTTP_404_NOT_FOUND)

        # 2. Проверить наличие запросов
        if user.requests_left <= 0:
            return Response({
                'success': False,
                'message': 'У вас закончились запросы. Пожалуйста, пополните баланс.',
                'requests_left': 0
            }, status=status.HTTP_403_FORBIDDEN)

        # 4. Сохранить сообщение пользователя
        user_message = ChatMessage.objects.create(
            chat=chat,
            role='user',
            content=user_message_content
        )

        # 5. Подготовка запроса к ИИ (передаем историю)
        messages_for_ai = [
            {"role": msg.role, "content": msg.content}
            for msg in ChatMessage.objects.filter(chat=chat).order_by('timestamp')
        ]

        ai_response_content = "Произошла ошибка при обращении к ИИ." # Значение по умолчанию
        tokens_used = 0 # Значение по умолчанию

        # --- БЛОК ВЗАИМОДЕЙСТВИЯ С ИИ ---
        try:
            # Используем выбранную модель
            if chat.ai_model.startswith('gpt'):
                # Для моделей OpenAI
                print(f"Используем модель: {chat.ai_model}")
                response = openai.chat.completions.create(
                    model=chat.ai_model,
                    messages=messages_for_ai,
                    # max_tokens=4000 # Можно добавить ограничения для некоторых моделей
                )
                # Убедитесь, что структура ответа соответствует новой версии API OpenAI
                if response.choices and len(response.choices) > 0:
                    ai_response_content = response.choices[0].message.content
                if response.usage:
                    tokens_used = response.usage.total_tokens
            elif chat.ai_model.startswith('claude'):
                # Для моделей Claude
                # Здесь будет код для API Claude
                ai_response_content = "Ответ от Claude (интеграция в разработке)"
            elif chat.ai_model.startswith('gemini'):
                # Для моделей Gemini
                # Здесь будет код для API Gemini
                ai_response_content = "Ответ от Gemini (интеграция в разработке)"
            elif chat.ai_model in ['dall-e', 'midjourney']:
                # Для генерации изображений
                # Здесь будет код для генерации изображений
                ai_response_content = "Ссылка на сгенерированное изображение (интеграция в разработке)"
            else:
                # Если модель не поддерживается
                ai_response_content = "Выбранная модель не поддерживается в данный момент"
        except Exception as e:
            # Обработка ошибок ИИ
            error_message = f"Ошибка при обращении к ИИ: {str(e)}"
            assistant_message = ChatMessage.objects.create(
                chat=chat,
                role='assistant',
                content=error_message,
                model_used=chat.ai_model,
                tokens_used=0
            )
            # Возвращаем ошибку пользователю, не 500, а например 400 или 503
            return Response({
                'success': False, 
                'message': error_message,
                'chat': ChatSerializer(chat).data
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        # --- КОНЕЦ БЛОКА ИИ ---

        # 3. Списать 1 запрос
        user.requests_left -= 1
        user.save()

        # 7. Сохранить ответ ИИ
        assistant_message = ChatMessage.objects.create(
            chat=chat,
            role='assistant',
            content=ai_response_content,
            model_used=chat.ai_model,
            tokens_used=tokens_used
        )

        # 9. Вернуть ответ ИИ пользователю с данными чата
        return Response({
            'success': True, 
            'message': ChatMessageSerializer(assistant_message).data,
            'chat': ChatSerializer(chat).data,
            'requests_left': user.requests_left
        })


class ReferralLinkView(APIView):
    """Получение реферальной ссылки пользователя"""
    permission_classes = [AllowAny]

    def get(self, request):
        telegram_id = request.query_params.get('telegram_id')
        
        if not telegram_id:
            return Response({
                'success': False,
                'message': 'Не указан telegram_id'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            user = BotUser.objects.get(telegram_id=telegram_id)
            
            # Получаем реферальный код пользователя
            referral_code = user.referral_code
            
            if not referral_code:
                # Если у пользователя нет реферального кода, генерируем новый
                import random
                import string
                referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                user.referral_code = referral_code
                user.save()
            
            # Формируем реферальную ссылку
            bot_username = settings.BOT_USERNAME
            referral_link = f"https://t.me/dahoai_bot?start={referral_code}"
            
            return Response({
                'success': True,
                'referral_code': referral_code,
                'referral_link': referral_link,
                'bonus_requests': settings.REFERRAL_BONUS_REQUESTS
            })
            
        except BotUser.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Пользователь не найден'
            }, status=status.HTTP_404_NOT_FOUND)