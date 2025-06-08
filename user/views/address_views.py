
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import cache_control, never_cache
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

# Import your models
from user.models import UserProfile, AddressUS




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def add_address(request):
    context = {}

    if request.method == "POST":
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        address_1 = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        zip_code = request.POST.get('zip_code', '').strip()
        next_url = request.POST.get('next')

        # Pass entered data back to template if error
        context.update({
            'first_name': first_name,
            'last_name': last_name,
            'address': address_1,
            'city': city,
            'state': state,
            'zip_code': zip_code,
            'next': next_url
        })

        # Validate fields...
        if not all([first_name, last_name, address_1, city, state, zip_code]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'accounts/add_address.html', context)

        if not re.match(r'^\d{6}$', zip_code):
            messages.error(request, 'Please enter a valid zip code.')
            return render(request, 'accounts/add_address.html', context)

        try:
            with transaction.atomic():
                new_address = AddressUS.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    address_1=address_1,
                    city=city,
                    state=state,
                    zipcode=zip_code,
                    user_profile=request.user.profile
                )

                user_addresses = AddressUS.objects.filter(user_profile=request.user.profile)
                if not user_addresses.exclude(id=new_address.id).filter(is_default=True).exists():
                    new_address.is_default = True
                    new_address.save()

                messages.success(request, 'Address added successfully.')

                if next_url:
                    return redirect(next_url)
                else:
                    return redirect('view_profile')

        except Exception as e:
            print(f"Error creating address: {e}")
            messages.error(request, 'An error occurred while adding your address.')

    else:
        context['next'] = request.GET.get('next', '')

    return render(request, 'accounts/add_address.html', context)





@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required
def addresses(request):
    # Try to get the UserProfile, or create a new one if it doesn't exist
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    addresses = AddressUS.objects.filter(user_profile=user_profile)

    # Check if there is no default address set, and set the first address as default
    if not any(address.is_default for address in addresses):
        first_address = addresses.first()
        if first_address:
            with transaction.atomic():
                first_address.is_default = True
                first_address.save()

    return render(request, 'accounts/address.html', {'addresses': addresses})



@login_required(login_url="login_view")
def set_default_address(request, address_id):
    address = get_object_or_404(AddressUS, id=address_id)
    address.is_default = True

    # Unset the "is_default" field for other addresses
    AddressUS.objects.filter(user_profile=address.user_profile).exclude(id=address_id).update(is_default=False)

    # Corrected redirect statement
    return redirect('addresses')



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required
def delete_address(request, address_id):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    address = get_object_or_404(AddressUS, id=address_id, user_profile=user_profile)

    if request.method == 'POST':
        address.delete()
        return redirect('addresses')  # Replace with the actual name of your address list view

    return render(request, 'accounts/confirm_delete.html', {'address': address})



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
@login_required(login_url="login_view")
def edit_address(request, address_id):
    address = get_object_or_404(AddressUS, id=address_id, user_profile=request.user.profile)

    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        address_1 = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip_code')

        # Check required fields
        if not all([first_name, last_name, address_1, city, state, zip_code]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'accounts/edit_address.html', {'address': address})

        # Validate 6-digit zip code
        if not re.match(r'^\d{6}$', zip_code):
            messages.error(request, 'Please enter a valid 6-digit zip code.')
            return render(request, 'accounts/edit_address.html', {'address': address})

        try:
            address.first_name = first_name
            address.last_name = last_name
            address.address_1 = address_1
            address.city = city
            address.state = state
            address.zipcode = zip_code  # make sure your model field is 'zipcode' or change accordingly
            address.save()

            messages.success(request, 'Address updated successfully.')
            return redirect('view_profile')

        except Exception as e:
            print(f"Error updating address: {e}")
            messages.error(request, 'Error updating address. Please try again.')

    return render(request, 'accounts/edit_address.html', {'address': address})