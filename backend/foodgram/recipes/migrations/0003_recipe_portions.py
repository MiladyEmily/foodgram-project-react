# Generated by Django 3.2 on 2024-01-16 04:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0002_auto_20230622_1804'),
    ]

    operations = [
        migrations.AddField(
            model_name='recipe',
            name='portions',
            field=models.PositiveIntegerField(default=2, verbose_name='Количество порций'),
            preserve_default=False,
        ),
    ]
