from django.urls import path
from . import views

app_name = 'store'  

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('create-preference/<int:product_id>/', views.create_preference, name='create_preference'),
    path('payment/success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('payment/failure/<int:order_id>/', views.payment_failure, name='payment_failure'),
    path('payment/pending/<int:order_id>/', views.payment_pending, name='payment_pending'),
]