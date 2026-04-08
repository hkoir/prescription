from django.urls import path
from . import views
from. views import checkout

app_name = 'payment'



urlpatterns = [ 

    path('', views.BasketView, name='basket'),
    path('orderplaced/', views.order_placed, name='order_placed'),
    path('error/', views.Error.as_view(), name='error'),
    path('webhook/', views.stripe_webhook), 

    path('checkout/', checkout.as_view(), name='checkout'),
    path('confirm-address/', views.confirm_address, name='confirm_address'),
    path('process-order/', views.process_order, name='process_order'),
    path('generate_invoice/', views.generate_invoice, name='generate_invoice'),
    path('send_test_email/', views.send_test_email, name='send_test_email'),
    path('initiate_ecommerce_payment/<int:order_id>/', views.initiate_ecommerce_payment, name='initiate_ecommerce_payment'),
    
   
]
