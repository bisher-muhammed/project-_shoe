from django.urls import path
from .import views


urlpatterns = [
    path('',views.home,name='home'),

    path('otp_page/',views.otp_page,name='otp_page'),
    path('login_view/', views.login_view, name='login_view'),
    path('signup_view/',views.signup_view, name='signup_view'),
    path('send_otp/',views.send_otp, name='send_otp'),
    path('verify_otp/',views.verify_otp,name='verify_otp'),
    # path('otp_verification/',views.otp_verification, name='otp_verification'),
    path('logout_view/',views.logout_view, name='logout_view'),
    path('product_list/', views.product_list, name='product_list'),
    path('product_detials/<int:product_id>/',views.product_detials, name='product_detials'),
    path('product_list/',views.size_color_options,name='size_color_options'),
    path('resend_otp/',views.resend_otp, name='resend_otp'),
    path('add_address',views.add_address, name='add_address'),
    path('dashboard/',views.view_profile, name='view_profile'),
    path('dashboard/change-image/',views.change_image_view, name='change_image_view'),
    path('address/',views.addresses, name='addresses'),
    path('address/<int:address_id>/set_default/',views.set_default_address, name='set_default_address'),
    path('order_list/',views.order_list, name='order_list'),
    path('view_order/<int:order_id>/',views.view_order, name='view_order'),
    path('cancel_order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('return_order/<int:order_id>/', views.return_order, name='return_order'),
    path('add_wishlist/<int:product_id>/', views.add_wishlist, name='add_wishlist'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('delete_wishlist_item/<int:product_id>/', views.delete_wishlist_item, name='delete_wishlist_item'),
    path('wallet/', views.wallet, name='wallet'),
    # path('forgot_password/', views.forgot_password, name='forgot_password'),
    # path('email_valid/', views.email_valid,name='email_valid'),
    path('shop/',views.shop_lists,name='shop_lists'),
    # path('reset_password/',views.reset_password,name='reset_password')
    path('forgot_password/',views.forgot_password,name='forgot_password'),
    path('confirm_password/',views.confirm_password,name='confirm_password'),
    path('profile_forget_password/<int:user_id>/',views.profile_forget_password,name='profile_forget_password'),
    path('confrim_password/',views.profile_confrim_password,name='profile_confrim_password'),   

    # path('reason_view/<int:order_id>/', views.reason_view, name='reason_view'),
    path('filter/<str:category_name>/',views. filter_products_by_category, name='filter_products_by_category'),
    path('filter_brand/<str:brand_name>/',views. filter_products_by_brand, name='filter_products_by_brand'),
    path('about/',views.about,name='about'),
    path('contact/',views.contact,name='contact')

    



    

]
