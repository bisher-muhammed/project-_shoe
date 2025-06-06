from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache, cache_control
from django.http import JsonResponse
from django.db.models import Count, Sum, F, Q, ExpressionWrapper, DecimalField
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils import timezone
from datetime import datetime
import calendar

# For ExtractMonth and ExtractYear
from django.db.models.functions import ExtractMonth, ExtractYear

# Import your models
from adminapp.models import Product, Category
from django.contrib.auth.models import User
from adminapp.utils.admin_access import superuser_required
from core.models import *




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


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
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
        if start_date_str:
            start_date = timezone.make_aware(datetime.strptime(start_date_str, "%Y-%m-%d"))
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        if end_date_str:
            end_date = timezone.make_aware(datetime.strptime(end_date_str, "%Y-%m-%d"))
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        now = timezone.now()

        if start_date and start_date > now:
            messages.warning(request, "Start date is in the future. Ignoring start date.")
            start_date = None
        if end_date and end_date > now:
            messages.warning(request, "End date is in the future. Adjusting to the current time.")
            end_date = now

        if start_date and end_date and start_date > end_date:
            messages.error(request, "Invalid date range. Start date cannot be after end date.")
            start_date = end_date = None

        if start_date and end_date:
            order_filter &= Q(created_at__range=(start_date, end_date))
        elif start_date:
            order_filter &= Q(created_at__gte=start_date)
        elif end_date:
            order_filter &= Q(created_at__lte=end_date)

    except ValueError:
        messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")

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
            Q(user__username__icontains=query) | Q(order_numbe__icontains=query)
        )
        messages.info(request, f"Search results for: '{query}'")

    for order in latest_orders[:50]:
        payment_data = Payment.objects.filter(user=order.user, created_at__gte=order.created_at).first()
        order.payment_method = payment_data.payment_method if payment_data else 'N/A'

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
def admin_logout(request):
    logout(request)

    return redirect('admin_login')
