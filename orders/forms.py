
from django import forms
from .models import OrderItem 
    

class OrderItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(OrderItemForm, self).__init__(*args, **kwargs)
        self.fields['delivery_status'].queryset = OrderItem.objects.exclude(delivery_status__icontains='Delivered')

    class Meta:
        model = OrderItem
        fields = ['order', 'product', 'price', 'quantity', 'delivery_status', 'confirmation_status', 'id']

