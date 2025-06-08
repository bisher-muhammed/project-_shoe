
from django.urls import path
from user.views import order_views as views 


urlpatterns = [
    path('order_list/',views.order_list, name='order_list'),
    path('view_order/<int:order_id>/',views.view_order, name='view_order'),
    path('cancel_order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('return_order/<int:order_id>/', views.return_order, name='return_order'),
]
