import json
import os
import random
import string
import uuid
import logging
from time import sleep
from datetime import datetime
from io import BytesIO

import requests
import stripe
from reportlab.pdfgen import canvas

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage, send_mail, BadHeaderError
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView

from accounts.models import Address
from basket.basket import Basket
from orders.models import OrderItem, Order
from payment_gateway.utils import create_payment_invoice
from prescription.models import Patient
from store.models import Product, AudioModel
from accounts.utils import send_sms
from decimal import Decimal    


def order_placed(request):
    basket = Basket(request)
    audio_files = AudioModel.objects.all()
    current_date = datetime.now().strftime('%Y-%m-%d')

    User = get_user_model()
    user = User.objects.get(pk=request.user.id)
    if user.is_authenticated:
        email = user.email

    try:
        with transaction.atomic():
            for item in basket:
                product = item.get('product')
                product_qty = item.get('qty')
                if product.qty >= product_qty:
                    product.qty -= product_qty
                    product.save()
                else:
                    print(' do not have enough quantity')
                    messages.error(request, f'Not enough quantity available for {product.title}')
                    return render(request, 'basket/summary.html', {'current_date': current_date})   
        phone_number = '+8801743800705'
        order_key = 'order_key'       
        basket.clear()   
        message = f"Mr {request.user.username} has placed and confirmed an order Please check"
        send_sms(tenant=request.tenant, phone_number=phone_number, message=message)             

        return render(request, 'payment/orderplaced.html', {'audio_files': audio_files, 'current_date': current_date, 'basket': basket})
   
    except ObjectDoesNotExist as e:
        print(f'Error processing order: {e}')
        messages.error(request, f'Error processing order: {e}')
        return render(request, 'payment/orderplaced.html', {'audio_files': audio_files, 'current_date': current_date, 'basket': basket})


class Error(TemplateView):
    template_name = 'payment/error.html'





@login_required
def initiate_ecommerce_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    total_payable = Decimal(order.total_paid) + Decimal(order.delivery_option)
    patient = None 
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        messages.warning(request, "Only patients can book doctors. Please create a patient profile first.")
        return redirect(f"{reverse('prescription:create_patient_profile')}?next={request.path}")
 

    invoice = create_payment_invoice(
        patient=patient,
        invoice_type='ecommerce',
        amount=total_payable,
        description='ecommerce purchase', 
        related_object_id=order.id,
        doctor=None,
        doctor_booking=None,      
        ecommerce_order=order
    )
    request.session['ecommerce_invoie_id'] = invoice.id
    print('initiate ecommerce payment url trigger')
    return redirect(reverse('payment_gateway:review_invoice') + f'?tran_id={invoice.tran_id}')





