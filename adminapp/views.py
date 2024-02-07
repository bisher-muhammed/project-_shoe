from urllib import response
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum,F, DecimalField
from .models import Category, Brand, ProductOffer, ProductSize, Size, Color, Product,Coupon,Offer
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from core.models import Order,ProductOrder
from django.utils import timezone
import calendar
from django.db.models.functions import TruncMonth
from collections import defaultdict
from django.http import JsonResponse
from django.db.models import Count
from django.db.models.functions import ExtractMonth, ExtractYear,Coalesce
from PIL import Image 
from.models import Banner
from datetime import datetime, timedelta
from core.models import *
from django.db.models import Max

from django.http import HttpResponse
from django.contrib import messages
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO



@never_cache
def admin_login(request):
    if request.user.is_authenticated:
        return redirect('admin_home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user and user.is_superuser and user.is_active:
            login(request, user)
            return redirect('admin_home')
        else:
            messages.error(request, "Invalid credentials. Please try again.")
            return redirect("admin_login")
    
    return render(request, 'admin/admin_login.html')
from django.db.models import Q
def admin_home(request):
    if request.user.is_authenticated and request.user.is_superuser:

        category_order_counts = (
        ProductOrder.objects
        .filter(ordered=True)
        .values('product__category__category_name')
        .annotate(order_count=Count('id'))
    )

    # Prepare data for JavaScript
        category_labels = [item['product__category__category_name'] for item in category_order_counts]
        order_counts = [item['order_count'] for item in category_order_counts]

        # Create a dictionary to store category-wise order counts
        
        total_users = User.objects.count()
        total_products = Product.objects.count()
        total_orders = Order.objects.count()
        total_categories = Category.objects.count()
        users = User.objects.all()
        products = Product.objects.all()

        total_revenue = ProductOrder.objects.filter(ordered=True).aggregate(
            total_revenue=Sum(F('order__order_total') + F('order__order_value'), output_field=DecimalField())
        )['total_revenue']

        now = timezone.now()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day_of_month = now.replace(day=calendar.monthrange(now.year, now.month)[1], hour=23, minute=59, second=59, microsecond=999999)

        monthly_earning = ProductOrder.objects.filter(ordered=True, created_at__range=(first_day_of_month, last_day_of_month)).aggregate(monthly_earning=Sum('product_price'))['monthly_earning']

        sales_stats = sales_statistics(request)

        # Monthly Orders
        monthly_orders = (
            ProductOrder.objects
            .filter(ordered=True, created_at__range=(first_day_of_month, last_day_of_month))
            .annotate(month=ExtractMonth('created_at'))
            .values('month')
            .annotate(monthly_orders=Sum('quantity'))
            .order_by('month')
        )

        # Yearly Orders
        yearly_orders = (
            ProductOrder.objects
            .filter(ordered=True)
            .annotate(year=ExtractYear('created_at'))
            .values('year')
            .annotate(yearly_orders=Sum('quantity'))
            .order_by('year')
        )

        latest_orders = (
            Order.objects.select_related('user', 'address', 'coupon', 'cart__user')
            .prefetch_related('productorder_set__product', 'productorder_set__cart_item__product')
            .exclude(Q(status='Returned') | Q(status='Cancelled'))
            .order_by('-created_at')

            [:10]  # Adjust the number as needed
        )

        for order in latest_orders:
            # ...
            payment_data = Payment.objects.filter(user=order.user, created_at__gte=order.created_at).first()
            order.payment_method = payment_data.payment_method if payment_data else 'N/A'

        total_order_amount = latest_orders.aggregate(total_order_amount=Sum('order_total'))['total_order_amount']

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
            'users': users,
            'products': products,
            'total_revenue': total_revenue,
            'monthly_earning': monthly_earning,
            'sales_stats': sales_stats,
            'monthly_orders': monthly_orders,
            'yearly_orders': yearly_orders,
            'category_labels': category_labels,
            'order_counts': order_counts,
            'latest_orders': latest_orders,
        }

        return render(request, 'admin/admin_home.html', context)
    else:
        return JsonResponse({}, status=403)
