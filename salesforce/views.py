
from django.http import HttpResponse
from . import services
from decouple import config
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from inventory_management_system.utils import (response_template,STATUS_SUCCESS, STATUS_FAILED)
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from user.models import User, Account
from rest_framework import status
from django.core.cache import cache
from salesforce.services import fetch_salesforce_users, encrypt_data
from user.models import User as CustomUser
from .models import EncryptionKeyId, AccountCredentials
from django.contrib.auth.models import User as AuthUser
import boto3
import xmltodict
import logging


logger = logging.getLogger('watchtower')
client = boto3.client("kms")
@api_view(['GET', "POST"])
def auth_dialog(request):
    admin_user = User.objects.get(user=request.user)
    url = services.get_auth_dialog_url(admin_user)
    return Response(response_template(STATUS_SUCCESS, url=url),
                    status=status.HTTP_200_OK)

@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def get_auth_token(request):
    code = request.GET.get('code')
    admin_user = User.objects.get(user=request.user)
    token = services.get_access_token(code,admin_user)
    access_token = token.get('access_token')
    refresh_token = token.get('refresh_token')
    cache.set("salesforce_refresh_token",refresh_token, timeout=None)
    cache.set("salesforce_access_token",access_token, timeout=7200)
    return Response(response_template(STATUS_SUCCESS, token=access_token),
                    status=status.HTTP_200_OK)

    
 

@api_view(["POST", "GET"])
def get_salesforce_users(request):
    admin_user = CustomUser.objects.get(user=request.user)
    fetch_salesforce_users(admin_user)
    # async_task("salesforce.services.fetch_salesforce_users",admin_user)
    return Response(response_template(STATUS_SUCCESS, message="users are being fetched"))


@api_view(["GET", "POST"])
def create_user(request,id):
    try:
        dict = xmltodict.parse(request.body)
        logger.info(f'user created on the salesforce: {dict}')
        user = AuthUser.objects.get(id=id)
        admin_user = CustomUser.objects.get(user=user)
        fetch_salesforce_users(admin_user)
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
        logger.exception(f'exception occured : {str(e)}')
        return Response(response_template(STATUS_FAILED, message=f'error occured: {str(e)}'), status=status.HTTP_400_BAD_REQUEST)
        


import pdb
@api_view(["GET"])
@permission_classes([IsAdminUser, IsAdminUser])
def create_and_save_encryption_key(request):
    try:
        pdb.set_trace()
        admin_user = User.objects.get(user=request.user)
        response = client.create_key()
        key_id = response.get('KeyMetadata').get('KeyId')
        key_id_obj = EncryptionKeyId.objects.create(account=admin_user.account, keyid=key_id)
        key_id_obj.save()
        return Response(response_template(STATUS_SUCCESS, message="key is created and successfully saved"))
    except Exception as e:
        logger.error(f"Exception Occurred in creating encryption key - {str(e)}")
        return Response(response_template(STATUS_FAILED, error=f"{str(e)}"), status=status.HTTP_400_BAD_REQUEST)
    


@api_view(["POST"])
@permission_classes([IsAdminUser])
def add_salesforce_credentials(request):
    try:
        admin_user = User.objects.get(user=request.user)
        client_id = request.data.get('client_id', None)
        client_secret = request.data.get('client_secret',None)
        if not (client_id and client_secret):
            return Response(response_template(STATUS_FAILED, message="either client id or client secret is missing"))
        encrypted_client_id = encrypt_data(client_id, admin_user.account)
        encrypted_client_secret = encrypt_data(client_secret, admin_user.account)
        sf_acc_creds = AccountCredentials.objects.create(account=admin_user.account, client_id=encrypted_client_id, client_secret=encrypted_client_secret)
        sf_acc_creds.save()
        return Response(response_template(STATUS_SUCCESS,message='information is successfully saved'),status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception(f'an exception occured: {str(e)}')
        return Response(response_template(STATUS_FAILED,error=f'error occured while saving the info as: {str(e)}'),status=status.HTTP_400_BAD_REQUEST)   
