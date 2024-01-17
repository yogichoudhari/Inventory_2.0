from django.contrib import admin
from .models import PaymentLog
# Register your models here.



@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ['id','amount','status','user','customer_stripe_id','created_at','product']
    

