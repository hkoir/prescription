from django import forms
from store.models import Review
from .models import CompanyReview

from django import forms
from store.models import Product, ProductSpecification, Category, ProductType, ProductSpecificationValue, ProductImage, ProductVideo
from django.forms.models import inlineformset_factory



class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['text', 'rating', 'image_one', 'image_two', 'image_three', 'image_four']

    text = forms.CharField(widget=forms.Textarea)
    rating = forms.IntegerField()
    image_one = forms.ImageField(required=False)
    image_two = forms.ImageField(required=False)
    image_three = forms.ImageField(required=False)
    image_four = forms.ImageField(required=False)



class CompanyReviewForm(forms.ModelForm):
    class Meta:
        model = CompanyReview
        fields = ['delivery_quality', 'payment_quality', 'communication_quality', 'product_quality']


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name','slug','parent']


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['title', 'description', 'slug', 'regular_price', 'discount_price', 'is_active', 'qty', 'size', 'video']

class ProductTypeForm(forms.ModelForm):
    class Meta:
        model = ProductType
        fields = ['name']

class ProductSpecificationForm(forms.ModelForm):
    class Meta:
        model = ProductSpecification
        fields = ['name']

class ProductSpecificationValueForm(forms.ModelForm):
    class Meta:
        model = ProductSpecificationValue
        fields = ['specification', 'value']

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_feature']

class ProductVideoForm(forms.ModelForm):
    class Meta:
        model = ProductVideo
        fields = ['video', 'alt_text', 'is_feature']
