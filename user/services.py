from .models import Permission,User as User
from django.db.models import Q
from django.conf import settings
import logging
import pdb
from rest_framework_simplejwt.tokens import RefreshToken,AccessToken
import stripe
from django.contrib.auth.models import User
from decouple import config
from django.dispatch import receiver
from .signals import user_logged_in
from .models import UserLoggedInActivity
from datetime import timedelta
from salesforce.models import EncryptionKeyId
from payment.services import assign_subscription_to_user
import boto3
from django.core.cache import cache
from django.db import transaction
#log configuration 
logger = logging.getLogger('file_logger')
# granting permission to user 
stripe.api_key = config("STRIPE_SECRET_KEY")



def grant_permission(account,permission_id,user_id):
    user_instance = User.objects.filter(account=account,pk=user_id).first()
    if not user_instance:
        return False
    permission_instance = Permission.objects.filter(pk=permission_id).first()
    if not permission_instance:
        return False
    user_instance.permissions.add(permission_instance)
    user_instance.save()
    return True

def create_stripe_customer(created_user_instance):
    try:
        customer_stripe_response = stripe.Customer.create(
            name = created_user_instance.username,
            email = created_user_instance.email
        )
        pm = stripe.PaymentMethod.create(
          type="card",
          card={
            "token":"tok_visa"},
        )   
        stripe.PaymentMethod.attach(
            pm.id,
            customer=customer_stripe_response.id,
        )
        return customer_stripe_response.id
    except Exception as e:
        logger.error(f'error occured: {str(e)}')

@receiver(user_logged_in)
def log_user_logged_in_success(sender,request,user,**kwargs):
    user_agent_info = request.META.get('HTTP_USER_AGENT')[:255],
    ip = request.META.get('REMOTE_ADDR')
    user_login_activity_log = UserLoggedInActivity(ip_address=ip,
                                                user=user,
                                                user_agent_info=user_agent_info,
                                                login_status=kwargs.get('login'))
    user_login_activity_log.save()
    

def get_tokens_for_user(user,account):

    '''This view is used to create token for user'''
    access_token = AccessToken()
    access_token.lifetime = timedelta(seconds=account.token_expires_in_seconds)
    token = access_token.for_user(user)
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(token),
    }


def create_admin_data_encryption_key(admin):
    client = boto3.client('kms')
    response = client.create_key()
    key_id = response.get('KeyMetadata').get('KeyId')
    key_id_obj = EncryptionKeyId.objects.create(account=admin.account, keyid=key_id)
    key_id_obj.save()
    
    
def create_user_from_external_resources(user_data,role,account):
    try:
        with transaction.atomic():
            username = user_data.get('username', '')
            first_name = user_data.get('firstname', '')
            last_name = user_data.get('lastname', '')
            phone = user_data.get('phonenumbers',None)
            email = user_data.get('email', '')
            address = user_data.get('address', {})
            user_instance = User.objects.create_user(username=username, phone=phone, account=account,
                role=role, city=address.get('city', ''), state=address.get('state', ''),
                is_verified=False, email=email, first_name=first_name, last_name=last_name, is_imported=True)
            

            user_stripe_id = create_stripe_customer(user_instance)
            user_instance.stripe_id = user_stripe_id
            _,subscription_instance = assign_subscription_to_user(user_instance,billing_id=1,product_id=1)
            user_instance.subscription = subscription_instance
            user_instance.save()
            user_dict = {}
            user_dict.update({"username":username,'first_name':first_name,"last_name":last_name,"email":email})
            logger.info("New user created successfully with salesforce data")
            return user_dict
    except Exception as e:
        logger.error(f'an error occured while creating the user: {str(e)}')
        return None
    

def default_password_not_updated(user):
    if user.is_imported and user.last_password_change is None:
        return True
    else:
        return False
        

def verify_otp(otp,user_instance=None):
    try:
        # Check if user instance exists
        if not user_instance:
            raise Exception("Incorrect otp")
        otp_key = "otp_"+str(user_instance.id)

        # Check if OTP key exists in cache
        if otp_key in cache:
            stored_otp = cache.get(otp_key)
            if otp==stored_otp:
                cache.delete(otp_key)
                return True
            else: 
                return False
        else:
            raise Exception(f"otp is expired")
    except Exception as e:
        logger.error(f'an error occured during otp verification: {str(e)}')