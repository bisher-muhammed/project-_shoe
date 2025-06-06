from django.urls import path
from adminapp.views import auth_views as views


urlpatterns = [
    path('', views.admin_login, name='admin_login'),
    path('admin_home/', views.admin_home, name='admin_home'),
    path('sales_statistics/', views.sales_statistics, name='sales_statistics'),
    
    
    path('admin_logout/', views.admin_logout, name='admin_logout'),
]


