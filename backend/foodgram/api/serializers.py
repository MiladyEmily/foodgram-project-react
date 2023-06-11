import re
import base64

from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (
    Tag, Ingredient, Recipe, ShoppingCart, FavoriteRecipes, RecipeTag,
    IngredientRecipe
)
from users.models import Subscribe


User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Декодирует строку из base64 в картинку и сохраняет файл."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тэгов."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')

    def validate_color(self, value):
        """Проверяет, является ли переданная строка кодом цвета HEX."""
        is_hex_code = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', value)
        if not is_hex_code:
            raise serializers.ValidationError('Это не код цвета Hex')
        return value


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингридиентов."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class UserBaseSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для юзеров.
    Доп.поле is_subscribed - подписан ли текущий пользователь на этого.
    """
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'username',
            'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        """
        Вычисляет, подписан ли текущий пользователь на этого.
        """
        current_user = self.context.get('request').user
        return (
            current_user.is_authenticated
            and Subscribe.objects.filter(
                user=current_user,
                author=obj
            ).exists()
        )


class UserGetSerializer(UserBaseSerializer):
    """
    Сериализатор для чтения юзеров.
    """
    pass


class RecipeReadSerializer(serializers.ModelSerializer):
    """
    Сериализатор для чтения рецептов.
    Доп.поле is_favorited - есть ли рецепт в избранном у текущего пользователя.
    Доп.поле is_in_shopping_cart - есть ли рецепт в корзине у текущего
    пользователя.
    Подробный показ Ingredient, Tag, User, с которыми связан рецепт.
    """
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    tags = TagSerializer(many=True)
    ingredients = serializers.SerializerMethodField()
    author = UserGetSerializer()
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name', 'text', 'image',
            'cooking_time', 'is_favorited', 'is_in_shopping_cart'
        )

    def get_ingredients(self, obj):
        """
        Добавляет информацию об ингридиенте и его количестве в выдачу.
        """
        ingredients = []
        ingredientrecipe_list = obj.ingredients.all()
        for item in ingredientrecipe_list:
            base_ingredient_info = IngredientSerializer(item.ingredient).data
            base_ingredient_info['amount'] = item.amount
            ingredients.append(base_ingredient_info)
        return ingredients

    def get_is_in_shopping_cart(self, obj):
        """
        Вычисляет, есть ли рецепт в корзине у текущего пользователя.
        """
        current_user = self.context.get('request').user
        return (
            current_user.is_authenticated
            and ShoppingCart.objects.filter(
                user=current_user,
                recipe=obj
            ).exists()
        )

    def get_is_favorited(self, obj):
        """
        Вычисляет, есть ли рецепт в избранном у текущего пользователя.
        """
        current_user = self.context.get('request').user
        return (
            current_user.is_authenticated
            and FavoriteRecipes.objects.filter(
                user=current_user,
                recipe=obj
            ).exists()
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания/редактирования рецептов.
    """
    author = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault()
    )
    tags = serializers.SlugRelatedField(
        slug_field='id',
        queryset=Tag.objects.all(),
        many=True
    )
    ingredients = serializers.SlugRelatedField(
        slug_field='id',
        queryset=Ingredient.objects.all(),
        many=True
    )
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name', 'text', 'image',
            'cooking_time'
        )
        read_only_fields = ('author',)

    def to_internal_value(self, data):
        """
        Дополнительно убирает из первоначальных данных количество ингридиента.
        """
        data_without_amount = data.copy()
        if 'ingredients' in data:
            ingredients = data['ingredients'].copy()
            for i in range(len(ingredients)):
                ingredients[i] = ingredients[i]['id']
            data_without_amount['ingredients'] = ingredients
        return super().to_internal_value(data_without_amount)

    def create(self, validated_data):
        """
        Создаёт объект рецепта.
        Создаёт связь многое-ко-многим с моделью Tag, Ingredient.
        """
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        current_recipe = Recipe.objects.create(**validated_data)
        for tag in tags:
            RecipeTag.objects.create(
                tag=tag, recipe=current_recipe)
        self.create_ingredient_recipe_link(current_recipe, ingredients)
        return current_recipe

    def create_ingredient_recipe_link(self, current_recipe, ingredients):
        """
        Создаёт связь многое-ко-многим с Ingredient через IngredientRecipe.
        Вносит в модель IngredientRecipe параметр исходных данных - amount.
        """
        ingredients_with_amount = self.initial_data['ingredients']
        for i in range(len(ingredients)):
            amount = ingredients_with_amount[i]['amount']
            IngredientRecipe.objects.create(
                ingredient=ingredients[i], recipe=current_recipe, amount=amount
            )

    def update(self, instance, validated_data):
        """
        Частично обновляет существующй рецепт.
        Полностью перезаписывает связи IngredietnRecipe (если такое поле было
        передано).
        """
        instance.image = validated_data.get('image', instance.image)
        if 'ingredients' in validated_data:
            IngredientRecipe.objects.filter(recipe=instance).delete()
            ingredients = validated_data.pop('ingredients')
            self.create_ingredient_recipe_link(instance, ingredients)
        return super().update(instance, validated_data)

    def validate_cooking_time(self, value):
        """Проверяет, что время приготовления неотрицательное."""
        if value <= 0:
            raise serializers.ValidationError(
                'Время приготовления не может быть отрицательным.'
            )
        return value

    def validate_ingredients(self, value):
        """Проверяет, что количество ингридиента неотрицательное."""
        ingredients = self.initial_data['ingredients']
        for ingredient in ingredients:
            if ingredient['amount'] <= 0:
                raise serializers.ValidationError(
                    'Количество ингридиента не может быть отрицательным.'
                )
        return value


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для сокращенного показа рецепта."""
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'cooking_time', 'image')


class UserSubscribeSerializer(UserBaseSerializer):
    """
    Сериализатор для показа юзера с его рецептами.
    Рецепты показываются по краткой форме RecipeShortSerializer.
    Доп.поле recipes_count - количество рецептов пользователя.
    """
    recipes_count = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'username',
            'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_recipes_count(self, obj):
        """Считает общее количество рецептов пользователя."""
        return obj.recipes.count()

    def get_recipes(self, obj):
        """
        Ограничивает количество рецептов в выдаче, если был передан параметр
        'recipes_limit'.
        """
        recipes_list = obj.recipes.all()
        query_parameters = self.context.get('request').query_params
        if 'recipes_limit' in query_parameters:
            recipes_limit = query_parameters['recipes_limit']
            if recipes_limit.isdigit():
                recipes_list = recipes_list[:int(recipes_limit)]
        return RecipeShortSerializer(recipes_list, many=True).data


class SubscribeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для подписки.
    Пара User(author)-User(user) должна быть уникальна.
    """
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    author = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Subscribe
        fields = ('user', 'author')
        validators = [
            UniqueTogetherValidator(
                queryset=Subscribe.objects.all(),
                fields=('user', 'author')
            )
        ]

    def validate(self, data):
        """Проверяет, что пользователь не подписывается сам на себя."""
        kwargs = self.context.get('request').parser_context['kwargs']
        author = get_object_or_404(User, pk=kwargs['id'])
        user = self.context.get('request').user
        if author == user:
            raise serializers.ValidationError('Не разрешена подписка на себя')
        return data

    def validate_author(self, value):
        """Присваивает значение полю автор."""
        kwargs = self.context.get('request').parser_context['kwargs']
        author_id = kwargs['id']
        author = get_object_or_404(User, pk=author_id)
        return author


class FavoriteRecipesSerializer(serializers.ModelSerializer):
    """
    Сериализатор для добавления рецепта в избранное.
    Пара Recipe-User должна быть уникальна.
    """
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = FavoriteRecipes
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=FavoriteRecipes.objects.all(),
                fields=('user', 'recipe')
            )
        ]


class ShoppingCartSerializer(serializers.ModelSerializer):
    """
    Сериализатор для добавления рецепта в корзину.
    Пара Recipe-User должна быть уникальна.
    """
    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe')
            )
        ]
