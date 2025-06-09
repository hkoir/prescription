from django import forms
from .models import SymptomCheckSession

class SymptomSessionStartForm(forms.ModelForm):
    class Meta:
        model = SymptomCheckSession
        fields = ['dob', 'gender','location']
        widgets = {
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type':'date'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
        }





class SymptomCheckForm(forms.ModelForm):
    class Meta:
        model = SymptomCheckSession
        fields = ['current_medications', 'vital_signs']
        widgets = {
            'current_medications': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'E.g., Paracetamol 500mg twice daily',
                'rows': 3,
            }),
            'vital_signs': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'E.g., Temp: 100.4°F, BP: 120/80, HR: 80',
                'rows': 3,
            }),
        }
