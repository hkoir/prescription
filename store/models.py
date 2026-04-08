from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey

from accounts.models import CustomUser




class Category(MPTTModel):  
    name = models.CharField(
        verbose_name=_("Category Name"),
        help_text=_("Required and unique"),
        max_length=255,
        unique=True,
    )
    slug = models.SlugField(verbose_name=_("Category safe URL"), max_length=255, unique=True)
    parent = TreeForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to="images/categories",default="images/default.png",) 
    alt_text = models.CharField(
        verbose_name=_("Alturnative text"),
        help_text=_("Please add alturnative text"),
        max_length=255,
        null=True,
        blank=True,
    )
    is_popular = models.BooleanField(default=False)
    is_hot_sale = models.BooleanField(default=False)
    is_regular = models.BooleanField(default=True) 

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def get_absolute_url(self):
        return reverse("store:category_list", args=[self.slug])

    def __str__(self):
        return self.name


class ProductType(models.Model): 
    name = models.CharField(verbose_name=_("Product Name"), help_text=_("Required"), max_length=255, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Product Type")
        verbose_name_plural = _("Product Types")

    def __str__(self):
        return self.name


class ProductSpecification(models.Model): 
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)# RESTRICT
    name = models.CharField(verbose_name=_("Name"), help_text=_("Required"), max_length=255)

    class Meta:
        verbose_name = _("Product Specification")
        verbose_name_plural = _("Product Specifications")

    def __str__(self):
        return self.name    

from django.core.exceptions import ValidationError
import uuid

def validate_max_words(value, max_words=100):
    words = value.split()
    if len(words) > max_words:
        raise ValidationError(f"Too many words! Maximum allowed is {max_words}.")

class Product(models.Model):       
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)# RESTRICT   
    category = models.ForeignKey(Category, related_name='products',on_delete=models.CASCADE) # RESTRICT
    title = models.CharField(
        verbose_name=_("title"),
        help_text=_("Required"),
        max_length=255,
    )
   
    product_code = models.CharField(
        verbose_name=_("Product Code"),
        max_length=20,
        unique=True,
        help_text=_("Unique product code identifier"),
        null=True,
        blank=True,
      
    )    

    description = models.TextField(verbose_name=_("description"), help_text=_("Not Required"), blank=True)
    slug = models.SlugField(max_length=255,unique=True)
    regular_price = models.DecimalField(
        verbose_name=_("Regular price"),
        help_text=_("Maximum 11999.99"),
        error_messages={
            "name": {
                "max_length": _("The price must be between 0 and 11999.99."),
            },
        },
        max_digits=10,
        decimal_places=2,
    )
    discount_price = models.DecimalField(
        verbose_name=_("Discount price"),
        help_text=_("Maximum 10999.99"),
        error_messages={
            "name": {
                "max_length": _("The price must be between 0 and 10999.99."),
            },
        },
        max_digits=10,
        decimal_places=2,
    )
    is_active = models.BooleanField(
        verbose_name=_("Product visibility"),
        help_text=_("Change product visibility"),
        default=True,
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    users_wishlist = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="user_wishlist", blank=True)
   
    qty =models.PositiveBigIntegerField(default=0)
    size_choices = (
        ('S', 'Small'),
        ('M', 'Medium'),
        ('L', 'Large'),
        ('XL', 'Extra Large'),
    )
    size = models.CharField(max_length=2, choices=size_choices, default='M')
    video = models.FileField(
        verbose_name=_("video"),
        help_text=_("Upload a product video"),
        upload_to="videos/",
        null=True,
        blank=True,)
    
    is_popular = models.BooleanField(default=False)
    is_hot_sale = models.BooleanField(default=False)
    is_regular = models.BooleanField(default=True)
    is_clothing = models.BooleanField(default=False)
    is_smart_watch = models.BooleanField(default=False)
    is_gps_tracker = models.BooleanField(default=False)
    is_bluetooth_tracker = models.BooleanField(default=False)
    is_mobile_accessories = models.BooleanField(default=False)
    is_safe_security = models.BooleanField(default=False)
    is_computer_accessories = models.BooleanField(default=False)
    is_offer = models.BooleanField(default=False)
    is_seller_product = models.BooleanField(default=False)
    is_dropshipping_bdshop = models.BooleanField(default=False)
    is_dropshipping_bd = models.BooleanField(default=False)


    likes = models.ManyToManyField(CustomUser, related_name='liked_products', blank=True)
    mini_description = models.TextField(verbose_name=_(" nini_description"), help_text=_("Not Required"),
        blank=True,
        validators=[validate_max_words])

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def save(self, *args, **kwargs):
        if not self.product_code:  
            # Example format: PRD-ABC12345
            prefix = "PRD"
            unique_part = uuid.uuid4().hex[:8].upper()
            self.product_code = f"{prefix}-{unique_part}"
            
            # Ensure uniqueness in case of rare collision
            while Product.objects.filter(product_code=self.product_code).exists():
                unique_part = uuid.uuid4().hex[:8].upper()
                self.product_code = f"{prefix}-{unique_part}"
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("store:product_detail", args=[self.slug])

    def __str__(self):
        return self.title


