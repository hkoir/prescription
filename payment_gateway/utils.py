import requests
from clients.models import GlobalSMSConfig, TenantSMSConfig
import requests


def send_sms(tenant=None, phone_number=None, message=""):  
    config = None
  
    if tenant:
        config = TenantSMSConfig.objects.filter(tenant=tenant).first()

    if not config:
        config = GlobalSMSConfig.objects.first()

    if not config:
        raise Exception("No SMS configuration found.")

    params = {
        "api_key": config.api_key,
        "type": "text",
        "number": phone_number,
        "senderid": config.sender_id or "DefaultSID",
        "message": message,
    }

    try:
        response = requests.get(config.api_url, params=params)
        print("SMS Provider Response:", response.text)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise Exception(f"SMS sending failed: {str(e)}")






# example of sending sms
def notify_payment(student, guardian, paid_amount):
    tenant = student.user.tenant
    phone_number = guardian.phone_number
    message = f"Dear {guardian.name}, your payment of BDT {paid_amount} has been received. Thank you."

    try:
        send_sms(tenant, phone_number, message)
    except Exception as e:
        print("SMS failed:", e)







import time
from.models import PaymentInvoice



def create_payment_invoice(
    patient,
    invoice_type,
    amount,
    description,
    related_object_id=None,
    doctor=None,
    ai_prescription=None,
    doctor_booking=None,
    doctor_prescription=None,
    doctor_followup_booking =None,
    zoom_meeting=None,
    symptom_checker=None,
):
    from .models import PaymentInvoice  # Optional: if circular import issues

    invoice = PaymentInvoice.objects.create(
        patient=patient,
        doctor=doctor,

        ai_prescription=ai_prescription,
        doctor_booking=doctor_booking,
        doctor_prescription=doctor_prescription,
        doctor_followup_booking =doctor_followup_booking ,
        zoom_meeting=zoom_meeting,
        symptom_checker=symptom_checker,

        invoice_type=invoice_type,
        amount=amount,
        description=description,
        related_object_id=related_object_id,
        tran_id=f"txn_{int(time.time())}",  # For uniqueness
    )
    return invoice




from .models import TenantPaymentConfig

def is_payment_enabled_for_tenant(tenant):
    try:
        config = TenantPaymentConfig.objects.get(tenant=tenant)
        return config.enable_payment_gateway
    except TenantPaymentConfig.DoesNotExist:
        return False  # or True based on your default policy













