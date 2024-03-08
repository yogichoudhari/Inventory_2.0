from django.urls import path
from . import views, services


urlpatterns = [
    path('oauth/auth_dialog/', views.auth_dialog ),
    path('oauth/callback', views.get_auth_token ),
    path('users/',views.get_salesforce_users),
    path('webhooks/<int:id>/create-user',views.create_user),
    path('encryption/create-key',views.create_and_save_encryption_key),
    path('add-salesforce-credentials',views.add_salesforce_credentials)
    
]
