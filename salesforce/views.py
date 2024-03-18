
from django.http import HttpResponse
from . import services
from .services import validate_token
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from inventory_management_system.utils import (response_template,STATUS_SUCCESS, STATUS_FAILED)
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAdminUser
from user.models import User
from rest_framework import status
from django.core.cache import cache
from salesforce.services import encrypt_data
from user.models import User as User
from .models import AccountCredentials, Auth
from django_q.tasks import async_task
import boto3
import logging


logger = logging.getLogger('watchtower')
client = boto3.client("kms")
@api_view(['GET', "POST"])
@permission_classes([IsAdminUser])
def auth_dialog(request):
   try:
       # get admin user
       admin_user = request.user
       # get auth dialog url
       url = services.get_auth_dialog_url(admin_user) 
       # if url is None/False
       if not url: 
           raise Exception("an error occured") 
       # return success response
       return Response(response_template(STATUS_SUCCESS, url=url),
                       status=status.HTTP_200_OK)
   # catch exceptions
   except Exception as e:
       # log exception
       logger.exception(f"error: {str(e)}")
       return Response(response_template(STATUS_FAILED,error=f'error: {str(e)}')) # return error response

@api_view(["GET"])
def get_auth_token(request,id):
   try:
       code = request.GET.get('code')
       admin_user = User.objects.get(id=int(id))
       # get access token
       response = services.get_access_token(code,admin_user,int(id))
       if response.status_code==200:
            # extract tokens from the response
            access_token = response.json().get('access_token')
            refresh_token = response.json().get('refresh_token')
       else:
            raise Exception(f'{response}')
    
       # encrypt tokens
       encrypted_access_token = encrypt_data(access_token)
       encrypted_refresh_token = encrypt_data(refresh_token)
       
       # get salesforce auth object which container encrypted tokens
       sf_auth_obj = Auth.objects.filter(account=admin_user.account).first()
       
       # if no auth object found related to this admin
       if not sf_auth_obj:
           # create new auth object which will contain the encrypted tokens 
           sf_auth_obj = Auth.objects.create(access_token=encrypted_access_token, refresh_token=encrypted_refresh_token, account=admin_user.account)
           sf_auth_obj.save()
           
       # update auth object with tokens if the admin account already has the auth object
       sf_auth_obj.access_token = encrypted_access_token
       sf_auth_obj.refresh_token = encrypted_refresh_token
       sf_auth_obj.save()
       
       # return success response
       return Response(response_template(STATUS_SUCCESS,message='auth token are successfully created at stored'),
                       status=status.HTTP_200_OK)
   # catch exceptions
   except Exception as e:
       # log exception
       logger.exception(f"an exception occured: {str(e)}")
       # return error response
       return Response(response_template(STATUS_FAILED, error=f'error occured while getting access token: {str(e)}'),status=status.HTTP_400_BAD_REQUEST)

    
 

@api_view(["POST", "GET"])
@permission_classes([IsAdminUser])
def get_salesforce_users(request):
    try:
        # Get the current user from the request
        admin_user = request.user
        
        # Check if the token for the admin user is valid
        if validate_token(admin_user):
            # If the token is valid, initiate an asynchronous task to fetch Salesforce users
            async_task("salesforce.services.fetch_salesforce_users", admin_user)
            
            # Return a success response indicating that users are being fetched
            return Response(response_template(STATUS_SUCCESS, message="users are being fetched and added to the database"),status=status.HTTP_201_CREATED)
        else:
            # If the token is not valid, raise an exception
            raise Exception("an error occured while validating the access token")
    except Exception as e:
         # If any exception occurs during the process, log the error and return a failure response
        logger.exception(f'error occured while fetching salesforce users: {str(e)}')
        return Response(response_template(STATUS_FAILED, error=f'{str(e)}'),status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "POST"])
def create_user(request,id):
    try:
        # Retrieve the admin user based on the provided id
        admin_user = User.objects.get(id=int(id))
        
        # Extract XML data from the request body
        xml_data = request.body
        
        # Check if the token for the admin user is valid
        if validate_token(admin_user):
            # If the token is valid, initiate an asynchronous task to add a user from Salesforce
            
            async_task("salesforce.services.add_user_from_salesforce", admin_user, xml_data) # Asynchronously add user from Salesforce
            
             # Return a SOAP response indicating acknowledgment (only SOAP response is accepted or it will throw an error)
            return HttpResponse("""
		    			<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
		    			<soapenv:Body>
		    			<notificationsResponse xmlns="http://soap.sforce.com/2005/09/outbound">
		    			<Ack>true</Ack>
		    			</notificationsResponse>
		    			</soapenv:Body>
		    			</soapenv:Envelope>
		    		""",content_type="text/xml",status=status.HTTP_200_OK)
    except Exception as e:
        # If any exception occurs during the process, log the error and return a failure response
        logger.exception(f'exception occured : {str(e)}')
        return Response(response_template(STATUS_FAILED, message=f'error occured: {str(e)}'), status=status.HTTP_400_BAD_REQUEST)
        
    



@api_view(["POST"])
@permission_classes([IsAdminUser])
def add_salesforce_credentials(request):
    """ This view will add the admin salesforce account credentials 
        to the database in encrypted form 
    """
    try:
        # Extract admin user request user context
        admin_user = request.user
        
        # Extract Client Id from the request
        client_id = request.data.get('client_id', None)
        
        # Extract Client secret from the request
        client_secret = request.data.get('client_secret', None)
        
        # Base url for the  admin's salesforce account api communication 
        base_url = request.data.get('base_url', None)
        
        # Checking if the any of the three creds in None
        if not (client_id and client_secret and base_url):
            # If any of these is none  then raise an error with status code 400 Bad Request
            raise Exception("either client id or client secret or base_url is missing")
        
        #Encrypt both the tokens using AWS KMS
        encrypted_client_id = encrypt_data(client_id)
        encrypted_client_secret = encrypt_data(client_secret)
        
        # Add the encrypted creds to the database 
        sf_acc_creds = AccountCredentials.objects.create(
            account=admin_user.account,
            client_id=encrypted_client_id,
            client_secret=encrypted_client_secret,
            base_url=base_url)
        sf_acc_creds.save()
        
        # Return Success Response indicating that the information is successfully saved
        return Response(response_template(STATUS_SUCCESS,message='information is successfully saved'),status=status.HTTP_201_CREATED)

    except Exception as e:
        #log Exception if occured
        logger.exception(f'an exception occured: {str(e)}')
        return Response(response_template(STATUS_FAILED,error=f'error occured while saving the info as: {str(e)}'),status=status.HTTP_400_BAD_REQUEST)   
