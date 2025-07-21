from decimal import Decimal
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import cache_control, never_cache, cache_page
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q

from adminapp.models import Product, Coupon
from core.models import *
from user.models import Wishlist,UserProfile,Wallet
from core.views.cart_views import calculate_cart_total
import razorpay

from core.utils import send_order_confirmation_email






@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def checkout(request):
    user = request.user

    # Get or create UserProfile
    user_profile, _ = UserProfile.objects.get_or_create(user=user)

    # Get all addresses linked to the profile
    addresses = AddressUS.objects.filter(user_profile=user_profile)

    # Get or create active cart
    cart, _ = Cart.objects.get_or_create(user=user, active=True)
    cart_items = cart.cartitem_set.all()

    if not cart_items.exists():
        messages.info(request, "Cannot proceed to checkout. The cart is empty.")
        return redirect('cart_list')

    # Filter valid coupons: not used by user
    used_coupons = Coupon.objects.filter(used_by=user)
    coupon_list = Coupon.objects.exclude(Q(used_by=user) | Q(id__in=used_coupons))

    total = calculate_cart_total(cart_items)
    discount_amount = 0
    selected_coupon_code = ''
    selected_coupon = None
    selected_address = None

    # Address selection
    selected_address_id = request.POST.get('selected_address')
    if selected_address_id:
        try:
            selected_address = addresses.get(id=selected_address_id)
        except AddressUS.DoesNotExist:
            messages.error(request, "Selected address is invalid.")
            return redirect('checkout')

    # Coupon selection and validation
    selected_coupon_code = request.POST.get('selected_coupon_code', '').strip()
    if selected_coupon_code:
        try:
            selected_coupon = Coupon.objects.get(coupon_code=selected_coupon_code)

            if selected_coupon.used_by.filter(id=user.id).exists():
                messages.error(request, "You have already used this coupon.")
                return redirect('checkout')

            discount_amount = selected_coupon.discount_amount
            total = max(total - discount_amount, 0)  # Prevent negative total

            # Remove selected coupon from the list
            coupon_list = coupon_list.exclude(coupon_code=selected_coupon_code)

        except Coupon.DoesNotExist:
            messages.error(request, "Selected coupon does not exist.")
            return redirect('checkout')

    # Store values in session
    request.session['discount_amount'] = discount_amount
    request.session['selected_coupon'] = selected_coupon_code
    request.session['price_value'] = total

    default_address = addresses.filter(is_default=True).first()

    context = {
        'cart': cart,
        'addresses': addresses,
        'default_address': default_address,
        'selected_address': selected_address,
        'coupon_list': coupon_list,
        'selected_coupon': selected_coupon,
        'price_value': total,
        'discount_amount': discount_amount,
        'selected_coupon_code': selected_coupon_code,
    }

    return render(request, 'CART/checkout.html', context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def placeorder(request):
    if not request.user.is_authenticated:
        return redirect("login_view")

    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)

    if not cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('home')

    total = calculate_cart_total(cart_items)
    grand_total = total

    if request.method == 'POST':
        address_id = request.POST.get('shipping_address')
        selected_coupon_code = request.POST.get('selected_coupon_code')

        # Validate address
        try:
            address = AddressUS.objects.get(id=address_id, user_profile__user=current_user)


        except AddressUS.DoesNotExist:
            messages.error(request, "Please select a valid shipping address.")
            return redirect('checkout')

        # Validate coupon (if any)
        coupon_instance = None
        discount_amount = 0

        if selected_coupon_code:
            try:
                coupon_instance = Coupon.objects.get(coupon_code=selected_coupon_code)
                if coupon_instance.is_blocked:
                    messages.error(request, "This coupon is no longer valid.")
                    return redirect('checkout')
                if coupon_instance.used_by.filter(id=current_user.id).exists():
                    messages.error(request, "You have already used this coupon.")
                    return redirect('checkout')
                discount_amount = coupon_instance.discount_amount
            except Coupon.DoesNotExist:
                messages.error(request, "Invalid coupon selected.")
                return redirect('checkout')

        # Create Order
        order = Order.objects.create(
            user=current_user,
            address=address,
            order_total=grand_total,
            coupon=coupon_instance if coupon_instance else None
        )
        # Generate order number
        today = date.today()
        order.order_number = f"{today.strftime('%Y%m%d')}{order.id}"
        order.save()


        # Add user to coupon used list
        if coupon_instance:
            coupon_instance.used_by.add(current_user)

        # Final price after discount
        price_value = grand_total - discount_amount

        # Debug prints (you can remove in production)
        print("Grand Total:", grand_total)
        print("Discount:", discount_amount)
        print("Final Price:", price_value)
        print("Coupon Code:", selected_coupon_code)

        # Optional: clean session
        if 'selected_coupon_code' in request.session:
            del request.session['selected_coupon_code']

        return redirect('payments', order_id=order.id)

    return redirect('checkout')





