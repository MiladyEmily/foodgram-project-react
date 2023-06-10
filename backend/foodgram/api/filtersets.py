from django_filters import filters
from django_filters.rest_framework.filterset import FilterSet
from recipes.models import Recipe
from pprint import pprint


class MultiValueTagFilter(filters.BaseCSVFilter, filters.CharFilter):
    def filter(self, qs, value):
        if value:
            qs = qs.filter(tags__slug__in=value)
        return qs


class RecipeFilterSet(FilterSet):
    """Переименовывает поля фильтрации для связанных моделей в Title."""
    tags = MultiValueTagFilter(field_name='tags__slug')

    class Meta:
        model = Recipe
        fields = ['author', 'tags']
    
    def filter_queryset(self, queryset):
        current_user = self.request.user
        if current_user.is_authenticated and 'is_favorited' in self.data:
            is_favorited = self.data['is_favorited']
            if is_favorited == '1':
                queryset = queryset.filter(favorited_by__user=current_user)
            if is_favorited == '0':
                queryset = queryset.exclude(favorited_by__user=current_user)
        if current_user.is_authenticated and 'is_in_shopping_cart' in self.data:
            is_in_shopping_cart = self.data['is_in_shopping_cart']
            if is_in_shopping_cart == '1':
                queryset = queryset.filter(in_shopping_cart__user=current_user)
            if is_in_shopping_cart == '0':
                queryset = queryset.exclude(in_shopping_cart__user=current_user)
        return super().filter_queryset(queryset)