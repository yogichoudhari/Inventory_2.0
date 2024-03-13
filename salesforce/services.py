from payment.services import assign_subscription_to_user
from user.models import User as CustomUser, Role
from django.contrib.auth.models import User
from payment.services import assign_subscription_to_user
from user.services import create_stripe_customer
from .models import EncryptionKeyId, AccountCredentials
from django.db import transaction
from .models import Auth
from datetime import datetime
from django.utils import timezone
from django_q.tasks import async_task
from decouple import config
from django.core.cache import cache
import requests
import logging
import boto3
import pdb
import xmltodict


logger = logging.getLogger('file')  # Initialize the logger

API_VERSION = 'v59.0'


def get_client_credentials(admin_user):
    # get the account related to the admin user
    account = admin_user.account
    
    # Get the client ID , client secret and base_url from the account
    sf_cred_obj = AccountCredentials.objects.filter(account=account).first()

    # check if the client credentials are available in the object decrypt the id and secret
    if sf_cred_obj:
        decrypted_client_id = decrypt_data(sf_cred_obj.client_id)
        decrypted_client_secret = decrypt_data(sf_cred_obj.client_secret)
        base_url = sf_cred_obj.base_url
        
        # return salesforce client credentials 
        return base_url, decrypted_client_id, decrypted_client_secret
    
    # if there are no credentials in the account then return None
    else:
        return None, None, None



def get_auth_dialog_url(admin_user):
    try:
        
        # Retrive the salesforce client credentials from database pertaining to the admin
        BASE_URL,CLIENT_ID,_ = get_client_credentials(admin_user)
        
        # check if the credentials are None
        if not (BASE_URL and CLIENT_ID):
            
            # if none then raise the exception 
            raise Exception("No Salesforce credentials available.")
        
        # construct the redirect URL with the version number app
        REDIRECT_URI = f'https://localhost:8000/api/salesforce/oauth/{admin_user.id}/callback'
        
        # construct the auth dialog uri for the autherization and the code for requesting access token
        url = f"{BASE_URL}/services/oauth2/authorize?response_type=code&redirect_uri={REDIRECT_URI}&client_id={CLIENT_ID}"
        
        # Return constructed auth dialog url
        return url  
    except Exception as e:
        # log exceptions if any 
        logger.error(f'an error occured while requesting the auth dialog url: {str(e)}')
        # and return None as the url was not constructed due to the exception
        return None
    

def get_access_token(code,admin_user,admin_id):
    try:
        # Retrive the salesforce client credentials from database pertaining to the admin                                                                                                                                                               
        BASE_URL,CLIENT_ID,CLIENT_SECRET = get_client_credentials(admin_user)

        # check if the credentials are None
        if not (BASE_URL and CLIENT_ID and CLIENT_SECRET):
            # if none then raise the exception 
            raise Exception("insufficient client credentials to process the request")

        # construct the redirect URI for the OAuth flow
        REDIRECT_URI = f"https://localhost:8000/api/salesforce/oauth/{admin_id}/callback"

        # setting content type header to json
        headers = {
                   "content-type": "application/json"
                   }

        #  Construct the payload for the POST Request for  getting Access Token
        payload = {
            'grant_type':'authorization_code',
            'code':code,
            'client_id':CLIENT_ID,
            'client_secret':CLIENT_SECRET,
            'redirect_uri':REDIRECT_URI
        }

        # Access token api url 
        access_tokenn_url = f"{BASE_URL}/services/oauth2/token"

        # sending the post request to access token api
        response = requests.post(access_tokenn_url,params=payload,headers=headers)

        # log the access token response 
        logger.info(f'access token response obj: {response.json()}')

        # return the response 
        return response
    except Exception as e:
        logger.error(f'an error occured while geting the access token: {str(e)}')
        
    
