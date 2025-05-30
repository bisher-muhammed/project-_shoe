from django.shortcuts import redirect
from functools import wraps


def superuser_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin_login')  # your admin login URL name
        if not request.user.is_superuser:
            # redirect non-superusers somewhere safe (e.g., user homepage or logout)
            return redirect('home')  # change to your normal user home page
        return view_func(request, *args, **kwargs)
    return _wrapped_view
        