import os
import imghdr
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import cache_control, never_cache
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from adminapp.models import Coupon,Banner
from adminapp.utils.admin_access import superuser_required





@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def coupon_management(request):
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code')
        discount_amount = request.POST.get('discount_amount')
        minimum_purchase = request.POST.get('minimum_purchase')
        expiry_date = request.POST.get('expiry_date')

        print(f"Coupon Code: {coupon_code}")
        print(f"Discount Amount: {discount_amount}")
        print(f"Minimum Purchase: {minimum_purchase}")
        print(f"Expiry Date: {expiry_date}")

        # Check for empty fields
        if not (coupon_code and discount_amount and minimum_purchase and expiry_date):
            messages.error(request, "Please fill out all fields.")
        else:
            try:
                # Validate discount_amount and minimum_purchase as positive values
                discount_amount = int(discount_amount)
                minimum_purchase = float(minimum_purchase)

                if discount_amount <= 0:
                    raise ValidationError("Discount Amount must be a positive value.")

                if minimum_purchase < 0:
                    raise ValidationError("Minimum Purchase must be a non-negative value.")

                if discount_amount >= minimum_purchase:
                    raise ValidationError("Discount Amount must be less than the Minimum Purchase.")

                # Check for unique coupon code
                if Coupon.objects.filter(coupon_code=coupon_code).exists():
                    raise ValidationError("Coupon Code must be unique.")

                # Create the Coupon object
                Coupon.objects.create(
                    coupon_code=coupon_code,
                    discount_amount=discount_amount,
                    minimum_purchase=minimum_purchase,
                    expiry_date=expiry_date,
                    
                )

                messages.info(request, "Coupon created successfully.")
            except (ValueError, ValidationError) as e:
                messages.info(request, str(e))

    coupon_list = Coupon.objects.all()
    return render(request, 'admin/coupon_management.html', {'coupon_list': coupon_list,})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def block_coupon(request,coupon_id):
    coupon =get_object_or_404(Coupon,pk=coupon_id)
    coupon.is_blocked = True
    coupon.save()
    return redirect('coupon_management')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def unblock_coupon(request,coupon_id):
    coupon = get_object_or_404(Coupon,pk = coupon_id)
    coupon.is_blocked=False
    coupon.save()
    return redirect('coupon_management')








@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def admin_banner(request):
    max_banner_limit = 10
    banners = Banner.objects.all()

    if banners.count() >= max_banner_limit:
        messages.error(request, f"Cannot create more than {max_banner_limit} banners.")
    else:
        if request.method == 'POST':
            banner_image = request.FILES.get('image')
            title = request.POST.get('title', '').strip()
            subtitle = request.POST.get('sub_title', '').strip()

            # Validate required fields
            if not all([banner_image, title, subtitle]):
                messages.error(request, "Please provide all the required fields.")
            else:
                # Validate image type and size
                valid_image_types = ['jpeg', 'png', 'gif', 'bmp', 'webp']
                file_type = imghdr.what(banner_image)

                if file_type not in valid_image_types:
                    messages.error(request, "Invalid file type. Upload only: JPEG, PNG, GIF, BMP, or WebP.")
                elif banner_image.size > 2 * 1024 * 1024:  # 2MB
                    messages.error(request, "Image size should not exceed 2MB.")
                else:
                    # All validations passed — save banner
                    banner = Banner(
                        banner_img=banner_image,
                        title=title,
                        subtitle=subtitle,
                    )
                    banner.save()
                    messages.success(request, "Banner created successfully.")

    context = {"banners": banners}
    return render(request, "admin/admin_banner.html", context)



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def edit_banner(request, banner_id):
    banner = get_object_or_404(Banner, id=banner_id)

    if request.method == "POST":
        banner_img = request.FILES.get('image')
        title = request.POST.get('title', '').strip()
        subtitle = request.POST.get('sub_title', '').strip()

        # Validate title and subtitle
        if not all([title, subtitle]):
            messages.error(request, "Please provide all the required fields.")
        else:
            # Validate image if a new one is uploaded
            if banner_img:
                valid_image_types = ['jpeg', 'png', 'gif', 'bmp', 'webp']
                file_type = imghdr.what(banner_img)

                if file_type not in valid_image_types:
                    messages.error(request, "Invalid image format. Accepted formats: JPEG, PNG, GIF, BMP, WebP.")
                    return redirect('edit_banner', banner_id=banner.id)

                if banner_img.size > 2 * 1024 * 1024:  # 2MB
                    messages.error(request, "Image size must not exceed 2MB.")
                    return redirect('edit_banner', banner_id=banner.id)

                # Update image
                banner.banner_img = banner_img

            # Update other fields
            banner.title = title
            banner.subtitle = subtitle
            banner.save()

            messages.success(request, "Banner updated successfully.")
            return redirect("admin_banner")

    context = {"banner": banner}
    return render(request, 'admin/edit_banner.html', context)



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def banner_active(request, banner_id):
    try:
        banner = Banner.objects.get(id=banner_id)
        print(f"Activating banner: {banner.title}")
        banner.is_active = True
        banner.save()
        messages.success(request, 'Listed successfully.')
    except Banner.DoesNotExist:
        messages.error(request, 'Banner not found.')
        print(f"Banner not found with ID: {banner_id}")
    return redirect('admin_banner')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def banner_blocked(request, banner_id):
    try:
        banner = Banner.objects.get(id=banner_id)
        print(f"Blocking banner: {banner.title}")
        banner.is_active = False
        banner.save()
        messages.success(request, 'Unlisted successfully.')
    except Banner.DoesNotExist:
        messages.error(request, 'Banner not found.')
        print(f"Banner not found with ID: {banner_id}")
    return redirect('admin_banner')


