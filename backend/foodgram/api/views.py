from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .permissions import IsAdminOrReadOnly, IsAuthorOrAdminOrReadOnly
from .serializers import (
    TagSerializer, IngredientSerializer, SubscribeSerializer,
    UserSubscribeSerializer, RecipeWriteSerializer, RecipeReadSerializer,
    FavoriteRecipesSerializer, RecipeShortSerializer, ShoppingCartSerializer
)
from .filtersets import RecipeFilterSet
from recipes.models import Tag, Ingredient, Recipe, FavoriteRecipes, ShoppingCart
from users.models import Subscribe
from pprint import pprint
from djoser.views import UserViewSet


User = get_user_model()


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilterSet

    """def get_filterset_kwargs(self, filterset_class):
        kwargs = super(RecipeViewSet, self).get_filterset_kwargs(filterset_class)
        kwargs['user'] = self.request.user
        return kwargs"""

    def get_serializer_class(self):
        if self.action == 'favorite':
            return FavoriteRecipesSerializer
        elif self.action == 'shopping_cart':
            return ShoppingCartSerializer
        elif self.request.method == 'GET':
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        headers = self.get_success_headers(serializer.data)
        instance_serializer = RecipeReadSerializer(instance, context={'request': request})
        return Response(instance_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def add_del_recipe_to_users_list(self, model_name):
        recipe = get_object_or_404(Recipe, pk=self.request.parser_context['kwargs']['pk'])
        current_user = self.request.user
        if self.request.method == "DELETE":
            instance = get_object_or_404(model_name, user=current_user, recipe=recipe)
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        elif self.request.method == "POST":
            data_with_recipe = self.request.data.copy()
            data_with_recipe['recipe'] = recipe.pk
            serializer = self.get_serializer(data=data_with_recipe)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=current_user, recipe=recipe)
            headers = self.get_success_headers(serializer.data)
            instance_serializer = RecipeShortSerializer(recipe)
            return Response(instance_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(['post', 'delete'], detail=True, permission_classes=(permissions.IsAuthenticated, ))
    def favorite(self, request, *args, **kwargs):
        return self.add_del_recipe_to_users_list(FavoriteRecipes)
    
    @action(["post", "delete"], detail=True, permission_classes=(permissions.IsAuthenticated,))
    def shopping_cart(self, request, *args, **kwargs):
        return self.add_del_recipe_to_users_list(ShoppingCart)
    
    def show_users_list(self):
        current_user = self.request.user
        if self.action == 'favorite_recipes':
            recipes_list = Recipe.objects.filter(favorited_by__user=current_user)
        elif self.action == 'shopping_cart_recipes':
            recipes_list = Recipe.objects.filter(in_shopping_cart__user=current_user)
        page = self.paginate_queryset(recipes_list)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(recipes_list, many=True)
        return Response(serializer.data)
    
    @action(['get',], detail=False, permission_classes=(permissions.IsAuthenticated,))
    def favorite_recipes(self, request, *args, **kwargs):
        return self.show_users_list()

    @action(['get',], detail=False, permission_classes=(permissions.IsAuthenticated,))
    def shopping_cart_recipes(self, request, *args, **kwargs):
        return self.show_users_list()


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ('^name',)
    pagination_class = None


class UserCustomViewSet(UserViewSet):
    def get_serializer_class(self):
        if self.action == 'subscribe':
            return SubscribeSerializer
        elif self.action == 'subscriptions':
            return UserSubscribeSerializer
        return super().get_serializer_class()

    @action(["post", "delete"], detail=True, permission_classes=(permissions.IsAuthenticated,))
    def subscribe(self, request, *args, **kwargs):
        self.get_object = self.get_instance
        author = get_object_or_404(User, pk=request.parser_context['kwargs']['id'])
        current_user = self.request.user
        if request.method == "DELETE":
            instance = get_object_or_404(Subscribe, user=current_user, author=author)
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        elif request.method == "POST":
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=current_user, author=author)
            headers = self.get_success_headers(serializer.data)
            instance_serializer = UserSubscribeSerializer(author, context={'request': request})
            return Response(instance_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(['get',], detail=False, permission_classes=(permissions.IsAuthenticated,))
    def subscriptions(self, request, *args, **kwargs):
        current_user = self.request.user
        subscriptions = User.objects.filter(followers__user=current_user)
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(subscriptions, many=True)
        return Response(serializer.data)
