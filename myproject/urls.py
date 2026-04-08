
from django.contrib import admin
from django.urls import path,include,re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from django.views.static import serve as static_serve
from django.conf import settings
import os

urlpatterns = [
    path('admin/', admin.site.urls),   
    path('', include('accounts.urls', namespace='accounts')),
    path("accounts/", include("django.contrib.auth.urls")), 
    path('clients/',include('clients.urls',namespace='clients')),  
    path('prescription/',include('prescription.urls',namespace='prescription')),  
    path('finance/',include('finance.urls',namespace='finance')),  
    path('messaging/',include('messaging.urls',namespace='messaging')),  
    path('symptom_checker/',include('symptom_checker.urls',namespace='symptom_checker')),  
    path('payment_gateway/',include('payment_gateway.urls',namespace='payment_gateway')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('other_services/',include('other_services.urls',namespace='other_services')),
    path('appointments/',include('appointments.urls',namespace='appointments')),

    path('chat/',include('chat.urls',namespace='chat')),
    path('mobile_api/',include('mobile_api.urls',namespace='mobile_api')),  

    path('store/',include('store.urls',namespace='store')), 
    path('basket/',include('basket.urls',namespace='basket')),  
    path('payment/',include('payment.urls',namespace='payment')),  
    path('orders/',include('orders.urls',namespace='orders')),   



]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
