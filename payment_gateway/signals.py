from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from io import BytesIO
from xhtml2pdf import pisa

from .models import PaymentInvoice

def generate_invoice_pdf(invoice):
    html = render_to_string('payment_gateway/payment_invoice_template.html', {'invoice': invoice})
    result = BytesIO()
    pisa.CreatePDF(src=html, dest=result)
    return result.getvalue()

@receiver(post_save, sender=PaymentInvoice)
def send_invoice_email(sender, instance, created, **kwargs):
    # Send when newly created or updated with AI prescription
    if not instance.patient or not instance.patient.user.email:
        return

    if created or instance.ai_prescription:
        pdf_data = generate_invoice_pdf(instance)
        email = EmailMessage(
            subject='Your Invoice',
            body='Dear patient, please find attached your invoice.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[instance.patient.user.email],
        )
        email.attach(f'invoice_{instance.tran_id}.pdf', pdf_data, 'application/pdf')
        email.send()
