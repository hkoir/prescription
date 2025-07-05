# urls.py
from django.urls import path
from . import views

app_name='payment_gateway'

urlpatterns = [
    path('payment/initiate/', views.initiate_payment, name='initiate_payment'),   
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/thank-you/<int:invoice_id>/', views.post_payment_redirect, name='post_payment_redirect'),
   
    path('payment/fail/', views.payment_fail, name='payment_fail'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'), 
    path('review/', views.review_invoice, name='review_invoice'),  
    path('payment/thank-you/', views.payment_thank_you, name='thank_you'), 
    path('invoice/payment/download/<int:invoice_id>/', views.download_payment_invoice_pdf, name='download_payment_invoice_pdf'),

]
