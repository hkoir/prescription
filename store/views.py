from django.shortcuts import get_object_or_404, render

from .models import Category, Product
from django.views.generic import ListView

from .models import Review,AudioModel,AudioModel
from .forms import CompanyReviewForm
from django.shortcuts import redirect
from .forms import ReviewForm
from django.http import JsonResponse



def welcome_message(request):
    audio_files=AudioModel.objects.all()
    return render(request, 'store/welcome_page.html', {'audio_files':audio_files})


def product_all(request):
   # products = Product.objects.prefetch_related("product_image").filter(is_active=True).order_by('-id') 
    products = Product.objects.prefetch_related("product_image").all().order_by('-id')
    categories = Category.objects.all()
    audio_files= AudioModel.objects.all()
    product_stars = []
    
    for product in products:
        product.sale_percentage = ((product.regular_price - product.discount_price) / product.regular_price) * 100
        reviews = product.reviews.all()
        if reviews:
            total_rating = sum(review.rating for review in reviews)
            average_rating = total_rating / len(reviews)
            product.stars = get_stars(average_rating)   
            product_stars.append(product.stars)        
        else:
            product.stars = None  # Set stars to None if there are no reviews for the product          
    return render(request, "store/index.html", {'categories': categories, 'products': products,'product_stars':product_stars,'audio_files':audio_files})



def get_stars(rating):
    full_stars = int(rating)
    half_stars = 1 if rating - full_stars >= 0.5 else 0
    empty_stars = 5 - full_stars - half_stars
    return '★' * full_stars + '½' * half_stars + '☆' * empty_stars


def product_reviews(request, slug):  
    product = get_object_or_404(Product, slug=slug, is_active=True)
    reviews = Review.objects.filter(product=product)

    if reviews:
        total_rating = sum(review.rating for review in reviews)
        average_rating = total_rating / len(reviews)
        product.stars = get_stars(average_rating)
    else:
        product.stars = None     
   

    return render(request, "store/product_reviews.html", {'product': product, 'reviews': reviews})


def category_list(request, category_slug=None):
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category)  

    for product in products:
        product.sale_percentage = ((product.regular_price - product.discount_price) / product.regular_price) * 100
        reviews = product.reviews.all()
        if reviews:
            total_rating = sum(review.rating for review in reviews)
            average_rating = total_rating / len(reviews)
            product.stars = get_stars(average_rating)           
        else:
            product.stars = None 

    return render(request, "store/category.html", {"category": category, "products": products})

# def product_detail(request, slug):
#     product = get_object_or_404(Product, slug=slug, is_active=True) 
#     specifications = product.productspecificationvalue_set.all()
#     reviews = product.reviews.all()
#     if reviews:
#         total_rating = sum(review.rating for review in reviews)
#         average_rating = total_rating / len(reviews)
#         product.stars = get_stars(average_rating)           
#     else:
#         product.stars = None   
   
#     return render(request, "store/single.html", {"product": product, "specifications": specifications})
    


from .models import Product, AudioModel

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    specifications = product.productspecificationvalue_set.all()
    audio_files = AudioModel.objects.all()  # Fetch all audio files

    product.sale_percentage = ((product.regular_price - product.discount_price) / product.regular_price) * 100

    success_audio_url = None
    failure_audio_url = None

    for audio in audio_files:
        if audio.success_audio:
            success_audio_url = audio.success_audio.url
        else:
            print("no success audio")
        if audio.failure_audio:
            failure_audio_url = audio.failure_audio.url
        else:
            print("no failure audio")

    reviews = product.reviews.all()
    if reviews:
        total_rating = sum(review.rating for review in reviews)
        average_rating = total_rating / len(reviews)
        product.stars = get_stars(average_rating)
    else:
        product.stars = None

    return render(request, "store/single.html", {"product": product, "specifications": specifications, 'success_audio_url': success_audio_url, 'failure_audio_url': failure_audio_url})




class ProductListView(ListView):
    model = Product
    template_name = 'store/product_list.html'  
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()  
        context['products'] = Product.objects.all()  
             
        return context
  


# def search(request):
#     query = request.GET.get('q')
#     results = Product.objects.filter(title__icontains=query).order_by('-id') if query else Product.objects.none()   
#     return render(request, 'store/search.html', {'results': results, 'query': query})

from fuzzywuzzy import fuzz

def search(request):

    query = request.GET.get('q')
    predefined_answers = {
        "What is the product return policy?": "Our product return policy allows customers to return products within 30 days of purchase.",
        "How can I track my order?": "You can track your order by logging into your account and visiting the 'Order History' section.",
        "What payment methods do you accept?": "We accept all major credit cards and PayPal for payment.",
        # Add more predefined questions and answers here
    }

    answer = None
    for predefined_question, predefined_answer in predefined_answers.items():
        if fuzz.partial_ratio(predefined_question.lower(), query.lower()) > 80:
            answer = predefined_answer
            break

    if answer:
        return render(request, 'store/search_new.html', {'answer': answer, 'query': query})
    else:
        results = Product.objects.filter(title__icontains=query).order_by('-id') if query else Product.objects.none()
        for result in results:
            result.sale_percentage = ((result.regular_price - result.discount_price) / result.regular_price) * 100
        return render(request, 'store/search_new.html', {'results': results, 'query': query})