def generate_invoice(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=invoice.pdf'

    basket = Basket(request)
    user_id = request.user.id
    baskettotal = basket.get_total_price()
    order_key = str(uuid.uuid4()) 
    
    User = get_user_model()
    user = User.objects.get(pk=request.user.id)
    if user.is_authenticated:
        email=user.email
        try:
             user_address = Address.objects.filter(customer=user).first()
        except ObjectDoesNotExist:
            print('User address not found')
            return HttpResponse("User address not found")

    current_datetime = datetime.now().strftime("%Y-%m-%d")
    invoice_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

#    p = canvas.Canvas(response)
    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    p.setFont("Helvetica-Bold", 20)
    p.setFillColorRGB(0, 0, 255)
    p.drawString(170, 750, 'Invoice for your order')
    p.line(150,730, 420,730)
    p.line(150,725, 420,725)

    p.setFont("Helvetica-Bold", 14)
    p.setFillColorRGB(0, 0, 255)
    p.drawString(170, 700, 'Respect Quality Service(RQS)')

    local_image_path = "/home/humayun/myproject/static/images/Logo.png"  
    p.drawImage(local_image_path, 50, 730, width=50, height=50)
 
   
    p.setFont("Helvetica-Bold", 12)
    p.setFillColorRGB(0, 0, 0)
    p.drawString(400,650, f'TO:{user_address.full_name}')
    p.drawString(400, 630, f'Date: {current_datetime}')

    p.drawString(400,610, f'invoice#{current_datetime}/{invoice_number}')

    p.drawString(50,650, 'From:')
    p.drawString(50,630, 'ddealshop.com')
    p.drawString(50,610, 'Powered by mymeplus Technology') 

    p.drawString(50, 570, f'order key: {order_key}')
   
    p.drawString(50, 550, f'Total BDT {baskettotal:,.2f} ({basket.price_to_words(baskettotal)})')

# Set up column headings in the table
    col1 = 50
    col2 = 100
    col3 = 270
    col4 = 370
    col5 = 470

    p.drawString(col1, 520, 'PID')
    p.drawString(col2, 520, 'Product Name')
    p.drawString(col3, 520, 'Unit Price')
    p.drawString(col4, 520, 'Quantity')
    p.drawString(col5, 520, 'Total Price')

    row_height = 30
    y_position = 490

    for item in basket:
        product_id = str(item.get('product_id', ''))
        product_title = item.get('product', {}).title
        unit_price = str(item.get('price', ''))
        quantity = str(item.get('qty', ''))
        total_price = str(item.get('qty', 0) * item.get('price', 0))

        p.setFont("Helvetica-Bold", 10)

        p.drawString(col1, y_position, product_id)
        p.drawString(col2, y_position, product_title)
        p.drawString(col3, y_position, unit_price)
        p.drawString(col4, y_position, quantity)
        p.drawString(col5, y_position, total_price)
        y_position -= row_height
    

    p.setFont("Helvetica-Bold", 12)
    p.setFillColorRGB(0,0,255)
    p.drawString(50,320, "Terms and Conditions:")

    p.setFont("Helvetica-Bold", 9)
    p.setFillColorRGB(0,0,0)

    x_position=50
    y_position_2=300

    terms_and_conditions = [

        "1. Payment Terms: Payment is due upon receipt of this invoice.",
        "2. Product Returns and Refunds: Our return policy allows for returns within 3 days of the purchase date",
        "   - returned items must be in their original condition and packaging.",
        "3. Shipping and Delivery:",
        "   - Delivery times are estimates and may vary based on location and other factors.",
        "   - We are not responsible for delays or issues caused by third-party shipping carriers.",
        "4. Product Warranty:",
        "   - Our products come with a standard warranty. Please refer to our warranty policy for details.",
        "5. Privacy Policy:",
        "   - We respect your privacy and handle your personal information securely. Refer to our Privacy Policy for details.",
        "6. Customer Support:",
        "   - For any inquiries or assistance, please contact our customer support team.",
        "7. Governing Law:",
        "   - This invoice and any disputes arising from it shall be governed by the laws of the country.",
    ]
   
    for line in terms_and_conditions:
        p.drawString(x_position, y_position_2, line)
        y_position_2 -= 14

    p.setFont("Helvetica-Bold", 16)
    p.setFillColorRGB(0,0,255)
    p.drawString(200,70, "Happy Shopping:")

    p.line(180,55, 340,55)
    p.line(180,50, 340,50)
  
    p.showPage()
    p.save()
    buffer.seek(0)
    pdf_content = buffer.getvalue()

    pdf_content = response.content
    logger = logging.getLogger(__name__)

    try:
        email_body = """Thank you for your order. Please see attached your invoice.
        Please note that the invoice doesn't include the delivery charge.
        Wish you best of luck.
        Happy Shopping
        """
        to_email = email
        from_email=settings.DEFAULT_FROM_EMAIL
        email = EmailMessage(
            "Your invoice",
            email_body,
            from_email,
            [to_email],
            reply_to=[settings.DEFAULT_FROM_EMAIL],
            headers={"Message-ID": "foo"},
            )      
        buffer.seek(0)  
        email.attach('invoice.pdf', buffer.read(), 'application/pdf')
        email.send()

        if request.method == 'POST':
            delivery_charge = request.POST.get('deliveryCharge')  # from ajax call in checkout.html
            print('delivery charge', delivery_charge)

            if Order.objects.filter(order_key=order_key).exists():
                print('Order with the same key already exists')
                pass
            else:
                order = Order.objects.create(
                    user_id=user_id,  
                    delivery_option=delivery_charge,              
                    full_name=user_address.full_name,
                    phone=user_address.phone,
                    post_code=user_address.postcode,
                    address1=user_address.address_line,
                    address2=user_address.address_line2,
                    city=user_address.town_city,
                    total_paid=baskettotal,
                    order_key = order_key,
                    created = datetime.now(),
                    status = 'pending'           
                
                )
                buffer.seek(0)
                pdf_content = ContentFile(buffer.read(), name='invoice.pdf')  
                order.invoice_pdf.save('invoice.pdf', pdf_content, save=True) 
      
                order_id = order.pk
                print('Order created:', order)
            try:
                for item in basket:
                    OrderItem.objects.create(
                        order_id=order_id,
                        product=item['product'],
                        price=item['price'],
                        quantity=item['qty'],
                        # size=item['size'],
                      
                    )
                basket.clear()
                phone_number = '+8801743800705'
                message = f"Mr {request.user.username} has created an order."
                send_sms(tenant=request.tenant, phone_number=phone_number, message=message)  
                
                return JsonResponse({
                    "order_id": order.id,
                    "message": "OrderItems created successfully!"
                })
               
            except InvalidOperation as e:
                print(f"Error creating OrderItem: {e}")
                return HttpResponse("Error creating OrderItem.")
            
      
        return render(request,'payment/orderplaced.html' )      
    
    except BadHeaderError as e:
        logger.error(f'Error sending email: {e}') 
    return render(request,'payment/orderplaced.html' )  

   

def send_test_email(request):
    basket = Basket(request)
    audio_files = AudioModel.objects.all()
    current_date = datetime.now().strftime('%Y-%m-%d')    
    logger = logging.getLogger(__name__)   
    User = get_user_model()
    user = User.objects.get(pk=request.user.id)
    if user.is_authenticated:
        to_email = user.email

    try:
     
        from_email=settings.DEFAULT_FROM_EMAIL
        email = EmailMessage(
            "Hello",
            "Body goes here: this is finally happen",
            from_email,
            [user.email],       
            reply_to=[settings.DEFAULT_FROM_EMAIL],
            headers={"Message-ID": "foo"},
            )
        email.send()        

    except BadHeaderError as e:
        logger.error(f'Error sending email: {e}')
    return HttpResponse("email send successfully") 



@login_required
def BasketView(request):
    basket = Basket(request)
    total = str(basket.get_total_price())
    total = total.replace('.', '')
    total = int(total)

    return render(request, 'payment/payment_form.html')

    # stripe.api_key = settings.STRIPE_SECRET_KEY
    # intent = stripe.PaymentIntent.create(
    #     amount=total,
    #     currency='bdt',
    #     metadata={'userid': request.user.id}
    # )

    # return render(request, 'payment/payment_form.html', {'client_secret': intent.client_secret, 
    #                                                         'STRIPE_PUBLISHABLE_KEY': os.environ.get('STRIPE_PUBLISHABLE_KEY')})


@csrf_exempt
def stripe_webhook(request):
    from orders.views import payment_confirmation
    payload = request.body
    event = None
    try:
        event = stripe.Event.construct_from(
            json.loads(payload), stripe.api_key
        )
    except ValueError as e:
        print(e)
        return HttpResponse(status=400)

    # Handle the event
    if event.type == 'payment_intent.succeeded':
        payment_confirmation(event.data.object.client_secret)
    else:
        print('Unhandled event type {}'.format(event.type))
    return HttpResponse(status=200)



class checkout(TemplateView):
   template_name = "payment/check_out.html"
   model =Address,AudioModel
    
   grandTotalPrice = 0 

   def get_context_data(self, **kwargs): 
        context = super().get_context_data(**kwargs)
        audio_files = AudioModel.objects.all()           
        User = get_user_model()
        user = User.objects.get(pk=self.request.user.id)
        if user.is_authenticated:           
            context['customer_address'] =Address.objects.filter(customer=user)
        else:
            message_text= messages.warning(self.request, 'Please log in before checking out!')
            context['customer_address'] = message_text
       
        basket = Basket(self.request)
        context['total_price'] = basket.get_total_price()
        context['order_key'] = str(uuid.uuid4()) 
        context['audio_files'] = audio_files       

        return context
 

def confirm_address(request):
    pass

def process_order(request):
    pass