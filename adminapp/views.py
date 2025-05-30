import os
import imghdr
import calendar
from io import BytesIO
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from PIL import Image

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.images import get_image_dimensions
from django.db import transaction, IntegrityError
from django.db.models import (
    Sum, F, Count, Q, Max, ExpressionWrapper, DecimalField
)
from django.db.models.functions import (
    TruncMonth, ExtractMonth, ExtractYear, Coalesce
)
from django.utils import timezone
from django.utils.timezone import make_aware, now
from django.utils.html import escape
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from .models import (
    Category, Brand, ProductOffer, ProductSize, Size, Color,
    Product, Coupon, Offer, Banner,
)
from core.models import Order, ProductOrder,Payment

from .utils.admin_access import superuser_required



@never_cache
def admin_login(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_home')
        else:
            # Redirect normal users to their homepage or logout them
            return redirect('home')  # or logout(request) and then redirect('login')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user and user.is_superuser and user.is_active:
            login(request, user)
            return redirect('admin_home')
        else:
            messages.error(request, "Invalid credentials. Please try again.")

    return render(request, 'admin/admin_login.html')



from django.utils.timezone import make_aware
from datetime import datetime

@superuser_required
def admin_home(request):
    if not (request.user.is_authenticated and request.user.is_superuser):
        return JsonResponse({}, status=403)

    query = request.GET.get('q', '').strip()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    order_filter = Q()
    start_date = end_date = None

    try:
        # Parse and make timezone-aware start and end dates
        if start_date_str:
            start_date = timezone.make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"))
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        if end_date_str:
            end_date = timezone.make_aware(datetime.strptime(end_date_str, "%Y-%m-%d"))
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        now = timezone.now()

        # Validate future dates
        if start_date and start_date > now:
            print("Start date is in the future, ignoring.")
            start_date = None
        if end_date and end_date > now:
            print("End date is in the future, adjusting to now.")
            end_date = now

        # Handle invalid range
        if start_date and end_date and start_date > end_date:
            print("Start date is after end date, ignoring both.")
            start_date = end_date = None

        # Apply valid filters
        if start_date and end_date:
            order_filter &= Q(created_at__range=(start_date, end_date))
            print("Filtering orders between", start_date, "and", end_date)
        elif start_date:
            order_filter &= Q(created_at__gte=start_date)
            print("Filtering orders from", start_date)
        elif end_date:
            order_filter &= Q(created_at__lte=end_date)
            print("Filtering orders up to", end_date)

    except ValueError as e:
        print("Invalid date format:", e)

    # Print range for debug
    first_order = Order.objects.order_by('created_at').first()
    last_order = Order.objects.order_by('-created_at').first()
    print("Earliest order in DB:", first_order.created_at if first_order else "N/A")
    print("Latest order in DB:", last_order.created_at if last_order else "N/A")

    # Chart data
    category_order_counts = (
        ProductOrder.objects
        .filter(order_filter)
        .values('product__category__category_name')
        .annotate(order_count=Count('id'))
    )
    category_labels = [item['product__category__category_name'] for item in category_order_counts]
    order_counts = [item['order_count'] for item in category_order_counts]

    # Totals
    total_users = User.objects.count()
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_orders = Order.objects.filter(order_filter).count()

    total_revenue = ProductOrder.objects.filter(order_filter).aggregate(
        total_revenue=Sum(
            ExpressionWrapper(
                F('order__order_total') + F('order__order_value'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
    )['total_revenue'] or 0

    # Monthly earning
    now = timezone.now()
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day_of_month = now.replace(
        day=calendar.monthrange(now.year, now.month)[1],
        hour=23, minute=59, second=59, microsecond=999999
    )
    monthly_earning = ProductOrder.objects.filter(
        ordered=True,
        created_at__range=(first_day_of_month, last_day_of_month)
    ).aggregate(monthly_earning=Sum('product_price'))['monthly_earning'] or 0

    sales_stats = sales_statistics(request)

    # Monthly & Yearly Orders
    monthly_orders = ProductOrder.objects.filter(order_filter).annotate(
        month=ExtractMonth('created_at')
    ).values('month').annotate(
        monthly_orders=Sum('quantity')
    ).order_by('month')

    yearly_orders = ProductOrder.objects.filter(order_filter).annotate(
        year=ExtractYear('created_at')
    ).values('year').annotate(
        yearly_orders=Sum('quantity')
    ).order_by('year')

    # Latest Orders
    latest_orders = Order.objects.select_related(
        'user', 'address', 'coupon', 'cart__user'
    ).prefetch_related(
        'productorder_set__product', 'productorder_set__cart_item__product'
    ).filter(order_filter).exclude(
        Q(status='Returned') | Q(status='Cancelled')
    ).order_by('-created_at')

    if query:
        latest_orders = latest_orders.filter(
            Q(user__username__icontains=query) | Q(id__icontains=query)
        )
        print("Search query applied:", query)

    print("Total latest orders after filters:", latest_orders.count())

    # Add payment method info
    for order in latest_orders[:50]:
        payment_data = Payment.objects.filter(user=order.user, created_at__gte=order.created_at).first()
        order.payment_method = payment_data.payment_method if payment_data else 'N/A'
        

    # Total amount
    total_order_amount = latest_orders.aggregate(total_order_amount=Sum('order_total'))['total_order_amount'] or 0

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(latest_orders, 10)
    try:
        latest_orders = paginator.page(page)
    except PageNotAnInteger:
        latest_orders = paginator.page(1)
    except EmptyPage:
        latest_orders = paginator.page(paginator.num_pages)

    context = {
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_categories': total_categories,
        'total_revenue': total_revenue,
        'monthly_earning': monthly_earning,
        'sales_stats': sales_stats,
        'monthly_orders': monthly_orders,
        'yearly_orders': yearly_orders,
        'category_labels': category_labels,
        'order_counts': order_counts,
        'latest_orders': latest_orders,
        'query': query,
        'start_date': start_date.date() if start_date else '',
        'end_date': end_date.date() if end_date else '',
        'total_order_amount': total_order_amount,
    }

    return render(request, 'admin/admin_home.html', context)


@superuser_required
def admin_category(request):
    category_name = ''
    description = ''
    category_image = None

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
            return redirect('admin_category')  # Prevent duplicate form submission

    # Render form with existing values if errors exist
    total_categories = Category.objects.count()
    category_list = Category.objects.all()

    return render(request, 'admin/admin_category.html', {
        'category_list': category_list,
        'total_categories': total_categories,
        'form_data': {
            'category_name': category_name,
            'description': description
        }
    })

@superuser_required
def block_category(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    category.is_blocked = True
    category.save()
    return redirect('admin_category')

@superuser_required
def unblock_category(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    category.is_blocked = False
    category.save()
    return redirect('admin_category')




@superuser_required
def add_product(request):
    categories = Category.objects.all()
    brands = Brand.objects.all()
    size_options = Size.objects.filter(is_active=True)

    error_message = None
    form_data = {}
    selected_sizes = []
    images = {
        'image1': None,
        'image2': None,
        'image3': None,
    }

    if request.method == 'POST':
        # Get images
        product_img1 = request.FILES.get('image1')
        product_img2 = request.FILES.get('image2')
        product_img3 = request.FILES.get('image3')

        images['image1'] = product_img1
        images['image2'] = product_img2
        images['image3'] = product_img3

        # Validate required fields
        required_fields = [
            'product_name',
            'product_category',
            'product_brand',
            'product_description',
            'original_price',
            'offer_price',
        ]

        # Basic field validation
        for field in required_fields:
            value = request.POST.get(field, '').strip()
            form_data[field] = value
            if not value:
                error_message = f"Please enter a value for {field.replace('_', ' ').title()}"
                break

        # Validate price fields specifically
        if not error_message:
            try:
                original_price = float(form_data['original_price'])
                offer_price = float(form_data['offer_price'])
                
                if original_price <= 0:
                    error_message = "Original price must be greater than 0"
                elif offer_price <= 0:
                    error_message = "Offer price must be greater than 0"
                elif offer_price >= original_price:
                    error_message = "Offer price must be less than the original price"
                    
            except (ValueError, TypeError):
                error_message = "Please enter valid numeric values for prices"

        # Validate images
        if not error_message:
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
            max_size = 5 * 1024 * 1024  # 5MB

            for img_name, img in [('image1', product_img1), ('image2', product_img2), ('image3', product_img3)]:
                if img:
                    if img.content_type not in allowed_types:
                        error_message = "Only JPG, PNG, or WEBP images are allowed"
                        break
                    if img.size > max_size:
                        error_message = "Each image must be smaller than 5MB"
                        break

        # Validate size selection and quantities
        if not error_message:
            product_size_ids = request.POST.getlist('sizes')
            selected_sizes = product_size_ids

            if not product_size_ids:
                error_message = "Please select at least one size"
            else:
                # Validate quantities for selected sizes
                for size_id in product_size_ids:
                    quantity = request.POST.get(f'quantity_{size_id}', '').strip()
                    if not quantity:
                        error_message = f"Please provide quantity for selected size"
                        break
                    try:
                        quantity_int = int(quantity)
                        if quantity_int <= 0:
                            error_message = f"Quantity must be greater than 0"
                            break
                    except ValueError:
                        error_message = f"Please provide valid numeric quantity"
                        break

        # Create product if no errors
        if not error_message:
            try:
                product_name = form_data['product_name']
                product_category_id = form_data['product_category']
                product_brand_id = form_data['product_brand']
                product_description = form_data['product_description']

                # Get category and brand objects
                category = Category.objects.get(id=product_category_id)
                brand = Brand.objects.get(id=product_brand_id)

                with transaction.atomic():
                    # Create the product
                    product = Product.objects.create(
                        product_name=product_name,
                        product_description=product_description,
                        original_price=original_price,
                        offer_price=offer_price,
                        category=category,
                        brand=brand,
                        product_img1=product_img1,
                        product_img2=product_img2,
                        product_img3=product_img3,
                    )

                    # Create ProductSize objects for each selected size
                    for size_id in product_size_ids:
                        size = Size.objects.get(id=size_id)
                        quantity = int(request.POST.get(f'quantity_{size_id}'))
                        ProductSize.objects.create(
                            product=product, 
                            size=size, 
                            quantity=quantity
                        )

                    # Success - redirect to product list
                    messages.success(request, f'Product "{product_name}" created successfully!')
                    return redirect('admin_product_list')

            except Category.DoesNotExist:
                error_message = "Selected category does not exist"
            except Brand.DoesNotExist:
                error_message = "Selected brand does not exist"
            except Size.DoesNotExist:
                error_message = "One or more selected sizes do not exist"
            except Exception as e:
                error_message = f"Error creating product: {str(e)}"

    return render(request, 'admin/add_product.html', {
        'categories': categories,
        'brands': brands,
        'size_options': size_options,
        'error_message': error_message,
        'form_data': form_data,
        'selected_sizes': selected_sizes,
        'images': images,
    })

@superuser_required
def admin_brand(request):
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
                # Passed all checks; create brand
                Brand.objects.create(
                    brand_name=brand_name,
                    brand_description=brand_description,
                    brand_image=brand_image
                )
                messages.success(request, f"Brand '{brand_name}' added successfully.")
                return redirect('admin_brand')

    brand_list = Brand.objects.all()
    return render(request, 'admin/admin_brand.html', {'brand_list': brand_list})

@superuser_required
@require_GET
def activate_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_active = True
    brand.save()
    return redirect('admin_brand')

@superuser_required
@require_GET
def deactivate_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_active = False
    brand.save()
    return redirect('admin_brand')




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


@superuser_required
def add_size(request):
    if request.method == 'POST':
        size_name = request.POST.get('size_name')
        
        if not size_name:
            return HttpResponse("Please fill out the 'Size Name' field.")

        # Check if size with the same name already exists
        if Size.objects.filter(name=size_name).exists():
            return HttpResponse("Size with this name already exists.")

        size = Size.objects.create(name=size_name)
        size.save()

    return redirect('variance_management')




@superuser_required
def activate_size(request, size_id):
    size = get_object_or_404(Size, id=size_id)
    size.is_active = True
    size.save()
    return redirect('variance_management')


@superuser_required
def deactivate_size(request, size_id):
    size = get_object_or_404(Size, id=size_id)
    size.is_active = False
    size.save()
    return redirect('variance_management')


@superuser_required
def admin_product_list(request):
    products = Product.objects.select_related('brand', 'category').filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    categories = Category.objects.filter(is_blocked=False)

    search_query = request.GET.get('search', '').strip()
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    error = None
    today = now().date()

    # Parse and validate dates same as before...
    start_date_obj = None
    end_date_obj = None
    # ... (date parsing code unchanged)

    # Apply filters only if no error
    if not error:
        # Build a dictionary of filters
        filter_kwargs = {}

        if category_id:
            try:
                category = Category.objects.get(id=category_id, is_blocked=False)
                filter_kwargs['category'] = category
            except Category.DoesNotExist:
                error = "Selected category is invalid."

        if brand_id:
            try:
                brand = Brand.objects.get(id=brand_id, is_active=True)
                filter_kwargs['brand'] = brand
            except Brand.DoesNotExist:
                error = "Selected brand is invalid."

        if start_date_obj:
            filter_kwargs['created_at__date__gte'] = start_date_obj
        if end_date_obj:
            filter_kwargs['created_at__date__lte'] = end_date_obj

        # Apply the filters at once
        products = products.filter(**filter_kwargs)

        # Search filter with OR on multiple fields
        if search_query:
            products = products.filter(
                Q(product_name__icontains=search_query) |
                Q(brand__brand_name__icontains=search_query) |
                Q(category__category_name__icontains=search_query)
            )

    context = {
        'products': products,
        'brands': brands,
        'categories': categories,
        'search_query': search_query,
        'category_id': category_id,
        'brand_id': brand_id,
        'start_date': start_date,
        'end_date': end_date,
        'today': today,
        'error': error,
    }

    return render(request, 'admin/product_list.html', context)


@superuser_required
@require_GET
def activate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = True
    product.save()
    return redirect('admin_product_list')


@superuser_required
@require_GET
def deactivate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = False
    product.save()
    return redirect('admin_product_list')


@superuser_required
def edit_product(request, product_id):
    categories = Category.objects.all()
    brands = Brand.objects.all()
    all_sizes = Size.objects.filter(is_active=True)

    error_message = None
    form_data = {}
    selected_sizes = {}

    product = get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        print("Request method:", request.method) 
        
        # Get images from the form (if any)
        product_img1 = request.FILES.get('product_img1')
        print("Received product_img1:", product_img1)
        product_img2 = request.FILES.get('product_img2')
        print("Received product_img2:", product_img2)
        product_img3 = request.FILES.get('product_img3')
        print("Received product_img3:", product_img3)

        # Validate form fields
        fields_to_validate = [
            'product_name',
            'product_category',
            'product_brand',
            'product_description',
            'original_price',
            'offer_price',
        ]

        for field in fields_to_validate:
            value = request.POST.get(field, '').strip()
            form_data[field] = value
            if not value:
                error_message = f"Please enter a value for {field.replace('_', ' ')}"
                break

        if not error_message:
            try:
                original_price = float(form_data['original_price'])
                offer_price = float(form_data['offer_price'])
                if offer_price >= original_price:
                    error_message = "Offer price must be less than original price."
            except ValueError:
                error_message = "Please enter valid numbers for prices."

        if not error_message:
            try:
                with transaction.atomic():
                    # Update product fields
                    product.product_name = form_data['product_name']
                    product.product_description = form_data['product_description']
                    product.original_price = original_price
                    product.offer_price = offer_price
                    product.category = Category.objects.get(id=form_data['product_category'])
                    product.brand = Brand.objects.get(id=form_data['product_brand'])

                    # Only update images if new images were uploaded
                    if product_img1:
                        product.product_img1 = product_img1
                    if product_img2:
                        product.product_img2 = product_img2
                    if product_img3:
                        product.product_img3 = product_img3

                    product.save()

                    # Handle sizes and quantities
                    ProductSize.objects.filter(product=product).delete()
                    selected_size_ids = request.POST.getlist('sizes')

                    for size_id in selected_size_ids:
                        size = Size.objects.get(id=size_id)
                        quantity_str = request.POST.get(f'quantity_{size_id}', '').strip()

                        if quantity_str.isdigit():
                            quantity = int(quantity_str)
                            ProductSize.objects.create(product=product, size=size, quantity=quantity)
                        else:
                            error_message = f"Please enter a valid quantity for size {size.name}."
                            raise ValueError("Invalid quantity input")

                return redirect('admin_product_list')  # Adjust this to match your actual product list URL name

            except (Category.DoesNotExist, Brand.DoesNotExist):
                error_message = "Selected category or brand does not exist."
            except Exception as e:
                if not error_message:
                    error_message = f"An error occurred: {str(e)}"

        # Preserve selected sizes if the form fails
        for size in all_sizes:
            quantity_str = request.POST.get(f'quantity_{size.id}', '').strip()
            if quantity_str.isdigit():
                selected_sizes[size.id] = int(quantity_str)

    else:
        # Populate form with existing product data
        form_data = {
            'product_name': product.product_name,
            'product_description': product.product_description,
            'original_price': product.original_price,
            'offer_price': product.offer_price,
            'product_category': product.category.id,
            'product_brand': product.brand.id,
        }

        # Load sizes and quantities for this product
        product_sizes = ProductSize.objects.filter(product=product).values_list('size_id', 'quantity')
        selected_sizes = {size_id: quantity for size_id, quantity in product_sizes}

    # Enrich size options with selection and quantity info
    enriched_size_options = []
    for size in all_sizes:
        enriched_size_options.append({
            'id': size.id,
            'name': size.name,
            'checked': size.id in selected_sizes,
            'quantity': selected_sizes.get(size.id, 0),
        })

    return render(request, 'admin/edit_product.html', {
        'product': product,
        'categories': categories,
        'brands': brands,
        'size_options': enriched_size_options,
        'form_data': form_data,
        'error_message': error_message,
    })

@superuser_required
@never_cache
def admin_userlist(request):

    data=User.objects.filter(is_superuser=False).order_by('id')

    context={'data':data}
    return render(request, 'admin/admin_userlist.html', context)

@superuser_required   
def activate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    messages.success(request, 'User activated successfully.')
    return redirect('admin_userlist')

@superuser_required
@require_POST
def deactivate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    messages.success(request, 'User deactivated successfully.')
    return redirect('admin_userlist')

@superuser_required
def admin_order(request):
    # Order the orders by the most recent ones
    orders = Order.objects.all().order_by('-created_at')
    
    # Pagination
    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page = request.GET.get('page', 1)

    try:
        paginated_orders = paginator.page(page)
    except PageNotAnInteger:
        paginated_orders = paginator.page(1)
    except EmptyPage:
        paginated_orders = paginator.page(paginator.num_pages)

    total_orders = Order.objects.count()

    return render(request, 'admin/admin_order.html', {'orders': paginated_orders, 'total_orders': total_orders})

# views.py


@superuser_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)

    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        if new_status:
            order.status = new_status
            order.save()
    
    # Redirect to the order detail page or any other relevant page
    return redirect('admin_order')


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

@superuser_required
def block_coupon(request,coupon_id):
    coupon =get_object_or_404(Coupon,pk=coupon_id)
    coupon.is_blocked = True
    coupon.save()
    return redirect('coupon_management')

def unblock_coupon(request,coupon_id):
    coupon = get_object_or_404(Coupon,pk = coupon_id)
    coupon.is_blocked=False
    coupon.save()
    return redirect('coupon_management')



@superuser_required
def sales_statistics(request):
    orders = Order.objects.filter(is_ordered=True)
    users = User.objects.all()

    # Monthly sales data for products
    month_data = [0] * 12

    for order_item in orders:
        product_orders = ProductOrder.objects.filter(order=order_item)

        for product_order_item in product_orders:
            # Access the associated product and perform calculations
            product = product_order_item.product
            month_data[order_item.created_at.month - 1] += (
                product_order_item.quantity * product.offer_price
            )

    # User registration count per month
    user_chart = [0] * 12
    for user_item in users:
        if user_item.date_joined:
            user_chart[user_item.date_joined.month - 1] += 1

    # Product creation count per month
    product_chart = [0] * 12
    for order_item in orders:
        product_orders = ProductOrder.objects.filter(order=order_item)

        for product_order_item in product_orders:
            # Access the associated product and perform calculations
            product = product_order_item.product
            product_chart[product_order_item.created_at.month - 1] += 1

    context = {
        'month_data': month_data,
        'user_chart': user_chart,
        'product_chart': product_chart,
    }

    return context

@superuser_required
def get_order_dates(request):
    if request.user.is_authenticated:
        now = timezone.now()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day_of_month = now.replace(day=calendar.monthrange(now.year, now.month)[1], hour=23, minute=59, second=59, microsecond=999999)

        order_dates = ProductOrder.objects.filter(ordered=True, created_at__range=(first_day_of_month, last_day_of_month)).values_list('created_at', flat=True)
        order_dates_list = [date.strftime('%Y-%m-%d') for date in order_dates]
        first_day_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day_of_year = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)

        order_dates = ProductOrder.objects.filter(ordered=True, created_at__range=(first_day_of_year, last_day_of_year)).values('created_at')
        order_dates_list = [date['created_at'].strftime('%Y-%m-%d') for date in order_dates]

        data = {
            'order_dates': order_dates_list,
        }

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({}, status=403)



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




@superuser_required
def salesreport(request):
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    search_query = request.GET.get('search', '').strip().lower()

    start_date = end_date = None

    # Validate and parse dates
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            # Include full end day for equal dates
            if start_date and start_date == end_date:
                end_date += timedelta(days=1)
    except ValueError:
        messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
        return redirect('salesreport')

    # Validate logical order
    if start_date and end_date and start_date > end_date:
        messages.error(request, "Start date cannot be after end date.")
        return redirect('salesreport')

    # Base queryset
    order_qs = Order.objects.select_related('user', 'address', 'coupon', 'cart__user') \
        .prefetch_related('productorder_set__product', 'productorder_set__cart_item__product') \
        .exclude(Q(status="Returned") | Q(status="Cancelled"))

    if start_date and end_date:
        order_qs = order_qs.filter(created_at__gte=start_date, created_at__lt=end_date)

    # Apply search
    if search_query:
        matched_users = User.objects.filter(username__icontains=search_query).values_list('id', flat=True)
        matching_payments = Payment.objects.filter(payment_method__icontains=search_query).values_list('user_id', flat=True)

        order_qs = order_qs.filter(
            Q(user__id__in=matched_users) |
            Q(user__id__in=matching_payments)
        )

    total_order_amount = order_qs.aggregate(total_order_amount=Sum('order_total'))['total_order_amount'] or 0

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(order_qs, 10)
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    # Attach payment method
    for order in orders:
        payment_data = Payment.objects.filter(user=order.user, created_at__gte=order.created_at).first()
        order.payment_method = payment_data.payment_method if payment_data else 'N/A'

    return render(request, 'admin/salesreport.html', {
        'orders': orders,
        'total_order_amount': total_order_amount,
        'search_query': search_query,
        'start_date': start_date_str,
        'end_date': end_date_str,
    })


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

@superuser_required
def offer_product(request):
    products = Product.objects.filter(is_active=True)

    if request.method == 'POST':
        product_id = request.POST.get('product')
        offer_percentage = request.POST.get('offer_percentage', 0)
        expiry_date = request.POST.get('expiry_date')

        try:
            product = Product.objects.get(pk=product_id, is_active=True)
        except Product.DoesNotExist:
            messages.error(request, 'Invalid product selected')
            return redirect('offer_product')

        expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d').date()

        if expiry_date <= timezone.now().date():
            messages.error(request, 'Please provide a valid expiry date')
            return redirect('offer_product')

        try:
            # Get the existing offer or create a new one for the selected product
            product_offer, created = ProductOffer.objects.get_or_create(product=product, defaults={'percentage': 0, 'expiry_date': timezone.now()})
            product_offer_percentage = float(offer_percentage) if offer_percentage is not None else 0
            product_offer.percentage = product_offer_percentage
            product_offer.expiry_date = expiry_date
            product_offer.save()

            # Calculate and update discounted price
            best_offer = product.productoffer_set.first()

            if hasattr(product.category, 'offer_set'):
                best_category_offer = product.category.offer_set.aggregate(Max('percentage'))['percentage__max']
                best_offer = product_offer if not best_category_offer or product_offer.percentage > best_category_offer else product_offer

            if best_offer:
                discounted_price = product.original_price - (product.original_price * (best_offer.percentage / 100))
                Product.objects.filter(pk=product_id, is_active=True).update(offer_price=discounted_price)

            messages.success(request, 'Offer applied successfully')

        except IntegrityError as e:
            messages.error(request, f"Error creating or updating offer: {e}")
            print(f"Error: {e}")
            print(f"product_id: {product_id}, offer_percentage: {offer_percentage}, expiry_date: {expiry_date}")

        return redirect('offer_product')

    products_with_offers = Product.objects.filter(productoffer__isnull=False)

    return render(request, 'admin/offer_product.html', {'products': products, 'products_with_offers': products_with_offers})
    
@superuser_required    
def admin_logout(request):
    logout(request)

    return redirect('admin_login')



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

@superuser_required
def view_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_products = ProductOrder.objects.filter(order=order)

    context = {
        'order': order,
        'order_products': order_products,
        
    }

    return render(request, 'admin/admin_order_view.html',context)


