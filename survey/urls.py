from django.urls import path
from . import views
urlpatterns = [
    path('oauth/dialog/',views.oauth_dialog),
    path('oauth/callback',views.get_oauth_code),
    path("<int:product_id>/response",views.submit_feedback),
    path('<int:product_id>',views.feedback_list)
]