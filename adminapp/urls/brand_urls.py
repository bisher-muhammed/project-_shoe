from django.urls import path
from adminapp.views import brand_views as views

urlpatterns = [
    path('admin_brand/', views.admin_brand, name='admin_brand'),
    path('activate_brand/<int:brand_id>/', views.activate_brand, name='activate_brand'),
    path('deactivate_brand/<int:brand_id>/', views.deactivate_brand, name='deactivate_brand'),
    path('edit_brand/<int:brand_id>/', views.edit_brand, name='edit-brand'),
]

