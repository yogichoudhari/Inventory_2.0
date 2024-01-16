from django.urls import path
from . import views
urlpatterns = [
    path('oauth/auth_dialog/', views.auth_dialog ),
    path('oauth/callback', views.get_auth_token ),
    path('users/',views.get_salesforce_users),
]
