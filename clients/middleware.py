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
from channels.db import database_sync_to_async
from django_tenants.utils import get_tenant_model
from clients.models import Domain 
from django.utils.timezone import now
from django.contrib.auth.models import AnonymousUser
from prescription.models import Doctor, Patient
from datetime import timedelta


class TenantMiddlewareASGI:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        host_value = None
        for k, v in scope.get("headers", []):
            if k == b'host':
                host_value = v.decode()
                break

        tenant = None
        if host_value:
            # strip port, lowercase for safety
            domain = host_value.split(":")[0].lower()
            tenant = await self._get_tenant_for_host(domain)

        scope["tenant"] = tenant  # may be None
        return await self.inner(scope, receive, send)

    @database_sync_to_async
    def _get_tenant_for_host(self, domain_name: str):
        """
        Look up tenant via Domain model (domains__domain). Return tenant or None.
        """
        try:
            domain_obj = Domain.objects.select_related("tenant").get(domain=domain_name)
            return domain_obj.tenant
        except Domain.DoesNotExist:
            return None





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
    

class TrackUserActivityMiddleware2(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user
        if not isinstance(user, AnonymousUser) and user.is_authenticated:
            try:
                doctor = Doctor.objects.get(user=user)
                doctor.last_seen = now()
                doctor.is_online = True
                doctor.save(update_fields=["last_seen", "is_online"])
            except Doctor.DoesNotExist:
                try:
                    patient = Patient.objects.get(user=user)
                    patient.last_seen = now()
                    patient.is_online = True
                    patient.save(update_fields=["last_seen", "is_online"])
                except Patient.DoesNotExist:
                    pass
        return None




ONLINE_TIMEOUT = 120  
LAST_SEEN_WRITE_THROTTLE = 30  


class TrackUserActivityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            return

        user = request.user
        now = timezone.now()
        update_fields = []

        if not user.is_online:
            user.is_online = True
            update_fields.append("is_online")
  
        if not user.last_seen or (now - user.last_seen).total_seconds() > LAST_SEEN_WRITE_THROTTLE:
            user.last_seen = now
            update_fields.append("last_seen")

        if update_fields:
            user.save(update_fields=update_fields) 
        cache.set(f"user_online_{user.id}", True, timeout=ONLINE_TIMEOUT + 5)
