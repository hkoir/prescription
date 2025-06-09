from django.shortcuts import redirect
from django_tenants.utils import get_tenant_model
from django.http import Http404
import logging

logger = logging.getLogger(__name__)
from django.utils import timezone
from django_tenants.utils import get_public_schema_name
from django.contrib import messages

from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.http import HttpResponseForbidden
from django.urls import resolve
from django.contrib.auth import logout
from django.conf import settings
from django.utils.timezone import now
from.models import UserRequestLog
from django.urls import Resolver404

from django.contrib.auth import get_user_model
User = get_user_model() 
from django.core.cache import cache
from datetime import timedelta



class CustomGeneralPurposeMiddleWare:
    def __init__(self, get_response):
        self.get_response = get_response
        self.tenant_only_namespaces = ['appointments', 'billing','core','facilities','finance','inventory','lab_tests','leavemanagement','medical_records','messaging','patients'] 

    def __call__(self, request):       

        if request.tenant.schema_name == get_public_schema_name():
            try:
                resolver_match = resolve(request.path)
                if resolver_match.namespace in self.tenant_only_namespaces:
                    messages.warning(request, "This page is not available on the public site.")
                    return redirect('clients:dashboard')  # or render a custom warning page
            except:
                pass
        
        tenant = getattr(request, 'tenant', None)
        is_public_tenant = tenant and tenant.schema_name == get_public_schema_name()

        if is_public_tenant:
            return self.get_response(request)
        if request.user.is_authenticated and tenant:
            user_tenant = getattr(request.user, 'tenant', None)
            if user_tenant and user_tenant.schema_name != tenant.schema_name:
                logout(request)
                messages.error(request, "You are not allowed to log in to this tenant.")
                return redirect('login')

        return self.get_response(request)
    

