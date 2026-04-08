from django.urls import path
from . import views

app_name = 'orders'



urlpatterns = [
    path('add/', views.add, name='add'),
    path('order-item/', views.order_item, name='order-item'),
    
    path('update_delivery_status/', views.update_delivery_status, name='update_delivery_status'),
    path('order_crud_read/', views.order_crud_read, name='order_crud_read'),
    path('order_crud_add/', views.order_crud_add, name='order_crud_add'),
    path('order_crud_delete/<int:id>', views.order_crud_delete, name='order_crud_delete'),
    path('order_crud_update/<int:id>', views.order_crud_update, name='order_crud_update'),
    
    path('update_delivery_confirmation/<int:item_id>', views.update_delivery_confirmation, name='update_delivery_confirmation'),
    path('product-review/<slug:slug>', views.product_review, name='product-review'), 
   
 
    path('all-order-items/', views.all_order_items, name='all-order-items'),   
    path('<int:order_id>/', views.order_detail, name='order_detail'),
      
]
