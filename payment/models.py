from django.db import models
# from product.models import Product
from user.models import User, Account


class PaymentLog(models.Model):
    amount = models.PositiveIntegerField()
    customer_stripe_id = models.CharField(max_length=200)
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    payment_status_choices = [
        ('success','success'),
        ('failed', 'failed')
    ]
    status = models.CharField(choices=payment_status_choices)
    created_at = models.DateTimeField(auto_now_add=True)
    product = models.ForeignKey("product.Product",on_delete=models.SET_NULL,null=True)
    


class SubscriptionPlan(models.Model):
    plan_choices = [
        ("M","Monthly"),
        ("Q","Quaterly"),
        ("Y","Yearly"),
    ]
    name = models.CharField(choices=plan_choices ,max_length=100)
    price_id = models.CharField(max_length=100)
    product = models.ForeignKey("Subscription", on_delete=models.CASCADE)

class Subscription(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=100,unique=True)
    product_id = models.CharField(max_length=100)

    
 
class Coupon(models.Model):
    coupon_id = models.CharField(max_length=15)
    subscription = models.OneToOneField(Subscription,on_delete=models.CASCADE)

class UserSubscriptionDetail(models.Model):
    subscription_id = models.CharField(max_length=30)
    coupon = models.ForeignKey(Coupon,on_delete=models.SET_NULL,null=True)
    status = models.CharField(max_length=35)
    end_on = models.DateField()
    billing = models.CharField(max_length=20)
    name = models.CharField(max_length=35)
    