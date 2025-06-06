import calendar
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.cache import cache_control
from django.utils import timezone
from django.db.models import Q, Sum

from core .models import Order, ProductOrder, Payment  # Adjust the import if models are in another app
from django.contrib.auth.models import User
from adminapp.utils.admin_access import superuser_required




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def view_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_products = ProductOrder.objects.filter(order=order)

    context = {
        'order': order,
        'order_products': order_products,
        
    }

    return render(request, 'admin/admin_order_view.html',context)





@cache_control(no_cache=True, must_revalidate=True, no_store=True)
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



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
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
    







@cache_control(no_cache=True, must_revalidate=True, no_store=True)

@superuser_required
def admin_order(request):
    query = request.GET.get('q', '').strip()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    orders = Order.objects.all().order_by('-created_at')
    order_filter = Q()

    # --- Handle date filtering ---
    try:
        if start_date_str:
            start_date = timezone.make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"))
        else:
            start_date = None

        if end_date_str:
            end_date = timezone.make_aware(datetime.strptime(end_date_str, "%Y-%m-%d"))
        else:
            end_date = None

        now = timezone.now()
        if start_date and start_date > now:
            messages.warning(request, "Start date is in the future. Ignoring.")
            start_date = None
        if end_date and end_date > now:
            messages.warning(request, "End date is in the future. Adjusting to now.")
            end_date = now

        if start_date and end_date and start_date > end_date:
            messages.error(request, "Start date cannot be after end date.")
            start_date = end_date = None

        if start_date and end_date:
            order_filter &= Q(created_at__range=(start_date, end_date))
        elif start_date:
            order_filter &= Q(created_at__gte=start_date)
        elif end_date:
            order_filter &= Q(created_at__lte=end_date)
    except ValueError:
        messages.error(request, "Invalid date format. Use YYYY-MM-DD.")

    # --- Handle search query ---
    if query:
        order_filter &= (
            Q(order_number__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query) |
            Q(productorder__product__product_name__icontains=query)
        )
        messages.info(request, f"Search results for: '{query}'")

    orders = orders.filter(order_filter).distinct()

    # Pagination
    paginator = Paginator(orders, 10)
    page = request.GET.get('page', 1)
    try:
        paginated_orders = paginator.page(page)
    except PageNotAnInteger:
        paginated_orders = paginator.page(1)
    except EmptyPage:
        paginated_orders = paginator.page(paginator.num_pages)

    total_orders = orders.count()

    context = {
        'orders': paginated_orders,
        'total_orders': total_orders,
        'query': query,
        'start_date': start_date_str,
        'end_date': end_date_str,
    }
    return render(request, 'admin/admin_order.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)

    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        if new_status and new_status in dict(Order.STATUS):
            old_status = order.status
            order.status = new_status
            order.save()
            
            messages.success(request, f'Order {order.order_number} status updated from "{old_status}" to "{new_status}"')
        else:
            messages.error(request, 'Invalid status selected.')
    
    return redirect('admin_order')
