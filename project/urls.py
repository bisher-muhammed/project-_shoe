from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404

from django.shortcuts import render

# Custom 404 view
def custom_404_view(request, exception):
    print("Custom 404 handler called!")
    return render(request, '404.html', status=404)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('adminapp/', include('adminapp.urls')),
    path('core/', include('core.urls')),
    path('', include('user.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Register the custom 404 handler
handler404 = 'project.urls.custom_404_view'  
