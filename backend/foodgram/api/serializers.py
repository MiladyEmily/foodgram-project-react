import re

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.validators import UniqueValidator, UniqueTogetherValidator
from djoser.serializers import UserCreateSerializer

from recipes.models import (FavoriteRecipes, Ingredient, IngredientRecipe,
                            Recipe, RecipeTag, ShoppingCart, Tag)
from users.models import Subscribe
from .fields import Base64ImageField


User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""
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
    """Сериализатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class UserWriteSerializer(UserCreateSerializer):
    """
    Сериализатор для юзеров.
    Делает поле username обязательным, а email нечувствительным к регистру.
    """
    email = serializers.EmailField(
        validators=[
            UniqueValidator(queryset=User.objects.all(), lookup='iexact'),
        ]
    )

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'username',
                  'password')


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


class IngredientWithAmountReadSerializer(serializers.ModelSerializer):
    """Сериализатор для показа ингредиента с его количеством в рецепте."""
    ingredient = IngredientSerializer()

    class Meta:
        model = IngredientRecipe
        fields = (
            'ingredient', 'amount'
        )

    def to_representation(self, instance):
        """
        Делает так, чтобы информация об ингредиенте и его количестве была на
        одном уровне вложенности.
        """
        ret = super().to_representation(instance)
        ret['ingredient']['amount'] = ret['amount']
        return ret['ingredient']


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
    ingredients = IngredientWithAmountReadSerializer(many=True)
    author = UserGetSerializer()
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name', 'text', 'image',
            'cooking_time', 'is_favorited', 'is_in_shopping_cart', 'portions',
        )

    def get_is_in_shopping_cart(self, obj):
        """
        Вычисляет, есть ли рецепт в корзине у текущего пользователя.
        В поле показывается количество порций в корзине (0 если рецепта нет).
        """
        current_user = self.context.get('request').user
        if not current_user.is_authenticated:
            return 0
        shopping_cart_obj = ShoppingCart.objects.filter(
                user=current_user,
                recipe=obj
            )
        if not shopping_cart_obj:
            return 0
        return shopping_cart_obj[0].portions_to_shop

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


class IngredientIdAmountSerializer(serializers.ModelSerializer):
    id = serializers.SlugRelatedField(
        source='ingredient',
        slug_field='id',
        queryset=Ingredient.objects.all(),
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


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
    ingredients = IngredientIdAmountSerializer(many=True)
    image = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name', 'text', 'image',
            'cooking_time', 'portions'
        )
        read_only_fields = ('author',)

    def create(self, validated_data):
        """
        Создаёт объект рецепта.
        Создаёт связь многое-ко-многим с моделью Tag, Ingredient.
        """
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        current_recipe = Recipe.objects.create(**validated_data)
        bulk_tags = [
            RecipeTag(
                recipe=current_recipe,
                tag=tag
            )
            for tag in tags
        ]
        RecipeTag.objects.bulk_create(bulk_tags)
        self.create_ingredient_recipe_link(current_recipe, ingredients)
        return current_recipe

    def create_ingredient_recipe_link(self, current_recipe, ingredients):
        """
        Создаёт связь многое-ко-многим с Ingredient через IngredientRecipe.
        Вносит в модель IngredientRecipe параметр исходных данных - amount.
        """
        bulk_ingredients = [
            IngredientRecipe(
                recipe=current_recipe,
                ingredient=ingredient['ingredient'],
                amount=ingredient['amount']
            )
            for ingredient in ingredients
        ]
        IngredientRecipe.objects.bulk_create(bulk_ingredients)

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

    def check_positive(self, value, text):
        """Проверяет, что значение в поле > 0."""
        if value <= 0:
            raise serializers.ValidationError(
                f'{text} должно быть положительным числом.'
            )
        return value

    def validate_cooking_time(self, value):
        """Проверяет, что время приготовления > 0."""
        return self.check_positive(value, 'Время приготовления')
    
    def validate_portions(self, value):
        """Проверяет, что количество порций > 0."""
        return self.check_positive(value, 'Количество порций')

    def validate_ingredients(self, value):
        """Проверяет, чтобы ингредиенты для одного рецепта не повтоялись."""
        unique_ingredients_pk = []
        for ingredient in value:
            current_pk = ingredient['ingredient'].pk
            if current_pk in unique_ingredients_pk:
                raise serializers.ValidationError(
                    'Ингредиенты в списке не должны повторяться.'
                )
            unique_ingredients_pk.append(current_pk)
        return value

    def validate_tags(self, value):
        """Проверяет, чтобы теги для одного рецепта не повтоялись."""
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                'Теги в списке не должны повторяться.'
            )
        return value

    def to_representation(self, instance):
        """Заменяет сериализатор выдачи на RecipeReadSerializer."""
        ret = RecipeReadSerializer(
            instance,
            context={'request': self.context['request']}
        )
        return ret.data


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
        fields = ('user', 'recipe', 'portions_to_shop')
        validators = [
            UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe')
            )
        ]
  