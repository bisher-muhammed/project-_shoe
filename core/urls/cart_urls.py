from django.urls import path
from core.views import cart_views as views  # Adjust if your cart-related views are elsewhere

urlpatterns = [
    path('core/add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('add-to-cart-from-wishlist/<int:product_id>/', views.add_to_cart_from_wishlist, name='add_to_cart_from_wishlist'),
    path('cart_list/', views.cart_list, name='cart_list'),
    path('cart_update/<int:cart_item_id>/', views.cart_update, name='cart_update'),
    path('remove_cart/<int:cart_item_id>/', views.remove_cart, name='remove_cart'),
    path('clear_cart/', views.clear_cart, name='clear_cart'),
    path('calculate_subtotal/', views.calculate_subtotal, name='calculate_subtotal'),
]
