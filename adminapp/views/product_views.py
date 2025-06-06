from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction, IntegrityError
from django.db.models import Q, Max
from django.utils.timezone import now
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET
from django.contrib import messages
from datetime import datetime



# Import your custom superuser check decorator
from adminapp .utils.admin_access import superuser_required


# Import your models
from adminapp.models import (
    Product,
    Category,
    Brand,
    Size,
    ProductSize,
    ProductOffer,
)



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
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



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def admin_product_list(request):
    products = Product.objects.select_related('brand', 'category').filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    categories = Category.objects.filter(is_blocked=True) 
    

    search_query = request.GET.get('search', '').strip()
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    error = None
    today = now().date()

    start_date_obj = None
    end_date_obj = None

    date_format = "%Y-%m-%d"
    try:
        if start_date:
            start_date_obj = datetime.strptime(start_date, date_format).date()
        if end_date:
            end_date_obj = datetime.strptime(end_date, date_format).date()
        if start_date_obj and end_date_obj and start_date_obj > end_date_obj:
            error = "Start date must be before end date."
    except ValueError:
        error = "Invalid date format. Please use YYYY-MM-DD."

    # Apply category filter
    if category_id:
        try:
            category = Category.objects.get(id=category_id, is_blocked=True)
            products = products.filter(category=category)
        except Category.DoesNotExist:
            error = "Selected category is invalid."

    # Apply brand filter
    if brand_id:
        try:
            brand = Brand.objects.get(id=brand_id, is_active=True)
            products = products.filter(brand=brand)
        except Brand.DoesNotExist:
            error = "Selected brand is invalid."

    # Apply date filters
    if start_date_obj:
        products = products.filter(created_at__date__gte=start_date_obj)
    if end_date_obj:
        products = products.filter(created_at__date__lte=end_date_obj)

    # Apply search (after brand/category/date filters)
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query) |
            Q(brand__brand_name__icontains=search_query) |
            Q(category__category_name__icontains=search_query)
        )

    # Display validation message if any
    if error:
        messages.error(request, error)

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



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
@require_GET
def activate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = True
    product.save()
    return redirect('admin_product_list')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
@require_GET
def deactivate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = False
    product.save()
    return redirect('admin_product_list')



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
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



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
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
