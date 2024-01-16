
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Product
from .models import PaymentLog
from user.models import User as CustomUser
from .serializers import (PaymentLogSerializer)
from django.forms.models import model_to_dict
import stripe
from inventory_management_system.utils import (send_email,response_template, STATUS_FAILED, 
                                               STATUS_SUCCESS)
from django.conf import settings

# Create your views here.


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
            send_email(subject,email,"inventory_stock_email.html",context)
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
