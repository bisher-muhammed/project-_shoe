import json
from django.shortcuts import render,redirect
from adminapp.models import Product,Coupon
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponseBadRequest, JsonResponse
from django.contrib import messages
from django.db.models import Sum
from .models import *
from user.models import Wishlist
from django.core.exceptions import ObjectDoesNotExist
from  user.views import *
from django.views.decorators.http import require_POST
from core.models import *
import datetime
from django.contrib.auth.models import User
from django.views.decorators.cache import cache_page


@login_required(login_url="login_view")
def add_to_cart(request, product_id):
    if request.method == 'POST':
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            # Handle the case where the product doesn't exist
            return render(request, 'accounts/home.html')

        # Get the selected size (assuming you have a selected_size_id in your form)
        selected_size_id = request.POST.get('size', None)
        if not selected_size_id:
            error_message = "Please select a size before adding to cart."
            messages.error(request, error_message)
            return redirect('product_detials', product_id=product_id)

        selected_size = get_object_or_404(Size, pk=selected_size_id)

        # Get or create the user's active cart
        cart, created = Cart.objects.get_or_create(user=request.user, active=True)

        # Filter the ProductSize instances based on the selected product and size
        product_size = ProductSize.objects.filter(product=product, size=selected_size).first()

        if product_size:
            quantity = int(request.POST.get('quantity', 1))

            if product_size.quantity >= quantity:
                with transaction.atomic():
                    # If the order is placed, reduce the available quantity
                    order = Order.objects.filter(cart=cart, is_ordered=True).order_by('-created_at').first()
                    if order:
                        product_size.quantity -= quantity
                        product_size.save()

                    # Check if the item is already in the cart
                    cart_item, created = CartItem.objects.get_or_create(
                        user=request.user,
                        cart=cart,
                        product=product,
                        size=selected_size,
                        defaults={'quantity': 0}  # set quantity to 0 initially
                    )

                    if not created:
                        # If the item is already in the cart, update the quantity
                        cart_item.quantity += quantity
                        cart_item.save()

                    # Assign the corresponding ProductSize to the CartItem
                    cart_item.product_size = product_size
                    cart_item.save()

                    # Calculate the price and save the cart item
                    cart_item.price = cart_item.quantity * cart_item.product.offer_price
                    cart_item.save()

                    # Update the cart total
                    cart.update_total()

                # messages.success(request, "Product added to the cart!")
                return redirect('cart_list')

            else:
                messages.error(request, "Insufficient quantity available for the selected size.")
                return redirect('product_detials', product_id=product_id)
        else:
            messages.error(request, "Selected size is not available for the product.")
            return redirect('product_detials', product_id=product_id)

    else:
        return HttpResponseBadRequest("Invalid request method")



def cart_list(request):
    cart = Cart.objects.filter(user=request.user if request.user.is_authenticated else None, active=True).first()

    if cart:
        cart_items = cart.cartitem_set.all()

        # Fetch available quantity for each cart item
        for cart_item in cart_items:
            product_size = ProductSize.objects.filter(product=cart_item.product, size=cart_item.size).first()
            if product_size:
                cart_item.available_quantity = product_size.quantity
            else:
                cart_item.available_quantity = 0

    else:
        cart_items = []

    return render(request, 'CART/cart_list.html', {'cart_items': cart_items})



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


def product_list(request):
    products = Product.objects.all()
    print(products)
    return render(request, 'admin/product_list.html', {'products': products})

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
    logger.info(f"Cart update data: {json.dumps(data)}")
    return JsonResponse(data)

# def cart_update(request, cart_item_id):
#     cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
    
#     data = json.loads(request.body.decode('utf-8'))
#     action = data.get('action')
    
#     if action == 'increase':
#         # Calculate the remaining quantity that can be added
#         remaining_quantity = cart_item.product_size.quantity - cart_item.quantity
#         # Increase the quantity up to the available quantity
#         cart_item.quantity += min(remaining_quantity, 1)
#     elif action == 'decrease' and cart_item.quantity > 1:
#         cart_item.quantity -= 1

