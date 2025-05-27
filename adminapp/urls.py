from django.urls import path
from .import views 

urlpatterns = [
    path('', views.admin_login, name='admin_login'),
    
    path('admin_home/', views.admin_home, name='admin_home'),
    path('admin_category/', views.admin_category, name='admin_category'),
    path('block_category/<int:category_id>/',views.block_category, name='block_category'),
    path('unblock_category/<int:category_id>/', views.unblock_category, name='unblock_category'),
    path('add_product/',views.add_product,name='add_product'),
    path('admin_brand/',views.admin_brand,name='admin_brand'),
    path('activate_brand/<int:brand_id>/', views.activate_brand, name='activate_brand'),
    path('deactivate_brand/<int:brand_id>/', views.deactivate_brand, name='deactivate_brand'),
    path('variance-management/', views.variance_management, name='variance_management'),
    path('edit_brand/<int:brand_id>/',views.edit_brand,name='edit-brand'),
    path ('edit_category/<int:category_id>/',views.edit_category,name='edit_category'),
    path('add-size/', views.add_size, name='add_size'),
    
    path('activate-size/<int:size_id>/', views.activate_size, name='activate_size'),
    path('deactivate-size/<int:size_id>/', views.deactivate_size, name='deactivate_size'),
    path('product_list/',views.product_list, name= 'product_list'),
    path('activate_product/<int:product_id>/', views.activate_product, name='activate_product'),
    path('deactivate_product/<int:product_id>/', views.deactivate_product, name='deactivate_product'),
    path('admin_userlist/', views.admin_userlist, name='admin_userlist'),
    path('activate_user/<int:user_id>/', views.activate_user, name='activate_user'),
    path('deactivate_user/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    path('edit_product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('admin_order/',views.admin_order,name='admin_order'),
    path('update_order_status/<int:order_id>/',views.update_order_status, name='update_order_status'),
    path('coupon_management/',views.coupon_management,name='coupon_management'),
    path('block_coupon/<int:coupon_id>/',views.block_coupon, name='block_coupon'),
    path('unblock_coupon/<int:coupon_id>/', views.unblock_coupon, name='unblock_coupon'),
    path('sales_statistics/',views.sales_statistics,name='sales_statistics'),
    path('admin_banner/', views.admin_banner, name='admin_banner'),
    path('edit_banner/<int:banner_id>/',views.edit_banner, name="edit_banner"),
    path('banner_active/<int:banner_id>/',views.banner_active,name='banner_active'),
    path('banner_blocked/<int:banner_id>/', views.banner_blocked, name='banner_blocked'),
   path('admin_order_view/<int:order_id>/',views.view_order, name='admin_order_view'),

    path('salesreport/',views.salesreport,name='salesreport'),
    path('category_offer/', views.category_offer, name='category_offer'),
    path('offer_product/',views.offer_product,name='offer_product'),
    path('admin_logout/', views.admin_logout,name='admin_logout')
    
]

