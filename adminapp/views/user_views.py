from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from datetime import datetime

from django.contrib.auth.models import User  
from adminapp.utils.admin_access import superuser_required




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
@never_cache
def admin_userlist(request):
    query = request.GET.get('q', '').strip()
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    filters = Q(is_superuser=False)
    start_date = end_date = None

    try:
        if start_date_str:
            start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
            start_date = start_date.replace(hour=0, minute=0, second=0)

        if end_date_str:
            end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d'))
            end_date = end_date.replace(hour=23, minute=59, second=59)

        now = timezone.now()

        if start_date and start_date > now:
            messages.warning(request, "Start date is in the future. Ignoring it.")
            start_date = None

        if end_date and end_date > now:
            messages.warning(request, "End date is in the future. Adjusted to current time.")
            end_date = now

        if start_date and end_date and start_date > end_date:
            messages.error(request, "Invalid range. Start date cannot be after end date.")
            start_date = end_date = None

        if start_date and end_date:
            filters &= Q(date_joined__range=(start_date, end_date))
        elif start_date:
            filters &= Q(date_joined__gte=start_date)
        elif end_date:
            filters &= Q(date_joined__lte=end_date)

    except ValueError:
        messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")

    if query:
        filters &= Q(username__icontains=query) | Q(email__icontains=query)
        messages.info(request, f"Search results for: '{query}'")

    user_list = User.objects.filter(filters).order_by('-date_joined')

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(user_list, 10)  # Show 10 users per page

    try:
        paginated_users = paginator.page(page)
    except PageNotAnInteger:
        paginated_users = paginator.page(1)
    except EmptyPage:
        paginated_users = paginator.page(paginator.num_pages)

    context = {
        'data': paginated_users,
        'query': query,
        'start_date': start_date_str or '',
        'end_date': end_date_str or '',
    }

    return render(request, 'admin/admin_userlist.html', context)

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required   
def activate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    messages.success(request, 'User activated successfully.')
    return redirect('admin_userlist')



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@superuser_required
@require_POST
def deactivate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    messages.success(request, 'User deactivated successfully.')
    return redirect('admin_userlist')
