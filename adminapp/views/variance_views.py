from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.cache import cache_control
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test

from adminapp.models import Size

from django.utils import timezone
from datetime import datetime
from adminapp.utils.admin_access import superuser_required







@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def variance_management(request):
    try:
        size_list = Size.objects.all()
    except Size.DoesNotExist:
        return HttpResponse("No sizes found.")

    context = {
        'size_list': size_list,
    }

    return render(request, 'admin/variance_management.html', context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def add_size(request):
    if request.method == 'POST':
        size_name = request.POST.get('size_name')
        
        if not size_name:
            messages.error(request, "⚠️ Please fill out the 'Size Name' field.")
            return redirect('variance_management')

        if Size.objects.filter(name=size_name).exists():
            messages.warning(request, "❗Size with this name already exists.")
            return redirect('variance_management')

        Size.objects.create(name=size_name)
        messages.success(request, f"✅ Size '{size_name}' added successfully.")

    return redirect('variance_management')



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def activate_size(request, size_id):
    size = get_object_or_404(Size, id=size_id)
    size.is_active = True
    size.save()
    return redirect('variance_management')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def deactivate_size(request, size_id):
    size = get_object_or_404(Size, id=size_id)
    size.is_active = False
    size.save()
    return redirect('variance_management')

