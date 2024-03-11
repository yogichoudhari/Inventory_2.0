from django.urls import path
from . import views


urlpatterns = [
    path('oauth/auth_dialog/', views.auth_dialog ),
    path('oauth/<str:id>/callback', views.get_auth_token ),
    path('users/',views.get_salesforce_users),
    path('webhooks/<str:id>/create-user',views.create_user),
    # path('encryption/create-key',views.create_and_save_encryption_key),
    path('add-salesforce-credentials',views.add_salesforce_credentials)
    
]
