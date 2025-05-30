from django.contrib import admin
from. models import *
from core.models import Cart,CartItem
from user.models import AddressUS,Wallet
from core.models import ProductOrder,Order,Payment
import re



admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Size)
admin.site.register(Color)
admin.site.register(Product)
admin.site.register(Cart)
admin.site.register(Order)
admin.site.register(ProductOrder)
admin.site.register(CartItem)
admin.site.register(AddressUS)
admin.site.register(Coupon)
admin.site.register(Payment)
admin.site.register(Wallet)
admin.site.register(Banner)
admin.site.register(Offer)
admin.site.register(ProductSize)







