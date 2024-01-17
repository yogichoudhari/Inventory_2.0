from django.db import models
from django.contrib.auth.models import User as BuiltInUser
from django.core.exceptions import ValidationError
from indian_cities.dj_city import cities
from django.dispatch import receiver
from django.db.models.signals import post_delete
from django.utils import timezone
state_choices = (("Andhra Pradesh","Andhra Pradesh"),
                 ("Arunachal Pradesh ","Arunachal Pradesh "),
                 ("Assam","Assam"),
                 ("Bihar","Bihar"),
                 ("Chhattisgarh","Chhattisgarh"),
                 ("Goa","Goa"),
                 ("Gujarat","Gujarat"),
                 ("Haryana","Haryana"),
                 ("Himachal Pradesh","Himachal Pradesh"),
                 ("Jammu and Kashmir ","Jammu and Kashmir "),
                 ("Jharkhand","Jharkhand"),
                 ("Karnataka","Karnataka"),
                 ("Kerala","Kerala"),
                 ("Madhya Pradesh","Madhya Pradesh"),
                 ("Maharashtra","Maharashtra"),
                 ("Manipur","Manipur"),
                 ("Meghalaya","Meghalaya"),
                 ("Mizoram","Mizoram"),
                 ("Nagaland","Nagaland"),
                 ("Odisha","Odisha"),
                 ("Punjab","Punjab"),
                 ("Rajasthan","Rajasthan"),
                 ("Sikkim","Sikkim"),
                 ("Tamil Nadu","Tamil Nadu"),
                 ("Telangana","Telangana"),
                 ("Tripura","Tripura"),
                 ("Uttar Pradesh","Uttar Pradesh"),
                 ("Uttarakhand","Uttarakhand"),
                 ("West Bengal","West Bengal"),
                 ("Andaman and Nicobar Islands","Andaman and Nicobar Islands"),
                 ("Chandigarh","Chandigarh"),
                 ("Dadra and Nagar Haveli","Dadra and Nagar Haveli"),
                 ("Daman and Diu","Daman and Diu"),
                 ("Lakshadweep","Lakshadweep"),
                 ("Delhi","Delhi"),
                 ("Puducherry","Puducherry"))




class Roll(models.Model):
    roll_choices = (
        ('Admin',"Admin"),
        ("Customer","Customer")
    )
    name = models.CharField(choices=roll_choices, max_length=50)

    def __str__(self):
        return self.name


def phone_validator(value):
    if len(value)>10 or len(value)<10:
        raise ValidationError("phone number should be 10 digit")
    try:
        if type(int(value))==int:
            return value
    except ValueError:
        raise ValidationError("number should be numerical")
    

class Permission(models.Model):
    permission_name = models.CharField(max_length=80,null=False)
    permission_set = models.JSONField(null=False)
    related_to = models.CharField(null=False)
    def __str__(self):
        permission_set  = {k:v for k,v in self.permission_set.items() if v==True}
        return str(permission_set) + "_" +str(self.related_to)
        
class User(models.Model):
    user = models.OneToOneField(BuiltInUser, on_delete=models.CASCADE, related_name="extra_user_fields")
    roll = models.ForeignKey(Roll,on_delete=models.CASCADE)
    phone = models.CharField(validators=[phone_validator],max_length=10,null=False)
    city = models.CharField(choices=cities,max_length=50)
    state = models.CharField(choices=state_choices, max_length=35)
    account = models.ForeignKey('Account',on_delete=models.SET_NULL,related_name='users',null=True)
    permissions = models.ManyToManyField(Permission,related_name="permission")
    subscription_id = models.CharField(max_length=50,null=True)
    stripe_id = models.CharField(max_length=55,null=True)
    is_verified = models.BooleanField(default=False)
    def __str__(self):
        return self.user.username
@receiver(post_delete,sender=User)
def delete_builtin_user(sender,instance,**kwargs):
    instance.user.delete()
    
    

class Account(models.Model):
    admin = models.OneToOneField(User,on_delete=models.CASCADE,related_name='related_account')
    name = models.CharField(max_length=33,null=False,blank=False)
    logo = models.BinaryField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True,blank=True)
    def save(self,*args,**kwargs):
        if self.created_at:
            self.updated_at = timezone.now()
        super(Account,self).save(*args,**kwargs)
    def __str__(self):
        return self.name
