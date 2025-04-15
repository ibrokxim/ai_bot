from django.db import migrations

def create_initial_plans(apps, schema_editor):
    """
    Добавление начальных тарифных планов в базу данных
    """
    Plan = apps.get_model('bot_admin', 'Plan')
    
    # Проверка, если планы уже существуют
    if Plan.objects.count() == 0:
        # Создаем базовые планы
        Plan.objects.create(
            name='Базовый',
            requests=50,
            price=299.00,
            is_active=True,
            duration_days=30,
            description='Базовый тарифный план с ограниченным количеством запросов',
            priority=1,
            is_subscription=False,
            discount_percent=0,
            allowed_models='gpt-3.5-turbo'
        )
        
        Plan.objects.create(
            name='Стандарт',
            requests=200,
            price=999.00,
            is_active=True,
            duration_days=30,
            description='Стандартный тарифный план со средним количеством запросов',
            priority=2,
            is_subscription=False,
            discount_percent=0,
            allowed_models='gpt-3.5-turbo,gpt-4'
        )
        
        Plan.objects.create(
            name='Премиум',
            requests=500,
            price=1999.00,
            is_active=True,
            duration_days=30,
            description='Премиум тарифный план с большим количеством запросов и дополнительными возможностями',
            priority=3,
            is_subscription=False,
            discount_percent=0,
            allowed_models='gpt-3.5-turbo,gpt-4,claude-3'
        )
        
        # Создаем подписки
        Plan.objects.create(
            name='Базовая подписка',
            requests=150,
            price=249.00,
            is_active=True,
            duration_days=30,
            description='Ежемесячная базовая подписка',
            priority=4,
            is_subscription=True,
            discount_percent=15,
            allowed_models='gpt-3.5-turbo'
        )
        
        Plan.objects.create(
            name='Премиум подписка',
            requests=600,
            price=1499.00,
            is_active=True,
            duration_days=30,
            description='Ежемесячная премиум подписка со скидкой',
            priority=5,
            is_subscription=True,
            discount_percent=25,
            allowed_models='gpt-3.5-turbo,gpt-4,claude-3'
        )

class Migration(migrations.Migration):
    dependencies = [
        ('bot_admin', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_initial_plans),
    ] 