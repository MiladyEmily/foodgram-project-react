# Generated by Django 3.2 on 2023-06-09 18:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0003_rename_count_ingredientrecipe_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recipe',
            name='name',
            field=models.CharField(max_length=200, unique=True, verbose_name='Название'),
        ),
    ]