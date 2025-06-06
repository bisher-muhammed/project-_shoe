from django.urls import path
from adminapp.views import product_views as views

urlpatterns = [
    path('add_product/', views.add_product, name='add_product'),

    path('admin_product_list/', views.admin_product_list, name='admin_product_list'),
    path('activate_product/<int:product_id>/', views.activate_product, name='activate_product'),
    path('deactivate_product/<int:product_id>/', views.deactivate_product, name='deactivate_product'),
    path('edit_product/<int:product_id>/', views.edit_product, name='edit_product'),

    path('offer_product/', views.offer_product, name='offer_product'),
]