#     cart_item.save()

#     data = {
#         'quantity': cart_item.quantity,
#         'subtotal': calculate_subtotal(cart_item),
#     }
#     logger.info(f"Cart update data: {json.dumps(data)}")
#     return JsonResponse(data)

def calculate_cart_total(cart_items):
    total = 0
    for cart_item in cart_items:
        total += cart_item.product.offer_price * cart_item.quantity
    return total

# checkout view
from django.db.models import Q

from django.db.models import Q

@login_required(login_url="login_view")
def checkout(request):
    # Get the user's UserProfile if it exists, otherwise create one
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Get all addresses associated with the user
    addresses = AddressUS.objects.filter(user_profile=user_profile)

    # Assuming you have a user and each user has a related Cart
    user = request.user

    # If the user has a UserProfile, get the related Cart; otherwise, create one
    cart, cart_created = Cart.objects.get_or_create(user=user, active=True)

    # Retrieve all coupons excluding those used by the current user
    used_coupons = Coupon.objects.filter(used_by=user)
    coupon_list = Coupon.objects.exclude(Q(used_by=user) | Q(id__in=used_coupons))

    total = calculate_cart_total(cart.cartitem_set.all())
    print("Total in checkout:", total)

    # Initialize discount_amount to 0
    discount_amount = 0

    # Adjust this based on your actual model and relationships
    default_address = addresses.filter(is_default=True).first()
    selected_address_id = request.POST.get('selected_address')
    selected_address = addresses.filter(id=selected_address_id).first() if selected_address_id else None
    selected_coupon_code = request.POST.get('selected_coupon_code', '')
    selected_coupon = None

    if selected_coupon_code:
        try:
            selected_coupon = Coupon.objects.get(coupon_code=selected_coupon_code)

            # Check if the user has already used the coupon
            if selected_coupon.used_by.filter(id=user.id).exists():
                messages.error(request, "You have already used this coupon.")
                return redirect('checkout')

            # Continue with your existing logic
            discount_amount = selected_coupon.discount_amount
            total -= discount_amount

            request.session['discount_amount'] = discount_amount

            # Remove the used coupon from the list
            coupon_list = coupon_list.exclude(Q(coupon_code=selected_coupon_code))
        except Coupon.DoesNotExist:
            messages.error(request, "Selected coupon does not exist.")
    else:
        request.session['discount_amount'] = 0

    request.session['price_value'] = total
    request.session['selected_coupon'] = selected_coupon_code

    # You can also fetch other necessary data for the checkout page, e.g., shipping information, etc.
    context = {
        'cart': cart,
        'addresses': addresses,
        'default_address': default_address,
        'selected_address': selected_address,
        'coupon_list': coupon_list,
        'selected_coupon': selected_coupon,
        'price_value': total,  # Assuming price_value is the total after applying the discount
        'discount_amount': discount_amount,
        'selected_coupon_code': selected_coupon_code,
        # Add other context variables as needed
    }

    if cart.cartitem_set.exists():
        return render(request, 'CART/checkout.html', context)
    else:
        messages.info(request, "Cannot proceed to checkout. The cart is empty.")
        return redirect('cart_list')

# placeorder view
# placeorder view
# placeorder view

