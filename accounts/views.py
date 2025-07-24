
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse,JsonResponse
from django.db.models import Q
from .forms import UserRegistrationForm,CustomLoginForm,CustomUserCreationForm
from django.db import connection
from .forms import TenantUserRegistrationForm
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.db import transaction
from clients.models import Client,SubscriptionPlan
from .forms import AssignPermissionsForm
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Permission
from django.apps import apps
from django.http import JsonResponse
from django.contrib.auth.models import User, Group
from .forms import UserGroupForm
from .forms import AssignPermissionsToGroupForm
from django.core.paginator import Paginator
from django.contrib.auth.models import Group
from django_tenants.utils import schema_context
from .tokens import account_activation_token
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from.models import CustomUser
from django.core.mail import send_mail

from.forms import PartnerJobSeekerRegistrationForm
from clients.models import Subscription
from django.utils import timezone
from django_tenants.utils import get_public_schema_name
from clients.models import Tenant
from .models import PhoneOTP
from accounts.utils import send_sms

import logging
logger = logging.getLogger(__name__)




def home(request):
    return render(request,'accounts/home.html')


def send_tenant_email(email, username, password, subdomain):
    subject = "Your Credentials for login"
    message = (
        f"Welcome to our platform!\n\n"
        f"Your account has been created successfully.\n\n"
        f"Username: {username}\n"
        f"Password: {password}\n"
        f"Subdomain: {subdomain}\n"
        f"Login URL: http://{subdomain}.localhost:8000\n\n"
        f"Thank you for using our service!"
    )
    send_mail(subject, message, 'your-email@example.com', [email])






import logging
from django.core.mail import send_mail
from django.conf import settings
logger = logging.getLogger(__name__)
from django.core.exceptions import ValidationError

def register_view(request):   
    current_tenant = getattr(connection, 'tenant', None)
    current_schema = current_tenant.schema_name if current_tenant else None
    registerForm = TenantUserRegistrationForm()

    if request.method == 'POST':
        registerForm = TenantUserRegistrationForm(request.POST, request.FILES, tenant=current_tenant)

        if registerForm.is_valid():
            with transaction.atomic():
                user = registerForm.save(commit=False)
                user.email = registerForm.cleaned_data.get('email', '').strip()
                user.phone_number = registerForm.cleaned_data.get('phone_number', '').strip()
                role = registerForm.cleaned_data['role']
                user.set_password(registerForm.cleaned_data['password1'])

                user.is_active = False
                user.tenant = current_tenant
                user.role = 'patient' if role == 'patient' else 'doctor'
                user.save()

                email_sent = False
                sms_sent = False

                if user.email:
                    try:
                        current_site = get_current_site(request)
                        subdomain = f"{current_schema}" if current_schema != 'public' else ''
                        domain = current_site.domain

                        subject = 'Activate your Account'
                        message = render_to_string('accounts/registration/account_activation_email.html', {
                            'user': user,
                            'domain': domain,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': account_activation_token.make_token(user),
                            'subdomain': subdomain
                        })

                        user.email_user(subject=subject, message=message)
                        email_sent = True
                    except Exception as e:
                        messages.warning(request, f"Email sending failed: {e}")

                if user.phone_number:
                    try:
                        return send_otp(request, user.phone_number)  # this returns redirect
                    except Exception as e:
                        messages.warning(request, f"SMS failed: {e}")

                if not user.email and not user.phone_number:
                    messages.error(request, "You must provide at least an email or a phone number.")
                    user.delete()
                    return render(request, 'accounts/registration/register.html', {'form': registerForm})

                if email_sent:
                    messages.info(request, "Please check your email to activate your account.")
                    return render(request, 'accounts/registration/register_email_confirm.html', {'form': registerForm})

                # If neither email nor SMS worked
                messages.error(request, "We could not send activation via email or SMS. Please try again.")
                user.delete()
                return render(request, 'accounts/registration/register.html', {'form': registerForm})
    else:
        registerForm = TenantUserRegistrationForm(tenant=current_tenant)
    return render(request, 'accounts/registration/register.html', {'form': registerForm})
