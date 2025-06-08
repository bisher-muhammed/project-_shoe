from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.cache import cache_control, never_cache
from django.db.models import Q
from django.db import transaction
import json

# Models
from adminapp.models import Product, Size, ProductSize  
from core.models import Cart, CartItem,Order            
                    





@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def add_to_cart(request, product_id):
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method.")

    product = get_object_or_404(Product, pk=product_id)

    selected_size_id = request.POST.get('size')
    if not selected_size_id:
        messages.error(request, "Please select a size before adding to cart.")
        return redirect('product_detials', product_id=product_id)

    selected_size = get_object_or_404(Size, pk=selected_size_id)

    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1:
            raise ValueError
    except ValueError:
        messages.error(request, "Invalid quantity selected.")
        return redirect('product_detials', product_id=product_id)

    product_size = ProductSize.objects.filter(product=product, size=selected_size).first()
    if not product_size:
        messages.error(request, "Selected size is not available for the product.")
        return redirect('product_detials', product_id=product_id)

    if product_size.quantity < quantity:
        messages.error(request, f"Only {product_size.quantity} item(s) available for the selected size.")
        return redirect('product_detials', product_id=product_id)

    cart, _ = Cart.objects.get_or_create(user=request.user, active=True)

    with transaction.atomic():
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            cart=cart,
            product=product,
            size=selected_size,
            defaults={'quantity': 0}
        )

        # If already exists, increase quantity
        cart_item.quantity += quantity
        cart_item.product_size = product_size
        cart_item.price = cart_item.quantity * cart_item.product.offer_price
        cart_item.save()

        # If previously ordered, deduct quantity
        order = Order.objects.filter(cart=cart, is_ordered=True).order_by('-created_at').first()
        if order:
            product_size.quantity -= quantity
            product_size.save()

        cart.update_total()

    messages.success(request, "Product added to the cart.")
    return redirect('cart_list')



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def cart_list(request):
    search_query = request.GET.get('q', '')
    cart = Cart.objects.filter(user=request.user, active=True).first()
    cart_items = cart.cartitem_set.all().order_by('-created_at') if cart else []

    if search_query:
        cart_items = cart_items.filter(
            Q(product__product_name__icontains=search_query)
            
        )


    for cart_item in cart_items:
        product_size = ProductSize.objects.filter(product=cart_item.product, size=cart_item.size).first()
        cart_item.available_quantity = product_size.quantity if product_size else 0

    return render(request, 'CART/cart_list.html', {
        'cart_items': cart_items,
        'search_query': search_query
    })




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def clear_cart(request):
    # Get the user's active cart
    cart = Cart.objects.filter(user=request.user, active=True).first()

    if cart:
        # Clear all cart items
        cart.cartitem_set.all().delete()
        # Update the cart total
        cart.update_total()
        messages.success(request, "Cart cleared successfully!")
    else:
        messages.warning(request, "No active cart found.")

    return redirect('cart_list')



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def remove_cart(request, cart_item_id):
    try:
        cart_item = CartItem.objects.get(pk=cart_item_id)
    except CartItem.DoesNotExist:
        messages.error(request, "Cart item does not exist")
        return redirect('cart_list')

    cart = get_object_or_404(Cart, user=request.user, active=True)

    # Remove the cart item from the user's cart
    if cart_item.cart == cart:
        cart_item.delete()
        return redirect('cart_list')
    else:
        messages.error(request, "Cart item does not belong to the current user")
        return redirect('home')

def calculate_subtotal(cart_item):
    
    subtotal = cart_item.quantity * cart_item.product.offer_price
    return subtotal

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
def cart_update(request, cart_item_id):
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
    
    # action = request.POST.get('action')
    print("action workedrequest.POST.get('action')")
    data = json.loads(request.body.decode('utf-8'))
    action = data.get('action')
    print(action)
    
    
    

    
    if action == 'increase':
         cart_item.quantity += 1
    elif action == 'decrease' and cart_item.quantity > 1:
        cart_item.quantity -= 1

    cart_item.save()

    data = {
        'quantity': cart_item.quantity,
        'subtotal': calculate_subtotal(cart_item),
    }
    return JsonResponse(data)


def calculate_cart_total(cart_items):
    total = 0
    for cart_item in cart_items:
        total += cart_item.product.offer_price * cart_item.quantity
    return total


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def add_to_cart_from_wishlist(request, product_id, quantity=1):
    product = get_object_or_404(Product, id=product_id)

    # Get or create the user's active cart
    cart, created = Cart.objects.get_or_create(user=request.user, active=True)

    # Check if the product is already in the cart
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'user': request.user})

    if not created:
        # If the product is already in the cart, update the quantity
        cart_item.quantity += quantity
    else:
        # If the product is not in the cart, create a new cart item with the given quantity
        cart_item.quantity = quantity

    cart_item.price = cart_item.quantity * cart_item.product.offer_price
    cart_item.save()

    cart.update_total()

    messages.success(request, f"{product.product_name} added to your cart!")

    return redirect('wishlist')  