def placeorder(request):
    if not request.user.is_authenticated:
        return redirect("login_view")
    current_user = request.user

    # Check if the user has any items in the cart
    cart_items = CartItem.objects.filter(user=current_user)
    if cart_items.count() <= 0:
        return redirect('product_list')

    total = calculate_cart_total(cart_items)
    grand_total = total

    if request.method == 'POST':
        address_id = request.POST.get('shipping_address')

        try:
            address = AddressUS.objects.get(id=address_id)
        except AddressUS.DoesNotExist:
            messages.warning(request, "Select a valid address.")
            return redirect('checkout')

        # Store the selected_coupon_code in the session
        selected_coupon_code = request.POST.get('selected_coupon_code')
        request.session['selected_coupon_code'] = selected_coupon_code

        if selected_coupon_code:
            # Retrieve the Coupon instance based on the coupon code
            try:
                coupon_instance = Coupon.objects.get(coupon_code=selected_coupon_code)
            except Coupon.DoesNotExist:
                messages.error(request, "Selected coupon does not exist.")
                return redirect('checkout')
        else:
            coupon_instance = None

        # Initialize the 'data' variable here
        data = Order()
        data.user = current_user
        data.address = address
        data.order_total = grand_total
        data.order_value = grand_total  # Use grand_total as order_value
        # Define discount_amount here before using it
        discount_amount = 0
        if coupon_instance:
            discount_amount = coupon_instance.discount_amount
            data.order_discount = discount_amount
            data.coupon = coupon_instance

        data.save()

        yr, mt, dt = map(int, datetime.date.today().strftime('%Y %m %d').split())
        current_date = datetime.date(yr, mt, dt)
        order_number = f"{current_date.strftime('%Y%m%d')}{data.id}"
        data.order_number = order_number
        data.save()

        order = Order.objects.get(user=current_user, is_ordered=False, order_number=order_number)

        # Calculate price_value as grand_total minus discount_amount
        price_value = grand_total - discount_amount

        print("Grand Total in placeorder:", grand_total)
        print("Discount Amount in placeorder:", discount_amount)
        print("Price Value in placeorder:", price_value)
        print("Selected Coupon Code in placeorder:", selected_coupon_code)

        # Remove the selected_coupon_code from the session after placing the order
        # del request.session['selected_coupon_code']

        context = {
            'order': order,
            'cart_items': cart_items,
            'total': total,
            'grand_total': grand_total,
            'address': address,
            'selected_address': address,
            'discount_amount': discount_amount,
            'price_value': price_value,
            'selected_coupon_code': selected_coupon_code,
        }

        # Check if the user has already used the coupon
        if coupon_instance and coupon_instance.used_by.filter(id=current_user.id).exists():
            messages.error(request, "You have already used this coupon.")
            return redirect('checkout')

        # Remove the used coupon from the user's coupon list
        if coupon_instance:
            coupon_instance.used_by.add(current_user)

        return redirect('payments', order_id=order.id)
    
    # Redirect to the checkout page if the request method is not POST
    return redirect('checkout')

# payments view

# payments view
from django.views.decorators.http import require_http_methods
@require_http_methods(["GET", "POST"])
def payments(request, order_id):
    current_user = request.user

    try:
        order = get_object_or_404(Order, user=current_user, is_ordered=False, id=order_id)
        address = order.address
        grand_total = order.order_total

        # Retrieve discount_amount from the session
        discount_amount = request.session.get('discount_amount', 0)

        # Calculate the price_value
        price_value = grand_total - discount_amount

        # Retrieve other details like selected_coupon_code, quantity, etc.
        selected_coupon_code = request.session.get('selected_coupon_code', '')
        quantity = request.GET.get('quantity', '')

        context = {
            'address': address,
            'order': order,
            'cart_items': CartItem.objects.filter(user=current_user),  # Ensure consistent cart item retrieval
            'total': sum(cart_item.product.offer_price * cart_item.quantity for cart_item in CartItem.objects.filter(user=current_user)),
            'grand_total': grand_total,
            'selected_address': address,
            'discount_amount': discount_amount,
            'price_value': price_value,
            'selected_coupon_code': selected_coupon_code,
            'quantity': quantity,
        }

        if request.method == 'POST':
            # Handle POST request for processing payment
            user_wallet, _ = Wallet.objects.get_or_create(user_profile__user=current_user)

            # Convert order.order_total to Decimal
            order_total_decimal = Decimal(str(order.order_total))

