

from django.urls import path, include

urlpatterns = [
    path('auth/', include('adminapp.urls.auth_urls')),
    path('category/', include('adminapp.urls.category_urls')),
    path('products/', include('adminapp.urls.product_urls')),
    path('orders/', include('adminapp.urls.order_urls')),
    path('brands/', include('adminapp.urls.brand_urls')),
    path('users/', include('adminapp.urls.user_urls')),
    path('banner/', include('adminapp.urls.banner_urls')),
    path('variance/', include('adminapp.urls.variance_urls')),
]
