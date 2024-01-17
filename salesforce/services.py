from decouple import config
from django.core.cache import cache
from rest_framework.response import Response
import requests
import urllib.parse
import logging
import pdb
import time
from user.models import User as CustomUser,Roll
from django.contrib.auth.models import User
from inventory_management_system.utils import response_template,  STATUS_SUCCESS,send_email
logger = logging.getLogger('main')
CLIENT_ID = config('SALESFORCE_CLIENT_ID')
CLIENT_SECRET = config('SALESFORCE_CLIENT_SECRET')
REDIRECT_URI = config("SALESFORCE_REDIRECT_URI")
base_url = "https://webkorps5-dev-ed.develop.my.salesforce.com"

def get_auth_dialog_url():
    url = f"{base_url}/services/oauth2/authorize?response_type=code&redirect_uri={REDIRECT_URI}&client_id={CLIENT_ID}"
    return url


from http.cookies import SimpleCookie

def get_access_token(code):
    pdb.set_trace()
    headers = {
               "content-type": "application/json"
               }
    
    payload = {
        'grant_type':'authorization_code',
        'code':code,
        'client_id':CLIENT_ID,
        'client_secret':CLIENT_SECRET,
        'redirect_uri':'https://localhost:8000/api/salesforce/oauth/callback'
    }
    access_tokenn_url = f"{base_url}/services/oauth2/token"
    response = requests.post(access_tokenn_url,params=payload,headers=headers)
    return response.json()
    
    
def fetch_salesforce_users(admin_user):
    try:
        pdb.set_trace()
        endpoint ="/services/data/v59.0/chatter/users/"
        url = f'{base_url}{endpoint}'
        access_token = cache.get('salesforce_access_token')
        headers = {'Authorization':f"Bearer {access_token}"}
        response = requests.get(url,headers=headers)
        logger.info(f'response {response.json()}')
        users = response.json()['users']
        roll = Roll.objects.get(name='Customer')
        account = admin_user.account
        users_arr = []
        for user in users:
            user_dict = {}
            if user['email'] not in ['noreply@example.com','yogesh.choudhari@webkorps.com'] and user['email'] not in [user.email for user in User.objects.all()]:
                username = '' if user['username']==None else user['username']
                first_name = '' if user['firstName']==None else user['firstName']
                last_name = '' if user['lastName']==None else user['lastName']
                phone = '' if len(user['phoneNumbers'])==0 else user['phoneNumbers'][0]
                email = '' if user['email']==None else user['email']
                address = user['address']
                auth_obj = User.objects.create_user(username=username,email=email,first_name=first_name,last_name=last_name)
                auth_obj.set_password('123456')
                auth_obj.save()
                user = CustomUser.objects.create(user=auth_obj,phone=phone,account=account,roll=roll,city=address['city'],state=address['state'],is_verified=True)
                user_dict.update({"username":username,'first_name':first_name,"last_name":last_name,"email":email})
                users_arr.append(user_dict)
        if users_arr:
            subject = "Salesforce user synchronization in Application"
            email = admin_user.user.email
            context = {"users":users_arr,"admin":admin_user}
            send_email(subject,email,'salesforce_user.html',context)
        else:
            logger.info(f'Users are up to date updated')
    except Exception as e:
        subject = "Salesforce user synchronization in Application"
        email = admin_user.user.email
        context = {"error":f'{str(e)}',"admin":admin_user}
        send_email(subject,email,'salesforce_user.html',context)
        logger.error(f'error occured while updating the user as {str(e)}')
            
                        
    


    