# Check if the user has sufficient balance in the wallet
            if not Payment.check_sufficient_balance(request, user_wallet, order_total_decimal, order_id):
                # If insufficient balance, handle accordingly (e.g., redirect with an error message)
                error_message = 'Insufficient balance'
                messages.error(request, error_message)
                return redirect('payments', order_id=order_id)
            
            if 'some_key_to_clear' in request.session:
                del request.session['some_key_to_clear']
                request.session.save()

            # Deduct the amount from the user's wallet
            user_wallet.balance -= order_total_decimal
            user_wallet.save()

            # Add logic for other payment processing steps if needed

            messages.success(request, 'Payment successful!')  # You can use messages.success for successful actions
            return redirect('success_page')  # Redirect to a success page or wherever needed

        return render(request, 'CART/placeorder.html', context)

    except Order.DoesNotExist:
        messages.error(request, 'Order not found or already processed.')
        return redirect('home')






@transaction.atomic
def cash_on_delivery(request, order_id):
    current_user = request.user

    try:
        # Ensure the order belongs to the current user and is not already ordered
        order = Order.objects.get(id=order_id, user=current_user, is_ordered=False)
        
    except Order.DoesNotExist:
        return redirect('home')  # Redirect to some page, adjust as needed

    total_amount = order.order_total
    payment = Payment(user=current_user, payment_method="Cash on delivery", amount_paid=total_amount, status="Not Paid")

    payment.save()
    
    # Update the order to mark it as ordered and set the payment method
    order.is_ordered = True
    order.payment = payment
    order.payment_method = "Cash on delivery"
    order.save()

    # Retrieve the cart items and create corresponding ProductOrder instances
    cart_items = CartItem.objects.filter(user=current_user)

    for cart_item in cart_items: 
        order_product = ProductOrder(
            order=order,
            user=current_user,
            product=cart_item.product,
            quantity=cart_item.quantity,
            product_price=cart_item.product.offer_price,
            ordered=True,
            address=order.address,
            size=cart_item.size
        )
        order_product.save()

    # Clear the cart after completing the order
    cart_items.delete()
    
    # Redirect to 'order_confirmed' with necessary parameters
    return redirect('order_confirmed', order_id=order_id)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@cache_page(0)
def order_confirmed(request, order_id):
    order = get_object_or_404(Order, id=order_id, is_ordered=True)
    order_products = ProductOrder.objects.filter(user=request.user, order=order)
    

    total_amount = 0

    for order_product in order_products:
        order_product.total = order_product.quantity * order_product.product_price
        total_amount += order_product.total
        selected_coupon_code = request.session.get('selected_coupon_code', '')
        updated_wallet_balance = Decimal(request.session.get('updated_wallet_balance', '0.00'))


    # Determine whether a coupon has been applied
    coupon_applied = bool(selected_coupon_code)
    order.reduce_product_size_quantity()
    # del request.session['updated_wallet_balance']

    context = {
        'order_products': order_products,
        'order': order,
        'address': order.address,
        'total_amount': total_amount,
        'selected_coupon_code': selected_coupon_code,
        'coupon_applied': coupon_applied,  # Add this to indicate whether a coupon has been applied
        'updated_wallet_balance': updated_wallet_balance,
    }
    
    if 'some_key_to_clear' in request.session:
        del request.session['some_key_to_clear']
        request.session.save()
        

    return render(request, 'CART/order_confirmed.html', context)
def coupon_list(request):

    coupon_list = Coupon.objects.filter(is_blocked=True)
   

    return render(request, 'admin/coupon_management.html', {'coupon_list': coupon_list,})

# views.py
# from django.http import JsonResponse
# from adminapp.models import Coupon

# def get_discount_amount(request):
#     if request.method == 'POST':
#         coupon_code = request.POST.get('coupon_code')
#         print(f"Received Coupon Code: {coupon_code}")

#         try:
#             coupon = Coupon.objects.get(coupon_code=coupon_code, is_blocked=False)
#             print(f"Found Coupon: {coupon}")
#             discount_amount = coupon.discount_amount
#         except Coupon.DoesNotExist:
#             print("Coupon Not Found")
#             discount_amount = 0

#         # Process the discount_amount as needed and render the checkout page
#         return render(request, 'CART/checkout.html', {'discount_amount': discount_amount})

