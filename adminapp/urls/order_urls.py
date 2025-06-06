# myapp/order_urls.py

from django.urls import path
from adminapp.views import order_views as views


urlpatterns = [
    path('admin_order/', views.admin_order, name='admin_order'),
    path('admin_order_view/<int:order_id>/', views.view_order, name='admin_order_view'),
    path('update_order_status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('salesreport/', views.salesreport, name='salesreport'),
]