class ProductSpecificationValue(models.Model):  
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    specification = models.ForeignKey(ProductSpecification, on_delete=models.CASCADE) #RESTRICT
    value = models.CharField(
        verbose_name=_("value"),
        help_text=_("Product specification value (maximum of 255 words"),
        max_length=255,
    )

    class Meta:
        verbose_name = _("Product Specification Value")
        verbose_name_plural = _("Product Specification Values")

    def __str__(self):
        return self.value


class ProductImage(models.Model):   
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_image")
    image = models.ImageField(
        verbose_name=_("image"),
        help_text=_("Upload a product image"),
        upload_to="images/",
        default="images/default.png",
    )  

    alt_text = models.CharField(
        verbose_name=_("Alturnative text"),
        help_text=_("Please add alturnative text"),
        max_length=255,
        null=True,
        blank=True,
    )
    is_feature = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")


class ProductVideo(models.Model): 
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="product_Video")
    video = models.FileField(
        verbose_name=_("video"),
        help_text=_("Upload a product video"),
        upload_to="videos/",
        null=True,
        blank=True,)

    alt_text = models.CharField(
        verbose_name=_("Alturnative text"),
        help_text=_("Please add alturnative text"),
        max_length=255,
        null=True,
        blank=True,
    )
    is_feature = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Product Video")
        verbose_name_plural = _("Product Videos")





class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    text = models.TextField()
    rating = models.IntegerField()
    image_one = models.ImageField(upload_to='review_images/', blank=True, null=True)
    image_two = models.ImageField(upload_to='review_images/', blank=True, null=True)
    image_three = models.ImageField(upload_to='review_images/', blank=True, null=True)
    image_four = models.ImageField(upload_to='review_images/', blank=True, null=True)






class CompanyReview(models.Model):
    DELIVERY_QUALITY_CHOICES = (
        ('', 'Select an option'), 
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    )

    PAYMENT_QUALITY_CHOICES = (
         ('', 'Select an option'), 
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    )

    COMMUNICATION_QUALITY_CHOICES = (
         ('', 'Select an option'), 
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    )

    PRODUCT_QUALITY_CHOICES = (
         ('', 'Select an option'), 
        (1, 'Poor'),
        (2, 'Below Average'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    )

    delivery_quality = models.IntegerField(choices=DELIVERY_QUALITY_CHOICES)
    payment_quality = models.IntegerField(choices=PAYMENT_QUALITY_CHOICES)
    communication_quality = models.IntegerField(choices=COMMUNICATION_QUALITY_CHOICES)
    product_quality = models.IntegerField(choices=PRODUCT_QUALITY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    review_text = models.TextField(blank='', null=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)




class AudioModel(models.Model):       
    success_audio = models.FileField(upload_to='audio/', blank=True, null=True)  
    failure_audio = models.FileField(upload_to='audio/', blank=True, null=True)

    welcome_message = models.FileField(upload_to='audio/', blank=True, null=True)  
    account_create_success = models.FileField(upload_to='audio/', blank=True, null=True)
    request_for_logged_in = models.FileField(upload_to='audio/', blank=True, null=True)  
    logged_in_success = models.FileField(upload_to='audio/', blank=True, null=True)
    forget_password = models.FileField(upload_to='audio/', blank=True, null=True)  
    order_placed_success = models.FileField(upload_to='audio/', blank=True, null=True)
    hold_on_message = models.FileField(upload_to='audio/', blank=True, null=True)