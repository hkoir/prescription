from django.db import models
from accounts.models import CustomUser
from datetime import date





class SymptomCheckSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE) 
    started_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

# Ai Output field =================================================================
    probable_disease = models.CharField(max_length=255, null=True, blank=True)  # e.g. 'Malaria'
    probable_symptoms = models.TextField(null=True, blank=True) 
    ai_summary = models.TextField(blank=True, null=True)  
 
  # Patient fixed field ====================================
    dob = models.DateField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        null=True,
        blank=True
    ) 

    weight_in_kg = models.DecimalField(max_digits=10,decimal_places=2,null=True, blank=True)  
    height_in_cm = models.DecimalField(max_digits=10,decimal_places=2,null=True, blank=True)   
    medical_history = models.TextField(blank=True, null=True,help_text="Previous conditions (e.g., diabetes, asthma)")
    allergies = models.TextField(blank=True, null=True,help_text="Any known drug or food allergies")   
    location = models.CharField(max_length=255, blank=True, null=True, help_text="Enter patient's location (City, Country)")
    
    # patient variable fields ========================
    current_medications = models.TextField(blank=True, null=True, help_text="Current medications with dosage")
    vital_signs = models.TextField(blank=True, null=True, help_text="Enter vital signs (e.g., Temp: 101°F, BP: 120/80, HR: 90 bpm)")
     
    duration = models.CharField(max_length=100,blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.dob:
            today = date.today()
            self.age = today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Session {self.id} for {self.user.username}"
 




class SymptomAnswer(models.Model):
    session = models.ForeignKey(SymptomCheckSession, on_delete=models.CASCADE, related_name="answers")
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
