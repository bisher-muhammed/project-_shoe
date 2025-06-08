from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q

# Your models (ensure they're from your actual app structure)
from adminapp.models import Product
from core.models import Order
from user.models import Wishlist




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def add_wishlist(request, product_id):
    try:
        product = get_object_or_404(Product, pk=product_id)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        
        # Check if product is already in wishlist
        if wishlist.products.filter(pk=product_id).exists():
            message = 'Product is already in your wishlist.'
            already_in_wishlist = True
        else:
            wishlist.products.add(product)
            message = 'Product added to wishlist successfully.'
            already_in_wishlist = False

        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': message,
                'already_in_wishlist': already_in_wishlist,
                'in_wishlist': True
            })
        else:
            messages.success(request, message)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'An error occurred while adding to wishlist.'
            })
        else:
            messages.error(request, 'An error occurred while adding to wishlist.')
            return redirect('home')
            
    except Exception as e:
        error_message = 'An error occurred while adding to wishlist.'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': error_message,
                'error': str(e)
            }, status=500)
        else:
            messages.error(request, error_message)
            return redirect('home')
        


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache       
@login_required(login_url="login_view")
def wishlist_view(request):
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    wishlist_items = wishlist.products.all().order_by('-id')

    search_query = request.GET.get('q')
    if search_query:
        wishlist_items = wishlist_items.filter(
            Q(product_name__icontains=search_query) 
        )

    if request.method == 'POST':
        orders = Order.objects.filter(user=request.user, is_ordered=True)

        for order in orders:
            for product in wishlist_items:
                if product.id == order.product.id:
                    wishlist.products.remove(product)

        messages.success(request, "Order completed. Wishlist updated.")
        return redirect('wishlist_view')

    return render(request, 'accounts/wishlist.html', {
        'wishlist_items': wishlist_items,
        'search_query': search_query
    })





@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def delete_wishlist_item(request, product_id):
    wishlist = get_object_or_404(Wishlist, user=request.user)
    product = get_object_or_404(Product, pk=product_id)

    if wishlist.products.filter(pk=product_id).exists():
        wishlist.products.remove(product)
        messages.success(request, "Item removed from wishlist.")
    else:
        messages.warning(request, "Item was not found in your wishlist.")

    return redirect('wishlist')