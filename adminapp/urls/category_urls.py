# adminapp/urls/category_urls.py

from django.urls import path
from adminapp.views import category_views as views

urlpatterns = [
    path('admin_category/', views.admin_category, name='admin_category'),
    path('block_category/<int:category_id>/', views.block_category, name='block_category'),
    path('unblock_category/<int:category_id>/', views.unblock_category, name='unblock_category'),
    path('edit_category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('category_offer/', views.category_offer, name='category_offer'),
]
