from django.contrib import admin
from .models import Product
# Register your models here.

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', "brand", "title", "actual_price",
                     "discounted_price", 'quantity', 'in_stock', 'account', 'created_by']