from django.urls import path
from user.views import auth_views as views 

urlpatterns = [

    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('otp_page/', views.otp_page, name='otp_page'),
    path('login_view/', views.login_view, name='login_view'),
    path('signup_view/', views.signup_view, name='signup_view'),
    path('send_otp/', views.send_otp, name='send_otp'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('logout_view/', views.logout_view, name='logout_view'),
    path('resend_otp/', views.resend_otp, name='resend_otp'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('confirm_password/', views.confirm_password, name='confirm_password'),
]

