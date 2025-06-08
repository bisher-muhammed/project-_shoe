import os
import re
import random
from decimal import Decimal
from mimetypes import guess_type

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.core.mail import send_mail
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.db import IntegrityError
from django.templatetags.static import static
from django.http import HttpResponse
from django.utils import timezone

# Import your models
from django.contrib.auth.models import User
from adminapp.models import (
    Product,
    Category,
    Offer,
    Brand,
    Banner,

)
from user.models import (
    UserProfile,
    Wallet
)
from core.models import Order


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def view_profile(request):
    user_profile = None
    image_url = None
    allowed_mimetypes = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']

    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        pass

    if user_profile and user_profile.image:
        image_path = user_profile.image.path
        if os.path.exists(image_path):
            mime_type, _ = guess_type(image_path)
            if mime_type in allowed_mimetypes:
                image_url = user_profile.image.url
            else:
                image_url = static('user/assets/imgs/my_images/user-icon-big.png')
        else:
            image_url = static('user/assets/imgs/my_images/user-icon-big.png')
    else:
        image_url = static('user/assets/imgs/my_images/user-icon-big.png')

    context = {
        'user_profile': user_profile,
        'image_url': image_url,
    }
    return render(request, 'accounts/dashboard.html', context)

@login_required(login_url="login_view")
def change_image_view(request):
    try:
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        if 'new_image' not in request.FILES:
            messages.error(request, "Please select an image to upload.")
        else:
            new_image = request.FILES['new_image']
            allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/webp']
            max_size = 2 * 1024 * 1024  # 2MB

            if new_image.content_type not in allowed_types:
                messages.error(request, "Only JPG, PNG, or WEBP images are allowed.")
            elif new_image.size > max_size:
                messages.error(request, "Image size must be less than 2MB.")
            else:
                user_profile.image = new_image
                user_profile.save()
                messages.success(request, "Profile image updated successfully.")
                return redirect('view_profile')

    # Set image_url for template fallback if image missing
    if user_profile and user_profile.image:
        image_path = user_profile.image.path
        if os.path.exists(image_path):
            image_url = user_profile.image.url
        else:
            image_url = static('user/assets/imgs/my_images/user-icon-big.png')
    else:
        image_url = static('user/assets/imgs/my_images/user-icon-big.png')

    context = {
        'user_profile': user_profile,
        'image_url': image_url,
    }
    return render(request, 'accounts/dashboard.html', context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def wallet(request):
    # Fetch orders for the user
    order_list = Order.objects.filter(user=request.user).order_by('-created_at')

    # Get or create the user profile
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Get or create the wallet
    user_wallet = Wallet.objects.filter(user_profile=user_profile).first()
    if not user_wallet:
        try:
            user_wallet = Wallet.objects.create(user_profile=user_profile, user=request.user)
        except IntegrityError:
            # Handle race condition if wallet already created by another thread
            user_wallet = Wallet.objects.get(user_profile=user_profile)

    # Ensure user is correctly assigned if for any reason it's missing
    if user_wallet.user_id is None:
        user_wallet.user = request.user
        user_wallet.save()

    # Initialize totals
    total_returned_amount = Decimal('0.00')
    total_canceled_amount = Decimal('0.00')

    # Get updated balance from session if available
    updated_wallet_balance = request.session.get('updated_wallet_balance')

    if updated_wallet_balance is not None:
        user_wallet.balance = Decimal(updated_wallet_balance)
        user_wallet.save()
    else:
        # Calculate balance from returned + canceled orders
        total_returned_amount = Decimal(
            Order.objects.filter(user=request.user, status="Returned").aggregate(
                Sum('order_total')
            )['order_total__sum'] or '0.00'
        )
        total_canceled_amount = Decimal(
            Order.objects.filter(user=request.user, status="Cancelled").aggregate(
                Sum('order_total')
            )['order_total__sum'] or '0.00'
        )
        user_wallet.balance = total_returned_amount + total_canceled_amount
        user_wallet.save()

        # Store balance in session
        request.session['updated_wallet_balance'] = str(user_wallet.balance)
        request.session.save()

    # Refresh wallet from DB to ensure consistency
    user_wallet.refresh_from_db()

    # Context for template
    context = {
        'user_wallet': user_wallet,
        'order_list': order_list,
        'total_returned_amount': total_returned_amount,
        'total_canceled_amount': total_canceled_amount,
        'updated_wallet_balance': str(user_wallet.balance)
    }

    return render(request, 'accounts/wallet.html', context)