from django.core.exceptions import ValidationError




def register_patient(request):   
    current_tenant = getattr(connection, 'tenant', None)
    current_schema = current_tenant.schema_name if current_tenant else None
    registerForm = TenantUserRegistrationForm()

    if request.method == 'POST':
        registerForm = TenantUserRegistrationForm(request.POST, request.FILES, tenant=current_tenant)

        if registerForm.is_valid():
            with transaction.atomic():
                user = registerForm.save(commit=False)
                user.email = registerForm.cleaned_data.get('email', '').strip()
                user.phone_number = registerForm.cleaned_data.get('phone_number', '').strip()
                role = registerForm.cleaned_data['role']
                user.set_password(registerForm.cleaned_data['password1'])

                user.is_active = False
                user.tenant = current_tenant
                user.role = 'patient' if role == 'patient' else 'doctor'
                user.save()

                email_sent = False
                sms_sent = False

                if user.email:
                    try:
                        current_site = get_current_site(request)
                        subdomain = f"{current_schema}" if current_schema != 'public' else ''
                        domain = current_site.domain

                        subject = 'Activate your Account'
                        message = render_to_string('accounts/registration/account_activation_email.html', {
                            'user': user,
                            'domain': domain,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': account_activation_token.make_token(user),
                            'subdomain': subdomain
                        })
                        user.email_user(subject=subject, message=message)
                        email_sent = True
                    except Exception as e:
                        messages.warning(request, f"Email sending failed: {e}")
                if user.phone_number:
                    try:
                        return send_otp(request, user.phone_number)  # this returns redirect
                    except Exception as e:
                        messages.warning(request, f"SMS failed: {e}")

                if not user.email and not user.phone_number:
                    messages.error(request, "You must provide at least an email or a phone number.")
                    user.delete()
                    return render(request, 'accounts/registration/register.html', {'form': registerForm})

                if email_sent:
                    messages.info(request, "Please check your email to activate your account.")
                    return render(request, 'accounts/registration/register_email_confirm.html', {'form': registerForm})

                # If neither email nor SMS worked
                messages.error(request, "We could not send activation via email or SMS. Please try again.")
                user.delete()
                return render(request, 'accounts/registration/register.html', {'form': registerForm})
    else:
        registerForm = TenantUserRegistrationForm(tenant=current_tenant)
    return render(request, 'accounts/registration/register.html', {'form': registerForm})




from.forms import PublicRegistrationForm

def register_public(request):   
    current_tenant = None
    if hasattr(connection, 'tenant'):      
        current_schema = connection.tenant.schema_name   
        current_tenant = connection.tenant         
    
    if request.method == 'POST':
        registerForm= PublicRegistrationForm(request.POST, request.FILES, tenant=current_tenant)
        if registerForm.is_valid():
            with transaction.atomic():
                user = registerForm.save(commit=False)
                user.email = registerForm.cleaned_data['email']
                user.set_password(registerForm.cleaned_data['password1'])
                user.is_active = False
                user.tenant = current_tenant
                user.save()

                current_site = get_current_site(request)
               
                if connection.tenant.schema_name == 'public':
                    subdomain = ''  # Empty for public domain
                    domain = current_site.domain  # e.g., "localhost"
                else:
                    subdomain = connection.tenant.schema_name  # e.g., "demo1"
                    domain = current_site.domain  # e.g., "localhost"
                subject = 'Activate your Account'
                message = render_to_string('accounts/registration/account_activation_email.html', {
                    'user': user,
                    'domain': domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                    'subdomain':subdomain
                })
                user.email_user(subject=subject, message=message)               

            return render(request, 'accounts/registration/register_email_confirm.html', {'form': registerForm})
    else:
        registerForm = PublicRegistrationForm(tenant=current_tenant)
    return render(request, 'accounts/registration/register.html', {'form': registerForm})



