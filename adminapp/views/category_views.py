import os
import imghdr
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from django.db import IntegrityError
from django.views.decorators.cache import cache_control

from adminapp.models import Category, Product, Offer, ProductOffer
from adminapp.utils.admin_access import superuser_required  # Adjust if your decorator is elsewhere




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def admin_category(request):
    category_name = ''
    description = ''
    category_image = None
    query = request.GET.get('q', '').strip()

    if request.method == 'POST':
        category_name = request.POST.get('category_name', '').strip()
        description = request.POST.get('description', '').strip()
        category_image = request.FILES.get('category_image')

        errors = False

        # Validate category name
        if not category_name:
            messages.error(request, "Please fill out the 'Category Name' field.")
            errors = True
        elif Category.objects.filter(category_name__iexact=category_name).exists():
            messages.error(request, f"The category '{category_name}' already exists.")
            errors = True

        # Validate image
        if not category_image:
            messages.error(request, "Please upload a category image.")
            errors = True
        else:
            valid_image_types = ['jpeg', 'png', 'gif', 'bmp', 'webp']
            file_type = imghdr.what(category_image)

            if file_type not in valid_image_types:
                messages.error(request, "Invalid file type. Upload only: JPEG, PNG, GIF, BMP, or WebP.")
                errors = True
            elif category_image.size > 2 * 1024 * 1024:  # 2MB
                messages.error(request, "Image size should not exceed 2MB.")
                errors = True

        if not errors:
            Category.objects.create(
                category_name=category_name,
                description=description,
                category_image=category_image
            )
            messages.success(request, f"Category '{category_name}' created successfully.")
            return redirect('admin_category')

    # Search filter
    category_list = Category.objects.all()
    if query:
        category_list = category_list.filter(
            Q(category_name__icontains=query) | Q(description__icontains=query)
        )
        messages.info(request, f"Search results for: '{query}'")

    total_categories = category_list.count()

    return render(request, 'admin/admin_category.html', {
        'category_list': category_list,
        'total_categories': total_categories,
        'query': query,
        'form_data': {
            'category_name': category_name,
            'description': description
        }
    })



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def block_category(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    category.is_blocked = True
    category.save()
    return redirect('admin_category')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def unblock_category(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    category.is_blocked = False
    category.save()
    return redirect('admin_category')



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        category_name = request.POST.get('category_name', '').strip()
        description = request.POST.get('description', '').strip()
        new_image = request.FILES.get('category_image')

        if not category_name:
            messages.error(request, "Category Name is required.")
            return redirect('edit_category', category_id=category.id)

        # Image validation
        if new_image:
            valid_image_types = ['jpeg', 'png', 'gif', 'bmp', 'webp']
            file_type = imghdr.what(new_image)

            if file_type not in valid_image_types:
                messages.error(request, "Invalid file type. Upload only: JPEG, PNG, GIF, BMP, or WebP.")
                return redirect('edit_category', category_id=category.id)

            if new_image.size > 2 * 1024 * 1024:  # 2MB
                messages.error(request, "Image size should not exceed 2MB.")
                return redirect('edit_category', category_id=category.id)

            # Delete old image
            if category.category_image and os.path.isfile(category.category_image.path):
                os.remove(category.category_image.path)

            category.category_image = new_image

        # Update other fields
        category.category_name = category_name
        category.description = description
        category.save()

        messages.success(request, "Category updated successfully.")
        return redirect('admin_category')

    return render(request, 'admin/edit_category.html', {'category': category})



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def category_offer(request):
    print("Inside category_offer view")
    print(request.POST)
    
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.filter(is_blocked=True)
    selected_category = None
    applied_offer = None
    all_offers = Offer.objects.all()  # Fetch all offers

    if request.method == 'POST':
        category_id = request.POST.get('selectCategory')
        print("Selected Category ID:", category_id)
        selected_category = get_object_or_404(Category, pk=category_id) if category_id else None
        print("Selected Category:", selected_category)

        if selected_category:
            offer_percentage = request.POST.get('offer_percentage')
            expiry_date = request.POST.get('expiry_date')

            print(f"Offer Percentage: {offer_percentage}")
            print(f"Expiry Date: {expiry_date}")

            expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()

            if expiry_date <= timezone.now().date():
                messages.error(request, 'Please provide a valid future expiration date')
                return redirect('category_offer')  # Redirect to the same page if there's an error

            try:
                # Get the existing offer or create a new one for the selected category
                category_offer, created = Offer.objects.get_or_create(category=selected_category, defaults={'percentage': 0, 'expiry_date': timezone.now()})
                category_offer.percentage = float(offer_percentage) if offer_percentage else 0.0
                category_offer.expiry_date = expiry_date
                category_offer.save()

            except IntegrityError as e:
                print(f"Error saving offer: {e}")

            print(f"Offer Saved: {category_offer}")
            
            # Update product prices in the selected category
            products_in_category = Product.objects.filter(category=selected_category, is_active=True)

            for product in products_in_category:
                product_offer = ProductOffer.objects.filter(product=product).first()
                best_offer = category_offer if not product_offer or category_offer.percentage > product_offer.percentage else product_offer

                if best_offer:
                    discounted_price = product.original_price - (product.original_price * (best_offer.percentage / 100))
                    print(f"Product: {product.product_name}, Original Price: {product.original_price}, Discounted Price: {discounted_price}")
                    product.offer_price = discounted_price
                    product.save()

            applied_offer = category_offer
            print('Applied Offer:', applied_offer)

            if applied_offer and applied_offer.expiry_date and applied_offer.expiry_date < timezone.now().date():
                print(f"The offer for {applied_offer.category.category_name} has expired.")
                for product in products_in_category:
                    product.offer_price = None
                    product.save()

    context = {
        'categories': categories,
        'selected_category': selected_category,
        'applied_offer': applied_offer,
        'all_offers': all_offers,  # Pass all offers to the template
    }

    return render(request, 'admin/category_offer.html', context)