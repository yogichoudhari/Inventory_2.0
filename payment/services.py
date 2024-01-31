from user.models import User as CustomUser
from payment.models import Subscription, SubscriptionPlan, Coupon
import stripe
import logging 

logger = logging.getLogger("main")
def assign_subscription_to_user(user,billing,product_name):
    try:
        price = SubscriptionPlan.objects.filter(name=billing).first()
        product = Subscription.objects.filter(name=product_name).first()
        coupon_id = Coupon.objects.filter(subscription=product).first()
        response = stripe.Subscription.create(
        customer=user.stripe_id,
        collection_method="send_invoice",
        items=[{"price": price.price_id}],
        days_until_due=10
        )
        return response,user,coupon_id.coupon_id
    except Exception as e:
        logger.error(f'error occuured while creating subscription for user {str(e)}')
        return None


def create_coupon(percent_off):
    coupon_obj = stripe.Coupon.create(
    duration="forever",
    percent_off=percent_off,
    )
    return coupon_obj.id
    
