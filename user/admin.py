from django.contrib import admin
from .models import Role, Account, Permission, User
# Register your models here.

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'name',]

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'logo', 'created_at', "updated_at"]

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['id', "permission_name", 'permission_set', 'related_to']

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display=["id", "username","email", "phone", "role", "address",
                   "account","stripe_id",
                   "is_verified","subscription_id"]