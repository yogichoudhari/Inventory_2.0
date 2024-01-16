from .models import Permission,User as CustomUser
from django.db.models import Q
from django.conf import settings
import logging
import pdb
#log configuration 
logging.basicConfig(filename="logfile.log",style='{',level=logging.DEBUG,format="{asctime} - {lineno}-- {message}")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# granting permission to user 

def grant_permission(account,permission_id,user_id):
    try:
        user_instance = CustomUser.objects.filter(account=account,pk=user_id).first()
        if not user_instance:
            return False
        permission_instance = Permission.objects.filter(pk=permission_id).first()
        if not permission_instance:
            return False
        user_instance.permissions.add(permission_instance)
        user_instance.save()
        return True
    except Exception as e:
        logger.exceptions(e,f'exeptions occured -- {str(e)}')


    
        
