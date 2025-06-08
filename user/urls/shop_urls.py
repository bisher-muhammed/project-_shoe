from django.urls import path
from user.views import shop_views as views 

urlpatterns = [

    path('product_detials/<int:product_id>/',views.product_details, name='product_detials'),
    path('shop/',views.shop_lists,name='shop_lists'),
    path('filter/<str:category_name>/',views. filter_products_by_category, name='filter_products_by_category'),
    path('filter_brand/<str:brand_name>/',views. filter_products_by_brand, name='filter_products_by_brand'),

    
]

