from django.shortcuts import render,redirect,get_object_or_404
from.models import PaymentProfile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.utils import timezone
from prescription.models import DoctorPrescription
from finance.utils import doctor_required,patient_required
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
import requests
from.forms import DoctorForm,DoctorPaymentForm
from prescription.models import Patient,Doctor
from .models import DoctorPayment, DoctorServiceLog, DoctorPaymentLog
from finance.utils import update_doctor_payment
from itertools import chain



PaymentGatewayAPI=None

def process_payment(payment_token, amount, currency='usd'):
    payment_gateway = PaymentGatewayAPI(api_key="your_api_key")    
    try:
        charge_response = payment_gateway.charge_card(
            token=payment_token,
            amount=amount,
            currency=currency
        )
        
        if charge_response['status'] == 'success':
            return True
        else:
            return False
    except Exception as e:
        return False
    




BKASH_BASE_URL = 'https://pay.bkash.com'  # or sandbox URL for testing
APP_KEY = 'your_app_key'
APP_SECRET = 'your_app_secret'
USERNAME = 'your_username'
PASSWORD = 'your_password'

def get_disbursement_token():
    url = f"{BKASH_BASE_URL}/token/grant"
    headers = {
        'Content-Type': 'application/json',
        'username': USERNAME,
        'password': PASSWORD
    }
    body = {
        'app_key': APP_KEY,
        'app_secret': APP_SECRET
    }

    response = requests.post(url, json=body, headers=headers)
    response_data = response.json()
    return response_data.get('id_token')



def pay_doctor_bkash(wallet_number, amount, invoice_id):
    token = get_disbursement_token()

    disbursement_url = f"{BKASH_BASE_URL}/disbursement/payment"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': token,
        'X-App-Key': APP_KEY
    }

    payload = {
        "mobile": wallet_number,
        "amount": str(amount),
        "trxID": invoice_id,  # optional tracking ID
        "paymentRefId": f"DOCTOR-PAY-{invoice_id}",
        "mode": "0001"  # Standard disbursement mode
    }

    response = requests.post(disbursement_url, json=payload, headers=headers)
    return response.status_code == 200, response.json()




@login_required
def pay_doctor(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    amount = 1000  
    wallet_number = doctor.payment_wallet_number
    success, response = pay_doctor_bkash(wallet_number, amount, invoice_id=f"DOC{doctor.id}{timezone.now().timestamp()}")

    if success:
        doctor_payment=DoctorPayment.objects.create(
            doctor=doctor,
            total_paid_amount=amount,
            payment_method='bKash',
            payment_date=timezone.now(),
            transaction_id=response.get('trxID'),
            remarks='Payment using Bikash wallet'
        )
        doctor_payment.update_payment_status()

        messages.success(request, "Doctor paid successfully via bKash.")
    else:
        messages.error(request, f"Payment failed: {response.get('message', 'Unknown error')}")

    return redirect('doctor:payment_summary', doctor_id=doctor.id)






@login_required
def patient_dashboard(request):
    patient = None
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.error(request, "Access denied. Only patients can view this dashboard.")
        return redirect('prescription:home')

    doctor_prescriptions = [
        {
            'type': 'Doctor',
            'created_at': pres.prescribed_at,
            'prescription': pres,
        }
        for pres in patient.patient_prescriptions.all()
    ]

    ai_prescriptions = [
        {
            'type': 'AI',
            'created_at': pres.created_at,
            'prescription': pres,
        }
        for pres in patient.patient_ai_prescriptions.all()
    ]

    # Combine and sort by date (most recent first)
    prescriptions = sorted(
        chain(doctor_prescriptions, ai_prescriptions),
        key=lambda x: x['created_at'],
        reverse=True
    )

    appointments = patient.patient_bookings.all()
    pending_appointments = appointments.filter(status='pending')
    
    datas =  prescriptions
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'patient/dashboard.html', {
        'patient': patient,
        'prescriptions': prescriptions,
        'appointments': appointments,
        'pending_appointments': pending_appointments,
        'page_obj':page_obj
    })



from django.urls import reverse
from .forms import PatientUpdateForm
from django.utils.http import url_has_allowed_host_and_scheme

