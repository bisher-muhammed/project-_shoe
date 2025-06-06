from django.urls import path
from adminapp.views import banner_views  as views

urlpatterns = [
    # Coupon management
    path('coupon_management/', views.coupon_management, name='coupon_management'),
    path('block_coupon/<int:coupon_id>/', views.block_coupon, name='block_coupon'),
    path('unblock_coupon/<int:coupon_id>/', views.unblock_coupon, name='unblock_coupon'),

    # Banner management
    path('admin_banner/', views.admin_banner, name='admin_banner'),
    path('edit_banner/<int:banner_id>/', views.edit_banner, name='edit_banner'),
    path('banner_active/<int:banner_id>/', views.banner_active, name='banner_active'),
    path('banner_blocked/<int:banner_id>/', views.banner_blocked, name='banner_blocked'),
]
