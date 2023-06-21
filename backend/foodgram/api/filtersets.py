from django_filters import filters
from django_filters.rest_framework.filterset import FilterSet
from recipes.models import Recipe, Ingredient


class MultiValueTagFilter(filters.BaseCSVFilter, filters.CharFilter):
    """
    Добавляет фильтрацию по полю tags с несколькими значениями (ИЛИ).
    """
    def filter(self, qs, value):
        if value:
            qs = qs.filter(tags__slug__in=value)
        return qs


class NameFilter(FilterSet):
    """Фильтр по name (вхождение с начала)."""
    class Meta:
        model = Ingredient
        fields = {
            'name': ['startswith'],
        }


class RecipeFilterSet(FilterSet):
    """
    Фильтр по tags(поле tags__slug), по id автора, по доп.вычисляемым
    полям is_in_shopping_cart (0,1) и is_favorited (0,1) (для авторизованных).
    """
    tags = MultiValueTagFilter(field_name='tags__slug')

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
