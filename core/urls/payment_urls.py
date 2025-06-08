from django.urls import path
from core.views import payment_views as views


urlpatterns = [

    path('checkout/',views.checkout,name='checkout'),
    path('placeorder/',views.placeorder,name='placeorder'),
    path('core/payments/<int:order_id>/',views.payments, name='payments'),
    path('cash_on_delivery/<int:order_id>/',views.cash_on_delivery,name='cash_on_delivery'),
    path('core/order_confirmed/<int:order_id>/',views.order_confirmed, name='order_confirmed'),
    path('confirm_razorpay_payment/<int:order_id>/', views.confirm_razorpay_payment, name='confirm_razorpay_payment'),
    path('wallet_pay/<int:order_id>/', views.wallet_pay, name='wallet_pay'),

]