#     return JsonResponse({'discount_amount': 0})

from django.shortcuts import redirect, get_object_or_404

@transaction.atomic
def confirm_razorpay_payment(request, order_id):
    current_user = request.user

    try:
        # Ensure the order belongs to the current user and is not already ordered
        order = Order.objects.get(id=order_id, user=current_user, is_ordered=False)
    except Order.DoesNotExist:
        # Order has already been marked as ordered, redirect to order_confirmed
        return redirect('order_confirmed', order_id=order_id)

    total_amount = order.order_total

    payment = Payment(user=current_user, payment_method="Razorpay", amount_paid=total_amount, status="Paid")
    payment.save()
    order.is_ordered = True
    order.payment = payment
    order.save()

    # Retrieve the cart items and create corresponding ProductOrder instances
    cart_items = CartItem.objects.filter(user=current_user)

    for cart_item in cart_items: 
        print(f"Creating ProductOrder for product: {cart_item.product.product_name}")
        print(f"CartItem size: {cart_item.size.name}")
        order_product = ProductOrder(
            order=order,
            user=current_user,
            product=cart_item.product,
            quantity=cart_item.quantity,
            product_price=cart_item.product.offer_price,
            ordered=True,
            address=order.address ,
            size=cart_item.size 
            # Set the address based on the order
        )
        order_product.save()

    # Clear the cart after completing the order
    cart_items.delete()

    # Redirect to 'order_confirmed' with necessary parameters
    return redirect('order_confirmed', order_id=order_id)






@transaction.atomic
def wallet_pay(request, order_id):
    current_user = request.user

    try:
        # Ensure the order belongs to the current user and is not already ordered
        order = Order.objects.get(id=order_id, user=current_user, is_ordered=False)

    except Order.DoesNotExist:
        messages.error(request, 'Order not found or already processed.')
        return redirect('home')

    total_amount = order.order_total

    # Get or create user profile and wallet
    user_profile, created = UserProfile.objects.get_or_create(user=current_user)
    user_wallet, created = Wallet.objects.get_or_create(user_profile=user_profile)

    # Convert order.order_total to Decimal
    order_total_decimal = Decimal(str(order.order_total))

    # Check if the user has sufficient balance in the wallet
    if not Payment.check_sufficient_balance(request, user_wallet, order_total_decimal, order_id):
        # If insufficient balance, handle accordingly (e.g., redirect with an error message)
        error_message = 'Insufficient balance'
        messages.error(request, error_message)
        return redirect('payments', order_id=order_id)

    # Deduct the amount from the user's wallet
    user_wallet.balance -= order_total_decimal
    updated_wallet_balance = user_wallet.balance
    user_wallet.save()

    # Create Payment instance with 'wallet_pay' as the payment method
    payment = Payment(user=current_user, payment_method="wallet_pay", amount_paid=total_amount, status="Not Paid")
    payment.save()

    # Update the order to mark it as ordered and set the payment method
    order.is_ordered = True
    order.payment = payment
    order.payment_method = "wallet_pay"
    order.save()

    # Retrieve the cart items and create corresponding ProductOrder instances
    cart_items = CartItem.objects.filter(user=current_user)

    for cart_item in cart_items:
        order_product = ProductOrder(
            order=order,
            user=current_user,
            product=cart_item.product,
            quantity=cart_item.quantity,
            product_price=cart_item.product.offer_price,
            ordered=True,
            address=order.address,
            size=cart_item.size 
        )
        order_product.save()

    # Clear the cart after completing the order
    cart_items.delete()

    # Convert Decimal to float before saving to session
    float_updated_wallet_balance = float(updated_wallet_balance)

    request.session['updated_wallet_balance'] = float_updated_wallet_balance
    request.session.save()

    # Add debugging statements
    print(f"Order ID: {order_id}")
    print(f"Total Amount: {order.order_total}")
    print(f"Updated wallet balance: {updated_wallet_balance}")

    # Redirect to 'order_confirmed' with necessary parameters
    return redirect('order_confirmed', order_id=order_id)


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