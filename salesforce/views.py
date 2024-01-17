from django.shortcuts import render,redirect
from . import services
from decouple import config
from pdb import set_trace
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from inventory_management_system.utils import response_template,STATUS_SUCCESS
from rest_framework import status
from django_q.tasks import async_task
from django.core.cache import cache
from salesforce.services import fetch_salesforce_users
from user.models import User as CustomUser
import pdb
import datetime
@api_view(['GET',"POST"])
def auth_dialog(request):
    url = services.get_auth_dialog_url()
    return Response(response_template(STATUS_SUCCESS,url=url),
                    status=status.HTTP_200_OK)

@api_view(["POST","GET"])
def get_auth_token(request):
    pdb.set_trace()
    code = request.GET.get('code')
    token = services.get_access_token(code)
    access_token = token.get('access_token')
    cache.set("salesforce_access_token",access_token,timeout=7200)
    return Response(response_template(STATUS_SUCCESS),
                    status=status.HTTP_200_OK)

    
    

@api_view(["POST","GET"])
def get_salesforce_users(request):
    admin_user = CustomUser.objects.get(user=request.user)
    # fetch_salesforce_users(admin_user)
    async_task("salesforce.services.fetch_salesforce_users",admin_user)
    return Response(response_template(STATUS_SUCCESS,message="users are being fetched"))