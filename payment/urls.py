from django.urls import path
from . import views

urlpatterns = [
    path("payment-success/<str:session_id>",views.payment_success),
    path("payment-failed/<str:session_id>",views.payment_failed),
    path("payment-history/",views.payment_history),
]
