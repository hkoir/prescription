from django import forms
from.models import Patient
from.models import DoctorPrescription,SuggestedMedicine,SuggestedLabTest,Patient,DoctorBooking
from.models import DoctorBooking
from.models import ZoomMeeting,DoctorFolloupBooking
from .models import Medicine, LabTest
from .models import Doctor 



class DoctorAdminForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = '__all__'
        widgets = {
            'start_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'end_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'hospital_start_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'hospital_end_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
        }





class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        exclude = ['user', 'remarks','age','free_ai_prescriptions_used']
        widgets = {
            'address': forms.TextInput(attrs={'style': 'height:100px; width:100%;'}),
            'dob': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            # Skip checkbox fields because they have different UI
            if not isinstance(field.widget, forms.CheckboxInput):
                existing_classes = field.widget.attrs.get('class', '')
                if 'form-control' not in existing_classes:
                    field.widget.attrs['class'] = (existing_classes + ' form-control').strip()






class AIPrescriptionForm(forms.Form):
    symptoms = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text="List multiple symptoms (e.g., fever, cough)"
    )
    duration = forms.CharField(help_text="How long has the patient had symptoms?")   
    
    current_medications = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        help_text="Current medications with dosage"
    )
    vital_signs = forms.CharField(
        required=False,
        help_text="Enter vital signs (e.g., Temp: 101°F, BP: 120/80, HR: 90 bpm)"
    )


class LabTestInterpretationForm(forms.Form):
    # No need to define lab_files in the form
    dummy = forms.CharField(required=False)  # Optional: to keep form non-empty if needed





class DirectDoctorBookingForm(forms.ModelForm):
    class Meta:
        model = DoctorBooking
        fields = [
             'symptom_image', 'symptom_video','symptoms_summary', 'duration',
            'vital_signs', 'location'
        ]
        widgets = {
            'symptoms_summary': forms.TextInput(attrs={'style': 'height:70px'}),
            'vital_signs': forms.TextInput(attrs={'style': 'height:70px'}),
             'symptom_image': forms.ClearableFileInput(attrs={
                'accept': 'image/*',
                'capture': 'environment',  # 'user' for front camera
                'class': 'form-control'
            }),
              
        }



class RequestVideoCallForm(forms.Form):
    video_call_message = forms.CharField(
        widget=forms.Textarea(attrs={'style':'height:100px'}),
        help_text="Write your request message  (Optional)"
    )



class RequestVideoCallForm(forms.ModelForm):
    class Meta:
        model = DoctorBooking
        fields = ["video_call_request_message"]
        widgets = {           
            "video_call_request_message":forms.TextInput(attrs={
            'style':'height:100px',
            'placeholder':"Write your request message  (Optional)"
            }),
            

        }
class ApproveRequestVideoCallForm(forms.ModelForm):
    class Meta:
        model = DoctorBooking
        fields = ["video_call_request_approve",'video_call_time']
        widgets={
            'video_call_time': forms.DateTimeInput(attrs={'type':'datetime-local'})
        }
       
       

#======================= follow-up schedules ====================================

class DoctorFolloupBookingRequestForm(forms.ModelForm):
    class Meta:
        model = DoctorFolloupBooking
        fields = ["patient_Current_status", 'symptom_image', 'symptom_video', 'proposed_followup_datetime']
        widgets = {
            "patient_Current_status": forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            "proposed_followup_datetime": forms.DateTimeInput(attrs={"type": "datetime-local", 'class': 'form-control'}),
            "symptom_video": forms.ClearableFileInput(attrs={'accept': 'video/*'}),
            "symptom_image": forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }



class DoctorFolloupBookingApprovedForm(forms.ModelForm):
    class Meta:
        model = DoctorFolloupBooking
        fields = ['approved_followup_datetime']
        widgets = {
            "approved_followup_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }




class PatientZoomRequestForm(forms.ModelForm):
    class Meta:
        model = ZoomMeeting
        fields = ["request_message", "doctor_folloup_booking",'proposed_meeting_datetime']
        widgets = {
            "request_message": forms.Textarea(attrs={
                'style': 'height:100px',
                'placeholder': 'Enter your message (optional) for this follow-up booking'
            }),
            "doctor_folloup_booking": forms.Select(attrs={
                'placeholder': 'Please select your desired booking ID',
                'class':'form-control'
            }),

             "proposed_meeting_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

       

class DoctorZoomScheduleForm(forms.ModelForm):
    class Meta:
        model = ZoomMeeting
        fields = ["scheduled_time"]
        widgets = {
            "scheduled_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class DoctorPrescriptionForm(forms.ModelForm):
    class Meta:
        model = DoctorPrescription
        fields = ['diagnosis', 'advice']
        widgets={
            'diagnosis':forms.Textarea(attrs={'style':'height:150px'}),
            'advice':forms.Textarea(attrs={'style':'height:150px'})
        }
      
       

class SuggestedMedicineForm(forms.ModelForm):
    class Meta:
        model = SuggestedMedicine
        exclude = ('prescription',)       
        widgets={
            'instructions':forms.TextInput(attrs={
                'style':'height:70px'
            })
        }



class SuggestedLabTestForm(forms.ModelForm):
    class Meta:
        model = SuggestedLabTest
        fields = ['lab_test_name', 'custom_lab_test_name']
        widgets={
            'lab_test_notes':forms.TextInput(attrs={
                'style':'height:70px'
            })
        }





class MedicineForm(forms.ModelForm):
    BRAND_CHOICES = [
        ('ACI', 'ACI'),
        ('Square', 'Square'),
        ('Beximco', 'Beximco'),
        ('Renata', 'Renata'),
        ('Others', 'Others'),
    ]

    brand = forms.ChoiceField(choices=BRAND_CHOICES, required=False)

    class Meta:
        model = Medicine
        fields = ['name', 'generic_name', 'medicine_type', 'brand', 'description', 'product_image']
        widgets = {
            'description': forms.TextInput(attrs={'style': 'height:90px'})
        }





class LabTestForm(forms.ModelForm):
    class Meta:
        model = LabTest
        fields = ['test_type', 'test_name', 'description', 'price']
        widgets = {
            'description': forms.TextInput(attrs={'style': 'height:90px'})
        }
