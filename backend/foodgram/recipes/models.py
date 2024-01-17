from django.core.validators import MinValueValidator
from django.db import models

from users.models import User


class Tag(models.Model):
    """
    Тэги для рецептов (может быть несколько)
    Связаны с Recipe через ManyToManyField и RecipeTag
    """
    name = models.CharField('Название', max_length=200, unique=True)
    color = models.CharField('Цветовой HEX-код', max_length=7, unique=True)
    slug = models.SlugField('Уникальный слаг', unique=True, max_length=200)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """
    Ингредиенты для рецептов (может быть несколько)
    Связаны с Recipe через IngredientRecipe
    """
    name = models.CharField('Название', max_length=200)
    measurement_unit = models.CharField('Единица измерения', max_length=200)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """
    Модель рецепта
    Связаны с Ingredient через IngredientRecipe (с доп.полем amount)
    Связаны с Tag через ManyToManyField и RecipeTag
    Связаны с User через ForeignKey
    Автосортиовка по убыванию даты публикации
    """
    name = models.CharField('Название', max_length=200)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор публикации',
    )
    text = models.TextField('Описание')
    cooking_time = models.PositiveIntegerField('Время приготовления, мин')
    pub_date = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True,
        db_index=True
    )
    tags = models.ManyToManyField(
        Tag, through='RecipeTag', verbose_name='Теги'
    )
    image = models.ImageField(
        'Картинка',
        upload_to='recipes/images/',
        null=False
    )
    portions = models.PositiveIntegerField('Количество порций')

    class Meta:
        ordering = ['-pub_date']

    def __str__(self):
        return self.name


class RecipeTag(models.Model):
    """
    Модель связи Recipe и Tag
    Пара Recipe-Tag должна быть уникальной
    """
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        verbose_name='Тег'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tag', 'recipe'],
                name='unique_tag_recipe_pair'
            )
        ]

    def __str__(self):
        return f'{self.recipe} {self.tag}'


class IngredientRecipe(models.Model):
    """
    Модель связи Recipe и Ingredient
    Пара Recipe-Ingredient должна быть уникальной
    Содержит доп.поле - amount
    """
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
        related_name='recipes'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='ingredients'
    )
    amount = models.FloatField(
        'Количество',
        validators=[MinValueValidator(0)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['ingredient', 'recipe'],
                name='unique_ingredient_recipe_pair'
            )
        ]

    def __str__(self):
        return f'{self.recipe} {self.ingredient}'

    def save(self, *args, **kwargs):
        """Добавлена проверка валидаторами перед сохранением в БД."""
        self.full_clean()
        super().save(*args, **kwargs)


class ShoppingCart(models.Model):
    """
    Модель связи Recipe и User для продуктовой корзины
    Пара Recipe-User должна быть уникальной
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Владелец списка',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_cart',
        verbose_name='Рецепт',
    )
    portions_to_shop = models.PositiveIntegerField('Количество порций')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe_in_cart_pair'
            )
        ]


class FavoriteRecipes(models.Model):
    """
    Модель связи Recipe и User для избранных рецептов
    Пара Recipe-User должна быть уникальной
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_recipes',
        verbose_name='Любитель рецепта',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Рецепт',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_fav_recipe_pair'
            )
        ]
