from django.db import models
from accounts.models import CustomUser
import uuid
from datetime import date
from django.conf import settings
from django.db.models import JSONField
from prescription.utils.utils import SPECIALIZATION_CHOICES
from uuid import uuid4
from django.utils.text import slugify
from prescription.utils.zoom import create_zoom_meeting
from django.utils import timezone
from datetime import timedelta
from symptom_checker.models import SymptomCheckSession


class LabTest(models.Model):  # New model
    lab_test_code = models.CharField(max_length=30,null=True,blank=True,unique=True)   
    test_type = models.CharField(max_length=100)
    test_name = models.CharField(max_length=255, unique=True)  
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.lab_test_code :            
            self.lab_test_code  = f"LTC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)    

    def __str__(self):
        return f"{self.test_name}"
    

class Medicine(models.Model):   
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name='product_user')
    product_id = models.CharField(max_length=150, unique=True, null=True, blank=True)  
    name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=100,null=True,blank=True)   
    medicine_type = models.CharField(max_length=50,null=True,blank=True,
        choices=
        {('syrup','Syrup'),
         ('tablet','Tablet'),
         ('capsule','Capsule'),
         ('injection','Injection')                 
         })   
    brand = models.CharField(max_length=255, blank=True, null=True)   
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    product_image= models.ImageField(upload_to='products',null=True,blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.product_id  :            
            self.product_id = f"LTC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)    


    def __str__(self):
        return f"{self.name}"


class Specialization(models.Model):
    name = models.CharField(max_length=100,choices=SPECIALIZATION_CHOICES , unique=True) 
    description = models.TextField(blank=True, null=True)   
    image = models.ImageField(upload_to='specializations/', blank=True, null=True)  
    treatments = models.TextField(blank=True, null=True) 

    def __str__(self):
        return self.name



class Doctor(models.Model): 
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True,blank=True)
    full_name = models.CharField(max_length=255)     
    department = models.CharField(max_length=100)
    specialization = models.TextField(null=True, blank=True)
    medical_license_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
   
    education = models.TextField(null=True, blank=True, help_text="Degrees and certifications")
    experience_years = models.PositiveIntegerField(null=True, blank=True, help_text="Years of medical experience")
    hospital_affiliations = models.TextField(null=True, blank=True, help_text="List of hospitals/clinics affiliated with")
    memberships = models.TextField(null=True, blank=True, help_text="Medical associations or memberships")
    awards = models.TextField(null=True, blank=True, help_text="Recognitions or achievements")

    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    photo = models.ImageField(upload_to='doctors/', blank=True, null=True)
    description = models.TextField(
        null=True, blank=True, 
        help_text="Provide a short  bio"
    )
    start_time = models.TimeField(help_text="Doctor's available start time", null=True, blank=True)
    end_time = models.TimeField(help_text="Doctor's available end time", null=True, blank=True)
    consultation_fees = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    folloup_consultation_fees = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    followup_validity_days = models.PositiveIntegerField(default=10, help_text="Follow-up discount validity in days",null=True,blank=True)
    payment_wallet_number = models.CharField(max_length=11, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name if  self.full_name else 'Unnamed Doctor'




class Patient(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='patient_profile')
    full_name = models.CharField(max_length=255) 
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city =models.CharField(max_length=255,null=True,blank=True)

    dob= models.DateField(null=True,blank=True)
    age = models.PositiveIntegerField(null=True,blank=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    body_weight = models.DecimalField(max_digits=7,decimal_places=2,null=True, blank=True,help_text="Please enter weight in kg")  
    body_height = models.DecimalField(max_digits=7,decimal_places=2,null=True, blank=True,help_text="Please enter height in cm")    
    medical_history = models.TextField(blank=True, null=True,help_text="Previous conditions (e.g., diabetes, asthma)")
    allergies = models.TextField(blank=True, null=True,help_text="Any known drug or food allergies")

    free_ai_prescriptions_used = models.IntegerField(default=0)   
    last_profile_update = models.DateTimeField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    remarks=models.TextField(null=True,blank=True)
    email = models.EmailField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.dob:
            today = date.today()
            self.age = today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
        super().save(*args, **kwargs)

    def needs_profile_update(self):
        if not self.last_profile_update:
            return True
        return timezone.now() - self.last_profile_update > timedelta(days=90)


    def __str__(self):
        return self.full_name
    



class AIPrescription(models.Model):
    ai_prescription_code = models.CharField(max_length=30, null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True, related_name='patient_ai_prescriptions')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    session = models.OneToOneField(
        SymptomCheckSession,
        on_delete=models.CASCADE,
        related_name="ai_prescription",
        null=True,
        blank=True  # optional if you want to allow manual prescriptions too
    )

    symptoms = models.TextField()
    duration = models.CharField(max_length=100, null=True, blank=True)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10)  

    medical_history = models.TextField(blank=True, null=True,help_text="Previous conditions (e.g., diabetes, asthma)")
    allergies = models.TextField(blank=True, null=True,help_text="Any known drug or food allergies")
    current_medications = models.TextField(blank=True, null=True, help_text="Current medications with dosage")
    vital_signs = models.TextField(blank=True, null=True, help_text="Enter vital signs (e.g., Temp: 101°F, BP: 120/80, HR: 90 bpm)")
    location = models.CharField(max_length=255, blank=True, null=True, help_text="Enter patient's location (City, Country)")
 
    diagnosis = models.TextField(blank=True)
    medicines = JSONField(default=list,null=True,blank=True)
    tests = models.TextField(blank=True)
    advice = models.TextField()
    recommended_specialty = models.TextField(blank=True, null=True)
    warning_signs = models.TextField(blank=True, null=True) 
    raw_response = models.TextField(blank=True, null=True)

    created_by_ai = models.BooleanField(default=True)
    reviewed_by = models.ForeignKey(Doctor, on_delete=models.SET_NULL, blank=True, null=True)
    reviewed_on = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.ai_prescription_code:
            self.ai_prescription_code = f"AIPCODE-{uuid.uuid4().hex[:8].upper()}"
        self.age = self.patient.age
        super().save(*args, **kwargs)

    def __str__(self):
        return f"AI Prescription #{self.ai_prescription_code} for {self.patient}"





class DoctorBooking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )
    booking_code = models.CharField(max_length=30, null=True, blank=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE,related_name='patient_bookings')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True,related_name='doctor_bookings')
    ai_prescription = models.ForeignKey(AIPrescription, on_delete=models.SET_NULL, null=True, blank=True,related_name='bookings')
   
    preferred_time = models.DateTimeField(null=True, blank=True)
    symptom_image = models.ImageField(upload_to='symptom_images/', null=True, blank=True)
    symptom_video = models.FileField(upload_to='symptom_videos/', null=True, blank=True)
    symptoms_summary = models.TextField(null=True, blank=True)

    #additional fields if patient does not have ai prescription 
    duration = models.CharField(max_length=100,null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10,null=True, blank=True)
    medical_history = models.TextField(blank=True, null=True,help_text="Previous conditions (e.g., diabetes, asthma)")
    allergies = models.TextField(blank=True, null=True,help_text="Any known drug or food allergies")
    current_medications = models.TextField(blank=True, null=True, help_text="Current medications with dosage")
    vital_signs = models.TextField(blank=True, null=True, help_text="Enter vital signs (e.g., Temp: 101°F, BP: 120/80, HR: 90 bpm)")
    location = models.CharField(max_length=255, blank=True, null=True, help_text="Enter patient's location (City, Country)")
    video_call_reuest_message = models.TextField(null=True,blank=True)
    video_call_reuest_approve =  models.CharField(null=True,blank=True,choices=[('approved','Approved'),('rejected','Rejected')])
    video_call_time = models.DateTimeField(null=True,blank=True)
    video_link = models.URLField(blank=True, null=True)   

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
 
  
 
    def save(self, *args, **kwargs):
        if not self.age:
            self.age = self.patient.age 
        if not self.gender:
            self.gender = self.patient.gender     
        if not self.booking_code:
            self.booking_code = f"BC-{uuid.uuid4().hex[:8].upper()}"   

        if not self.video_link and self.video_call_reuest_message:
            try:
                zoom_data = create_zoom_meeting(topic=f"Appointment #{self.booking_code}", duration=30)
                self.video_link = zoom_data["join_url"]  # Patient and doctor can use this
            except Exception as e:
                print("Zoom API error:", e)   

        super().save(*args, **kwargs)

 
    def is_followup_valid(self):
        if not self.doctor or not self.created_at:
            return False
        expiry_date = self.created_at + timedelta(days=self.doctor.followup_validity_days)
        return timezone.now().date() <= expiry_date.date()



    def __str__(self):
        return f"Booking for {self.patient} ({self.status})"
    



