

from django.urls import path, include
from adminapp.views import user_views as views


urlpatterns = [


    path('admin_userlist/', views.admin_userlist, name='admin_userlist'),
    path('activate_user/<int:user_id>/', views.activate_user, name='activate_user'),
    path('deactivate_user/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    
]