def account_activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user and account_activation_token.check_token(user, token):
        tenant_schema = getattr(user.tenant, "schema_name", None)

        if tenant_schema == "public":
            user.is_active = True
            user.is_staff = False
        elif user.role in ['doctor', 'patient']:
            user.is_active = True
            user.is_staff = False
        else:
            user.is_active = True
            user.is_staff = False

        user.save()

        if user.role == 'doctor':
            login(request, user, backend='accounts.backends.TenantAuthenticationBackend')  # ✅ Ensure user is logged in
            messages.success(request, "Thank you, your account has been successfully created. Please create your profile.")
            return redirect('finance:enroll_doctor')

        else:
            login(request, user, backend='accounts.backends.TenantAuthenticationBackend')
            messages.success(request, "Your account has been activated! You can work now.")
            return redirect('clients:tenant_expire_check')
    return render(request, 'accounts/registration/activation_invalid.html')




def login_view(request):
    current_tenant = None
    if hasattr(connection, 'tenant'):
        current_tenant = connection.tenant         
        current_schema = current_tenant.schema_name   

        subscriptions = Subscription.objects.all()
        current_date = timezone.now().date()
        for subscription in subscriptions:
            if subscription.expiration_date:
                if subscription.expiration_date < current_date:
                    subscription.is_expired = True
                    subscription.save()
    form = CustomLoginForm(initial={'tenant': current_schema })   

    if request.method == 'POST':
        form = CustomLoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
                    
            user = authenticate(request, username=username, password=password)
            tenant = current_schema 
            if user:                  
                login(request, user,backend='accounts.backends.TenantAuthenticationBackend')
                current_schema_found=request.tenant.schema_name == get_public_schema_name()
                protocol = 'https' if request.is_secure() else 'http'
                if not current_schema_found:   
                    messages.success(request, "Login successful!")                      
                    host = request.get_host()
                    parts = host.split('.')
                    if parts[0] == current_schema:
                        domain = '.'.join(parts[1:])
                    else:
                        domain = '.'.join(parts)
                    #domain = host.split(':')[0]  # strips port if any
                    #domain = 'aiha.live'
                    protocol = 'https'
                    tenant_url = f"{protocol}://{tenant}.{domain}/clients/tenant_expire_check/"
                    return redirect(tenant_url)       
                else:
                    messages.success(request, "Login successful!")                      
                    tenant_url = f"{protocol}://{domain}/clients/tenant_expire_check/"                    
                    return redirect(tenant_url)     

            else:
                messages.error(request, "Invalid username or password.")
        else:
            print(form.errors)
            form = CustomLoginForm(initial={'tenant':  current_schema })  
            messages.error(request, "Please provide correct username and password")
  
    
    form = CustomLoginForm(initial={'tenant':  current_schema })    
    return render(request, 'accounts/registration/login.html', {'form': form})




def send_otp(request, phone_number):
    if not phone_number:
        return render(request, "accounts/registration/register.html", {"error": "Phone number required."})

    otp_obj, _ = PhoneOTP.objects.get_or_create(phone_number=phone_number)
    otp_obj.generate_otp()

    message = f"Your verification code is: {otp_obj.otp}"
    try:
        send_sms(tenant=getattr(request, "tenant", None), phone_number=phone_number, message=message)
        print(f'your otp code is {otp_obj.otp}')
    except Exception as e:
        return render(request, "accounts/registration/register.html", {"error": f"SMS failed: {e}"})

    return render(request, "accounts/verify_otp.html", {
        "phone": phone_number,
        "valid_until": otp_obj.valid_until,
    })





from django.utils.crypto import constant_time_compare

