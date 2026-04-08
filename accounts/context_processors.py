

from django.db.utils import ProgrammingError
from django_tenants.utils import get_tenant
from clients.models import Tenant
from prescription.models import Patient,Doctor
from django.db.models import Q  
from messaging.models import Notification 



def user_info(request):
    profile_picture_url = None
    patient = None
    doctor= None   
    tenant_photo_url = None
    school_logo_url=None
    school_name=None

    if request.user.is_authenticated:
        try:
            current_client = get_tenant(request)
   
            if current_client.schema_name == 'public':
                return {
                    'user_info': request.user.username,
                    'profile_picture_url': profile_picture_url,
                    'school_logo_url': school_logo_url,
                    'school_name': school_name,
                }
           
            doctor = Doctor.objects.filter(user=request.user).first()
            patient = Patient.objects.filter(user=request.user).first()
          
            current_client = get_tenant(request)

            tenant_instance = Tenant.objects.filter(tenant=current_client).first()
            if tenant_instance and tenant_instance.logo:
                tenant_photo_url = tenant_instance.logo.url
                tenant_name = tenant_instance.name

         
            elif doctor:
                school_logo_url = patient.photo
                school_name = doctor.full_name
            elif patient:
                school_logo_url = patient.photo
                school_name = patient.full_name
            elif tenant_photo_url:
                school_logo_url = tenant_photo_url
                school_name = tenant_name

        except ProgrammingError:
            pass
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error in user_info context processor: {e}")

    return {
        'user_info': request.user.username if request.user.is_authenticated else None,
        'profile_picture_url': profile_picture_url,
        'school_logo_url': school_logo_url,
        'school_name': school_name,
    }




def tenant_schema(request):
    schema_name = getattr(request.tenant, 'schema_name', 'public')
    return {'schema_name': schema_name}



def unread_notifications(request):  
    current_client = get_tenant(request)   
    if current_client.schema_name == 'public':
       return {'unread_notifications': []}
    
    if not request.user.is_authenticated:
        return {'unread_notifications': []}

    notifications = Notification.objects.filter(is_read=False)

    filters = Q(user=request.user)

    if request.user.role == "patient":
        patient = Patient.objects.filter(user=request.user).first()
        if patient:
            filters |= Q(patient=patient)

    elif request.user.role == "doctor":
        doctor = Doctor.objects.filter(user=request.user).first()
        if doctor:
            filters |= Q(doctor=doctor)
    notifications = notifications.filter(filters).order_by('-created_at')
    return {'unread_notifications': notifications}





from chat.models import ChatThread
from django.db.models import Max,Count

def tenant_context(request):
    tenant_schema = getattr(request.tenant, "schema_name", "public")

    if not request.user.is_authenticated:
        return {
            'tenant_prefix': tenant_schema,
            'has_unread': False,
        }

    # Example: check if user is doctor or patient to query accordingly
    if hasattr(request.user, 'role') and request.user.role == 'doctor':
        threads_qs = (
            ChatThread.objects
            .filter(tenant_schema=tenant_schema, doctor_user=request.user)
            .select_related('patient_user')
            .annotate(
                last_msg_at=Max('messages__sent_at'),
                unread_count=Count(
                    'messages',
                    filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=request.user)
                )
            )
            .order_by('-last_msg_at', '-created_at')
        )
        has_unread = any(t.unread_count > 0 for t in threads_qs)
        user_role = 'doctor'

    elif hasattr(request.user, 'role') and request.user.role == 'patient':
        threads_qs = (
            ChatThread.objects
            .filter(tenant_schema=tenant_schema, patient_user=request.user)
            .select_related('doctor_user')
            .annotate(
                last_msg_at=Max('messages__sent_at'),
                unread_count=Count(
                    'messages',
                    filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=request.user)
                )
            )
            .order_by('-last_msg_at', '-created_at')
        )
        has_unread = any(t.unread_count > 0 for t in threads_qs)
        user_role = 'patient'

    else:
        # fallback for other roles or anonymous users
        has_unread = False
        user_role = None

    return {
        'tenant_prefix': tenant_schema,
        'has_unread': has_unread,
        'doctor_user_id': request.user.id if user_role == 'doctor' else None,
        'patient_user_id': request.user.id if user_role == 'patient' else None,
        'user_role': user_role,
        'user_id':request.user.id,
     
    }
