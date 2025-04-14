# Generated by Django 4.2.20 on 2025-04-09 14:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot_admin', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Plan',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('requests', models.IntegerField()),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Тарифный план',
                'verbose_name_plural': 'Тарифные планы',
                'db_table': 'plans',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Referral',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('referral_code', models.CharField(max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Реферальная ссылка',
                'verbose_name_plural': 'Реферальные ссылки',
                'db_table': 'referrals',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='UserPlan',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('activated_at', models.DateTimeField(auto_now_add=True)),
                ('expired_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Тарифный план пользователя',
                'verbose_name_plural': 'Тарифные планы пользователей',
                'db_table': 'user_plans',
                'managed': False,
            },
        ),
    ]
