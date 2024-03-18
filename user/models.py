from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.core.exceptions import ValidationError
from django.utils import timezone
import datetime
# from payment.models import UserSubscriptionDetail 

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
def phone_validator(value):
    try:
        if len(value)>14 or len(value)<10:
            raise ValidationError("please provide valid phone number")
        if type(int(value))==int:
            return value
    except ValueError:
        raise ValidationError("number should be numerical")
class Role(models.Model):
    role_choices = (
        ('Admin',"Admin"),
        ("Customer","Customer")
    )
    name = models.CharField(choices=role_choices, max_length=50)

    def __str__(self):
        return self.name


class MyUserManager(BaseUserManager):
    def create_user(self, username, email, account=None, first_name=None, 
                    last_name=None, address=None, role=None, phone=None, subscription=None, 
                    stripe_id=None, password=None, is_imported=False ):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email),
            first_name=first_name,
            last_name=last_name,
            username=username,
            account=account,
            address=address,
            role=role,
            phone=phone,
            subscription=subscription,
            stripe_id=stripe_id,
            password=password,
            is_imported=is_imported
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, account=None,  
                         first_name=None, last_name=None , 
                         role=None, address=None, phone=None, subscription=None, 
                         stripe_id=None, password=None, is_imported=False):
        """
        Creates and saves a superuser with the given email, date of
        birth and password.
        """
        user = self.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            username=username,
            account=account,
            address=address,
            role=role,
            phone=phone,
            subscription=subscription,
            stripe_id=stripe_id,
            password=password,
            is_imported=is_imported
        )
        user.is_admin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    username = models.CharField(max_length=128, unique=True, null=False)
    email = models.EmailField(
        max_length=255,
        unique=True
    )
    first_name = models.CharField(max_length=50, null=True)
    last_name = models.CharField(max_length=50, null=True)
    password = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(validators=[phone_validator], max_length=14, null=True)
    address = models.CharField(max_length=280, blank=True, null=True)
    account = models.ForeignKey('Account', on_delete=models.CASCADE, related_name='users', null=True)
    permissions = models.ManyToManyField("Permission", related_name="permission")
    subscription = models.ForeignKey("payment.UserSubscriptionDetail", on_delete=models.SET_NULL, blank=True, null=True)
    stripe_id = models.CharField(max_length=55, null=True, blank=True)
    is_imported = models.BooleanField(default=False)
    last_password_change = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    
    
    objects = MyUserManager()
    
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.email

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin




    

class Permission(models.Model):
    permission_name = models.CharField(max_length=80,null=False)
    permission_set = models.JSONField(null=False)
    related_to = models.CharField(null=False)
    def __str__(self):
        permission_set  = {k:v for k,v in self.permission_set.items() if v==True}
        return str(permission_set) + "_" +str(self.related_to)
        

    
    

class Account(models.Model):
    admin = models.OneToOneField("User",on_delete=models.CASCADE,related_name='related_account')
    name = models.CharField(max_length=33,null=False,blank=False,unique=True)
    logo = models.BinaryField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True,blank=True)
    token_expires_in_seconds = models.IntegerField(default=60*3)
    def save(self,*args,**kwargs):
        if self.created_at:
            self.updated_at = timezone.now()
        super(Account,self).save(*args,**kwargs)
    def __str__(self):
        return self.name


class UserLoggedInActivity(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    status = (
        ('success','success'), 
        ('failed','failed')
    )
    login_status = models.CharField(choices=status,max_length=8)
    ip_address = models.GenericIPAddressField()
    login_datetime = models.DateTimeField(auto_now=True)
    user_agent_info = models.CharField(max_length=255)