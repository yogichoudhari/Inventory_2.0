
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAdminUser,IsAuthenticated
from rest_framework import status
from django.contrib.auth.models import User
from .models import User as CustomUser,Account
from django.contrib import auth
from .serializers import (CustomUserSerializer,
                          LoginSerializer, 
                          UpdateCustomUserSerializer,
                          AdminUserSerializer,
                          PermissionSerializer)
from django.core.cache import cache
from inventory_management_system.utils import (get_tokens_for_user,
                                               send_otp_via_email,
                                               response_template)
from .services import grant_permission
from decouple import config
import stripe
import json
import pdb
import logging
# Create your views here.


# for views responses

STATUS_SUCCESS = "success"
STATUS_FAILED = "failed" 
#log configuration 
logger = logging.getLogger(__name__)

#stripe configuration 
stripe.api_key = config("STRIPE_SECRET_KEY")
@api_view(['POST'])
def register_admin(request):
    '''This view function is being used by the admin user to 
    
    register the new user
    '''
    if request.method=="POST":
        user_data = request.data
        serialized = AdminUserSerializer(data=user_data)
        if serialized.is_valid():
            created_user_instance = serialized.save()
            customer_stripe_response = stripe.Customer.create(
                name = created_user_instance.user.username,
                email = created_user_instance.user.email
            )
            created_user_instance.stripe_id = customer_stripe_response.id
            created_user_instance.save()
            send_otp_via_email(created_user_instance)
            return Response(response_template(STATUS_SUCCESS,message='An email is sent for verification'),
                            status=status.HTTP_201_CREATED)
        else:
            return Response(response_template(STATUS_FAILED,
                             error=f"{serialized.errors}"),
                            status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([IsAuthenticated,IsAdminUser])
def create_user(request):
    try:
        if request.method == "POST":
            user_data = request.data
            user_instance = request.user.extra_user_fields
            account_instance = Account.objects.get(admin=user_instance)
            
            # Wrap the code in a try-except block for handling serializer errors
            try:
                serialized = CustomUserSerializer(data=user_data,
                    context={"user": user_instance, "account": account_instance})
                serialized.is_valid(raise_exception=True)
            except Exception as e:
                # Log the validation error and return a response
                logger.error(f"User creation failed due to error: {e}")
                return Response(response_template(STATUS_FAILED,
                                 error=f'{e.detail}'),
                                status=status.HTTP_400_BAD_REQUEST)

            # Save the user instance
            created_user_instance = serialized.save()

            # Create a Stripe customer
            try:
                customer_stripe_response = stripe.Customer.create(
                    name=created_user_instance.user.username,
                    email=created_user_instance.user.email
                )
            except stripe.error.StripeError as stripe_error:
                # Log the Stripe error and return a response
                logger.error(f"Stripe customer creation failed: {stripe_error}")
                return Response(response_template(STATUS_FAILED,
                                 error=f'Stripe customer creation failed: {stripe_error}'),
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Update the user instance with the Stripe ID
            created_user_instance.stripe_id = customer_stripe_response.id
            created_user_instance.save()

            # Log user creation success
            logger.info(f"User is created successfully: {created_user_instance}")

            # Return a success response
            return Response({"status": STATUS_SUCCESS, "message": "User is created successfully"},
                            status=status.HTTP_201_CREATED)
    
    except Exception as e:
        # Log any unexpected exceptions
        print(logger)
        logger.error(f"Unexpected error during user creation: {e}")
        return Response(response_template(STATUS_FAILED,
                         error=f'Unexpected error: {e}'),
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def resend_otp(request):
    email = request.data.get('email')
    try:
        auth_user = User.objects.get(email=email)
        user = CustomUser.objects.get(user=auth_user)
        send_otp_via_email(user)
    except Exception as e:
        logger.exception(f"an error occured : that email is incorrect")
        return Response(response_template(STATUS_FAILED,error="user does not exist"),
                        status=status.HTTP_400_BAD_REQUEST)
    return Response(response_template(STATUS_SUCCESS,message="otp is successfully sent"),
                    status=status.HTTP_200_OK)



@api_view(['POST'])
def verify(request):
    
    otp = request.data.get('otp')
    user_id = cache.get(otp)
    logger.debug(f'Cache keys {cache.keys("*")}')
    try:
        user_instance = CustomUser.objects.get(id=user_id)
        logger.debug(f'Cache keys {cache.keys("*")}')
    except Exception as e:
        logger.debug(f'Cache keys {cache.keys("*")}')
        logger.exception(f'incorret key')
        return Response(response_template(STATUS_FAILED,error="incorrect otp entered"),
                         status=status.HTTP_400_BAD_REQUEST)
    otp_key = "otp_"+str(user_instance.id)
    if otp_key in cache:
        stored_otp = cache.get(otp_key)
        if otp==stored_otp:
            user_instance.is_verified=True
            user_instance.save()
            cache.delete(otp_key)
            return Response(response_template(STATUS_SUCCESS,message="user is verified"),
                            status=status.HTTP_200_OK)
        else:
            return Response(response_template(STATUS_FAILED,error="incorrect otp"),
                           status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response(response_template(STATUS_FAILED,error="otp is expired"),
                        status=status.HTTP_400_BAD_REQUEST)
    
@api_view(["POST"])
def login(request):
    '''This view function is used for login and when user
    user logins he will be provided with the Authentication Token
    '''
    user_data = request.data
    serialized= LoginSerializer(data=user_data)
    if serialized.is_valid():
        username = serialized.data.get('username')
        password = serialized.data.get('password')
        user = auth.authenticate(username=username,
                                 password=password)
        if username!='admin':
            extra_user_fields = CustomUser.objects.get(user=user)
            if user is not None and extra_user_fields.is_verified:
                auth.login(request,user)
                token = get_tokens_for_user(user)
                return Response(response_template(STATUS_SUCCESS,
                                 message='user logged in successfully',
                                 token=token),
                                status=status.HTTP_200_OK)
            else:
                return Response(response_template(STATUS_FAILED,error="user not varified"),
                                status=status.HTTP_403_FORBIDDEN)
        elif username=='admin':
                auth.login(request,user)
                token = get_tokens_for_user(user)
                return Response(response_template(STATUS_SUCCESS,
                                 message='user logged in successfully',
                                 token=token),
                                status=status.HTTP_200_OK)
    logger.error(f'error occured {serialized.errors}')             
    return Response(response_template(STATUS_FAILED,
                     error=f'{serialized.errors}'),status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAdminUser,IsAuthenticated])
def grant_permission_to_user(request):
    try:
        permission_id= request.data.get('permission_id')
        user_id = request.data.get('user_id')
        admin_user = CustomUser.objects.get(user=request.user)
        account = admin_user.account
        granted = grant_permission(account=account,user_id=user_id,permission_id=permission_id)
        if granted:
            return Response(response_template(STATUS_SUCCESS,
                             message="permission granted"),
                    status=status.HTTP_201_CREATED)
        else:
            return Response(response_template(STATUS_FAILED,error="Invalid User or Permission id"),
                            status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exceptions(e,f'exeptions occured -- {str(e)}')


@api_view(["POST"])
@permission_classes([IsAdminUser,IsAuthenticated])
def create_permission_set(request):
    serializer_permission = PermissionSerializer(data=request.data)
    if serializer_permission.is_valid():
        serializer_permission.save()
        return Response(response_template(STATUS_SUCCESS,
                         message="permission set successfully created"),
                        status=status.HTTP_201_CREATED)
    else:
        return Response(response_template(STATUS_FAILED,
                        error=serializer_permission.errors),
                        status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['PATCH',"GET"])
@permission_classes([IsAuthenticated])
def user_profile(request):
    if request.method=='GET':
        add_on_fields = request.user.extra_user_fields
        add_on_fields_serialize = UpdateCustomUserSerializer(add_on_fields)
        return Response(response_template(STATUS_SUCCESS,
                         data=add_on_fields_serialize.data),
                        status=status.HTTP_200_OK)
    if request.method=="PATCH":
        user_instance = CustomUser.objects.get(user=request.user)
        # permission = user_instance.permissions.get()
        nested_user_data= request.data.get("user")
        nested_user_id = nested_user_data.get("id")
        user_instance = CustomUser.objects.get(pk=id)
        user_serialize = UpdateCustomUserSerializer(user_instance,
                        data=request.data,partial=True,
                        context={"user_id":nested_user_id})
        if user_serialize.is_valid():
            user_serialize.save()
            return Response(response_template(STATUS_SUCCESS,
                             message="profile is updated successfully"),
                             status=status.HTTP_201_CREATED)
        else:
            return Response(response_template(STATUS_FAILED,
                             message=f'{user_serialize.errors}'),
                             status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAdminUser,IsAuthenticated])
def users(request):
    user = CustomUser.objects.get(user=request.user)
    account = user.related_account
    users = CustomUser.objects.filter(account=account)
    serialize_instances = UpdateCustomUserSerializer(users,many=True)
    return Response(response_template(STATUS_SUCCESS,data=serialize_instances.data),
                    status=status.HTTP_200_OK)
    
    

def get_salesforce_user(request):
    pass