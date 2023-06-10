from django.contrib import admin

from .models import Recipe, RecipeTag, FavoriteRecipes, Ingredient, IngredientRecipe, Tag, ShoppingCart


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
    list_editable = ('name', 'text')
    list_display = ('pk', 'name', 'author', 'text', 'in_favorite', 'get_tags')
    search_fields = ('name',)
    list_filter = ('author', 'tags__name')
    inlines = (IngredientInline, TagsInline, ShoppingCartInline, FavoriteInline)
    
    def in_favorite(self, obj):
        return obj.favorited_by.count()
    in_favorite.short_description = 'В избранном'

    def get_tags(self, instance):
        return [tag.name for tag in instance.tags.all()]
    get_tags.short_description = 'Тэги'


class IngredientAdmin(admin.ModelAdmin):
    list_editable = ('name', 'measurement_unit')
    list_display = ('pk', 'name', 'measurement_unit') 
    search_fields = ('name',)


class TagAdmin(admin.ModelAdmin):
    list_editable = ('name', 'slug', 'color')
    list_display = ('pk', 'name', 'slug', 'color')


class ShoppingCartAdmin(admin.ModelAdmin):
    list_editable = ('recipe', 'user')
    list_display = ('pk', 'recipe', 'user')


class FavoriteRecipesAdmin(admin.ModelAdmin):
    list_editable = ('recipe', 'user')
    list_display = ('pk', 'recipe', 'user')


admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
admin.site.register(FavoriteRecipes, FavoriteRecipesAdmin)
