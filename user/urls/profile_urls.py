from django.urls import path
from user.views import profile_views as views 



urlpatterns = [

path('wallet/', views.wallet, name='wallet'),
path('dashboard/',views.view_profile, name='view_profile'),
path('dashboard/change-image/',views.change_image_view, name='change_image_view'),

]



