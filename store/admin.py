from django import forms
from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from .models import (
    Category,
    Product,
    ProductImage,
    ProductSpecification,
    ProductSpecificationValue,
    ProductType,
    ProductVideo,
    Review,
    CompanyReview
)

admin.site.register(Category, MPTTModelAdmin) 

class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    inlines = [
        ProductSpecificationInline,
      
    ]


class ProductImageInline(admin.TabularInline):
    model = ProductImage



class ProductSpecificationValueInline(admin.TabularInline):
    model = ProductSpecificationValue

class ProductVideoInline(admin.TabularInline):
    model = ProductVideo

class ProductReviewInline(admin.TabularInline):
    model = Review


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [
        ProductSpecificationValueInline,
        ProductImageInline,
        ProductVideoInline,
        ProductReviewInline,     
        
    ]



# class ProductInline(admin.TabularInline):
#     model = Product
#     extra = 1

# class CategoryAdmin(admin.ModelAdmin):
#     inlines = [ProductInline]





@admin.register(CompanyReview)
class CompanyReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'delivery_quality', 'payment_quality', 'communication_quality', 'product_quality','review_text')