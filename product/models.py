from django.db import models
from user.models import Account


class Product(models.Model):
    category = models.CharField(max_length=100,null=False,blank=False)
    brand = models.CharField(max_length=25,default="")
    title = models.CharField(max_length=250,default="")
    quantity = models.PositiveIntegerField(default=0,null=False,blank=False)
    actual_price = models.PositiveIntegerField(default=99,null=False,blank=False)
    discounted_price = models.PositiveIntegerField(default=99,null=False,blank=False)
    account = models.ForeignKey(Account,on_delete=models.CASCADE)
    created_by = models.ForeignKey("user.User",on_delete=models.CASCADE,null=False)

    def save(self,*args,**kwargs):
        self.category = self.category.title()
        self.title = self.title.title()
        self.brand = self.brand.title()
        super(Product,self).save(*args,**kwargs)
    def __str__(self):
        return self.category
    
    @property
    def in_stock(self):
        if self.quantity>0:
            return "Available"
        else:
            return "out of stock"
