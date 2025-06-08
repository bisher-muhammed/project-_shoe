from django.urls import path, include

urlpatterns = [
    # Modular includes
    path('auth/', include('user.urls.auth_urls')),
    path('dashboard/', include('user.urls.profile_urls')),
    path('address/', include('user.urls.address_urls')),
    path('order_list/', include('user.urls.order_urls')),
    path('wishlist/', include('user.urls.wishlist_urls')),
    path('shop/', include('user.urls.shop_urls')),
]
