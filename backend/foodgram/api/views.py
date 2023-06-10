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
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        instance_serializer = RecipeReadSerializer(instance, context={'request': request})
        return Response(instance_serializer.data)
    
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
