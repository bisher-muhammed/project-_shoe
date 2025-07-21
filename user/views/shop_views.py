from django.shortcuts import render, get_object_or_404
from django.views.decorators.cache import cache_control, never_cache
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib import messages

# Models - ensure these are imported from the correct app
from adminapp.models import Product, ProductSize, Brand, Category



# utils.py or at the top of views/shop_views.py
def get_price_range(request):
    min_price_param = request.GET.get('min_price', '0')
    max_price_param = request.GET.get('max_price', '')

    try:
        min_price = float(min_price_param) if min_price_param else 0
        max_price = float(max_price_param) if max_price_param else 1e20
    except ValueError:
        return None, None, "Invalid price values."

    return min_price, max_price, None





@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def product_details(request, product_id):
    # Use get_object_or_404 for cleaner error handling
    product = get_object_or_404(Product, pk=product_id)

    # Fetch all ProductSize entries for this product with related Size
    product_sizes = ProductSize.objects.filter(product=product).select_related('size')

    # Build size and quantity info
    sizes_with_quantities = []
    for ps in product_sizes:
        sizes_with_quantities.append({
            'size': ps.size,
            'quantity': ps.quantity
        })

    # Optional: sort sizes alphabetically
    sizes_with_quantities.sort(key=lambda x: x['size'].name)

    # Related products (excluding this one)
    related_products = Product.objects.filter(brand=product.brand).exclude(id=product.id)[:4]

    context = {
        'product': product,
        'sizes_with_quantities': sizes_with_quantities,
        'selected_size_id': None,  # You can update this later
        'related_products': related_products,
    }

    return render(request, 'accounts/product_detials.html', context)






@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def shop_lists(request):
    products = Product.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    categories = Category.objects.filter(is_blocked=True)

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query) |
            Q(product_description__icontains=search_query)
        )

    # Get safe price range
    min_price, max_price, error = get_price_range(request)
    if error:
        messages.error(request, error)
        return redirect('shop_lists')

    # Apply price filter
    filtered_products = products.filter(offer_price__gte=min_price, offer_price__lte=max_price)

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(filtered_products, 12)
    try:
        filtered_products = paginator.page(page)
    except PageNotAnInteger:
        filtered_products = paginator.page(1)
    except EmptyPage:
        filtered_products = paginator.page(paginator.num_pages)

    context = {
        "products": filtered_products,
        "brands": brands,
        'categories': categories,
    }
    return render(request, 'accounts/shop.html', context)



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def filter_products_by_category(request, category_name):
    category_products = Product.objects.filter(category__category_name=category_name, is_active=True)

    min_price, max_price, error = get_price_range(request)
    if error:
        messages.error(request, error)
        return redirect('shop_lists')

    filtered_products = category_products.filter(offer_price__gte=min_price, offer_price__lte=max_price)

    return render(request, 'accounts/shop.html', {'products': filtered_products})




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def filter_products_by_brand(request, brand_name):
    brand_products = Product.objects.filter(brand__brand_name=brand_name, is_active=True)

    min_price, max_price, error = get_price_range(request)
    if error:
        messages.error(request, error)
        return redirect('shop_lists')

    filtered_products = brand_products.filter(offer_price__gte=min_price, offer_price__lte=max_price)

    return render(request, 'accounts/shop.html', {'products': filtered_products})

