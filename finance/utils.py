
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Sum
from.models import DoctorPaymentLog,DoctorServiceLog,DoctorPayment



def doctor_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if hasattr(request.user, 'role') and request.user.role in ['doctor', 'consultant']:
            return view_func(request, *args, **kwargs)
        return redirect('prescription:home')
    return user_passes_test(lambda u: u.is_authenticated)(_wrapped_view)




def patient_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if hasattr(request.user, 'role') and request.user.role in ['patient']:
            return view_func(request, *args, **kwargs)
        return redirect('prescription:home')
    return user_passes_test(lambda u: u.is_authenticated)(_wrapped_view)



def update_doctor_payment(doctor):
    total_due = DoctorServiceLog.objects.filter(doctor=doctor).aggregate(total=Sum('service_fee'))['total'] or 0
    total_paid = DoctorPaymentLog.objects.filter(doctor=doctor).aggregate(total=Sum('amount_paid'))['total'] or 0

    payment, created = DoctorPayment.objects.get_or_create(doctor=doctor)
    payment.total_due_amount = total_due
    payment.total_paid_amount = total_paid
    payment.is_paid = total_due <= total_paid
    payment.save()
