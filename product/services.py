import stripe
from payment.models import Subscription,SubscriptionPlan,UserSubscriptionDetail
from payment.services import assign_subscription_to_user
from datetime import datetime
def response_template(status,**response_obj):
    return {
        'status':status,
        'response':response_obj    
    }


def sync_stripe_data(user):
        if user.subscription==None:
            response,user_subscription_instance = assign_subscription_to_user(user,'monthly','Standard')
            user.subscription = user_subscription_instance
            user.save()
        else:
            subscription = stripe.Subscription.retrieve(user.subscription.subscription_id)
            subscription_plan = stripe.Price.retrieve(subscription['items']['data'][0]['price']['id'])
            plan_details = SubscriptionPlan.objects.get(price_id=subscription_plan.id)
            user_subscription_details = UserSubscriptionDetail.objects.get(subscription_id=subscription.id)
            user_subscription_details.status=subscription.status
            user_subscription_details.billing = plan_details.name
            date_object = datetime.utcfromtimestamp(subscription.current_period_end)
            user_subscription_details.end_on = date_object
            user_subscription_details.name=plan_details.product.name
            subscription_details = user_subscription_details.save()
            user.subscription=subscription_details
            user.save()