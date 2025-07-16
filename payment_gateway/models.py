from django.db import models
from django.db import models
from django.utils import timezone
from clients.models import Client
from prescription.models import Patient,Doctor
from prescription.models import DoctorBooking,DoctorFolloupBooking,ZoomMeeting,DoctorPrescription,AIPrescription

from symptom_checker.models import SymptomCheckSession
from appointments.models import Appointment


class PaymentSystem(models.Model):
    PAYMENT_METHODS = (
        ('bKash', 'bKash'),
        ('Rocket', 'Rocket'),
        ('CreditCard', 'CreditCard'),
        ('PayPal', 'PayPal'),
        ('sslcommerz', 'SSLCOMERZ'),
        ('aamarPay', 'Aamar Pay'),
        ('surujPay', 'Suruj Pay'),
        ('others', 'Others'),

    )
    method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    name = models.CharField(max_length=255)  
    base_url = models.URLField(blank=True, null=True)



    def __str__(self):
        return self.name
    


class TenantPaymentConfig(models.Model):
    tenant = models.OneToOneField(Client, on_delete=models.CASCADE)
    payment_system = models.ForeignKey(PaymentSystem, on_delete=models.CASCADE)    
    api_key = models.CharField(max_length=255, blank=True, null=True) 
    merchant_id = models.CharField(max_length=255, blank=True, null=True)
    payment_redirect_url = models.URLField(blank=True, null=True)
    client_id = models.CharField(max_length=255, blank=True, null=True)  
    client_secret = models.CharField(max_length=255, blank=True, null=True)
    enable_payment_gateway = models.BooleanField(default=True)

    def __str__(self):
        return f"Payment config for {self.tenant.name} using {self.payment_system.name}"









from datetime import time
from django.utils.timezone import now


class PaymentInvoice(models.Model):
    INVOICE_TYPES = [
        ('symptom-check', 'Symptom Check'),
        ('ai_prescription', 'AI Prescription'),
        ('consultation', 'Doctor Consultation'),
        ('direct-consultation', 'Direct Doctor Consultation'),
        ('video-consultation', 'Video Consultation'),
        ('followup-consultation', 'Follow-up Consultation'),
        ('followup-video-consultation', 'Follow-up Video Consultation'),  
        ('labtest', 'Lab Test'),
        ('medicine', 'Medicine'),
        ('appointment', 'Chamber Visit appointment'),
        ('Others', 'Others'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE,null=True, blank=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)  # ✅ Add this
    ai_prescription = models.OneToOneField(AIPrescription, on_delete=models.SET_NULL, null=True, blank=True,related_name='ai_prescription_invoice')
    symptom_checker = models.OneToOneField(SymptomCheckSession, on_delete=models.SET_NULL, null=True, blank=True,related_name='symptom_checker_invoice')
    doctor_booking = models.ForeignKey(DoctorBooking, on_delete=models.SET_NULL, null=True, blank=True,related_name='doctor_booking_invoice')
    doctor_prescription = models.ForeignKey(DoctorPrescription, on_delete=models.SET_NULL, null=True, blank=True,related_name='doctor_prescription_invoice')
    doctor_followup_booking = models.OneToOneField(DoctorFolloupBooking,on_delete=models.SET_NULL, null=True, blank=True,related_name='doctor_followup_invoice')
    zoom_meeting = models.OneToOneField(ZoomMeeting, on_delete=models.SET_NULL, null=True, blank=True,related_name='zoom_meeting_invoice')
    appointment= models.OneToOneField(Appointment, on_delete=models.SET_NULL, null=True, blank=True,related_name='appointment_invoice')
    related_object_id = models.PositiveIntegerField(blank=True, null=True)
    invoice_type = models.CharField(max_length=30, choices=INVOICE_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    tran_id = models.CharField(max_length=100, unique=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.invoice_type} — {self.patient} — ৳{self.amount}"


    def save(self, *args, **kwargs):
        if not self.tran_id:            
            self.tran_id = f"txn_{now().strftime('%Y%m%d%H%M%S')}_{self.patient.id}"
        super().save(*args, **kwargs)





class Payment(models.Model):
    transaction_id = models.CharField(max_length=100, unique=True)
    invoice = models.ForeignKey(PaymentInvoice, on_delete=models.CASCADE, related_name='payment_invoices')  # NEW
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)  # VALID, FAILED, CANCELLED
    method = models.CharField(max_length=100, blank=True, null=True)  # bKash, Visa, Rocket
    gateway_response = models.TextField(blank=True, null=True)  
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} ({self.status})"










