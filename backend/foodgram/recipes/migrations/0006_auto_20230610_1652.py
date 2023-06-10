# Generated by Django 3.2 on 2023-06-10 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0005_alter_recipe_name'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='shoppingcart',
            name='unique_user_recipe_in_cart_pair',
        ),
        migrations.RenameField(
            model_name='shoppingcart',
            old_name='recipe_in_cart',
            new_name='recipe',
        ),
        migrations.AddConstraint(
            model_name='shoppingcart',
            constraint=models.UniqueConstraint(fields=('user', 'recipe'), name='unique_user_recipe_in_cart_pair'),
        ),
    ]