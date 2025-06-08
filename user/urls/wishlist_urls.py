
from django.urls import path
from user.views import wishlist_views as views 


urlpatterns = [
    path('add_wishlist/<int:product_id>/', views.add_wishlist, name='add_wishlist'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('delete_wishlist_item/<int:product_id>/', views.delete_wishlist_item, name='delete_wishlist_item'),
]
