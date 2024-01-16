from decouple import config
from django.core.cache import cache
from rest_framework.response import Response
import requests
import urllib.parse
import logging
import pdb
import time
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
    
    
def fetch_salesforce_users():
    endpoint ="/services/data/v59.0/chatter/users/"
    url = f'{base_url}{endpoint}'
    access_token = cache.get('salesforce_access_token')
    print(access_token)
    headers = {'Authorization':f"Bearer {access_token}"}
    response = requests.get(url,headers=headers)
    logger.info(f'response {response.json()}')
    return response.json()
    
