
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from product.models import Product
from .models import PaymentLog, Subscription, SubscriptionPlan
from user.models import User as CustomUser
from .serializers import (PaymentLogSerializer)
from django.forms.models import model_to_dict
import stripe
from inventory_management_system.utils import (send_email,response_template, STATUS_FAILED, 
                                               STATUS_SUCCESS)
from django.conf import settings
from django_q.tasks import async_task
import logging
# Create your views here.
logger = logging.getLogger("main")

@api_view(["GET"])
def payment_success(request,session_id):
    session = stripe.checkout.Session.retrieve(session_id)
    customer = stripe.Customer.retrieve(session.customer)
    if session["payment_status"]=="paid":
        product = Product.objects.get(pk=session.metadata.get('product_id'))
        product.quantity = product.quantity-int(session.metadata.get("product_quantity"))
        total_amount = session.amount_total/100
        if product.quantity==0:
            email = product.created_by.user.email
            subject = "Inventory Product Stock Notification"
            product_dict = model_to_dict(product)
            product_dict["account"] = product.account.name
            context = product_dict
            async_task("inventory_management_system.utils.send_email",subject,email,"inventory_stock_email.html",context)
        product.save()
        user_instance = CustomUser.objects.get(id=session.metadata.get('user_id'))
        PaymentLog.objects.create(amount=total_amount,customer_stripe_id=session.customer,
                                user=user_instance,status=STATUS_SUCCESS,product=product)
        return Response(response_template(STATUS_SUCCESS,
                     message=f"your payment of {total_amount} is successfully done"),
                    status=status.HTTP_200_OK)

@api_view(["GET"])
def payment_failed(request,session_id):
    session = stripe.checkout.Session.retrieve(session_id)
    customer = stripe.Customer.retrieve(session.customer)
    if session['payment_status']=="unpaid":
        total_amount = session.amount_total/100
        product = Product.objects.get(pk=session.metadata.get('product_id'))
        user_instance = CustomUser.objects.get(id=session.metadata.get('user_id'))
        PaymentLog.objects.create(amount=total_amount,customer_stripe_id=session.customer,
                                user=user_instance,status=STATUS_FAILED,product=product)
        return Response(response_template(STATUS_FAILED,
                         message=f"payment of {total_amount} was unsuccessfull"),
                        status=status.HTTP_400_BAD_REQUEST)





@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request):
    user = CustomUser.objects.get(user=request.user)
    payment_history_instances = PaymentLog.objects.filter(user=user)
    serialize_payments_log = PaymentLogSerializer(payment_history_instances,
                                                  many=True)
    payment_history_list = serialize_payments_log.data
    return Response(response_template(STATUS_SUCCESS,data=payment_history_list),
                    status=status.HTTP_200_OK)


# @api_view(["POST"])
# @permission_classes([IsAuthenticated, IsAdminUser])
# def create_plan(request):
#     try:
#         response = stripe.Product.create(
#         name=f'{request.data.get("name")}',
#         default_price_data={
#         "currency":'inr',
#         "recurring":{
#         "interval":'year',
#         'interval_count':1
#         },
#         "unit_amount":int(request.data.get('price')*100)
#         }
#         )
#         plan_obj = SubscriptionPlan.objects.create(name=response.name,product_id=response.id)
#         plan_obj.save()
#         return Response(response_template(STATUS_SUCCESS,response=response))
#     except Exception as e:
#         return Response(response_template(STATUS_FAILED,error=f'{str(e)}'))
    

# def get_subscription(request):
#         user = CustomUser.objects.get(user=request.user)
#         product_id = request.data.get('product_id')
#         product = stripe.Product.retrieve(id=product_id)
#         session = stripe.checkout.Session.create(
#         line_items=[
#             {"price_data":{
#                 "currency":"inr",
#                 "product_data":{
#                     "name":product.name,
#                 },
#                 "product":product.id,
#                 "unit_amount":int(product.default_price*100)
#             },
#             "quantity":1}
#         ],
#         metadata={
#                 "product_id":product_id,
#                 "product_quantity":1,
#                 "user_id":user.id
#             },
#         mode="payment",
#         customer=user.stripe_id
#         success_url="http://127.0.0.1:8000/api/payments/subscription_payment-success/{CHECKOUT_SESSION_ID}",
#         cancel_url="http://127.0.0.1:8000/api/payments/subscription_payment-failed/{CHECKOUT_SESSION_ID}"
#         )
        

# def subscription_payment_success(request):
#     pass

# def subscription_payment_failed(request):
#     pass

@api_view(['POST'])
@permission_classes([IsAdminUser,IsAuthenticated])
def create_subscription_product(request):
    try:
        product_obj = stripe.Product.create(name=request.data.get('name'))
        admin_user = CustomUser.objects.get(user=request.user)
        subscription_product = Subscription.objects.create(account=admin_user.account,name=product_obj.name,
                                    product_id=product_obj.id)
        plans = request.data.get("plans")
        for plan in plans:
            if plan['interval']=="monthly":
                count = 1
            elif plan['interval']=='quaterly':
                count = 3
            else:
                count = 12
            price_obj = stripe.Price.create(
            currency=plan['currency'],
            unit_amount=int(plan['price']*100),
            recurring={"interval": "month",
                       'interval_count':count},
            product=product_obj.id
            )
            SubscriptionPlan.objects.create(name=plan['interval'],price_id=price_obj.id,
                                            product=subscription_product)
        return Response(response_template(STATUS_SUCCESS,message="Subscription product and its prices are created successfully"),
                        status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f"error occured {str(e)}")
        return Response(response_template(STATUS_FAILED,error=f'{str(e)}'),
                        status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAdminUser,IsAuthenticated])
def create_subscription(request):
    try:
        user = CustomUser.objects.get(id=request.data.get('user_id'))
        price = SubscriptionPlan.objects.filter(name=request.data.get('billing')).first()
        product = Subscription.objects.filter(name=request.data.get('product_name')).first()
        response = stripe.Subscription.create(
        customer=user.stripe_id,
        collection_method="send_invoice",
        items=[{"price": price.price_id}],
        days_until_due=10
        )
        return Response(response_template(STATUS_SUCCESS,message="User subscription is created successfully",
                                          response=response),status=status.HTTP_201_CREATED)
    except Exception as e:
        logger.error(f'error occuured while creating subscription for user {str(e)}')
        return Response(response_template(STATUS_FAILED,error=f'{str(e)}'),
                        status=status.HTTP_400_BAD_REQUEST)
        