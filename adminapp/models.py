from datetime import date, datetime
from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from django.db.models import F, Sum, Max
from image_cropping import ImageRatioField, ImageCropField
from django.utils import timezone


class  Category(models.Model):
    category_name=models.CharField(100,null=True,blank=True)
    description=models.TextField()
    category_image=models.ImageField(upload_to='media/category', null=False, blank=False)
    is_blocked=models.BooleanField(default=False)


    def __str__(self):
        return self.category_name
    

class Brand(models.Model):
    brand_name=models.CharField(max_length=100,unique=True)
    brand_description =models.TextField(max_length=400)
    brand_image=models.ImageField(upload_to='media/brands', blank=True, null=True)
    is_active = models.BooleanField(default=True) 
    def __str__(self):
        return self.brand_name



class Size(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True) 
   


    def __str__(self):
        return self.name

class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    

    product_name = models.CharField(max_length=100)
    product_description = models.TextField(max_length=400)
    original_price = models.IntegerField(validators=[MinValueValidator(0)])
    offer_price = models.IntegerField(validators=[MinValueValidator(0)])
    
    product_img1 = models.ImageField(upload_to='media/product/img1', blank=False, null=False)
    product_img2 = models.ImageField(upload_to='media/product/img2', blank=False, null=False)
    product_img3 = models.ImageField(upload_to='media/product/img3', blank=False, null=False)
    
    sizes = models.ManyToManyField(Size, related_name='products', blank=True)
    colors = models.ManyToManyField(Color, related_name='products', blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.product_name
    
    
    @property
    def total_available_quantity(self):
        return sum(size.quantity for size in self.sizes.all())
    

    def get_best_offer(self):
        category_offers = Offer.objects.filter(category=self.category)
        product_offer = self.productoffer_set.first()

        best_category_offer = category_offers.aggregate(Max('percentage'))['percentage__max']

        if product_offer and (not best_category_offer or product_offer.percentage > best_category_offer):
            # If product offer exists and is greater than the best category offer
            return product_offer
        elif category_offers:
            # If category offers exist, return the best one
            return category_offers.filter(percentage=best_category_offer).first()
        else:
            # No offers exist
            return None

    
    

class Coupon(models.Model):
    coupon_code = models.CharField(max_length=50,unique=True)
    discount_amount = models.PositiveIntegerField()
    minimum_purchase = models.IntegerField(null=True, default=0)

    expiry_date= models.DateField()
    is_blocked=models.BooleanField(default=False)
    used_by = models.ManyToManyField(User, blank=True)
    

    def __str__(self):
        return self.coupon_code
    
# total_revenue = Product.objects.aggregate(total_revenue=Sum(F('offer_price') * F('cartitem.quantity')))['total_revenue']    


class Banner(models.Model):
    banner_img=models.ImageField(upload_to='media/banner/image',null=True,blank=True)
    subtitle=models.CharField(max_length=50,blank=True,null=True)
    title = models.CharField(max_length=50, blank=True, null=True) 
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return self.title
    


    
    # def calculate_days_difference(self):
    #     if self.created_at and self.expiry_date:
    #         if isinstance(self.expiry_date, date):
    #             now = timezone.now().date()
    #             self.days_difference = (self.expiry_date - now).days
    #             self.is_active = self.days_difference > 0
    #         else:
    #             raise ValueError("Invalid type for expiry_date. Expected datetime.date.")
    #     else:
    #         # Handle the case where either created_at or expiry_date is not set
    #         raise ValueError("Both created_at and expiry_date must be set.")

    #     # Print the details, including is_active status
    #     print(f"Banner: {self.title}, Expiry Date: {self.expiry_date}, Days Difference: {self.days_difference}, Is Active: {self.is_active}")


 


class Offer(models.Model):
    category = models.OneToOneField(Category, on_delete=models.CASCADE)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    expiry_date = models.DateField()
    is_expired = models.BooleanField(default=False) 
    
    def __str__(self):
        return f"Offer for {self.category.category_name}" 


class ProductOffer(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    expiry_date = models.DateField()
    is_expired = models.BooleanField(default=False) 

    def __str__(self):
        return f"Offer for {self.product.product_name}"
    

class ProductSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='productsizes')
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)    

    


    # @property
    # def available_stock(self):
    #     # Calculate and return the available stock based on your business logic
    #     # Subtract the quantity in the cart from the total quantity
    #     cart_quantity = self.product.cartitem_set.filter(size=self.size).aggregate(total_quantity=models.Sum('quantity'))['total_quantity'] or 0
    #     return max(0, self.quantity - cart_quantity)