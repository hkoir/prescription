
from django import forms
from prescription.models import Patient
from .models import PaymentInvoice



class PaymentRequestForm(forms.ModelForm):
    class Meta:
        model = PaymentInvoice
        fields = ['patient', 'invoice_type', 'related_object_id', 'amount', 'description']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'invoice_type': forms.Select(attrs={'class': 'form-select'}),
            'related_object_id': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount in BDT'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Consultation with Dr. Rahman'}),
        }
