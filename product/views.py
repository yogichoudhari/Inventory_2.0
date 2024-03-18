import stripe
import pdb
import logging
import requests
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.permissions import IsAdminUser,IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework import status
from .models import Product
from payment.models import Subscription,SubscriptionPlan,UserSubscriptionDetail
from django.contrib.auth.models import User
from user.models import User as User
from django.contrib import auth
from .serializers import (ProductSerializer, 
                          SearchedProductListSerializer)
from .models import Product
from django.db.models import Q
from decouple import config
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from inventory_management_system.utils import (response_template)
from survey.services import create_survey_and_collector
from django.conf import settings
from django.forms.models import model_to_dict
from payment.services import assign_subscription_to_user
from .services import sync_stripe_data
from django_q.tasks import async_task
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"  

# Monkeysurvey Configuration

SM_API_BASE = "https://api.surveymonkey.com"
AUTH_CODE_ENDPOINT = "/oauth/authorize"
ACCESS_TOKEN_ENDPOINT = "/oauth/token"
redirect_uri = "http://localhost:8000/api/survey/oauth/callback"
CLIENT_ID= config("CLIENT_ID")
CLIENT_SECRET = config("CLIENT_SECRET")

# Create your views here.

logger = logging.getLogger('file_logger')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_page(120)
def product(request,id=None):
    '''Retrieve a single product if id is not None 
    or a list of all products.
    or a list of all products.
    '''
    try:
        user = request.user
        account = user.account
        if id:
            product = Product.objects.get(pk=id,account=account)
            serialized= ProductSerializer(product)
            return Response(response_template(STATUS_SUCCESS,data=serialized.data),
                            content_type='application/json',
                            status=status.HTTP_200_OK,)
        products = Product.objects.filter(account=account)
        serialized = ProductSerializer(products,many=True)
        return Response(response_template(STATUS_SUCCESS,data=serialized.data),
                        status=status.HTTP_200_OK)
    except Product.DoesNotExist:
        return Response(response_template(STATUS_FAILED,
                         message="product does not exist"),
                        status=status.HTTP_404_NOT_FOUND)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_product(request):
    try:
        user = request.user
        account = user.account
        search_param = request.query_params.get('param')
        if len(search_param)>=3:
            products = Product.objects.filter(Q(brand__icontains=search_param)|
                                          Q(category__icontains=search_param)|
                                          Q(title__icontains=search_param),
                                          account=account)
        else:
            products = Product.objects.filter(Q(brand__icontains=search_param)|
                                          Q(category__icontains=search_param),
                                          account=account)

        product_list= SearchedProductListSerializer(products,many=True).data
        if not products:
            return Response(response_template(STATUS_FAILED,data=[]),
                            status=status.HTTP_404_NOT_FOUND)
        else:
            return Response(response_template(STATUS_SUCCESS,data=product_list),
                            status=status.HTTP_200_OK)
    except:
        return Response(response_template(STATUS_FAILED,message="not available"),
                         status=status.HTTP_404_NOT_FOUND)

