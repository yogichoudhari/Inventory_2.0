from django.urls import path
from . import views

urlpatterns = [
    path("payment-success/<str:session_id>",views.payment_success),
    path("payment-failed/<str:session_id>",views.payment_failed),
    path("payment-history/",views.payment_history),
    path("create-subscription-product/",views.create_subscription_product),
    path("create-subscription/",views.create_subscription),
    path("modify-subscription/",views.modify_subscription),
    path("cancel-subscription/<int:user_id>",views.cancel_subscription),
    path("plans/",views.plans),
]