def verify_otp(request):
    phone = request.POST.get("phone")
    otp_input = request.POST.get("otp")

    if not phone or not otp_input:
        return render(request, "accounts/verify_otp.html", {
            "error": "Phone number and OTP are required.",
            "phone": phone
        })

    otp_entry = PhoneOTP.objects.filter(phone_number=phone).first()
    if not otp_entry:
        return render(request, "accounts/verify_otp.html", {
            "error": "OTP not found.",
            "phone": phone
        })

    if constant_time_compare(otp_entry.otp, otp_input) and timezone.now() <= otp_entry.valid_until:
        otp_entry.is_verified = True
        otp_entry.save()

        user = CustomUser.objects.filter(phone_number=phone).first()
        if user:
            user.is_phone_verified = True
            user.is_active = True
            user.save()

            login(request, user, backend='accounts.backends.TenantAuthenticationBackend')

            if user.role == 'doctor':
                messages.success(request, "Thank you, your account has been successfully created. Please create your profile.")
                return redirect('finance:enroll_doctor')
            else:
                messages.success(request, "Phone number verified successfully. You can now log in.")
                return redirect("accounts:login")
        else:
            return render(request, "accounts/verify_otp.html", {
                "error": "No user found for this phone number.",
                "phone": phone
            })
    else:
        return render(request, "accounts/verify_otp.html", {
            "error": "Invalid or expired OTP.",
            "phone": phone
        })




def logged_out_view(request):
    plans = SubscriptionPlan.objects.all().order_by('duration')
    for plan in plans:
        plan.features_list = plan.features.split(',')
        
    is_partner_job_seeker = False    
    is_public = False

    if request.user.is_authenticated:        
        is_partner_job_seeker = request.user.groups.filter(name__in=('partner','job_seeker')).exists()       
        is_public = request.user.groups.filter(name='public').exists()
       
    logout(request)     
    return render(request, 'accounts/registration/logged_out.html',{'plans':plans})




def assign_model_permission_to_user(user, model_name, permission_codename): 
    try:
        app_label, model_label = model_name.split('.')
        model = apps.get_model(app_label, model_label)
        content_type = ContentType.objects.get_for_model(model)
        permission = Permission.objects.get(codename=permission_codename, content_type=content_type)

        user.user_permissions.add(permission)
        user.save()
        
        return f"Permission '{permission_codename}' successfully assigned to {user.username}."
    except Permission.DoesNotExist:
        return f"Permission '{permission_codename}' does not exist for the model '{model_name}'."
    except Exception as e:
        return f"An error occurred: {e}"