@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@require_http_methods(["GET", "POST"])
def payments(request, order_id):
    current_user = request.user

    try:
        order = get_object_or_404(Order, user=current_user, is_ordered=False, id=order_id)
        address = order.address
        grand_total = order.order_total

        discount_amount = request.session.get('discount_amount', 0)
        price_value = grand_total - discount_amount
        selected_coupon_code = request.session.get('selected_coupon_code', '')
        quantity = request.GET.get('quantity', '')

        cart_items = CartItem.objects.filter(user=current_user)
        total = sum(cart_item.product.offer_price * cart_item.quantity for cart_item in cart_items)

        context = {
            'address': address,
            'order': order,
            'cart_items': cart_items,
            'total': total,
            'grand_total': grand_total,
            'selected_address': address,
            'discount_amount': discount_amount,
            'price_value': price_value,
            'selected_coupon_code': selected_coupon_code,
            'quantity': quantity,
        }

        if request.method == 'POST':
            user_wallet, _ = Wallet.objects.get_or_create(user_profile__user=current_user)
            order_total_decimal = Decimal(str(order.order_total))

            if Payment.check_sufficient_balance(request, user_wallet, order_total_decimal, order_id):
                messages.error(request, 'Insufficient balance')
                return redirect('payments', order_id=order_id)

            # Deduct amount
            user_wallet.balance -= order_total_decimal
            user_wallet.save()

            # Optionally process payment here

            messages.success(request, 'Payment successful!')
            return redirect('success_page')

        return render(request, 'CART/placeorder.html', context)

    except Order.DoesNotExist:
        messages.error(request, 'Order not found or already processed.')
        return redirect('home')






@login_required(login_url="login_view")
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



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@cache_page(0)
def order_confirmed(request, order_id):
    order = get_object_or_404(Order, id=order_id, is_ordered=True)
    order_products = ProductOrder.objects.filter(user=request.user, order=order)

    send_order_confirmation_email(order)

    total_amount = 0
    selected_coupon_code = request.session.get('selected_coupon_code', '')
    updated_wallet_balance = Decimal(request.session.get('updated_wallet_balance', '0.00'))

    for order_product in order_products:
        order_product.total = order_product.quantity * order_product.product_price
        total_amount += order_product.total

    coupon_applied = bool(selected_coupon_code)

    # Update product sizes
    order.reduce_product_size_quantity()

    # Optional: clean up session
    for key in ['some_key_to_clear', 'selected_coupon_code', 'updated_wallet_balance']:
        if key in request.session:
            del request.session[key]
    request.session.save()

    context = {
        'order_products': order_products,
        'order': order,
        'address': order.address,
        'total_amount': total_amount,
        'selected_coupon_code': selected_coupon_code,
        'coupon_applied': coupon_applied,
        'updated_wallet_balance': updated_wallet_balance,
    }

    return render(request, 'CART/order_confirmed.html', context)















@login_required(login_url="login_view")
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
    user_profile, _ = UserProfile.objects.get_or_create(user=current_user)
    user_wallet, _ = Wallet.objects.get_or_create(
    user_profile=user_profile,
    defaults={'user': current_user, 'balance': 0}
)
    

    # Convert order.order_total to Decimal
    order_total_decimal = Decimal(str(order.order_total))

    # Check if the user has sufficient balance in the wallet
    if Payment.check_sufficient_balance(request, user_wallet, order_total_decimal, order_id):
        messages.error(request, 'Insufficient balance')
        return redirect('payments', order_id=order_id)

    # ✅ Deduct the amount and update wallet
    user_wallet.balance -= order_total_decimal
    updated_wallet_balance = user_wallet.balance
    user_wallet.save()

    # ✅ Create payment record
    payment = Payment.objects.create(
        user=current_user,
        payment_method="wallet_pay",
        amount_paid=total_amount,
        status="Paid"
    )

    # ✅ Update the order
    order.is_ordered = True
    order.payment = payment
    order.payment_method = "wallet_pay"
    order.save()

    # ✅ Move items from cart to order
    cart_items = CartItem.objects.filter(user=current_user)
    for cart_item in cart_items:
        ProductOrder.objects.create(
            order=order,
            user=current_user,
            product=cart_item.product,
            quantity=cart_item.quantity,
            product_price=cart_item.product.offer_price,
            ordered=True,
            address=order.address,
            size=cart_item.size
        )
    cart_items.delete()

    # ✅ Store updated wallet balance in session
    request.session['updated_wallet_balance'] = float(updated_wallet_balance)
    request.session.save()

    # ✅ Redirect to confirmation
    return redirect('order_confirmed', order_id=order_id)
