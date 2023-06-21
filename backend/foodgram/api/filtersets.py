from django_filters import filters, rest_framework
from django_filters.rest_framework.filterset import FilterSet

from recipes.models import Ingredient, Recipe, Tag


class MultiValueTagFilter(filters.BaseCSVFilter, filters.CharFilter):
    """
    Добавляет фильтрацию по полю tags с несколькими значениями (ИЛИ).
    """
    def filter(self, qs, value):
        print(value)
        if value:
            qs = qs.filter(tags__slug__in=value)
        return qs


class NameFilterSet(FilterSet):
    """Фильтр по name (вхождение с начала)."""
    name = filters.CharFilter(lookup_expr='startswith')

    class Meta:
        model = Ingredient
        fields = ['name',]


class RecipeFilterSet(FilterSet):
    """
    Фильтр по tags(поле tags__slug), по id автора, по доп.вычисляемым
    полям is_in_shopping_cart (0,1) и is_favorited (0,1) (для авторизованных).
    """
    tags = rest_framework.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )

    class Meta:
        model = Recipe
        fields = ['author', 'tags']

    def filter_queryset(self, queryset):
        """
        Добавляет фильтр по is_in_shopping_cart (0,1) и is_favorited (0,1).
        """
        current_user = self.request.user
        is_auth = current_user.is_authenticated
        if is_auth and 'is_favorited' in self.data:
            is_favorited = self.data['is_favorited']
            if is_favorited == '1':
                queryset = queryset.filter(favorited_by__user=current_user)
            if is_favorited == '0':
                queryset = queryset.exclude(favorited_by__user=current_user)
        if is_auth and 'is_in_shopping_cart' in self.data:
            is_in_shopping_cart = self.data['is_in_shopping_cart']
            if is_in_shopping_cart == '1':
                queryset = queryset.filter(in_shopping_cart__user=current_user)
            if is_in_shopping_cart == '0':
                queryset = queryset.exclude(
                    in_shopping_cart__user=current_user
                )
        return super().filter_queryset(queryset)
