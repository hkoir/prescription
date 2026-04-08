from .models import Category, Product


def categories(request):
    return {"categories": Category.objects.filter(level=0), 'products':Product.objects.all()}


# context_processors.py
from django.db.models import Avg
from .models import Product

def get_stars(rating):
    full_stars = int(rating)
    half_stars = 1 if rating - full_stars >= 0.5 else 0
    empty_stars = 5 - full_stars - half_stars
    return '★' * full_stars + '½' * half_stars + '☆' * empty_stars

def product_stars(request):
    products = Product.objects.all()
    for product in products:
        reviews = product.reviews.all()
        if reviews:
            total_rating = reviews.aggregate(Avg('rating'))['rating__avg']
            if total_rating:
                product.stars = get_stars(total_rating)
            else:
                product.stars = None
        else:
            product.stars = None
    return {'product_stars': product.stars}
