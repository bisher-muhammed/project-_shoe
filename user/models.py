from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.contrib.auth.models import User
from adminapp.models import *




class AddressUS(models.Model):
    first_name = models.CharField(max_length=400, null=True, blank=True)
    last_name = models.CharField(max_length=400, null=True, blank=True)
    address_1 = models.CharField(max_length=255)
    city = models.CharField(max_length=200)
    state = models.CharField(max_length=255)
    zipcode = models.IntegerField()
    user_profile = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='addresses')
    is_default = models.BooleanField(default=False)

    def __str__(self):
         return f"{self.first_name} {self.last_name}, {self.address_1}, {self.city}, {self.state}, {self.zipcode}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='media/user', blank=True, null=True)
    address = models.ForeignKey(AddressUS, on_delete=models.SET_NULL, null=True,blank=True )
    wishlist = models.ManyToManyField(Product, related_name='wishlist_items')
    status = models.CharField(max_length=10,default='New')
    last_wallet_update_timestamp = models.DateTimeField(null=True, blank=True)


    def __str__(self):
        return self.user.username
class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, related_name='wishlists')

    def __str__(self):
        return f"Wishlist for {self.user.username}"    


class Wallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Wallet for {self.user_profile.user.username}"
    

    
    

