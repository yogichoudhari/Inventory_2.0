from django.contrib import admin
from .models import Roll, Account, Permission, User
# Register your models here.

@admin.register(Roll)
class RollAdmin(admin.ModelAdmin):
    list_display = ['id', 'name',]

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'logo', 'created_at', "updated_at"]

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['id', "permission_name", 'permission_set', 'related_to']

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display=["id", "user", "phone", "roll", "state", "city",
                   "account","stripe_id",
                   "is_verified","subscription_id"]