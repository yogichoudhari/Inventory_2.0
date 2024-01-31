from django.contrib import admin
from .models import PaymentLog, Subscription, SubscriptionPlan
# Register your models here.



@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ['id','amount','status','user','customer_stripe_id','created_at','product']
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['id','account','name',"product_id"]
@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['id','price_id','name',"product"]
    

