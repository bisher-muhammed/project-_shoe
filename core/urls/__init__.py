from django.urls import path, include

urlpatterns = [
    path('cart/', include('core.urls.cart_urls')),
    path('payments/', include('core.urls.payment_urls')),
]
