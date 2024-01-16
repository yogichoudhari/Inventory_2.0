from django.db import models
from product.models import Product


#create your models here

class Survey(models.Model):
    survey_id = models.PositiveIntegerField()
    collector_id = models.PositiveIntegerField()
    product = models.OneToOneField(Product,on_delete=models.CASCADE)
    