def fetch_salesforce_users(admin_user):
    try:
        
        # Extract the BASE_URL from the admin's account for the request
        sf_cred_obj = AccountCredentials.objects.filter(account=admin_user.account).first()
        BASE_URL = sf_cred_obj.base_url
        
        # api endpoint on which the request will be sent
        endpoint =f"/services/data/{API_VERSION}/chatter/users/"
        
        # constructing the url for request
        url = f'{BASE_URL}{endpoint}'
        
        # Retrive the encrypted  access token from the database
        auth_obj = Auth.objects.filter(account=admin_user.account).first()
        
        # decrypt the access token and add it to headers
        decrypted_access_token = decrypt_data(auth_obj.access_token)
        headers = {'Authorization':f"Bearer {decrypted_access_token}"}
        
        # send the request to the api 
        response = requests.get(url,headers=headers)
        
        # if the response is ok
        if response.status_code==200:
            
            # to commit at the last when the all the process related to the database is done 
            with transaction.atomic():
                # process the response and save the salesforce user 
                process_salesforce_users(admin_user,response)
        else:
            #if the response is not 200 log the error and raise an exception
            logger.error(f'error occured while fetching the users: {str(response.json())}')
            raise Exception("Error in getting salesforce users")
    
    # handle the exception and send an email to the admin informing about the error
    except Exception as e :
        template_name = "salesforce_user.html"
        subject= "Salesforce user synchronization in Application"
        email = admin_user.user.email
        context = {"error":f'{str(e)}',"admin":admin_user}
        async_task("inventory_management_system.utils.send_email",context,email,template_name,subject)
        logger.error(f'error occured while updating the user as {str(e)}')


def validate_token(admin_user):
    try:
        # Get the Salesforce auth object pertaining the admin account
        auth_obj = Auth.objects.filter(account=admin_user.account).first()
        
        # if auth obj exists
        if auth_obj:
            # then check if the token  has expired or not
            if timezone.now() > auth_obj.expires_at:
                # if it is expired then refresh the access token
                response = refresh_access_token(admin_user,auth_obj)
                
                # if the access token is successfully refreshed return True
                if response:
                    return True
                # if the  access token can't be refreshed 
                else:
                    return False
            # if the access token is not expired yet 
            else:
                return True
        else:
            # raise an exception if the admin user does not authenication token auth obj
            raise Exception("user does not have the authentication tokens")
    
    except Exception as e:
        # log the exception and return False
        logger.exception(f"Access token validation error :{str(e)}")
        return False
        
    
def refresh_access_token(admin_user, auth_obj):
    try:
        # Retrive the salesforce client credentials from database pertaining to the admin 
        BASE_URL ,CLIENT_ID, CLIENT_SECRET = get_client_credentials(admin_user)
        
        # check if the all credentials required for the sending the request is available
        if not (BASE_URL and CLIENT_ID and CLIENT_SECRET):
            # if none then raise the exception 
            raise Exception("insufficient client credentials to process the request")
        
        # check if the salesforce auth object exists if not then raise an exception
        if not auth_obj:
            raise Exception("admin does not have the salesforce auth credentials")
        
        # Decrypt the access token 
        decrypted_refresh_token = decrypt_data(auth_obj.refresh_token)
        
        # raise an exception if the access token is not decrypted
        if not decrypted_refresh_token:
            raise Exception("Error while decrypting the refresh token")
        
        # building a url for requesting the fresh access token usin
        refresh_access_token_url = f"{BASE_URL}/services/oauth2/token"
        
        # create the header for requeting the access token 
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        # create the payload  for making the post request with client id ,secret and refresh token 
        payload = {
            'grant_type': 'refresh_token',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'refresh_token':decrypted_refresh_token
        }
        
        #  make a POST request to the Salesforce server to retrive new access token
        response = requests.post(url=refresh_access_token_url, data=payload, headers=headers)
        
        # check if the response is successfull
        if response.status_code==200:
           # get the access token from the response
           access_token = response.json().get('access_token')
           
           #encrypt the access token before saving it the database
           encrypted_access_token = encrypt_data(access_token)
           
           # replace the access token to newly created access token in the database and save and return True
           auth_obj.access_token = encrypted_access_token
           auth_obj.save()
           return True

        # if the response is not 200
        else:
            # log the details of the response and return False
            logger.info(f" bad response: {str(response.json())}")
            return False
    except Exception as e:
        # Log the exeption and return False
        logger.error(f"error occured while refreshing the token: {str(e)}")
        return False
        