@api_view(["PATCH"])
def update_stock(request):
    '''This view function is for updating the product and can be 
    
    updated by Administrator only.
    '''
    if not request.user.is_superuser and request.user.is_authenticated:
        user = request.user
        try:
            permissions = user.permission.all()
            for permission in permissions:
                if permission.related_to=="product":
                    permission_instance = permission  
            permission = permission_instance.permission_set.get('can_create')   
        except:
            logger.exception(f"{request.user.username} does not have permissions")
            return Response(response_template(STATUS_FAILED,
                             error="user do not have permission to update"),
                            status=status.HTTP_403_FORBIDDEN)
        if not permission:
            return Response(response_template(STATUS_FAILED,
                             error="user do not have permission to update"),
                            status=status.HTTP_403_FORBIDDEN)
    product_id = request.data.get('id')
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        logger.exception(f"product {product_id} does not exist in product table")
        return Response(response_template(STATUS_FAILED,
                         message="product not found"),
                        status=status.HTTP_404_NOT_FOUND)
    serialized = ProductSerializer(product,data=request.data,
                                   partial=True)
    if serialized.is_valid():
        serialized.save()
        return Response(response_template(STATUS_SUCCESS,
                         message="product is updated"),
                        status=status.HTTP_200_OK)
    else:
        return Response(response_template(STATUS_FAILED,
                         message=f'{serialized.errors}'),
                        status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
def add_product(request):
    pdb.set_trace()
    if not request.user.is_admin and request.user.is_authenticated:
        user_instance = request.user
        try:
            permissions = user_instance.permission.all()
            for permission in permissions:
                if permission.related_to=="Product":
                    permission_instance = permission
            permission = permission_instance.permission_set.get('can_create')
        except:
            return Response(response_template(STATUS_FAILED,
                             error="user do not have permission to add product"),
                            status=status.HTTP_403_FORBIDDEN)
        if not permission:
            return Response(response_template(STATUS_FAILED,
                             error="user do not have permission to product"),
                            status=status.HTTP_403_FORBIDDEN)

    user_instance = request.user
    serialize_product_data = ProductSerializer(data=request.data,
                                               many=type(request.data)==list,
                                               context={'user_instance':user_instance})
    if serialize_product_data.is_valid():
        product = serialize_product_data.save()
        result = create_survey_and_collector(product)
        if result:
            return Response(response_template(STATUS_SUCCESS,
                             message="product added successfully"),
                            status=status.HTTP_201_CREATED)
    else:
        return Response(response_template(STATUS_FAILED,
                         error=f'{serialize_product_data.errors}'),
                        status=status.HTTP_400_BAD_REQUEST)



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def make_purchase(request, id):
    try:
        product_id = id
        user = request.user
        user_id = user.id
        account = user.account
        async_task("product.services.sync_stripe_data",user)
        try:
            product = Product.objects.get(pk=product_id,account=account)
        except Product.DoesNotExist:
            return Response(response_template(STATUS_FAILED,
                             message="product not found"),
                            status=status.HTTP_404_NOT_FOUND)
        quantity = request.data.get("quantity")
        if product.quantity==0:
            return Response(response_template(STATUS_FAILED,
                             message=f"Product is out of stock"),
                            status=status.HTTP_400_BAD_REQUEST)
        elif not product.quantity>=quantity:
            return Response(response_template(STATUS_FAILED,
                             message=f"Only {product.quantity} is in stock"),
                            status=status.HTTP_400_BAD_REQUEST)
        price = product.actual_price*quantity
        discounted_price = product.discounted_price*quantity
        discount = price-discounted_price
        customer_stripe_id =user.stripe_id
        # user_instance_dict = model_to_dict(user)
        session = stripe.checkout.Session.create(
        line_items=[
            {"price_data":{
                "currency":"inr",
                "product_data":{
                    "name":product.category,
                    "description":product.title,
                },
                "unit_amount":int(product.discounted_price*100)
            },
            "quantity":quantity}
        ],
        discounts=[{"coupon":user.subscription.coupon.coupon_id}],
        metadata={
                "product_id":product_id,
                "product_quantity":quantity,
                "user_id":user_id
            },
        mode="payment",
        customer=customer_stripe_id,
        success_url="http://127.0.0.1:8000/api/payments/payment-success/{CHECKOUT_SESSION_ID}",
        cancel_url="http://127.0.0.1:8000/api/payments/payment-failed/{CHECKOUT_SESSION_ID}"
        )
        payment_url = session.url
        if session.payment_status!="unpaid":
            data = {"product name":product.brand +" "+product.title,
                    "quantity": quantity,
                    "discount":discount,
                    "total amount":discounted_price,
                    "message":f"you have saved {discount} on this order"}
            
        return Response(response_template(STATUS_SUCCESS,url=payment_url),
                         status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"An Error Occured: {str(e)}")
        return Response(response_template(STATUS_FAILED,error=str(e)),status=status.HTTP_400_BAD_REQUEST) 
    
        