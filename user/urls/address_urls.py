from django.urls import path
from user.views import address_views as views 

urlpatterns = [
    
    path('add_address',views.add_address, name='add_address'),
    path('address/',views.addresses, name='addresses'),
    path('address/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('address/<int:address_id>/set_default/',views.set_default_address, name='set_default_address'),
    path('address/edit/<int:address_id>/', views.edit_address, name='edit_address'),
]
