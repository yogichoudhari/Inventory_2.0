from django.urls import path
from . import views
urlpatterns = [
    path('',views.product),
    path('<int:id>',views.product),
    path('update-stock/',views.update_stock),
    path("check-product",views.check_product,),
    path("<int:id>/make-purchase",views.make_purchase),
    path("add-product/",views.add_product),
]
