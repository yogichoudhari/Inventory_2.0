
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAdminUser,IsAuthenticated
from django.contrib.auth.models import User
from .models import User as CustomUser,Account, Role
from django.contrib import auth
from rest_framework import status
from .serializers import (CustomUserSerializer,
                          UpdateCustomUserSerializer,
                          AdminUserSerializer,
                          PermissionSerializer,RoleSerializer)
from django.db import transaction
from django.core.cache import cache
from inventory_management_system.utils import ( send_otp_via_email,
                                               response_template)
from django_q.tasks import async_task
from .services import (grant_permission, create_stripe_customer,get_tokens_for_user,
                       create_admin_data_encryption_key)
from payment.services import assign_subscription_to_user
from decouple import config
from .services import create_user_from_external_resources, default_password_not_updated
import stripe
import logging
from .signals import user_logged_in
import openpyxl
from salesforce.services import check_valid_user
# Create your views here.


# for views responses

STATUS_SUCCESS = "success"
STATUS_FAILED = "failed" 
#log configuration 
# logger = logging.getLogger("main")
logger = logging.getLogger("file_logger")
#stripe configuration 
stripe.api_key = config("STRIPE_SECRET_KEY")
@api_view(['POST'])
def register_admin(request):
    '''This view function is being used by the admin user to 
    register the new user
        '''
    try:
        if request.method=="POST":
            user_data = request.data
            serialized = AdminUserSerializer(data=user_data)
            if serialized.is_valid(raise_exception=True):
                with transaction.atomic():
                    created_user_instance = serialized.save()
                    stripe_id = create_stripe_customer(created_user_instance)
                    create_admin_data_encryption_key(created_user_instance)
                    created_user_instance.stripe_id = stripe_id
                    created_user_instance.save()
                    async_task("inventory_management_system.utils.send_otp_via_email",created_user_instance)
                return Response(response_template(STATUS_SUCCESS,message='An email is sent for verification'),status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.exception(f"error occured during user creation: {str(e)}")
        return Response(response_template(STATUS_FAILED,error=f"{str(e)}"),status=status.HTTP_400_BAD_REQUEST)
@api_view(["POST"])
@permission_classes([IsAuthenticated,IsAdminUser])
def create_user(request):
    try:
        if request.method == "POST":
            user_data = request.data
            billing_id = user_data['subscription']['billing_id']
            product_id = user_data['subscription']['product_id']
            user_instance = request.user.extra_user_fields
            account_instance = Account.objects.get(admin=user_instance)
            
            # Wrap the code in a try-except block for handling serializer errors
            serialized = CustomUserSerializer(data=user_data,context={"user": user_instance, "account": account_instance})
            serialized.is_valid(raise_exception=True)
            with transaction.atomic():
                created_user_instance = serialized.save()
                
                # Create a Stripe customer
                stripe_id = create_stripe_customer(created_user_instance)
                created_user_instance.stripe_id = stripe_id
                if 'subscription' in user_data:
                    _,subscription_instance = assign_subscription_to_user(created_user_instance,billing_id,product_id)
                    created_user_instance.subscription = subscription_instance  
                # lastly save the user 
                created_user_instance.save()
            # Return a success response
            return Response({"status": STATUS_SUCCESS, "message": "User is created successfully"},status=status.HTTP_201_CREATED)
    
    except Exception as e:
        # Log any unexpected exceptions
        logger.error(f"Unexpected error during user creation: {e}")
        return Response(response_template(STATUS_FAILED,error=f'Unexpected error: {str(e)}'),status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def resend_otp(request):
    try:
        email = request.data.get('email')
        auth_user = User.objects.get(email=email)
        user = CustomUser.objects.get(user=auth_user)
        # async_task("inventory_management_system.utils.send_otp_via_email",user)
        send_otp_via_email(user)
        return Response(response_template(STATUS_SUCCESS,message="otp is successfully sent"),status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"an error occured : {str(e)}")
        return Response(response_template(STATUS_FAILED,error="user does not exist"),status=status.HTTP_400_BAD_REQUEST)



@api_view(['POST'])
def verify_user_otp(request):
    try:
        # Get OTP and user ID from request data
        otp = request.data.get('otp')
        user_id = cache.get(otp)
        
        # Retrieve user instance
        user_instance = CustomUser.objects.filter(id=user_id).first()
        
        # Check if user instance exists
        if not user_instance:
            raise Exception("Incorrect otp")
        otp_key = "otp_"+str(user_instance.id)
        
        # Check if OTP key exists in cache
        if otp_key in cache:
            stored_otp = cache.get(otp_key)
            
            # Verify OTP
            if otp==stored_otp:
                # Mark user as verified
                user_instance.is_verified=True
                user_instance.save()
                cache.delete(otp_key)
                return Response(response_template(STATUS_SUCCESS,message="user is verified"), status=status.HTTP_200_OK)
            else:
                return Response(response_template(STATUS_FAILED,error="incorrect otp"),status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(response_template(STATUS_FAILED,error="otp is expired"),status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"An Error Occurred :{str(e)}")
        return Response(response_template(STATUS_FAILED),error=f"Something went wrong! {str(e)}.",status=status.HTTP_400_BAD_REQUEST)
    
@api_view(["POST"])
def get_token(request):
    try:
        '''This view function is used for login and when user
        user logins he will be provided with the Authentication Token
        '''

        username = request.data.get('username')
        password = request.data.get('password')
        user = auth.authenticate(username=username,
                                 password=password)
        user_extended_fields = CustomUser.objects.filter(user=user).first()
        if default_password_not_updated(user):
            pass
            return Response(response_template(STATUS_FAILED,message='please reset your password first'),status=status.HTTP_401_UNAUTHORIZED)
        elif user and user_extended_fields.is_verified:
            auth.login(request,user)
            user_main_object = CustomUser.objects.filter(user=user).first()
            account = user_main_object.account
            token = get_tokens_for_user(user,account)
            user = CustomUser.objects.get(user=user)
            user_logged_in.send(sender=get_token,request=request,user=user,login='success')
            return Response(response_template(STATUS_SUCCESS,message='user logged in successfully', token=token),status=status.HTTP_200_OK)
        elif not user_extended_fields.is_verified:
            send_otp_via_email(user_extended_fields)
            return Response(response_template(STATUS_FAILED,message='An email is sent for the otp verification'),status=status.HTTP_401_UNAUTHORIZED)
        else:
            user = User.objects.filter(username=username).first()
            if user:
                user_obj = CustomUser.objects.filter(user=user).first()
                user_logged_in.send(sender=get_token,request=request,user=user_obj,login='failed')     
        return Response(response_template(STATUS_FAILED,error=f'Incorrect password or username'),status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        logger.error("Error in getting authentication token"+ str(e)) 
        return Response(response_template(STATUS_FAILED,message=str(e)),status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST","GET"])
def refresh_token(request):
    pass

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
            return Response(response_template(STATUS_SUCCESS,message="permission granted"),status=status.HTTP_201_CREATED)
        else:
            return Response(response_template(STATUS_FAILED,error="Invalid User or Permission id"), status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exceptions(e,f'exeptions occured -- {str(e)}')


@api_view(["POST"])
@permission_classes([IsAdminUser,IsAuthenticated])
def create_permission_set(request):
    serializer_permission = PermissionSerializer(data=request.data)
    if serializer_permission.is_valid():
        serializer_permission.save()
        return Response(response_template(STATUS_SUCCESS,message="permission set successfully created"),status=status.HTTP_201_CREATED)
    else:
        return Response(response_template(STATUS_FAILED,error=serializer_permission.errors),status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['PATCH',"GET"])
@permission_classes([IsAuthenticated])
def user_profile(request):
    if request.method=='GET':
        add_on_fields = request.user.extra_user_fields
        add_on_fields_serialize = UpdateCustomUserSerializer(add_on_fields)
        return Response(response_template(STATUS_SUCCESS,data=add_on_fields_serialize.data),status=status.HTTP_200_OK)
        
    elif request.method=="PATCH":
        user_instance = CustomUser.objects.get(user=request.user)
        # permission = user_instance.permissions.get()
        nested_user_data= request.data.get("user")
        nested_user_id = nested_user_data.get("id")
        user_instance = CustomUser.objects.get(pk=id)
        user_serialize = UpdateCustomUserSerializer(user_instance,data=request.data,partial=True,context={"user_id":nested_user_id})
        if user_serialize.is_valid():
            user_serialize.save()
            return Response(response_template(STATUS_SUCCESS,message="profile is updated successfully"),status=status.HTTP_201_CREATED)
        
        else:
            return Response(response_template(STATUS_FAILED,message=f'{user_serialize.errors}'),status=status.HTTP_400_BAD_REQUEST)



@api_view(["GET"])
@permission_classes([IsAdminUser,IsAuthenticated])
def users(request):
    try:
        user = CustomUser.objects.get(user=request.user)
        account = user.related_account
        users = CustomUser.objects.filter(account=account)
        serialize_instances = UpdateCustomUserSerializer(users,many=True)
        return Response(response_template(STATUS_SUCCESS,data=serialize_instances.data),status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception(f"An Error Occured: {str(e)}")


@api_view(["GET","POST"])
def user_roles(request):
    try:
        roles = Role.objects.all()
        role_serialize = RoleSerializer(roles,many=True)
        logger.info("Returning User Roles Successfully!")
        return Response(response_template(STATUS_SUCCESS,data=role_serialize.data),status=status.HTTP_200_OK)
    except Exception as e:
        return Response(response_template(STATUS_FAILED,error=f'{str(e)}'),status=status.HTTP_400_BAD_REQUEST)


    
    

@api_view(['GET',"POST"])
@permission_classes([IsAdminUser])
def excel_to_dict(request):
    try:
        admin_user = CustomUser.objects.get(user=request.user)
        role = Role.objects.filter(name="Customer").first()
        # path = '/home/dell/Desktop/python training/Django Rest Framework/project05/User.xlsx'
        xl_file = request.FILES['xl']
        print(xl_file)
        wb = openpyxl.load_workbook(xl_file)
        ws = wb.active
        max_rows = ws.max_row
        first_row = True
        for row in ws.iter_rows(max_col=7, values_only=True):
            if first_row:
                first_row = False
                continue
            username, first_name,last_name, city, state,email, phone = row
            user_dict =  {}
            user_dict['username'] = username
            user_dict['firstname'] = first_name
            user_dict['lastname'] = last_name
            user_dict['email'] = email
            user_dict['address'] = {"city":city,"state":state}
            user_dict['phonenumbers'] = phone
            if check_valid_user(user_dict, admin_user):
                create_user_from_external_resources(user_dict, role, admin_user.account)

        return Response(response_template(STATUS_SUCCESS,message=f"addedd {max_rows} successfully"),
                        status=status.HTTP_200_OK)
    except Exception as e:
        return Response(response_template(STATUS_FAILED,error=f'An error occured as: {str(e)}')
                        , status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET'])
def csv_to_dict(request):
    pass