class DoctorFolloupBooking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )
    doctor_booking =models.ForeignKey(DoctorBooking,on_delete=models.CASCADE,related_name='doctor_folloup_bookings')
    booking_code = models.CharField(max_length=30, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
  
    patient_Current_status = models.TextField(null=True, blank=True)
    symptom_image = models.ImageField(upload_to='symptom_images/', null=True, blank=True)
    symptom_video = models.FileField(upload_to='symptom_videos/', null=True, blank=True)
   
    proposed_followup_datetime = models.DateTimeField(null=True, blank=True)
    approved_followup_datetime = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.booking_code:
            self.booking_code = f"BC-{uuid.uuid4().hex[:6].upper()}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Follow up ID-{self.booking_code} -Patient-{self.doctor_booking.patient} ({self.status})"

    

class ZoomMeeting(models.Model):   
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    doctor_booking =models.ForeignKey(DoctorBooking,on_delete= models.CASCADE,related_name='zoom_schedules',null=True, blank=True)
    doctor_folloup_booking =models.OneToOneField(DoctorFolloupBooking,on_delete= models.CASCADE,related_name='zoom_folloup_schedule',null=True, blank=True)
    meeting_code = models.CharField(max_length=20, blank=True, unique=True)
    request_message = models.TextField(blank=True, null=True)
    proposed_meeting_datetime = models.DateTimeField(null=True, blank=True)
    scheduled_time = models.DateTimeField(null=True, blank=True)
    zoom_meeting_link = models.URLField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("executed", "Executed")
        ],
        default="pending"
    )
      

    def save(self, *args, **kwargs):
        if not self.meeting_code:
            self.meeting_code = f"BC-{uuid.uuid4().hex[:4].upper()}"
        if not self.zoom_meeting_link and not self.status == 'rejected': 
            if self.meeting_code:           
                try:
                    zoom_data = create_zoom_meeting(topic=f"Appointment #{self.meeting_code}", duration=30)
                    self.zoom_meeting_link = zoom_data["join_url"] 
                except Exception as e:
                    print("Zoom API error:", e)   

        super().save(*args, **kwargs)



