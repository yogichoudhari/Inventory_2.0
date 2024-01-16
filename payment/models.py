from django.db import models
from product.models import Product
from user.models import User


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
    product = models.ForeignKey(Product,on_delete=models.SET_NULL,null=True)