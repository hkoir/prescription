from django.db import models
from accounts.models import CustomUser
from django.utils import timezone
from datetime import datetime,date



class AppointmentSlot(models.Model):
    doctor = models.ForeignKey("prescription.Doctor", on_delete=models.CASCADE)
    date = models.DateField(null=True,blank=True)
    start_time = models.TimeField(null=True,blank=True)
    end_time = models.TimeField(null=True,blank=True)
    slot_duration = models.IntegerField(null=True,blank=True)
    is_booked = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:    
            start_dt = datetime.combine(self.date or datetime.today().date(), self.start_time)
            end_dt = datetime.combine(self.date or datetime.today().date(), self.end_time)
            duration = (end_dt - start_dt).total_seconds() / 60  
            self.slot_duration = int(duration) if duration > 0 else 0
        else:
            self.slot_duration = None  # Or keep it blank

        super().save(*args, **kwargs)

    


class Appointment(models.Model):
    appointment_code = models.CharField(max_length=30,null=True,blank=True) 
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Checked', 'Checked'),
        ('Prescription-Given', 'Prescription Given'),
        ('Lab-Test-Requested', 'Lab Test Requested'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    user= models.ForeignKey(CustomUser, on_delete=models.CASCADE,null=True,blank=True)
    doctor = models.ForeignKey("prescription.Doctor", on_delete=models.CASCADE,null=True,blank=True,related_name='doctor_appointments')
    patient = models.ForeignKey("prescription.Patient", on_delete=models.CASCADE,null=True,blank=True,related_name='patient_appointments')
    patient_type = models.CharField(max_length=20,choices={('OPD','OPD'),('IPD','IPD')},null=True,blank=True)
    timeslot = models.ForeignKey(AppointmentSlot,on_delete=models.CASCADE,null=True,blank=True)
    date = models.DateField(default=timezone.now)   
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending')    
    payment_status = models.CharField(
        max_length=50, 
        choices=[('Unpaid', 'Unpaid'), ('Paid', 'Paid'), ('Partially-Paid', 'Partially Paid')],
        default='Unpaid'
    )

    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='followups')
    appointment_type = models.CharField(max_length=20, choices=[("initial", "Initial"), ("followup", "Follow-Up")], default="initial")
   

    def save(self, *args, **kwargs):
        if self.timeslot:
            self.date = self.timeslot.date

        if not self.appointment_code:
            year = timezone.now().strftime("%y")  # Last 2 digits of year
            existing_appointments = Appointment.objects.filter(date__year=self.date.year).count() + 1
            self.appointment_code = f"AP{year}{existing_appointments:06d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Patient:{self.patient} with {self.doctor} on {self.date}-at {self.timeslot}"


