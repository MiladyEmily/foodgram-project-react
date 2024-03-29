from django.contrib.auth import get_user_model
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import F

from recipes.models import (FavoriteRecipes, Ingredient, IngredientRecipe,
                            Recipe, ShoppingCart, Tag)
from users.models import Subscribe
from .filtersets import NameFilterSet, RecipeFilterSet
from .permissions import IsAdminOrReadOnly, IsAuthorOrAdminOrReadOnly
from .serializers import (FavoriteRecipesSerializer, IngredientSerializer,
                          RecipeReadSerializer, RecipeShortSerializer,
                          RecipeWriteSerializer, ShoppingCartSerializer,
                          SubscribeSerializer, TagSerializer,
                          UserSubscribeSerializer)


User = get_user_model()


class RecipeViewSet(viewsets.ModelViewSet):
    """
    Вьюсет для работы с /recipes.
    {id}/favorite/ - добавление рецепта в избранное.
    {id}/shopping_cart/ - добавление рецепта в корзину.
                        - с portions_to_shop - в теле обновляет количество
                          порций в корзине.
    download_shopping_cart/ - загружает .txt со списком покупок.
    """
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilterSet

    def get_serializer_class(self):
        if self.action == 'favorite':
            return FavoriteRecipesSerializer
        elif self.action == 'shopping_cart':
            return ShoppingCartSerializer
        elif self.request.method == 'GET':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def add_del_recipe_to_users_list(self, model_name):
        """
        Базовый @action для работы со списками юзера.
        Добавляет рецепт в список или удаляет из него.
        Ответ по сериализатору RecipeShortSerializer.
        """
        recipe = self.get_object()
        current_user = self.request.user
        if self.request.method == 'DELETE':
            instance = get_object_or_404(
                model_name,
                user=current_user,
                recipe=recipe
            )
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        if self.request.method == "PATCH":
            instance = get_object_or_404(
                model_name,
                user=current_user,
                recipe=recipe
            )
            serializer = self.get_serializer(
                instance,
                data=self.request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        data_with_recipe = self.request.data.copy()
        data_with_recipe['recipe'] = recipe.pk
        if model_name == ShoppingCart and self.request.method == 'POST':
            """
            При первом добавлении в корзину количество порций как в рецепте.
            """
            data_with_recipe['portions_to_shop'] = recipe.portions
        serializer = self.get_serializer(data=data_with_recipe)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=current_user, recipe=recipe)
        headers = self.get_success_headers(serializer.data)
        instance_serializer = RecipeShortSerializer(recipe)
        return Response(
            instance_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @action(
        ['post', 'delete'],
        detail=True,
        permission_classes=(permissions.IsAuthenticated,)
    )
    def favorite(self, request, *args, **kwargs):
        """Добавляет/удаляет рецепт из списка избранного."""
        return self.add_del_recipe_to_users_list(FavoriteRecipes)

    @action(
        ['post', 'delete', 'patch'],
        detail=True,
        permission_classes=(permissions.IsAuthenticated,)
    )
    def shopping_cart(self, request, *args, **kwargs):
        """Добавляет/удаляет рецепт из корзины."""
        return self.add_del_recipe_to_users_list(ShoppingCart)

    def create_str_ingredient_list(self):
        """Получает список покупок в строковом формате."""
        shopping_cart = self.request.user.shopping_cart.all()
        ingredient_set = []
        ingredient_set_len = 0
        for shop_obj in shopping_cart:
            recipe = shop_obj.recipe
            portions = shop_obj.portions_to_shop / recipe.portions
            ingredients = IngredientRecipe.objects.filter(
                recipe=recipe
                ).exclude(ingredient__measurement_unit='по вкусу')
            new_ingredient = ingredients.values_list(
                    'ingredient__name',
                    'ingredient__measurement_unit'
                ).annotate(total_amount=F('amount')*portions)
            for ingred in new_ingredient:
                i = 0
                while i < ingredient_set_len:
                    if ingredient_set[i][0] == ingred[0] and ingredient_set[i][1] == ingred[1]:
                        ingredient_set[i][2] = ingredient_set[i][2] + ingred[2]
                        break
                    i += 1
                if i != ingredient_set_len:
                    continue
                ingredient_set.append(list(ingred))
                ingredient_set_len += 1
        recipe_queryset = Recipe.objects.filter(
            in_shopping_cart__user=self.request.user
        )
        header = self.get_ingredient_list_header(recipe_queryset)
        footer = '\n⁃ Foodgram ⁃'
        ingredient_str_list = []
        for ingredient in ingredient_set:
            ingredient_str_list.append(
                f'▻ {ingredient[0]} ({ingredient[1]}) - {int(ingredient[2])}'
            )
        return header + '\n'.join(ingredient_str_list) + footer

    def get_ingredient_list_header(self, recipe_list):
        """Создаёт шапку для списка покупок."""
        header = '⁃ Список покупок ⁃\nдля приготовления: '
        for recipe in recipe_list:
            header += f'{recipe.name}, '
        return header[:-2] + '\n'

    @action(detail=False, permission_classes=(permissions.IsAuthenticated,))
    def download_shopping_cart(self, request, *args, **kwargs):
        """Создаёт и отдаёт .txt файл со списком покупок."""
        current_user = self.request.user
        ingredient_list = self.create_str_ingredient_list()
        filename = current_user.username + '_ingredients_list.txt'
        response = HttpResponse(
            ingredient_list,
            content_type='text/plain; charset=utf8',
            status=status.HTTP_200_OK
        )
        response['Content-Disposition'] = 'attachment; filename={0}'.format(
            filename)
        return response


class TagViewSet(viewsets.ModelViewSet):
    """
    Вьюсет для работы с /tags.
    Без пагинации.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class IngredientViewSet(viewsets.ModelViewSet):
    """
    Вьюсет для работы с /ingredients.
    Без пагинации.
    Поиск по полю name (вхождение с начала).
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filter_class = NameFilterSet
    pagination_class = None


class UserCustomViewSet(UserViewSet):
    """
    Дополненный вьюсет для работы с /users.
    """
    def get_serializer_class(self):
        if self.action == 'subscribe':
            return SubscribeSerializer
        elif self.action == 'subscriptions':
            return UserSubscribeSerializer
        return super().get_serializer_class()

    @action(
        ["post", "delete"],
        detail=True,
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscribe(self, request, *args, **kwargs):
        """
        Подписка на автора.
        Создаёт или удаляет объект подписки Subscribe.
        """
        author = self.get_object()
        current_user = self.request.user
        if request.method == "DELETE":
            instance = get_object_or_404(
                Subscribe, user=current_user, author=author
            )
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=current_user, author=author)
        headers = self.get_success_headers(serializer.data)
        instance_serializer = UserSubscribeSerializer(
            author, context={'request': request}
        )
        return Response(
            instance_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    @action(
        ['get', ],
        detail=False,
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscriptions(self, request, *args, **kwargs):
        """
        Показывает все объекты User, на которых подписан текущий юзер.
        Выдача по расширенному типу UserSubscribeSerializer.
        """
        current_user = self.request.user
        subscriptions = User.objects.filter(followers__user=current_user)
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(subscriptions, many=True)
        return Response(serializer.data)