def update_patient_profile(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id, user=request.user)
    next_url = request.GET.get('next') or request.POST.get('next') or reverse('prescription:home')

    if request.method == 'POST':
        form = PatientUpdateForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            form_instance = form.save(commit=False)
            form_instance.user = request.user
            form_instance.last_profile_update = timezone.now()
            form_instance.save()
            messages.success(request, 'Profile updated successfully')
            if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('prescription:home')            
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientUpdateForm(instance=patient)

    return render(request, 'patient/update_patient_profile.html', {
        'form': form,
        'patient': patient,
        'next': next_url
    })



@login_required
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)    
    if request.user != patient.user and request.user.role != 'admin' and request.user.role != 'doctor':
        return render(request, "403.html") 

    return render(request, "patient/patient_detail.html", {
        'patient': patient
    })


@doctor_required
@login_required
def doctor_earnings_view(request):
    doctor = get_object_or_404(Doctor, user=request.user)   
    payouts = DoctorPayment.objects.filter(doctor=doctor).order_by('-payment_date')

    total_due = payouts.aggregate(total=models.Sum('total_due_amount'))['total'] or 0
    total_paid = payouts.aggregate(total=models.Sum('total_paid_amount'))['total'] or 0
    total_unpaid = total_due - total_paid

    return render(request, 'finance/doctor_earningspayment_dashboard.html', {
        'payouts': payouts,
        'total_due': total_due,
        'total_paid': total_paid,
        'total_unpaid': total_unpaid,
    })





@login_required
def doctor_profile(request):
    doctor = get_object_or_404(Doctor, user=request.user)
    if not doctor:
        messages.warning(request,'Only associated doctor can view this profile')
        return redirect('prescription:home')
    return render(request, 'doctor/profile.html', {'doctor': doctor})




@login_required
def create_doctor_profile(request):
    # Prevent duplicate profile creation
    doctor = Doctor.objects.filter(user=request.user).first()
    if doctor:
        messages.warning(request, 'You have already created a doctor profile.')
        return redirect('finance:doctor_detail', doctor.id)

    if request.method == 'POST':
        form = DoctorForm(request.POST, request.FILES)
        if form.is_valid():
            doctor = form.save(commit=False)
            doctor.user = request.user
            doctor.save()
            messages.success(request, 'Doctor profile created successfully.')
            return redirect('finance:doctor_detail', doctor.id)
    else:
        form = DoctorForm()

    return render(request, 'doctor/create_doctor_profile.html', {'form': form})



from prescription.models import Doctor
from django.core.exceptions import PermissionDenied


@login_required
def manage_doctor_profile(request, id=None):
    doctor = Doctor.objects.filter(user=request.user).first()
    if doctor:
        messages.warning(request, 'You have already created a doctor profile.')
        return redirect('finance:doctor_dashboard')

    if id:
        instance = get_object_or_404(Doctor, id=id)
        if instance.user and instance.user != request.user and not request.user.is_staff and not request.user.is_superuser:
            raise PermissionDenied("You do not have permission to edit this profile.")
        message_text = "Profile updated successfully!"
    else:
        instance = None
        message_text = "Profile created successfully!"

    form = DoctorForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        doctor = form.save(commit=False)
        doctor.user = request.user
        doctor.save()
        messages.success(request, message_text)
        return redirect('finance:doctor_detail', doctor.id)

    datas = Doctor.objects.all()
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'doctor/create_doctor_profile.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj,
    })





