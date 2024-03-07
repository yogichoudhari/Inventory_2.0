from django.shortcuts import render,redirect
from django.http import HttpResponse
from . import services
from decouple import config
from pdb import set_trace
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from inventory_management_system.utils import response_template,STATUS_SUCCESS, STATUS_FAILED
from rest_framework import status
from django_q.tasks import async_task
from django.core.cache import cache
from salesforce.services import fetch_salesforce_users
from user.models import User as CustomUser
import pdb
import datetime
import xmltodict
import logging

logger = logging.getLogger('watchtower')

@api_view(['GET',"POST"])
def auth_dialog(request):
    url = services.get_auth_dialog_url()
    return Response(response_template(STATUS_SUCCESS,url=url),
                    status=status.HTTP_200_OK)

@api_view(["POST","GET"])
def get_auth_token(request):
    code = request.GET.get('code')
    token = services.get_access_token(code)
    access_token = token.get('access_token')
    refresh_token = token.get('refresh_token')
    cache.set("salesforce_refresh_token",refresh_token,timeout=None)
    cache.set("salesforce_access_token",access_token,timeout=7200)
    return Response(response_template(STATUS_SUCCESS,token=access_token),
                    status=status.HTTP_200_OK)

    
 

@api_view(["POST","GET"])
def get_salesforce_users(request):
    admin_user = CustomUser.objects.get(user=request.user)
    fetch_salesforce_users(admin_user)
    # async_task("salesforce.services.fetch_salesforce_users",admin_user)
    return Response(response_template(STATUS_SUCCESS,message="users are being fetched"))


@api_view(["GET","POST"])
def create_user(request):
    try:
        dict = xmltodict.parse(request.body)
        logger.info(f'user created on the salesforce: {dict}')
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
        return Response(response_template(STATUS_FAILED,message=f'error occured: {str(e)}'),status=status.HTTP_400_BAD_REQUEST)
        
        

