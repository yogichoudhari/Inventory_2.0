from django.urls import path
from . import views

urlpatterns = [
    path("payment-success/<str:session_id>",views.payment_success),
    path("payment-failed/<str:session_id>",views.payment_failed),
    path("payment-history/",views.payment_history),
    path("create_subscription_product/",views.create_subscription_product),
    path("create_subscription/",views.create_subscription),
    path("modify_subscription/",views.modify_subscription),
]
