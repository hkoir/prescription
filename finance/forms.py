from django import forms
from prescription.models import Doctor

class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        exclude = ['user','start_time','end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),        
            'description': forms.Textarea(attrs={'rows': 3}),
            'specialization': forms.Textarea(attrs={'rows': 2}),
            'education': forms.Textarea(attrs={'rows': 2}),
            'hospital_affiliations': forms.Textarea(attrs={'rows': 2}),
            'memberships': forms.Textarea(attrs={'rows': 2}),
            'awards': forms.Textarea(attrs={'rows': 2}),
            'chamber_location': forms.Textarea(attrs={'rows': 2}),
        }


from .models import DoctorPaymentLog

class DoctorPaymentForm(forms.ModelForm):
    class Meta:
        model = DoctorPaymentLog
        fields = ['amount_paid', 'payment_method', 'transaction_id', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }


from prescription.models import Patient
class PatientUpdateForm(forms.ModelForm):
    class Meta:
        model = Patient
        exclude=['remarks','user','free_ai_prescriptions_used','age','last_profile_update']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
            'medical_history': forms.Textarea(attrs={'rows': 2}),
            'allergies': forms.Textarea(attrs={'rows': 2}),
             'current_medications': forms.Textarea(attrs={'rows': 2}),
             'dob': forms.DateInput(attrs={'type': 'date'}),
             'body_weight':forms.NumberInput(attrs={'placeholder':'plese enter your weight in kg'}) ,
             'body_weight':forms.NumberInput(attrs={'placeholder':'plese enter your height in cm'})  

              }
