from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('bot_admin', '0001_initial'),  # Обновите зависимость на вашу последнюю миграцию
    ]

    operations = [
        migrations.AlterField(
            model_name='chat',
            name='ai_model',
            field=models.CharField(
                choices=[
                    ('gpt-4o-mini', 'GPT-4o Mini'),
                    ('claude-3-5', 'Claude 3.5'),
                    ('claude-3-7', 'Claude 3.7'),
                    ('gemini-2-flash', 'Gemini 2.0 Flash'),
                    ('gpt-4', 'GPT-4'),
                    ('gpt3-mini', 'GPT-3 Mini'),
                    ('dall-e', 'DALL-E'),
                    ('midjourney', 'Midjourney')
                ],
                default='gpt-4o-mini',
                max_length=50
            ),
        ),
    ] 