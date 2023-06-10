from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from recipes.models import Tag, Ingredient, Recipe, ShoppingCart, FavoriteRecipes, RecipeTag, IngredientRecipe
from users.models import Subscribe
from pprint import pprint
import re


User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')
    
    def validate_color(self, value):
        is_hex_code = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', value)
        if not is_hex_code:
            raise serializers.ValidationError('Это не код цвета Hex')
        return value


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class UserGetSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'username', 'is_subscribed')
    
    def get_is_subscribed(self, obj):
        current_user = self.context.get('request').user
        return (
            current_user.is_authenticated
            and Subscribe.objects.filter(user=current_user, author=obj).exists()
        )


class RecipeReadSerializer(serializers.ModelSerializer):
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    tags = TagSerializer(many=True)
    ingredients = serializers.SerializerMethodField()
    author = UserGetSerializer()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name', 'text', #'image',
            'cooking_time', 'is_favorited', 'is_in_shopping_cart'
        )
    
    def get_ingredients(self, obj):
        ingredients = []
        ingredientrecipe_list = IngredientRecipe.objects.filter(recipe=obj)
        for item in ingredientrecipe_list:
            base_ingredient_info = IngredientSerializer(item.ingredient).data
            base_ingredient_info['amount'] = item.amount
            ingredients.append(base_ingredient_info)
        return ingredients
    
    def get_is_in_shopping_cart(self, obj):
        current_user = self.context.get('request').user
        return (
            current_user.is_authenticated
            and ShoppingCart.objects.filter(user=current_user, recipe=obj).exists()
        )

    def get_is_favorited(self, obj):
        current_user = self.context.get('request').user
        return (
            current_user.is_authenticated
            and FavoriteRecipes.objects.filter(user=current_user, recipe=obj).exists()
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
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

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'name', 'text', #'image',
            'cooking_time'
        )

    def to_internal_value(self, data):
        ingredients = data['ingredients'].copy()
        for i in range(len(ingredients)):
            ingredients[i] = ingredients[i]['id']
        data_without_amount = data.copy()
        data_without_amount['ingredients'] = ingredients
        return super().to_internal_value(data_without_amount)
    
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        current_recipe = Recipe.objects.create(**validated_data)
        for tag in tags:
            RecipeTag.objects.create(
                tag=tag, recipe=current_recipe)
        amounts = self.initial_data['ingredients']
        for i in range(len(ingredients)):
            amount = amounts[i]['amount']
            IngredientRecipe.objects.create(
                ingredient=ingredients[i], recipe=current_recipe, amount=amount)
        return current_recipe
    
    def validate_cooking_time(self, value):
        # Проверяет, что время приготовления неотрицательное.
        if value <= 0:
            raise serializers.ValidationError('Время приготовления должно быть положительным целым числом')
        return value
    
    def validate_ingredients(self, value):
        # Проверяет, что количество ингридиента неотрицательное.
        ingredients = self.initial_data['ingredients']
        for ingredient in ingredients:
            if ingredient['amount'] <= 0:
                raise serializers.ValidationError('Количество ингридиента должно быть положительным числом')
        return value


class RecipeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'cooking_time') #'image',


class UserSubscribeSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'username', 'is_subscribed', 'recipes', 'recipes_count')
    
    def get_is_subscribed(self, obj):
        current_user = self.context.get('request').user
        return (
            current_user.is_authenticated
            and Subscribe.objects.filter(user=current_user, author=obj).exists()
        )
    
    def get_recipes_count(self, obj):
        return obj.recipes.count()
    
    def get_recipes(self, obj):
        recipes_list = obj.recipes.all()
        if 'recipes_limit' in self.context.get('request').query_params:
            recipes_limit = self.context.get('request').query_params['recipes_limit']
            if recipes_limit.isdigit():
                recipes_list = recipes_list[:int(recipes_limit)]
        return RecipeShortSerializer(recipes_list, many=True).data


class SubscribeSerializer(serializers.ModelSerializer):
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
        # Проверка, что пользователь не подписывается сам на себя.
        kwargs=self.context.get('request').parser_context['kwargs']
        author = get_object_or_404(User, pk=kwargs['id'])
        user = self.context.get('request').user
        if author == user:
            raise serializers.ValidationError('Не разрешена подписка на себя')
        return data

    def validate_author(self, value):
        # Присваивает значение полю автор.
        kwargs=self.context.get('request').parser_context['kwargs']
        author_id = kwargs['id']
        author = get_object_or_404(User, pk=author_id)
        return author


class FavoriteRecipesSerializer(serializers.ModelSerializer):
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
