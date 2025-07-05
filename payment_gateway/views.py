import requests
from django.conf import settings
from django.http import HttpResponse
from .forms import PaymentRequestForm
from django.views.decorators.csrf import csrf_exempt
from payment_gateway.models import Payment
import json
import time, requests
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import PaymentInvoice

import time
from django.utils import timezone
from .models import PaymentInvoice


from payment_gateway.utils import create_payment_invoice
from prescription.models import Patient,Doctor
from prescription.models import DoctorBooking
from prescription.forms import DirectDoctorBookingForm
from django.core.files.base import ContentFile
import base64
from django.db import IntegrityError

from django.contrib.auth.decorators import login_required


from prescription.models import DoctorFolloupBooking,AIPrescription,ZoomMeeting
from django.contrib import messages
from django.utils.http import urlencode



def review_invoice2(request):
    tran_id = request.GET.get('tran_id')
    invoice = get_object_or_404(PaymentInvoice, tran_id=tran_id)
    return render(request, 'payment_gateway/review_invoice.html', {
        'invoice': invoice
    })




def review_invoice(request):
    tran_id = request.GET.get('tran_id')
    invoice = get_object_or_404(PaymentInvoice, tran_id=tran_id)
    patient = invoice.patient
    doctor = invoice.doctor

    if invoice.invoice_type == 'direct-consultation' and doctor:
        parsed_description = f"Direct Consultation with {doctor.full_name}"

    elif invoice.invoice_type == 'consultation' and doctor and invoice.prescription:
        parsed_description = f"Confirm Booking with Dr. {doctor.full_name} (Prescription #{invoice.prescription.id})"

    elif invoice.invoice_type == 'video-consultation':
        parsed_description = f"Video Consultation with Doctor {doctor.full_name}"

    elif invoice.invoice_type == 'ai_prescription':
        parsed_description = "AI-generated Prescription Service"

    elif invoice.invoice_type == 'symptom-check':
        parsed_description = "Symptom Checker Analysis"

    elif invoice.invoice_type == 'labtest':
        parsed_description = "Lab Test Booking"

    elif invoice.invoice_type == 'followup-consultation':
        parsed_description = f"Follow-up Doctor Consultation with {doctor.full_name}"

    elif invoice.invoice_type == 'followup-video-consultation':
        parsed_description = f"Video Follow-up Consultation with {doctor.full_name}"

    else:
        parsed_description = invoice.description or "N/A"

    return render(request, 'payment_gateway/review_invoice.html', {
        'invoice': invoice,
        'parsed_description': parsed_description,
    })






def initiate_payment(request):
    if request.method == 'POST':
        tran_id = request.POST.get('tran_id')
        invoice = get_object_or_404(PaymentInvoice, tran_id=tran_id)

        post_data = {
            'store_id': settings.SSLZCOMMERZ_STORE_ID,
            'store_passwd': settings.SSLZCOMMERZ_STORE_PASS,
            'total_amount': invoice.amount,
            'currency': "BDT",
            'tran_id': invoice.tran_id,
            'success_url': request.build_absolute_uri('/payment_gateway/payment/success/'),
            'fail_url': request.build_absolute_uri('/payment_gateway/payment/fail/'),
            'cancel_url': request.build_absolute_uri('/payment_gateway/payment/cancel/'),

            'emi_option': 0,
            'cus_name': invoice.patient.full_name,
            'cus_email': invoice.patient.user.email or "info@example.com",
            'cus_phone': invoice.patient.phone or "017xxxxxxxx",
            'cus_add1': "Dhaka",
            'cus_city': "Dhaka",
            'cus_country': "Bangladesh",
            'shipping_method': "NO",
            'product_name': invoice.description or invoice.invoice_type,
            'product_category': "Healthcare",
            'product_profile': "general",
            'value_a': str(invoice.pk), 
        }

        url = (
            "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"
            if settings.SSLZCOMMERZ_IS_SANDBOX
            else "https://securepay.sslcommerz.com/gwprocess/v4/api.php"
        )

        response = requests.post(url, data=post_data)
        data = response.json()

        if data['status'] == "SUCCESS":
            return redirect(data['GatewayPageURL'])
        else:
            return HttpResponse("Payment failed: " + data.get('failedreason', 'Unknown'))

    return HttpResponse("Invalid request.")



