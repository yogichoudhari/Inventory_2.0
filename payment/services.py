from user.models import User as CustomUser
from payment.models import Subscription, SubscriptionPlan 
import stripe
import logging 

logger = logging.getLogger("main")
def assign_subscription_to_user(user,billing,product_name):
    try:
        price = SubscriptionPlan.objects.filter(name=billing).first()
        product = Subscription.objects.filter(name=product_name).first()
        response = stripe.Subscription.create(
        customer=user.stripe_id,
        collection_method="send_invoice",
        items=[{"price": price.price_id}],
        days_until_due=10
        )
        return response,user
    except Exception as e:
        logger.error(f'error occuured while creating subscription for user {str(e)}')
        return None