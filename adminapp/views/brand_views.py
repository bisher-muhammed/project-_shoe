from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_GET
from django.views.decorators.cache import cache_control
from django.db.models import Q
from django.contrib.auth.decorators import login_required
import imghdr
import os

from adminapp.models import Brand  # Adjust the import if models are in a different module
from adminapp.utils.admin_access import superuser_required







@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def admin_brand(request):
    query = request.GET.get('q', '').strip()

    if request.method == 'POST':
        brand_name = request.POST.get('brand_name', '').strip()
        brand_description = request.POST.get('brand_description', '').strip()
        brand_image = request.FILES.get('brand_image')

        # Validation
        if not brand_name:
            messages.error(request, "Please fill out the 'Brand Name' field.")
        elif Brand.objects.filter(brand_name__iexact=brand_name).exists():
            messages.error(request, f"The brand '{brand_name}' already exists.")
        elif not brand_image:
            messages.error(request, "Please upload a brand image.")
        else:
            valid_image_types = ['jpeg', 'png', 'gif', 'bmp', 'webp']
            file_type = imghdr.what(brand_image)

            if file_type not in valid_image_types:
                messages.error(request, "Invalid file type. Upload only: JPEG, PNG, GIF, BMP, or WebP.")
            elif brand_image.size > 2 * 1024 * 1024:  # 2MB
                messages.error(request, "Image size should not exceed 2MB.")
            else:
                Brand.objects.create(
                    brand_name=brand_name,
                    brand_description=brand_description,
                    brand_image=brand_image
                )
                messages.success(request, f"Brand '{brand_name}' added successfully.")
                return redirect('admin_brand')

    # Filter brand list based on query
    if query:
        brand_list = Brand.objects.filter(
            Q(brand_name__icontains=query) | Q(brand_description__icontains=query)
        )
        messages.info(request, f"Showing results for '{query}'")
    else:
        brand_list = Brand.objects.all()

    context = {
        'brand_list': brand_list,
        'query': query,
    }
    return render(request, 'admin/admin_brand.html', context)




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
@require_GET
def activate_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_active = True
    brand.save()
    return redirect('admin_brand')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
@require_GET
def deactivate_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_active = False
    brand.save()
    return redirect('admin_brand')




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def edit_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)

    if request.method == 'POST':
        brand_name = request.POST.get('brand_name', '').strip()
        brand_description = request.POST.get('brand_description', '').strip()
        new_image = request.FILES.get('brand_image')

        # Validate brand name
        if not brand_name:
            messages.error(request, "Please provide a brand name.")
            return redirect('edit_brand', brand_id=brand.id)

        # Check for unique brand name (excluding self)
        if Brand.objects.filter(brand_name__iexact=brand_name).exclude(id=brand_id).exists():
            messages.error(request, f"The brand '{brand_name}' already exists.")
            return redirect('edit_brand', brand_id=brand.id)

        # Update name & description
        brand.brand_name = brand_name
        brand.brand_description = brand_description

        # Validate and update image
        if new_image:
            valid_image_types = ['jpeg', 'png', 'gif', 'bmp', 'webp']
            file_type = imghdr.what(new_image)

            if file_type not in valid_image_types:
                messages.error(request, "Invalid file type. Upload only: JPEG, PNG, GIF, BMP, or WebP.")
                return redirect('edit_brand', brand_id=brand.id)

            if new_image.size > 2 * 1024 * 1024:  # 2MB
                messages.error(request, "Image size should not exceed 2MB.")
                return redirect('edit_brand', brand_id=brand.id)

            # Delete old image if exists
            if brand.brand_image and os.path.isfile(brand.brand_image.path):
                os.remove(brand.brand_image.path)

            brand.brand_image = new_image

        brand.save()
        messages.success(request, "Brand updated successfully.")
        return redirect('admin_brand')

    return render(request, 'admin/edit_brand.html', {'brand': brand})
