from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import cache_control, never_cache
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q, Count
from django.utils import timezone

# Models
from core.models import Order, ProductOrder  # Adjust if models are in another app

# Optional: messages if needed
from django.contrib import messages








@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def order_list(request):
    search_query = request.GET.get('search', '').strip()
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    orders = Order.objects.filter(user=request.user)

    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(productorder__product__name__icontains=search_query)  # correct reverse relation
        ).distinct()

    error_message = None
    current_date = timezone.now().date()
    start_date = None
    end_date = None

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        if start_date and start_date > current_date:
            error_message = "Start date cannot be in the future."
            start_date = None
        elif end_date and end_date > current_date:
            error_message = "End date cannot be in the future."
            end_date = None
        elif start_date and end_date and start_date > end_date:
            error_message = "Start date must be earlier than end date."
            start_date = None
            end_date = None
        else:
            if start_date:
                orders = orders.filter(created_at__date__gte=start_date)
            if end_date:
                orders = orders.filter(created_at__date__lte=end_date)

    except ValueError:
        error_message = "Invalid date format."

    orders = orders.order_by('-created_at')

    # Use exact keys matching your STATUS choices
    status_counts = Order.objects.filter(user=request.user).values('status').annotate(count=Count('id'))
    counts = {s['status']: s['count'] for s in status_counts}

    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    context = {
        'orders': orders,
        'search_query': search_query,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'error_message': error_message,
        'today': current_date,
        'total_count': sum(counts.values()),
        'delivered_count': counts.get('Delivered', 0),
        'pending_count': counts.get('pending', 0),
        'cancelled_count': counts.get('Cancelled', 0),
        'new_count': counts.get('New', 0),
    }
    return render(request, 'accounts/order_list.html', context)






@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def view_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_products = ProductOrder.objects.filter(order=order)

    context = {
        'order': order,
        'order_products': order_products,
        
    }

    return render(request, 'accounts/order_view.html',context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login")
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Debugging statement to print order status before update
    print(f"Order Status Before Update: {order.status}")

    # Implement your cancel logic here
    # For example, update the order status to 'Cancelled'
    order.status = 'Cancelled'
    order.save()

    # Debugging statement to print order status after update
    print(f"Order Status After Update: {order.status}")

    # Optionally, perform other cancellation actions

    # Redirect to the order list page
    return redirect('order_list')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = "Returned"
    order.save()

    # Redirect to the reason_view for the given order_id
    return redirect('order_list')

    # Handle the case where the order status is not "Returned"