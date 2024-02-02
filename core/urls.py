from django.urls import path
from.import views
from user.views import product_detials

 # Corrected import statement

urlpatterns = [
    # urls.py
    

   

# template

    

    path('core/add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),


    path('cart_list/',views.cart_list,name='cart_list'),
    path('home/',views.home,name='home'),
    path('cart_update/<int:cart_item_id>/', views.cart_update, name='cart_update'),
    path('remove_cart/<int:cart_item_id>/', views.remove_cart, name='remove_cart'),
    path('checkout/',views.checkout,name='checkout'),
    path('placeorder/',views.placeorder,name='placeorder'),
    path('core/payments/<int:order_id>/',views.payments, name='payments'),
    path('cash_on_delivery/<int:order_id>/',views.cash_on_delivery,name='cash_on_delivery'),
    path('core/order_confirmed/<int:order_id>/',views.order_confirmed, name='order_confirmed'),
    path('confirm_razorpay_payment/<int:order_id>/', views.confirm_razorpay_payment, name='confirm_razorpay_payment'),
    path('clear_cart/',views.clear_cart, name='clear_cart'),
    path('wallet_pay/<int:order_id>/',views.wallet_pay,name='wallet_pay'),
    path('add-to-cart-from-wishlist/<int:product_id>/', views.add_to_cart_from_wishlist, name='add_to_cart_from_wishlist'),
    path('calculate_subtotal/',views.calculate_subtotal,name='calculate_subtotal'),
    







    # path('get_discount_amount/',views.get_discount_amount, name='get_discount_amount'),
]
