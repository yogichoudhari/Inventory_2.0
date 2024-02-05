from user.models import User as CustomUser
from payment.models import Subscription, SubscriptionPlan, Coupon, UserSubscriptionDetail
import stripe
import logging 
from django_q.tasks import async_task
from datetime import datetime
from inventory_management_system.utils import send_email
logger = logging.getLogger("main")
def assign_subscription_to_user(user,billing,product_name):
    try:
        import pdb
        pdb.set_trace()
        price = SubscriptionPlan.objects.filter(name=billing).first()
        product = Subscription.objects.filter(name=product_name).first()
        coupon_id = Coupon.objects.filter(subscription=product).first()
        response = stripe.Subscription.create(
        customer=user.stripe_id,
        collection_method="send_invoice",
        items=[{"price": price.price_id}],
        days_until_due=10
        )
        invoice = stripe.Invoice.finalize_invoice(response.latest_invoice)
        timestamp = invoice.due_date
        dt_object = datetime.utcfromtimestamp(timestamp)
        invoice.due_date = dt_object
        date_object = datetime.utcfromtimestamp(response.current_period_end)
        user_subscription_instance = UserSubscriptionDetail.objects.create(
            subscription_id=response.id,
            status=response.status,
            coupon=coupon_id,
            end_on=date_object,
            billing=price.name,
            name=product.name,
        )
        context= {'invoice':invoice}
        subject= 'Subscription Activation Notification'
        to_email= user.user.email
        template_name= "subscription_notification.html"
        async_task("inventory_management_system.utils.send_email",context,to_email,template_name,subject)
        # send_email(email_args)
        return response,user_subscription_instance
    except Exception as e:
        logger.error(f'error occuured while creating subscription for user {str(e)}')
        return None


def create_coupon(percent_off):
    coupon_obj = stripe.Coupon.create(
    duration="forever",
    percent_off=percent_off,
    )
    return coupon_obj.id
    