def navbar(request):
     products = Product.objects.prefetch_related("product_image").filter(is_active=True)  
     categories = Category.objects.all()  
     return render(request, "code4Edu.html", {'categories': categories, 'products': products})

   


def submit_review(request, slug):
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
    return render(request, 'store/submit_review.html', {'form': form})


def company_review(request):
    form = CompanyReviewForm()
    if request.method == 'POST':
        form = CompanyReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user 
            # Set the user here if needed
            review.save()
            # Handle successful form submission
            return redirect('store:store_home')
    context = {'form': form}
    return render(request, 'company_review.html', context)    
    
  
def toggle_like(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user in product.likes.all():
        product.likes.remove(request.user)
        liked = False
    else:
        product.likes.add(request.user)
        liked = True
    likes_count = product.likes.count()
    return JsonResponse({'liked': liked, 'likes_count': likes_count})
    
# from django.shortcuts import render, redirect
# from store.forms import ProductForm,CategoryFormSet,ProductTypeFormSet, ProductSpecificationFormSet,ProductSpecificationValueFormSet, ProductImageFormSet, ProductVideoFormSet

# def create_product(request):
#     if request.method == 'POST':
#         product_form = ProductForm(request.POST, request.FILES)
#         category_formset = CategoryFormSet(request.POST, prefix='categories')
#         product_type_formset = ProductTypeFormSet(request.POST, prefix='categories')
#         product_specification_formset = ProductSpecificationFormSet(request.POST, prefix='specifications')
#         product_specification_value_formset = ProductSpecificationValueFormSet(request.POST, prefix='values')
#         product_image_formset = ProductImageFormSet(request.POST, request.FILES, prefix='images')
#         product_video_formset = ProductVideoFormSet(request.POST, request.FILES, prefix='videos')
       

#         if product_form.is_valid() and product_formset.is_valid() and product_image_formset.is_valid() and product_video_formset.is_valid():
#             product = product_form.save()
#             product_instances = product_formset.save(commit=False)
#             for instance in product_instances:
#                 instance.product = product
#                 instance.save()

#             for form in product_image_formset:
#                 if form.is_valid():
#                     image_instance = form.save(commit=False)
#                     image_instance.product = product
#                     image_instance.save()

#             for form in product_video_formset:
#                 if form.is_valid():
#                     video_instance = form.save(commit=False)
#                     video_instance.product = product
#                     video_instance.save()

#             return redirect('store:store_home')  # Replace with the URL name of your success page
#     else:
#         product_form = ProductForm()
#         product_formset = ProductSpecificationFormSet(prefix='specifications')
#         product_image_formset = ProductImageFormSet(prefix='images')
#         product_video_formset = ProductVideoFormSet(prefix='videos')

#     return render(request, 'store/create_product.html', {'product_form': product_form, 'product_formset': product_formset, 'product_image_formset': product_image_formset, 'product_video_formset': product_video_formset})


# from store.forms import ProductForm



# from django.shortcuts import render, redirect
# from .forms import ProductForm
# from .models import Product, ProductSpecification, ProductImage, ProductVideo

# def create_product(request):
#     if request.method == 'POST':
#         form = ProductForm(request.POST, request.FILES)
#         if form.is_valid():
#             product = form.save(commit=False)
#             product.save()

#             # Handle product specifications
#             spec_name = form.cleaned_data['specification_name']
#             spec_value = form.cleaned_data['specification_value']
#             if spec_name and spec_value:
#                 specification = ProductSpecification.objects.create(
#                     product=product,
#                     name=spec_name,
#                 )
#                 specification.save()

#             # Handle product images
#             if 'image' in request.FILES:
#                 for image_file in request.FILES.getlist('image'):
#                     image = ProductImage.objects.create(
#                         product=product,
#                         image=image_file,
#                     )
#                     image.save()

#             # Handle product videos
#             if 'video' in request.FILES:
#                 for video_file in request.FILES.getlist('video'):
#                     video = ProductVideo.objects.create(
#                         product=product,
#                         video=video_file,
#                     )
#                     video.save()

#             return redirect('store:store_home')  # Redirect to a success page
#     else:
#         form = ProductForm()

#     return render(request, 'store/create_product.html', {'form': form})


# def product_success_view(request):
#     return render(request, 'product_success.html')  # Success page template


from django.shortcuts import render, redirect
from .forms import ProductForm,ProductImageForm
from .models import Product, ProductSpecification, ProductImage, ProductVideo

def create_product(request):
    if request.method == 'POST':
        form = ProductImageForm(request.POST, request.FILES)
        if form.is_valid():
           image = form.save(commit=False)
           image.save()
        return redirect('store:store_home')  # Redirect to a success page
    else:
        form = ProductImageForm()

    return render(request, 'store/create_product.html', {'form': form})