def admin_category(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        description = request.POST.get('description')
        category_image = request.FILES.get('category_image') 

        if not category_name:
            messages.error(request, "Please fill out the 'Category Name' field.")
        else:
            Category.objects.create(
                category_name=category_name,
                description=description,
                category_image=category_image
            )
    total_categories = Category.objects.count()
    print(f"Total_categories: {total_categories}")
  
    category_list = Category.objects.all()
    return render(request, 'admin/admin_category.html', {'category_list': category_list,'total_categories':total_categories})

def block_category(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    category.is_blocked = True
    category.save()
    return redirect('admin_category')

def unblock_category(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    category.is_blocked = False
    category.save()
    return redirect('admin_category')



def add_product(request):
    categories = Category.objects.all()
    brands = Brand.objects.all()
    size_options = Size.objects.filter(is_active=True)

    error_message = None
    form_data = {}
    selected_sizes = []

    if request.method == 'POST':
        product_img1 = request.FILES.get('image1')
        product_img2 = request.FILES.get('image2')
        product_img3 = request.FILES.get('image3')

        fields_to_validate = [
            'product_name',
            'product_category',
            'product_brand',
            'product_description',
            'original_price',
            'offer_price',
        ]

        for field in fields_to_validate:
            value = request.POST.get(field)
            form_data[field] = value
            if not value:
                error_message = f"Please enter a value for {field.replace('_', ' ')}"
                break

        try:
            if not error_message:
                product_name = form_data['product_name']
                product_category_id = form_data['product_category']
                product_brand_id = form_data['product_brand']
                product_description = form_data['product_description']
                original_price = form_data['original_price']
                offer_price = form_data['offer_price']

                if offer_price >= original_price:
                    return HttpResponse("Offer price must be less than original price.")

                category = Category.objects.get(id=product_category_id)
                brand = Brand.objects.get(id=product_brand_id)

                with transaction.atomic():
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

                    product_size_ids = request.POST.getlist('sizes')
                    for size_id in product_size_ids:
                        size = Size.objects.get(id=size_id)
                        quantity = request.POST.get(f'quantity_{size_id}')
                        
                        # Add size with quantity to the product using ProductSize model
                        ProductSize.objects.create(product=product, size=size, quantity=quantity)

                    selected_sizes = request.POST.getlist('sizes')
                    product.sizes.set(selected_sizes)

                    product.save()

                return render(request, 'admin/add_product.html', {'categories': categories, 'brands': brands, 'size_options': size_options, 'error_message': error_message, 'form_data': form_data, 'selected_sizes': selected_sizes})

            return redirect('add_product')

        except (Category.DoesNotExist, Brand.DoesNotExist, Size.DoesNotExist) as e:
            error_message = f"Error creating product: {e}"

    return render(request, 'admin/add_product.html', {'categories': categories, 'brands': brands, 'size_options': size_options, 'error_message': error_message, 'form_data': form_data, 'selected_sizes': selected_sizes})
# def add_product(request):
#     categories = Category.objects.all()
#     brands = Brand.objects.all()
#     size_options = Size.objects.filter(is_active=True)
#     color_options = Color.objects.filter(is_active=True)
#     error_message = None
#     form_data = {}
#     selected_sizes = []  # Initialize with an empty list
#     selected_colors = []  
   

#     if request.method == 'POST':
#         # Use request.FILES for file uploads
#         product_img1 = request.FILES.get('product_img1')
#         product_img2 = request.FILES.get('product_img2')
#         product_img3 = request.FILES.get('product_img3')

#         fields_to_validate = [
#             'product_name',
#             'product_category',
#             'product_brand',
#             'product_description',
#             'original_price',
#             'offer_price',
            
           
#         ]

#         for field in fields_to_validate:
#             value = request.POST.get(field)
#             form_data[field] = value
#             if not value:
#                 print(form_data)  # Debugging line
#                 error_message = f"Please enter a value for {field.replace('_', ' ')}"
#                 break

#         try:
#             if not error_message:
#                 # Extract other fields as before
#                 product_name = form_data['product_name']
#                 product_category_id = form_data['product_category']
#                 product_brand_id = form_data['product_brand']
#                 product_description = form_data['product_description']
#                 original_price = form_data['original_price']
#                 offer_price = form_data['offer_price']
               
#                 if (offer_price) >= (original_price):
#                     return HttpResponse("Offer price must be less than original price.")
                
#                 category = Category.objects.get(id=product_category_id)
#                 brand = Brand.objects.get(id=product_brand_id)
                

#                 with transaction.atomic():
#                     product = Product.objects.create(
#                         product_name=product_name,
#                         product_description=product_description,
#                         original_price=original_price,
#                         offer_price=offer_price,
#                         category=category,
#                         brand=brand,
                        
#                         product_img1=product_img1,
#                         product_img2=product_img2,
#                         product_img3=product_img3,
          
#                     )

#                     product_size_ids = request.POST.getlist('sizes')
#                     for size_id in product_size_ids:
#                         size = Size.objects.get(id=size_id)
#                         product.sizes.add(size)

#                     # Handle multiple colors
#                     product_color_ids = request.POST.getlist('colors')
#                     for color_id in product_color_ids:
#                         color = Color.objects.get(id=color_id)
#                         product.colors.add(color)

#                     # Set selected sizes again
#                     selected_sizes = request.POST.getlist('sizes')
#                     product.sizes.set(selected_sizes)

#                     # Set selected colors again
#                     selected_colors = request.POST.getlist('colors')
#                     product.colors.set(selected_colors)

#                     product.save()
#                 return render(request, 'admin/add_product.html', {'categories': categories, 'brands': brands, 'size_options': size_options, 'color_options': color_options, 'error_message': error_message, 'form_data': form_data, 'selected_sizes': selected_sizes, 'selected_colors': selected_colors})

                    

#             return redirect('add_product')

#         except (Category.DoesNotExist, Brand.DoesNotExist, Size.DoesNotExist) as e:
#             error_message = f"Error creating product: {e}"

#     return render(request, 'admin/add_product.html', {'categories': categories, 'brands': brands, 'size_options': size_options, 'color_options': color_options, 'error_message': error_message, 'form_data': form_data, 'selected_sizes': selected_sizes, 'selected_colors': selected_colors})

def admin_brand(request):
    if request.method == 'POST':
        brand_name = request.POST.get('brand_name')
        brand_description = request.POST.get('brand_description')
        brand_image = request.FILES.get('brand_image')
        if Brand.objects.filter(brand_name=brand_name).exists():
            return HttpResponse("Brand with this name already exists.")
        if not brand_name:
            return HttpResponse("Please fill out the 'Brand Name' field.")

        brand = Brand.objects.create(
            brand_name=brand_name,
            brand_description=brand_description if brand_description else "",
            brand_image=brand_image,
        )

        brand.save()

    brand_list = Brand.objects.all()

    return render(request, 'admin/admin_brand.html', {'brand_list': brand_list})

@require_GET
def activate_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_active = True
    brand.save()
    return redirect('admin_brand')

@require_GET
def deactivate_brand(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    brand.is_active = False
    brand.save()
    return redirect('admin_brand')





def variance_management(request):
    try:
        size_list = Size.objects.all()
    except Size.DoesNotExist:
        return HttpResponse("No sizes found.")

    context = {
        'size_list': size_list,
    }

    return render(request, 'admin/variance_management.html', context)

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





def activate_size(request, size_id):
    size = get_object_or_404(Size, id=size_id)
    size.is_active = True
    size.save()
    return redirect('variance_management')

def deactivate_size(request, size_id):
    size = get_object_or_404(Size, id=size_id)
    size.is_active = False
    size.save()
    return redirect('variance_management')



def product_list(request):
    products = Product.objects.all()
    print(products)
    total_products = Product.objects.count()
    return render(request, 'admin/product_list.html', {'products': products,'total_products':total_products})


@require_GET
def activate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = True
    product.save()
    return redirect('product_list')

@require_GET
def deactivate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = False
    product.save()
    return redirect('product_list')

from django.core.exceptions import ObjectDoesNotExist
def edit_product(request, product_id):
    # Fetch categories, brands, and active sizes
    categories = Category.objects.all()
    brands = Brand.objects.all()
    size_options = Size.objects.filter(is_active=True)

    # Initialize variables
    error_message = None
    form_data = {}
    selected_sizes = {}

    # Fetch the product
    product = get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        # Get images from the form
        product_img1 = request.FILES.get('image1')
        product_img2 = request.FILES.get('image2')
        product_img3 = request.FILES.get('image3')

        # Fields to validate
        fields_to_validate = [
            'product_name',
            'product_category',
            'product_brand',
            'product_description',
            'original_price',
            'offer_price',
        ]

        for field in fields_to_validate:
            # Get value for each field from the form data
            value = request.POST.get(field)
            form_data[field] = value
            if not value:
                # If value is missing, set error message and break the loop
                error_message = f"Please enter a value for {field.replace('_', ' ')}"
                break

        try:
            if not error_message:
                # Extract product details from form data
                product_name = form_data['product_name']
                product_category_id = form_data['product_category']
                product_brand_id = form_data['product_brand']
                product_description = form_data['product_description']
                original_price = form_data['original_price']
                offer_price = form_data['offer_price']

                # Validate offer price
                if offer_price >= original_price:
                    return HttpResponse("Offer price must be less than original price.")

                # Get category and brand objects
                category = Category.objects.get(id=product_category_id)
                brand = Brand.objects.get(id=product_brand_id)

                with transaction.atomic():
                    # Update product details
                    product.product_name = product_name
                    product.product_description = product_description
                    product.original_price = original_price
                    product.offer_price = offer_price
                    product.category = category
                    product.brand = brand

                    # Update product images if provided
                    if product_img1:
                        product.product_img1 = product_img1
                    if product_img2:
                        product.product_img2 = product_img2
                    if product_img3:
                        product.product_img3 = product_img3

                    # Update product sizes and quantities
                    product_size_ids = request.POST.getlist('sizes')
                    ProductSize.objects.filter(product=product).delete()
                    for size_id in product_size_ids:
                        size = Size.objects.get(id=size_id)
                        quantity = request.POST.get(f'quantity_{size_id}')
                        ProductSize.objects.create(product=product, size=size, quantity=quantity)

                    # Set selected sizes
                    selected_sizes = {size.id: int(request.POST.get(f'quantity_{size.id}', 0)) for size in size_options}
                    product.sizes.set(selected_sizes.keys())

                    # Save the product
                    product.save()

                return redirect('edit_product', product_id=product_id)

        except (Category.DoesNotExist, Brand.DoesNotExist, Size.DoesNotExist) as e:
            error_message = f"Error updating product: {e}"

    # Populate form data with existing product details
    form_data['product_name'] = product.product_name
    form_data['product_description'] = product.product_description
    form_data['original_price'] = product.original_price
    form_data['offer_price'] = product.offer_price
    form_data['product_category'] = product.category.id
    form_data['product_brand'] = product.brand.id

    # Fetch product sizes and quantities
    product_sizes = ProductSize.objects.filter(product=product).values_list('size_id', 'quantity')
    selected_sizes = {size_id: quantity for size_id, quantity in product_sizes}

    return render(request, 'admin/edit_product.html', {
        'product': product,
        'categories': categories,
        'brands': brands,
        'size_options': size_options,
        'error_message': error_message,
        'form_data': form_data,
        'selected_sizes': selected_sizes,
    })


@never_cache
def admin_userlist(request):
    # search_query = request.GET.get('search')

    # if search_query:
    #     data = User.objects.filter(Q(username__icontains=search_query) | Q(email__icontains=search_query)).order_by('id')
    # else:
    #     data = User.objects.all().order_by('id')

    # context = {"data": data, "search": search_query}

    data=User.objects.filter(is_superuser=False).order_by('id')

    context={'data':data}
    return render(request, 'admin/admin_userlist.html', context)

    
def activate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    messages.success(request, 'User activated successfully.')
    return redirect('admin_userlist')

@require_POST
def deactivate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    messages.success(request, 'User deactivated successfully.')
    return redirect('admin_userlist')


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



def update_order_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)

    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        if new_status:
            order.status = new_status
            order.save()
    
    # Redirect to the order detail page or any other relevant page
    return redirect('admin_order')

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


from django.db.models import Sum, F, DecimalField
from django.utils import timezone

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




def admin_banner(request):
    # Set a maximum limit for creating banners
    max_banner_limit = 10

    banners = Banner.objects.all()

    # Check the banner limit outside the loop
    if banners.count() >= max_banner_limit:
        messages.error(request, f"Cannot create more than {max_banner_limit} banners.")
    else:
        if request.method == 'POST':
            banner_image = request.FILES.get('image')
            title = request.POST.get('title')
            subtitle = request.POST.get('sub_title')

            if not all([banner_image, title, subtitle]):
                messages.error(request, "Please provide all the required fields")
            else:
                banner = Banner(
                    banner_img=banner_image,
                    title=title,
                    subtitle=subtitle,
                )
                banner.save()

    context = {"banners": banners}
    return render(request, "admin/admin_banner.html", context)

def edit_banner(request, banner_id):
    banner = Banner.objects.get(id=banner_id)
    
    if request.method == "POST":
        banner_img = request.FILES.get('image')
        title = request.POST.get('title')
        subtitle = request.POST.get('sub_title')

        if not all([banner_img, title, subtitle]):
            messages.error(request, "Please provide all the required fields.")
        else:
            banner.banner_img = banner_img
            banner.title = title
            banner.subtitle = subtitle
            banner.save()

            messages.success(request, "Banner updated successfully")
            return redirect("admin_banner")

    context = {"banner": banner}
    return render(request, 'admin/edit_banner.html', context)


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


from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from datetime import datetime

def salesreport(request):
    # Fetch start and end date from the query parameters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Parse the date strings into datetime objects
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else None

    # Fetch orders with related data
    orders = Order.objects.select_related('user', 'address', 'coupon', 'cart__user') \
                     .prefetch_related('productorder_set__product', 'productorder_set__cart_item__product') \
                     .exclude(Q(status="Returned") | Q(status="Cancelled"))
    

    # Apply date filtering if start and end dates are provided
    if start_date and end_date:
        orders = orders.filter(created_at__range=[start_date, end_date])

    # Fetch payment details for each order
    for order in orders:
        payment_data = Payment.objects.filter(user=order.user, created_at__gte=order.created_at).first()
        order.payment_method = payment_data.payment_method if payment_data else 'N/A'

        total_order_amount = orders.aggregate(total_order_amount=Sum('order_total'))['total_order_amount']

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(orders, 10)
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)
    return render(request, 'admin/salesreport.html', {'orders': orders,'total_order_amount': total_order_amount})

from django.db import IntegrityError
from django.http import HttpResponseBadRequest


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
    
    
# def admin_logout(request)

        