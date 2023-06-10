from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Subscribe
from recipes.models import FavoriteRecipes, ShoppingCart


User = get_user_model()


class FavoriteInline(admin.TabularInline):
    model = FavoriteRecipes
    extra = 1


class ShoppingCartInline(admin.TabularInline):
    model = ShoppingCart
    extra = 1


class UserAdmin(admin.ModelAdmin):
    list_editable = ('password',)
    list_display = ('pk', 'username', 'first_name', 'last_name', 'password') 
    search_fields = ('email', 'username')
    inlines = (FavoriteInline, ShoppingCartInline)


class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('pk', 'author', 'user') 

admin.site.register(Subscribe, SubscribeAdmin)
admin.site.register(User, UserAdmin)
