

from django.urls import path
from adminapp.views import variance_views as views

urlpatterns = [
    path('variance-management/', views.variance_management, name='variance_management'),
    path('add-size/', views.add_size, name='add_size'),
    path('activate-size/<int:size_id>/', views.activate_size, name='activate_size'),
    path('deactivate-size/<int:size_id>/', views.deactivate_size, name='deactivate_size'),
]

