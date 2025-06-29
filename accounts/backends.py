from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django_tenants.utils import get_tenant_model
from django.core.exceptions import PermissionDenied
from clients.models import Client
User = get_user_model()
UserModel = get_user_model()

class TenantAuthenticationBackend(ModelBackend):
    """
    Allows authentication with phone number or email (or username fallback).
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = None

        if username is None or password is None:
            return None

        try:
            # Try phone number first
            user = UserModel.objects.get(phone_number=username)
        except UserModel.DoesNotExist:
            try:
                # Then try email
                user = UserModel.objects.get(email=username)
            except UserModel.DoesNotExist:
                try:
                    # Then try username
                    user = UserModel.objects.get(username=username)
                except UserModel.DoesNotExist:
                    return None

        if user and user.check_password(password):
            return user

        return None




        
# class TenantAuthenticationBackend(ModelBackend):
#     def authenticate(self, request, username=None, password=None, tenant=None, **kwargs):
#         if request is None or tenant is None:
#             return None

#         try:
#             tenant_obj = Client.objects.get(schema_name=tenant)  # 🔥 Get Tenant Object
#             user = User.objects.get(username=username, tenant=tenant_obj)  # 🔥 Pass the Object
#             if user.check_password(password):
#                 return user
#         except (User.DoesNotExist, Client.DoesNotExist):
#             return None