@csrf_exempt
def payment_success(request):
    if request.method == 'POST':
        data = request.POST
        tran_id = data.get('tran_id')
        invoice_id = data.get('value_a') 

        try:
            invoice = PaymentInvoice.objects.get(pk=invoice_id)
        except PaymentInvoice.DoesNotExist:
            return HttpResponse("Invalid invoice ID.")

        # Check if the payment already exists
        if Payment.objects.filter(transaction_id=tran_id).exists():
            return redirect('payment_gateway:post_payment_redirect', invoice_id=invoice.id)

        try:
            Payment.objects.create(
                transaction_id=tran_id,
                amount=invoice.amount,
                status=data.get('status'),
                method=data.get('payment_option') or data.get('card_brand') or data.get('card_issuer'),
                patient=invoice.patient,
                invoice=invoice,
                gateway_response=json.dumps(dict(data))
            )
        except IntegrityError:
            # In rare cases of race conditions
            return redirect('payment_gateway:post_payment_redirect', invoice_id=invoice.id)
        return redirect('payment_gateway:post_payment_redirect', invoice_id=invoice.id)
    return HttpResponse("❌ Invalid request method.")




from accounts.utils import send_sms

def post_payment_redirect(request, invoice_id):
    invoice = get_object_or_404(PaymentInvoice, id=invoice_id)
    patient = invoice.patient
    invoice.is_paid = True
    invoice.save()

    try:
        if invoice.invoice_type == 'direct-consultation':
            if invoice.doctor:
                next_url = reverse('prescription:book_doctor_direct', args=[invoice.doctor.id])
            else:
                raise ValueError("Missing doctor info for direct consultation")

        elif invoice.invoice_type == 'consultation':
            if invoice.doctor and invoice.prescription:
                send_sms(
                    tenant=request.tenant,
                    phone_number=invoice.doctor.phone_number,
                    message=f"You have a new consultation booking from {patient.full_name}. Please check your dashboard."
                )
                next_url = reverse('prescription:confirm_booking', args=[invoice.prescription.id, invoice.doctor.id])
            else:
                raise ValueError("Missing doctor or prescription info")

        elif invoice.invoice_type == 'video-consultation':
            if invoice.doctor_booking:
                next_url = reverse('prescription:request_video_call', args=[invoice.doctor_booking.id])
            else:
                raise ValueError("Missing doctor booking info for video consultation")

        elif invoice.invoice_type == 'followup-consultation':
            if invoice.related_object_id:
                next_url = reverse('prescription:request_doctor_followup_booking', args=[invoice.related_object_id])
            else:
                raise ValueError("Missing follow-up booking info")

        elif invoice.invoice_type == 'followup-video-consultation':
            if invoice.related_object_id:
                next_url = reverse('prescription:request_zoom_meeting', args=[invoice.related_object_id])
            else:
                raise ValueError("Missing follow-up video info")

        elif invoice.invoice_type == 'ai_prescription':
            next_url = reverse('prescription:create_ai_prescription')

        elif invoice.invoice_type == 'symptom-check':
            next_url = reverse('symptom_checker:start_symptom_check')

        elif invoice.invoice_type == 'labtest':
            messages.success(request, "Payment successful for lab test.")
            return redirect('lab:lab_test_home')

        else:
            return HttpResponse("✅ Payment successful, but no redirection defined.")

        return redirect(f"{reverse('payment_gateway:thank_you')}?next={next_url}")

    except Exception as e:
        messages.error(request, f"Payment successful, but booking details are missing. ({str(e)})")
        return redirect('prescription:home')
    


@csrf_exempt
def payment_fail(request):
    return HttpResponse("Payment failed!")

@csrf_exempt
def payment_cancel(request):
    return HttpResponse("Payment cancelled by user.")



# def thank_you(request, booking_id):
#     booking = get_object_or_404(DoctorBooking, id=booking_id)
#     return render(request, 'payment_gateway/thank_you.html', {'booking': booking})

def payment_thank_you(request):
    next_url = request.GET.get('next')
    return render(request, 'payment_gateway/thank_you.html', {
        'next_url': next_url,
    })







from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from .models import PaymentInvoice
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

@login_required
def download_payment_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(PaymentInvoice, id=invoice_id)

    # Optional: restrict access only to the patient or admin
    if invoice.patient.user != request.user and not request.user.is_staff:
        return HttpResponse("Unauthorized", status=401)

    template = get_template('payment_gateway/payment_invoice_template.html')
    html = template.render({'invoice': invoice})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.tran_id}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response


