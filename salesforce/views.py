
from django.http import HttpResponse
from . import services
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from inventory_management_system.utils import (response_template,STATUS_SUCCESS, STATUS_FAILED)
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAdminUser
from user.models import User, Account
from rest_framework import status
from django.core.cache import cache
from salesforce.services import encrypt_data
from user.models import User as CustomUser
from .models import AccountCredentials
from django.contrib.auth.models import User as AuthUser
from django_q.tasks import async_task
import boto3
import xmltodict
import logging


logger = logging.getLogger('watchtower')
client = boto3.client("kms")
@api_view(['GET', "POST"])
def auth_dialog(request):
    try:
        admin_user = User.objects.get(user=request.user)
        url = services.get_auth_dialog_url(admin_user)
        return Response(response_template(STATUS_SUCCESS, url=url),
                        status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception(f"error occured in salesforce_auth_dialog view: {str(e)}")
        return Response(response_template(STATUS_FAILED,error=f'error occured: {str(e)}'))
import pdb
@api_view(["GET"])
def get_auth_token(request,id):
    try:
        code = request.GET.get('code')
        admin_user = User.objects.get(id=int(id))
        username = admin_user.user.username
        token = services.get_access_token(code,admin_user,int(id))
        access_token = token.get('access_token')
        refresh_token = token.get('refresh_token')
        cache.set(f"salesforce_refresh_token_{username}", refresh_token, timeout=None)
        cache.set(f"salesforce_access_token_{username}", access_token, timeout=7200)
        return Response(response_template(STATUS_SUCCESS, token=access_token),
                        status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an exception occured: {str(e)}")
        return Response(response_template(STATUS_FAILED, error=f'error occured while getting access token: {str(e)}'),status=status.HTTP_400_BAD_REQUEST)

    
 

@api_view(["POST", "GET"])
def get_salesforce_users(request):
    try:
        admin_user = CustomUser.objects.get(user=request.user)
        async_task("salesforce.services.fetch_salesforce_users", admin_user)
        return Response(response_template(STATUS_SUCCESS, message="users are being fetched"))
    except Exception as e:
        logger.exception(f'error occured while fetching salesforce users: {str(e)}')
        return Response(response_template(STATUS_FAILED, error=f'error Occured as {str(e)}'))


@api_view(["GET", "POST"])
def create_user(request,id):
    try:
        admin_user = CustomUser.objects.get(id=int(id))
        xml_data = request.body
        async_task("salesforce.services.add_user_from_salesforce", admin_user, xml_data)
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
        
    


@api_view(["POST"])
@permission_classes([IsAdminUser])
def add_salesforce_credentials(request):
    try:
        admin_user = User.objects.get(user=request.user)
        client_id = request.data.get('client_id', None)
        client_secret = request.data.get('client_secret', None)
        base_url = request.data.get('base_url', None)
        if not (client_id and client_secret and base_url):
            return Response(response_template(STATUS_FAILED, message="either client id or client secret or base_url is missing"))
        encrypted_client_id = encrypt_data(client_id, admin_user.account)
        encrypted_client_secret = encrypt_data(client_secret, admin_user.account)
        sf_acc_creds = AccountCredentials.objects.create(
            account=admin_user.account,
            client_id=encrypted_client_id,
            client_secret=encrypted_client_secret,
            base_url=base_url)
        sf_acc_creds.save()
        return Response(response_template(STATUS_SUCCESS,message='information is successfully saved'),status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception(f'an exception occured: {str(e)}')
        return Response(response_template(STATUS_FAILED,error=f'error occured while saving the info as: {str(e)}'),status=status.HTTP_400_BAD_REQUEST)   