class DoctorPrescription(models.Model):
    doctor_prescription_code=models.CharField(max_length=30,null=True,blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True,blank=True)
    ai_prescription = models.ForeignKey(AIPrescription,on_delete=models.CASCADE,null=True,blank=True,related_name='doctor_prescriptions')
   
    booking_ref = models.ForeignKey(DoctorBooking, on_delete=models.CASCADE,null=True,blank=True,related_name='doctor_booking_refs')
    booking_folloup_ref = models.ForeignKey(DoctorFolloupBooking, on_delete=models.CASCADE,null=True,blank=True,related_name='doctor_folloup_booking_refs')
   
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="patient_prescriptions",null=True,blank=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="doctor_prescriptions",null=True,blank=True)
    diagnosis = models.TextField(verbose_name="Clinical Diagnosis",null=True,blank=True)
    advice = models.TextField(help_text="Follow-up instructions, lifestyle, or dietary advice",null=True,blank=True)
    prescribed_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.doctor_prescription_code:
            self.doctor_prescription_code= f"DPC-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)





class SuggestedMedicine(models.Model):
    prescription = models.ForeignKey(DoctorPrescription, on_delete=models.CASCADE, related_name="pres_medicines", null=True,blank=True)
    medicine_name = models.ForeignKey(Medicine,on_delete=models.CASCADE,null=True,blank=True,related_name='medicines')
    dosage = models.CharField(max_length=100, default='None')
    dosage_schedule = models.CharField(
        max_length=50,
        choices=[
            ("1+0+1", "1+0+1"),
            ("1+1+0", "1+1+0"),
            ("1+1+1", "1+1+1"),
            ('0+1+1', '0+1+1'),
            ('0+1+0', '0+1+0'),
            ('0+0+1', '0+0+1'),
            ('1+0+0', '1+0+0'),
            ("Every-4-Hours", "Every 4 Hours"),
            ("Every-6-Hours", "Every 6 Hours"),
            ("Every-8-Hours", "Every 8 Hours"),
            ("Every-12-Hours", "Every 12 Hours"),
            ("Every-24-Hours", "Every 24 Hours"),
            ("As Needed", "As Needed")
        ], null=True, blank=True
    )
    medication_duration = models.IntegerField(blank=True, null=True)
    instructions = models.TextField(blank=True, null=True)  # optional, like "after food"

    def __str__(self):
        return f"{self.medicine_name} ({self.dosage})"


class SuggestedLabTest(models.Model):
    prescription = models.ForeignKey(DoctorPrescription, on_delete=models.CASCADE, related_name="lab_tests", null=True,blank=True)
    lab_test_name = models.ForeignKey(LabTest,on_delete=models.CASCADE,null=True,blank=True,related_name='lab_tests')
    lab_test_notes = models.TextField(blank=True, null=True)  

    def __str__(self):
         return str(self.lab_test_name)
