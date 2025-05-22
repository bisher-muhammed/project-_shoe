from pyexpat.errors import messages
from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.shortcuts import redirect
from adminapp.models import Product, ProductOffer, ProductSize, Size
from django.db.models import Sum
from user.models import AddressUS, Coupon
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.contrib import messages
from django.shortcuts import redirect


from django.db import models, transaction
from django.db.models import Sum

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    def update_total(self):
        total = self.cartitem_set.aggregate(total_price=Sum(models.F('quantity') * models.F('product__offer_price')))['total_price']
        self.total = total if total is not None else 0
        self.save()
        return self.total 

class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True, swappable=True)
    product_size = models.ForeignKey(ProductSize, on_delete=models.CASCADE, null=True, blank=True)

    def total_price(self):
        return self.quantity * self.product.offer_price

    def __str__(self):
        return f"{self.quantity} x {self.product.product_name} in order {self.cart}"

    def total_prices(self):
        return Sum(item.total_price() for item in self.cart.cartitem_set.all())

class Order(models.Model):
    STATUS = [
        ('New', 'New'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned'),
        ('pending', 'pending'),
    ]

    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    order_number = models.CharField(max_length=200)
    address = models.ForeignKey(AddressUS, on_delete=models.SET_NULL, blank=True, null=True)
    order_total = models.FloatField()
    status = models.CharField(max_length=100, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cart = models.ForeignKey(Cart, on_delete=models.SET_NULL, null=True, blank=True)
    order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    quantity = models.IntegerField(default=0)
    is_ordered = models.BooleanField(default=False) 


    def save(self, *args, **kwargs):
        
        self.order_value = self.calculate_order_value()

        # Handle cancellations or returns
        if self.status in ['Cancelled', 'Returned']:
            self.cancel_or_return_order()

        
        super().save(*args, **kwargs)

    def calculate_order_value(self):
        discount_amount = self.coupon.discount_amount if self.coupon else 0
        calculated_value = self.order_total - discount_amount
        return calculated_value
    

    def reduce_product_size_quantity(self):
        with transaction.atomic():
            for item in self.productorder_set.all():
                if item.size:
                    try:
                        product_sizes = ProductSize.objects.filter(product=item.product, size=item.size)
                        for product_size in product_sizes:
                            print(f"Before reduction - Product: {item.product}, Size: {item.size}, Quantity: {product_size.quantity}")

                            # Print information about item and product_size
                            print(f"Item details: {item}")
                            print(f"ProductSize details: {product_size}")

                            # Multiply the item quantity with the size quantity when reducing
                            reduction_quantity = item.quantity

                            # Ensure that the quantity doesn't go below zero
                            if product_size.quantity >= reduction_quantity:
                                product_size.quantity -= reduction_quantity
                            else:
                                product_size.quantity = 0

                            product_size.save() 

                            print(f"After reduction - Product: {item.product}, Size: {item.size}, Quantity: {product_size.quantity}")
                    except ObjectDoesNotExist:
                        print(f"No ProductSize found for Product: {item.product}, Size: {item.size}")
                    except MultipleObjectsReturned:
                        # Handle the case when multiple ProductSize instances are found
                        raise MultipleObjectsReturned(f"Multiple ProductSize instances found for Product: {item.product}, Size: {item.size}")

    def cancel_or_return_order(self):
    # Increase product sizes when an order is cancelled or returned
        if self.status in ['Cancelled', 'Returned']:
            order_items = ProductOrder.objects.filter(order=self)
            for item in order_items:
                if item.size:
                    product_size = ProductSize.objects.get(product=item.product, size=item.size)
                    product_size.quantity += item.quantity

                    # Save the changes to the product size
                    product_size.save()
                    print(f"Updated quantity for ProductSize {product_size.id} to {product_size.quantity}")

            print("Cancellation/Return process completed.")                

    


        
class ProductOrder(models.Model):
    quantity = models.IntegerField()
    product_price = models.FloatField()
    ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    address = models.ForeignKey(AddressUS, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Add the cart_item relationship
    cart_item = models.ForeignKey(CartItem, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.product.product_name} in order {self.order}, user {self.order.user}"

# @receiver(post_save, sender=ProductOrder)
# def update_size_quantity(sender, instance, **kwargs):
#     print("Signal received for ProductOrder:", instance.id)

#     # Print relevant information for debugging
#     print(f"Size in ProductOrder instance: {instance.size.name}")
#     print(f"Quantity in ProductOrder instance: {instance.quantity}")

#     # Update the quantity of the selected size when a ProductOrder is created
#     if instance.ordered and not instance.cart_item:
#         size = instance.size

#         if size is not None:
           

    

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=100,default='Cancelled')
    amount_paid = models.FloatField(default=0)
    status = models.CharField(max_length=100)
    discount = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def check_sufficient_balance(request, user_wallet, order_total_decimal, order_id):
        if user_wallet.balance < order_total_decimal:
            messages.error(request, 'Insufficient balance')
            return True  # Indicate insufficient balance

        return False  # Sufficient balance
    



    def __str__(self):
        return self.payment_method 
    

    

    

    