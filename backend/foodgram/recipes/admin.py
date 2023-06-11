from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import (
    Recipe, RecipeTag, FavoriteRecipes, Ingredient, IngredientRecipe, Tag,
    ShoppingCart
)


class IngredientInline(admin.TabularInline):
    model = IngredientRecipe
    extra = 1


class TagsInline(admin.TabularInline):
    model = RecipeTag
    extra = 1


class FavoriteInline(admin.TabularInline):
    model = FavoriteRecipes
    extra = 1


class ShoppingCartInline(admin.TabularInline):
    model = ShoppingCart
    extra = 1


class RecipeAdmin(admin.ModelAdmin):
    """
    Отображение в админке модели Recipe
    Доп.поле "В избранном" - счетчик добавления в избранное
    Содержит инлайны для связи с Tag, Ingredient, ShoppingCart, Favorite
    """
    list_editable = ('name', 'text')
    list_display = (
        'pk', 'name', 'author', 'text', 'in_favorite', 'get_tags', 'get_image'
    )
    search_fields = ('name',)
    list_filter = ('author', 'tags__name')
    inlines = (
        IngredientInline, TagsInline, ShoppingCartInline, FavoriteInline
    )

    def in_favorite(self, obj):
        return obj.favorited_by.count()
    in_favorite.short_description = 'В избранном'

    def get_tags(self, obj):
        return [tag.name for tag in obj.tags.all()]
    get_tags.short_description = 'Тэги'

    def get_image(self, obj):
        return mark_safe(f'<img src={obj.image.url} width="80" hieght="30"')
    get_image.short_description = 'Картинка'


class IngredientAdmin(admin.ModelAdmin):
    """Oтображение в админке модели Ingredient"""
    list_editable = ('name', 'measurement_unit')
    list_display = ('pk', 'name', 'measurement_unit')
    search_fields = ('name',)


class TagAdmin(admin.ModelAdmin):
    """Oтображение в админке модели Tag"""
    list_editable = ('name', 'slug', 'color')
    list_display = ('pk', 'name', 'slug', 'color')


class ShoppingCartAdmin(admin.ModelAdmin):
    """Oтображение в админке модели ShoppingCart"""
    list_editable = ('recipe', 'user')
    list_display = ('pk', 'recipe', 'user')


class FavoriteRecipesAdmin(admin.ModelAdmin):
    """Oтображение в админке модели FavoriteRecipes"""
    list_editable = ('recipe', 'user')
    list_display = ('pk', 'recipe', 'user')


admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
admin.site.register(FavoriteRecipes, FavoriteRecipesAdmin)
