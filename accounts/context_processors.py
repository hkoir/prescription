

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

    notifications = notifications.filter(filters)
    return {'unread_notifications': notifications}