@login_required
def delete_doctor_profile(request, id):
    instance = get_object_or_404(Doctor, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('finance:create_doctor_profile')

    messages.warning(request, "Invalid delete request!")
    return redirect('finance:create_doctor_profile')







def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    return render(request, 'doctor/doctor_detail.html', {'doctor': doctor})


from payment_gateway.models import PaymentInvoice
from django.db.models import Sum

@doctor_required
@login_required
def doctor_dashboard(request):  
    doctor = Doctor.objects.filter(user=request.user).first()
    if not doctor:
        messages.warning(request, 'No doctor available')
        return redirect('prescription:home') 
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    today = timezone.localdate()
    start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else today
    end_date = timezone.datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else today

    prescriptions = doctor.doctor_prescriptions.filter(
        appointment_ref__isnull=True,
        prescribed_at__date__range=(start_date, end_date)
    )
    chamber_prescriptions = doctor.doctor_prescriptions.filter(
        appointment_ref__isnull=False,
        prescribed_at__date__range=(start_date, end_date)
    )
    pending_Chamber_appointments = doctor.doctor_appointments.filter(
        status='Pending',
        date__range=(start_date, end_date)
    )

    appointments = doctor.doctor_bookings.filter(
        created_at__range=(start_date, end_date)
    )
    pending_appointments = doctor.doctor_bookings.filter(
        status='pending',
        created_at__range=(start_date, end_date)
    )

    payouts = DoctorPayment.objects.filter(
        doctor=doctor,
        created_at__range=(start_date, end_date)
    ).order_by('-payment_date')

    total_due = payouts.aggregate(total=models.Sum('total_due_amount'))['total'] or 0
    total_paid = payouts.aggregate(total=models.Sum('total_paid_amount'))['total'] or 0
    total_unpaid = total_due - total_paid

    chamber_visit_fees = PaymentInvoice.objects.filter(
        doctor=doctor,appointment__isnull=False)
    total_chamber_visit_fees = chamber_visit_fees.aggregate(total=Sum('amount'))['total'] or 0


    paginator = Paginator(appointments, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
 
    return render(request, 'doctor/dashboard.html', {
        'doctor': doctor,
        'prescriptions': prescriptions,
        'chamber_prescriptions': chamber_prescriptions,
        'pending_Chamber_appointments': pending_Chamber_appointments,
        'total_chamber_visit_fees':total_chamber_visit_fees,
        'appointments': appointments,
        'pending_appointments': pending_appointments,
        'payouts': payouts,
        'total_due': total_due,
        'total_paid': total_paid,
        'total_unpaid': total_unpaid,
        'page_obj': page_obj,
        'start_date': start_date,
        'end_date': end_date
    })





def is_staff(user):
    return user.is_staff or user.is_superuser



@login_required
def create_manual_doctor_payment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    doctor_payment_obj = DoctorPayment.objects.filter(doctor=doctor).first()

    if not is_staff(request.user):
        messages.warning(request,'Only staff can access')
        return redirect('prescription:home')

    if request.method == 'POST':
        form = DoctorPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.doctor = doctor
            payment.user = request.user         
            payment.save()
            update_doctor_payment(doctor)
            messages.success(request, 'Payment added successfully.')
            return redirect('finance:doctor_payment_list')
    else:
        form = DoctorPaymentForm()        

    return render(request, 'finance/create_manual_payment.html', {'form': form, 'doctor': doctor,'doctor_payment_obj':doctor_payment_obj})




@login_required
def doctor_payment_list(request):
    payments = DoctorPayment.objects.select_related('doctor').order_by('-created_at')    
    return render(request, 'finance/doctor_payment_list.html', {'payments': payments})



def doctor_payment_detail(request, doctor_id):
    payment = get_object_or_404(DoctorPayment, doctor_id=doctor_id)
    doctor = payment.doctor

    if request.user.role == 'patient':
        messages.warning(request,'Only associated staff doctor can access')
        return redirect('finance:doctor_payment_list')


    service_logs = DoctorServiceLog.objects.filter(doctor=doctor).order_by('-service_date')
    payment_logs = DoctorPaymentLog.objects.filter(doctor=doctor).order_by('-payment_date')

    context = {
        'payment': payment,
        'service_logs': service_logs,
        'payment_logs': payment_logs,
        'doctor': doctor,
    }
    return render(request, 'finance/doctor_payment_detail.html', context)



@login_required
def confirm_payment_status(request, payment_id):
    payment = get_object_or_404(DoctorPaymentLog, id=payment_id)
    if payment.doctor.user != request.user:
        messages.warning(request,'only associated doctor can confirm')
        return redirect('finance:confirm_payment_status')

    if request.method == 'POST':
        status = request.POST.get('payment_confirmation')
        if status in ['received', 'declined']:
            payment.payment_confirmation = status
            payment.save()
            messages.success(request, 'Payment confirmation updated.')
        else:
            messages.warning(request, 'Invalid confirmation value.')
        return redirect('finance:doctor_payment_detail', payment.doctor.id)

    return render(request, 'finance/confirm_payment.html', {'payment': payment})
