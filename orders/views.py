from django.http.response import JsonResponse
from django.shortcuts import render,redirect
from basket.basket import Basket
from orders.models import Order, OrderItem
import uuid
from decimal import Decimal
from django.contrib.auth import get_user_model      
        
from django.http import JsonResponse

from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render
from .forms import OrderItemForm
from django.forms import modelformset_factory
from orders.models import OrderItem,Order
from store.models import Product
from accounts.models import Address
from django.http import HttpResponse, HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.admin.views.decorators import user_passes_test 

from payment.views import generate_invoice

OrderItemFormSet = formset_factory(OrderItemForm, extra=0)
from django.core.files.base import ContentFile

import logging
from datetime import datetime
from decimal import InvalidOperation
from django.core.files.base import ContentFile


logger = logging.getLogger(__name__)

def add(request):   
    basket = Basket(request)    
    user_id = request.user.id
    baskettotal = basket.get_total_price()    
    order_key = str(uuid.uuid4())       

    User = get_user_model()
    user = User.objects.get(pk=request.user.id)
    if user.is_authenticated:        
        try:
             user_address = Address.objects.filter(customer=user).first()
        except ObjectDoesNotExist:
            print('User address not found')
            return HttpResponse("User address not found")

    if request.method == 'POST':
        delivery_charge = request.POST.get('deliveryCharge')  # from ajax call in checkout.html
        print('delivery charge', delivery_charge)

        if Order.objects.filter(order_key=order_key).exists():
            print('Order with the same key already exists')
            pass
        else:

            order = Order.objects.create(
                user_id=user_id,
             
                full_name=user_address.full_name,
                phone=user_address.phone,
                post_code=user_address.postcode,
                address1=user_address.address_line,
                address2=user_address.address_line2,
                city=user_address.town_city,
                total_paid=baskettotal,
                order_key = order_key,
                created = datetime.now()             
              
            )

            
            order_id = order.pk
            print('Order created:', order)
        try:
            for item in basket:
                OrderItem.objects.create(
                    order_id=order_id,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['qty']
                )
            print('OrderItems created successfully!')
            return HttpResponse("OrderItems created successfully!")
        except InvalidOperation as e:
            print(f"Error creating OrderItem: {e}")
            return HttpResponse("Error creating OrderItem.")
        
    basket.clear()
    return render(request,'payment/orderplaced.html' )


def order_item(request):
    user_id = request.user.id 
    order_items = OrderItem.objects.filter(order__user__id=user_id)   
    User = get_user_model()
    user = User.objects.get(pk=user_id) 
    user_name = user.username    

    context = {
        'order_items': order_items,
        'user_name': user_name,            
    }
    return render(request, 'orders/order_item.html', context)

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Prefetch


@staff_member_required
def all_order_items(request):
    orders_qs = Order.objects.all()
    paginator = Paginator(orders_qs, 5)         
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)
    return render(request, 'orders/all_order_items.html', {'orders': orders})


@staff_member_required
def order_detail(request, order_id):  
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related(
            Prefetch('items__product__product_image')  # prefetch images too
        ),
        id=order_id
    )
    items = order.items.select_related('product').all()
    return render(request, 'orders/order_detail.html', {'order': order, 'items': items})







# Below function not success yet, need troubleshooting. finally crud with modal has been develped to update
@user_passes_test(lambda u: u.is_staff)
def update_delivery_status(request):
    OrderItemFormSet = modelformset_factory(OrderItem, form=OrderItemForm, extra=0)
    queryset = OrderItem.objects.exclude(delivery_status='Delivered')
    if request.method == 'POST':
        formset = OrderItemFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.save()
            return redirect('accounts:dashboard')
        else:
            print(formset.errors)
            print("Instances not saved properly.")
    else:
        formset = OrderItemFormSet(queryset=queryset)
    return render(request, 'orders/delivery_status.html', {'formset': formset})


# Below function not success yet, need troubleshooting

from django.shortcuts import get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def update_delivery_confirmation(request, item_id):
    if request.method == 'POST':
        confirmation_status = request.POST.get('delivery_confirmation') 
        order_item_obj = get_object_or_404(OrderItem, id=item_id)
        order_item_obj.confirmation_status = confirmation_status
        order_item_obj.save()      

        return redirect('orders:all-order-items') 
    return render(request, 'orders/order_item.html')


def payment_confirmation(data):
    Order.objects.filter(order_key=data).update(billing_status=True)


def user_orders(request):
    user_id = request.user.id
    orders = Order.objects.filter(user_id=user_id).filter(billing_status=True)
    return orders



@user_passes_test(lambda u: u.is_staff)
def order_crud_read(request):
    order_items_list = OrderItem.objects.all().order_by('-id')  
    paginator = Paginator(order_items_list, 5) 
    page_number = request.GET.get('page')
    order_items = paginator.get_page(page_number)
    context = {
        'order_items': order_items,
    }
    return render(request, 'orders/order_crud.html', context)



@user_passes_test(lambda u: u.is_staff)
def order_crud_update(request, id):
    if request.method == 'POST':
        product_title = request.POST.get('product')
        quantity = request.POST.get('quantity')
        price = request.POST.get('price')
        delivery_status = request.POST.get('delivery_status')
        confirmation_status = request.POST.get('confirmation_status')

        product_obj = get_object_or_404(Product, title=product_title)
        order_item_obj = get_object_or_404(OrderItem, id=id)

        order_item_obj.product = product_obj
        order_item_obj.quantity = quantity
        order_item_obj.price = price
        order_item_obj.delivery_status = delivery_status
        order_item_obj.confirmation_status = confirmation_status
        order_item_obj.save()

        return redirect('orders:order_crud_read') 
    return render(request, 'orders/order_crud.html')
   


@user_passes_test(lambda u: u.is_staff)
def order_crud_delete(request,id):
    order_items = OrderItem.objects.filter(id=id)
    order_items.delete()
    context={
        'order_items':order_items
    }
    return redirect('orders:order_crud_read') 


# add is not required here as ecommerce adding product is difficult from here
@user_passes_test(lambda u: u.is_staff)
def order_crud_add(request):       
    return render(request, 'orders/order_crud.html')


from store.forms import ReviewForm

def product_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)    
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()          
            return redirect('store:company_review')
    else:
        form = ReviewForm()
    
    return render(request, 'orders/submit_product_review.html', {'form': form})