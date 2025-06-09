from django.db import models
from accounts.models import CustomUser
from prescription.models import Doctor,Patient
from prescription.models import DoctorPrescription,AIPrescription
from django.db.models import F



class PaymentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="user_payment_profile")
    payment_token = models.CharField(max_length=255, unique=True)  # Token from payment gateway
    card_last4 = models.CharField(max_length=4, blank=True, null=True)  # Last 4 digits
    card_brand = models.CharField(max_length=50,
                                  
    choices=[
        ('VISA','Visa'),
        ('MASTER-CARD','Master card'),
         ('AMEX','American Express')
        ], blank=True, null=True)  
    
    cvv=models.CharField(max_length=3,null=True,blank=True)
    expiry_date = models.CharField(max_length=5, blank=True, null=True)     
    card_expiry_month = models.IntegerField(blank=True, null=True)  # Expiry month
    card_expiry_year = models.IntegerField(blank=True, null=True)  # Expiry year



class DoctorPayment(models.Model):
    user= models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True,blank=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, null=True,blank=True,related_name='doctor_payments')
    total_due_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,blank=True, null=True)  # total service value
    total_paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,blank=True, null=True)   # actual payment done
    payment_method = models.CharField(max_length=50, choices=[
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Mobile', 'Mobile Payment'),
    ],default='Cash',blank=True, null=True)
    payment_date = models.DateField(blank=True, null=True)
    transaction_id=models.CharField(max_length=20,null=True,blank=True)
    payment_confirmation = models.CharField(max_length=20,choices={('received','Recived'),('declined','Declined')},blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    is_paid = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)   
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def due_amount(self):
        return self.total_due_amount - self.total_paid_amount

    def update_payment_status(self):
        self.is_paid = self.due_amount <= 0
        self.save()
        
    def __str__(self):
        doctor_name = self.doctor.full_name if self.doctor and self.doctor.full_name else "Unknown Doctor"
        return f"Payment to {doctor_name} on {self.payment_date}"

      
class DoctorPaymentLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='payment_logs')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=[
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Mobile', 'Mobile Payment'),
    ], default='Cash', blank=True, null=True)
    payment_date = models.DateField(auto_now_add=True)
    transaction_id = models.CharField(max_length=20, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    payment_confirmation = models.CharField(
        max_length=20, choices={('received', 'Received'), ('declined', 'Declined')}, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)



class DoctorServiceLog(models.Model):
    user= models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True,blank=True)
    ai_prescription = models.ForeignKey(AIPrescription, on_delete=models.CASCADE, related_name="doctor_service_logs",null=True, blank=True,)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE,related_name='doctor_logs')    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE,null=True, blank=True,related_name='patient_logs')
    service_date = models.DateField()
    service_fee = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    is_paid = models.BooleanField(default=False)    
    created_at = models.DateTimeField(auto_now_add=True)   
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.service_fee:
            self.service_fee = self.doctor.consultation_fees

        super().save(*args, **kwargs)

        payment_obj, created = DoctorPayment.objects.get_or_create(doctor=self.doctor)
        if created:
            payment_obj.total_due_amount = self.service_fee
            payment_obj.save()
        else:
            DoctorPayment.objects.filter(doctor=self.doctor).update(
                total_due_amount=F('total_due_amount') + self.service_fee
            )

    def __str__(self):
        return f"Consultatin by {self.doctor} on {self.service_date} for patient--{self.patient}"
    



class AIPrescriptionPayment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE,null=True,blank=True)
    ai_prescription = models.OneToOneField(AIPrescription, on_delete=models.CASCADE)
    payment_date = models.DateTimeField(auto_now_add=True)
    used_for_prescription = models.BooleanField(default=False)
    successful = models.BooleanField(default=True) 
    amount = models.DecimalField(max_digits=10, decimal_places=2,null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=[('paid', 'Paid'), ('pending', 'Pending')], null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)