@login_required
def assign_permissions(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to assign roles.")
        return redirect('core:home')

    if request.method == 'POST':
        form = AssignPermissionsForm(request.POST)
        if form.is_valid():
            try:
               
                selected_permissions = form.cleaned_data['permissions']
                model_name = form.cleaned_data['model_name']   
                email = form.cleaned_data['email']  
                user = CustomUser.objects.get(email=email)                   

                cleaned_model_name = model_name.strip("[]").strip("'\"")                
                user = CustomUser.objects.get(email=email)
                
                for permission_codename in selected_permissions:
                    cleaned_codename = permission_codename.strip("[]").strip("'\"")                    
                    message = assign_model_permission_to_user(user, cleaned_model_name, cleaned_codename)
                    messages.success(request, message)                
                return redirect('accounts:assign_permissions')
            except Permission.DoesNotExist:
                messages.error(request, f"Permission '{permission_codename}' does not exist.")
            except Exception as e:
                print(e)
                messages.error(request, f"An error occurred: {e}")
        else:
            print(form.errors)
    else:
        form = AssignPermissionsForm()

    users = CustomUser.objects.all().order_by('-date_joined')
    paginator = Paginator(users,8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'accounts/assign_permission.html', {'form': form, 'users': users,'page_obj':page_obj})



@login_required
def assign_user_to_group(request):
    group_data = Group.objects.all()

    if request.method == 'POST':
        form = UserGroupForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email'] 
            group = form.cleaned_data['group']
            new_group_name = form.cleaned_data['new_group_name']

            try:
                user = CustomUser.objects.get( email=email)
            except User.DoesNotExist:
                messages.error(request, f"User '{username}' does not exist.")
                return redirect('accounts:assign_user_to_group')

            if group:
                user.groups.add(group)
                messages.success(request, f"User '{email}' was added to the existing group '{group.name}'.")
            elif new_group_name:
                group, created = Group.objects.get_or_create(name=new_group_name)
                user.groups.add(group)
                if created:
                    messages.success(request, f"Group '{new_group_name}' was created and '{username}' was added to it.")
                else:
                    messages.success(request, f"User '{username}' was added to the existing group '{new_group_name}'.")
            
            user.save()
            return redirect('accounts:assign_user_to_group')
    else:
        form = UserGroupForm()
    return render(request, 'accounts/assign_user_to_group.html', {'form': form,'group_data':group_data})




def assign_permissions_to_group(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to assign roles.")
        return redirect('core:home')

    group_name = None
    assigned_permissions = []
    group_data = Group.objects.all() 

    if request.method == 'POST':
        form = AssignPermissionsToGroupForm(request.POST)
        if form.is_valid():
            group = form.cleaned_data['group']
            model_name = form.cleaned_data['model_name']
            selected_permissions = form.cleaned_data['permissions']

            try:
                model_class = apps.get_model(*model_name.split('.'))
                content_type = ContentType.objects.get_for_model(model_class)

                for permission in selected_permissions:
                    if permission.content_type == content_type:
                        group.permissions.add(permission)

                group_name = group.name
                assigned_permissions = group.permissions.select_related('content_type').all() 
                messages.success(request, f"Permissions successfully assigned to the group '{group.name}'.")
                return redirect('accounts:assign_permissions_to_group')

            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
        else:
            print(form.errors)
    else:
        form = AssignPermissionsToGroupForm()

    groups_info = []
    for group in group_data:
        users_in_group = group.user_set.all() 
        permissions_in_group = group.permissions.select_related('content_type').all()  
        groups_info.append({
            'group': group,
            'users': users_in_group,
            'permissions': permissions_in_group
        })

    return render(
        request,
        'accounts/assign_permissions_to_group.html',
        {
            'form': form,
            'group_name': group_name,
            'assigned_permissions': assigned_permissions,
            'groups_info': groups_info,  # Pass the group data to the template
        }
    )



# for ajax
def get_permissions_for_model(request):
    model_name = request.GET.get('model_name', '')    
    try:
        app_label, model_name = model_name.split('.')
        model_class = apps.get_model(app_label, model_name)   
        content_type = ContentType.objects.get_for_model(model_class) 
        permissions = Permission.objects.filter(content_type=content_type)
        permission_data = [
            {'id': perm.id, 'name': perm.name, 'codename': perm.codename}
            for perm in permissions
        ]        
        return JsonResponse({'permissions': permission_data})    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


from prescription.models import Patient,Doctor

def common_search(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:     
        employees = Doctor.objects.filter(
            Q(name__icontains=query) | Q(employee_code__icontains=query)
        ).values('id', 'name', 'employee_code')
        results.extend([
            {'id': emp['id'], 'text': f"{emp['name']} ({emp['employee_code']})"}
            for emp in employees
        ]) 

        medications = Patient.objects.filter(
            Q(name__icontains=query) | Q(product_id__icontains=query)
        ).values('id', 'name', 'product_id')
        results.extend([
            {'id': prod['id'], 'text': f"{prod['name']} ({prod['product_id']})"}
            for prod in medications
        ])
     
     

    return JsonResponse({'results': results})



@login_required
def search_all(request):
    query = request.GET.get('q')
   
    employees = Doctor.objects.filter(
        Q(name__icontains=query) | 
        Q(employee_code__icontains=query) | 
        Q(email__icontains=query) | 
        Q(phone__icontains=query) | 
        Q(position__name__icontains=query) | 
        Q(department__name__icontains=query)
    )

  



    return render(request, 'accounts/search_results.html', {
        'employees': employees, 
      
        'query': query,
        
    })
