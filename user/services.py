from .models import Permission,User as CustomUser
from django.db.models import Q
from django.conf import settings
import logging
import pdb
import stripe
from decouple import config
from django.dispatch import receiver
from .signals import user_logged_in
from .models import UserLoggedInActivity
#log configuration 
logging.basicConfig(filename="logfile.log",style='{',level=logging.DEBUG,format="{asctime} - {lineno}-- {message}")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# granting permission to user 
stripe.api_key = config("STRIPE_SECRET_KEY")
def grant_permission(account,permission_id,user_id):
    user_instance = CustomUser.objects.filter(account=account,pk=user_id).first()
    if not user_instance:
        return False
    permission_instance = Permission.objects.filter(pk=permission_id).first()
    if not permission_instance:
        return False
    user_instance.permissions.add(permission_instance)
    user_instance.save()
    return True

def create_stripe_customer(created_user_instance):
    customer_stripe_response = stripe.Customer.create(
        name = created_user_instance.user.username,
        email = created_user_instance.user.email
    )
    return customer_stripe_response.id

@receiver(user_logged_in)
def log_user_logged_in_success(sender,request,user,**kwargs):
    user_agent_info = request.META.get('HTTP_USER_AGENT')[:255],
    ip = request.META.get('REMOTE_ADDR')
    user_login_activity_log = UserLoggedInActivity(ip_address=ip,
                                                user=user,
                                                user_agent_info=user_agent_info,
                                                login_status=kwargs.get('login'))
    user_login_activity_log.save()
    