def process_salesforce_users(admin_user, response):
    users = response.json()['users']
    role = Role.objects.get(name='Customer')
    account = admin_user.account
    users_arr = []
    for user in users:
        if check_valid_user(user,admin_user):
            user_data = {key.lower():value for key,value in user.items()}
            if user_data.get('phonenumbers',[]):
                user_data['phonenumbers'] = user_data['phonenumbers'][0]["phonenumber"]
            else:
                del user_data['phonenumbers']
            user_obj = create_user_from_salesforce_users(user_data,role,account)
            if user_obj:
                users_arr.append(user_obj)
            else:
                raise Exception(f"an error occured while creating the user")
    if users_arr:
        subject= "Salesforce user synchronization in Application"
        email = admin_user.user.email
        context = {"users":users_arr,"admin":admin_user}
        template_name = "salesforce_user.html"
        async_task("inventory_management_system.utils.send_email",context,email,template_name,subject)
    else:
        logger.info(f'Users are up to date updated')
        
        

def check_valid_user(user,admin_user):
    if ( user['email'] not in ['noreply@example.com',admin_user.user.email] 
        and user['email'] not in [user.email for user in User.objects.all()]):
        return True
    else:
        return False

def create_user_from_salesforce_users(user_data,role,account):
    try:
        username = user_data.get('username', '')
        first_name = user_data.get('firstname', '')
        last_name = user_data.get('lastname', '')
        phone = user_data.get('phonenumbers',None)
        email = user_data.get('email', '')
        address = user_data.get('address', {})
        
        base_user_obj = User.objects.create_user(username=username, email=email, first_name=first_name, last_name=last_name)
        base_user_obj.set_password('123456')
        base_user_obj.save()
        "file_logger": {"level": "INFO", "handlers": ["file"], "propagate": False,},
        user = CustomUser.objects.create(
            user=base_user_obj,
            phone=phone,
            account=account,
            role=role,
            city=address.get('city', ''),
            state=address.get('state', ''),
            is_verified=True
        )
        
        user_stripe_id = create_stripe_customer(user)
        user.stripe_id = user_stripe_id
        _,subscription_instance = assign_subscription_to_user(user,billing_id=1,product_id=1)
        user.subscription = subscription_instance
        user.save()
        user_dict = {}
        user_dict.update({"username":username,'first_name':first_name,"last_name":last_name,"email":email})
        return user_dict
    except Exception as e:
        logger.error(f'an error occured while creating the user: {str(e)}')
        return None

            
                        
 

def encrypt_data(data):
    try:
        client = boto3.client('kms')
        keyid = EncryptionKeyId.objects.all().first()
        if keyid:
            byte_data = data.encode('utf-8')
            response = client.encrypt(
            KeyId=keyid.keyid,
            Plaintext=byte_data
            )
            encrypted_data = response['CiphertextBlob']
            return encrypted_data
        else:
            return None
    except Exception as e:
        logger.error(f'an error occured while decryption: {str(e)}')
        return None
    
def decrypt_data(data):
    try:
        client = boto3.client('kms')
        keyid = EncryptionKeyId.objects.all().first()
        if keyid:
            byte_data = data.tobytes()
            response = client.decrypt(
            KeyId=keyid.keyid,
            CiphertextBlob=byte_data
            )
            decrypted_byte_data = response['Plaintext']
            decrypted_data = decrypted_byte_data.decode('utf-8')
            return decrypted_data
        else:
            return None
    except Exception as e:
        logger.error(f"error occured while decryption: {str(e)}")
        return None
    


def add_user_from_salesforce(admin_user,xml_data):
    data_dict = xmltodict.parse(xml_data)
    sf_user_info = data_dict["soapenv:Envelope"]["soapenv:Body"]["notifications"]["Notification"]["sObject"]
    modified_sObject_data = {}
    for key, value in sf_user_info.items():
        modified_key = key.replace("sf:", "").lower()
        if modified_key == "mobilephone":
            modified_key = "phonenumbers"
        modified_sObject_data[modified_key] = value
    logger.info(f"here is the recent user created using salesforce: {modified_sObject_data}")
    role = Role.objects.get(name='Customer')
    account = admin_user.account
    user_obj = create_user_from_salesforce_users(modified_sObject_data, role, account)
    user_obj = [user_obj]
    if user_obj:
        subject= "New User is created through the salesforce"
        email = admin_user.user.email
        context = {"users":user_obj,"admin":admin_user}
        template_name = "salesforce_user.html"
        async_task("inventory_management_system.utils.send_email",context,email,template_name,subject)
        
    