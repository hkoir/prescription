from django.urls import path
from .views import ProductListView
from . import views

app_name = 'store'
 
from django.contrib.auth.decorators import user_passes_test
decorated_product_list_view = user_passes_test(lambda u: u.is_staff)(ProductListView.as_view())



urlpatterns = [
    path('', views.product_all, name='store_home'), 
    path('welcome-message', views.welcome_message, name='welcome-message'),  
    path('<slug:slug>', views.product_detail, name='product_detail'),
    path('shop/<slug:category_slug>/', views.category_list, name='category_list'),
    
    path('product-list/', ProductListView.as_view(), name='product-list'),
    path('search/', views.search, name='search'),

    path('submit_review/<slug:slug>', views.submit_review, name='submit_review'), # this is for product review form submit
    path('product_reviews/<slug:slug>', views.product_reviews, name='product_reviews'), # this is to read product review 
    path('company_review/', views.company_review, name='company_review'),# This is for submit company review form
   # path('read-company_reviews/', views.read_company_reviews, name='read-company-reviews'),# this need to implement to read company
     path('toggle-like/<int:product_id>/',views.toggle_like, name='toggle_like'),

] 
