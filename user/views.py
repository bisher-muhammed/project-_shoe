from django.shortcuts import render, redirect,get_object_or_404
from adminapp.models import Product
from django.contrib.auth import login, logout, authenticate
from django.http import HttpResponse, HttpResponseNotFound
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.cache import cache_control, never_cache
import re
from adminapp import views
from adminapp .models import Banner
from django.contrib import messages
from django.db.models import Q
from adminapp.models import Product, Color,Size
from.models import UserProfile,AddressUS, Wallet
from core.models import ProductOrder,Order
from django.db.models import Sum
from adminapp.models import Category
from django.utils import timezone
from adminapp.models import *

import random
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.db import transaction

from django.contrib.auth import update_session_auth_hash
from django.db.models import Q




from django.db.models import Count
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True)
@never_cache
def home(request):
    # if request.user.is_anonymous:
    #     return redirect('login_view')

    context = {}  # Initialize the context variable

    products = Product.objects.filter(is_active=True).order_by('-offer_price')
    category_list = Category.objects.all()
    all_offers = Offer.objects.all()
    brands = Brand.objects.filter(is_active=True)
    applied_offer = Offer.objects.all()
    banners = Banner.objects.filter(is_active=True)
    search_query = request.GET.get('search', '')
    
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query) |
            Q(product_description__icontains=search_query)
        )

    # Calculate days difference for each banner

    # Fetch the most ordered products (monthly best sellers)
    monthly_best_sellers = Product.objects.filter(
    productorder__created_at__month=timezone.now().month,
    productorder__ordered=True,  # Assuming there is a field named 'ordered' in ProductOrder
    is_active=True
).annotate(order_count=Sum('productorder__quantity')).order_by('-order_count')[:6]
    delay_step = 0.2
    delay_values = [i * delay_step for i in range(len(brands))]


    most_sold_products = Product.objects.filter(
            productorder__ordered=True,
            is_active=True
        ).annotate(order_count=Sum('productorder__quantity')).order_by('-order_count')[:6]

    new_arrivals = Product.objects.filter(
        is_active=True
    ).order_by('-created_at')[:6]    

    
      

    context.update({
        'products': products,
        'category': category_list,
        'banners': banners,
        'search_query': search_query,
        'all_offers': all_offers,
        'applied_offer': applied_offer,
        'brands': brands,
        'monthly_best_sellers': monthly_best_sellers,  # Fixed the update syntax here
        'delay_values': delay_values,
        'new_arrivals': new_arrivals,
        'most_sold_products': most_sold_products,
    })

    if not request.user.is_active:
        request.session.flush()
        print(applied_offer)

    print("Applied Offer:", applied_offer)
    for product in products:
        print(f"Product: {product.product_name}, Offer: {applied_offer}")

    return render(request, 'accounts/home.html', {'username': request.user.username, **context})

    

# @never_cache
# def login_view(request):
#     if 'username' in request.session:
#         return redirect('home')
#     if request.method=='POST':
#         username=request.POST.get('username')
#         password=request.POST.get('password')
#         if not username or not password:
#             error = "Both username and password are required."
#             return render(request, 'accounts/login_view.html', {'error': error})

#         user=authenticate(username=username,password=password)
#         if user is not None:
#             request.session['username']=username
#             login(request,user)
#             return redirect("home")
#         else:
#             error = "Invalid credentials"
#             return render(request, 'accounts/login_view.html', {'error': error})

#     return render(request,'accounts/login_view.html')# Assuming you have a URL named 'login'

# @cache_control(must_revalidate=True, no_transform=True, no_cache=True, no_store=True)
# def signup_view(request):
#     if request.method=='POST':
#         username=request.POST.get('username')
#         email=request.POST.get('email')
#         password=request.POST.get('pass1')
#         confrim_password=request.POST.get('pass2')

#         request.session['uname'] = username
#         request.session['email'] = email
#         request.session['password'] = password



#         try:
#             if not username or  not email or not password:
#                 messages.error(request, 'Enter details to field')
#                 return redirect('signup_view')
#         except:
#             pass

#         try:
#             if User.objects.filter(username=username).exists():
#                 messages.error(request, "Username already exists. Please choose a different one.")
#                 return redirect("signup_view")
#             elif not username.isalnum():
#                 messages.warning(request, "Username contains invalid characters. Please use only letters and numbers.")
#                 return redirect("signup_view")
#         except:
#             pass

#         try:
#             if User.objects.filter(email=email):
#                 messages.error(request, "Email already exists")
#                 return redirect("signup_view")
#         except:
#             pass

#         try:
#             validate_email(email)
#         except ValidationError:
#             messages.error(request, "Invalid email address")
#             return redirect('signup_view')

#         try:
#             if password !=confrim_password:
#                 messages.error(request, "passwords not matching")
#                 return redirect("signup_view")
#         except:
#             pass

#         try:
#             if len(username)>20:
#                 messages.error(request, "username is too long")
#                 return redirect("signup_view")
#         except:
#             pass

#         try:
#             if len(password)<8:
#                 messages.error(request, "Password must be at least 8 characters")
#                 return redirect("signup_view")
#         except:
#             pass

#         request.session['verification_type'] = 'signup_view'
#         send_otp(request)
#         return render(request, 'accounts/otp_verification.html')

#     return render(request, 'accounts/signup_view.html')
# import time
# from datetime import datetime

# def send_otp(request):
#     s=""
#     for x in range(0,4):
#         s+=str(random.randint(0,9))
#     print(s)
#     request.session["otp"] = s
#     request.session["otp_creation_time"] = time.time()
    
    
#     email = request.session.get('email')
#     send_mail("otp for sign up", s, 'bisherp2@gmail.com', [request.session['email']], fail_silently=False)
#     return render(request, 'accounts/otp_verification.html')
   

# from django.shortcuts import render, redirect
# from django.contrib.auth import authenticate, login
# from django.contrib import messages
# from django.contrib.auth.models import User

# # ... (other imports)

# from django.shortcuts import render, redirect
# from django.contrib.auth import authenticate, login
# from django.contrib import messages
# from django.contrib.auth.models import User
# import random
# import time
# from django.core.mail import send_mail
# from django.urls import reverse

# def otp_verification(request):
#     print("Inside otp_verification view")
#     print(f"Session data before redirection: {request.session}")

#     email = request.session.get('email', '')  # Define email here with a default value

#     if request.method == 'POST':
#         otp_entered = request.POST.get('otp')
#         otp_sent = request.session.get('otp')

#         # Get OTP creation time from session
#         otp_creation_time = request.session.get('otp_creation_time', 0)

#         # Check if OTP is expired (more than 60 seconds old)
#         if time.time() - otp_creation_time > 60:
#             messages.error(request, "OTP has expired. Please request a new one.")
#             return render(request, 'accounts/otp_verification.html', {"email": email})

#         user_id = request.session.get('user_id')
#         verification_type = request.session.get('verification_type')

#         print(f"Verification type: {verification_type}")

#         if otp_entered == otp_sent:
#             username = request.session.get('uname')
#             email = request.session.get('email')
#             password = request.session.get('password')

#             if verification_type == 'signup_view':
#                 user = User.objects.create_user(username=username, email=email, password=password)
#                 user.save()
#                 return redirect('login_view')  # Redirect to login page for signup_view

#             elif verification_type == 'login_view':
#                 user = authenticate(request, username=email, password=password)
#                 if user is not None:
#                     username = user.username
#                     request.session['username'] = username
#                     login(request, user)
#                     return redirect('home')
#                 else:
#                     messages.error(request, 'Invalid credentials')
#                     return redirect('login_view')

#         elif verification_type == 'forgot_password':
#                 new_password = request.POST.get('new_password')  # Retrieve the new password from the form

#                 try:
#                     user = User.objects.get(id=user_id, email=email)
#                     user.set_password(new_password)
#                     user.save()
#                     messages.success(request, 'Password updated successfully!')
                    
#                     return redirect('forgot_password')  # Redirect to login page for forgot_password

#                 except User.DoesNotExist:
#                     messages.error(request, 'User does not exist.')
#                     return redirect('login_view')  # Redirect to login page for forgot_password

#                 except Exception as e:
#                     messages.error(request, f'Error updating password: {e}')

#         else:
#             messages.error(request, "Invalid OTP. Please try again.")
#             return render(request, 'accounts/otp_verification.html', {"email": email})

#     # Handle GET requests by rendering the OTP verification form
#     return render(request, 'accounts/otp_verification.html', {"email": request.session.get('email')})



# def resend_otp(request):
#     new_otp = "".join([str(random.randint(0, 9)) for _ in range(4)])
#     print("New OTP:", new_otp)
#     email = request.session.get('email')
#     send_mail("New OTP for Sign Up", new_otp, 'bisherp2@gmail.com', [email], fail_silently=False)
#     request.session['otp'] = new_otp
#     print("Resending OTP...")

# # ... (other views)


@never_cache
def login_view(request):
    if "username" in request.session:
        return redirect("home")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not email or not password:
            messages.warning(request, "Please fill in both email and password.")
            return redirect("login_view")

        user = authenticate(request, username=email, password=password)
        print(user, email, password)

        if user is not None and user.is_active:
            login(request, user)
            request.session["username"] = user.username  # Optional: track in session
            messages.success(request, "Logged in successfully.")
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("login_view")

    return render(request, "accounts/login_view.html")



def signup_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confrim_password = request.POST.get("confirm_password")

        request.session["uname"] = username
        request.session["email"] = email
        request.session["password"] = password
        try:
            if not username or not email or not password:
                messages.error(request, "Enter details to field")
                return redirect("signup_view")
        except:
            pass

        try:
            if User.objects.filter(username=username).exists():
                messages.error(
                    request, "Username already exists. Please choose a different one."
                )
                return redirect("signup_view")
            elif not username.isalnum():
                messages.warning(
                    request,
                    "Username contains invalid characters. Please use only letters and numbers.",
                )
                return redirect("signup_view")
        except:
            pass

        try:
            if User.objects.filter(email=email):
                messages.error(request, "Email already exists")
                return redirect("signup_view")
        except:
            pass

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email address")
            return redirect("signup_view")

        try:
            if password != confrim_password:
                messages.error(request, "passwords not matching")
                return redirect("signup_view")
        except:
            pass

        try:
            if len(username) > 20:
                messages.error(request, "username is too long")
                return redirect("signup_view")
        except:
            pass

        try:
            if len(password) < 8:
                messages.error(request, "Password must be at least 8 characters")
                return redirect("signup_view")
        except:
            pass

        request.session["verification_type"] = "signup_view"
        send_otp(request)
        return render(request, "accounts/verify_otp.html", {"email": email})

    return render(request, "accounts/signup_view.html")


def otp_page(request):
    if "username" in request.session:
        return redirect("home")

    # Check if "email" key is present in the session
    if "email" in request.session:
        email = request.session["email"]
        return render(request, "accounts/verify_otp.html", {"email": email})
    else:
        # Handle the case when the "email" key is not found in the session
        # You can redirect to an error page or take appropriate action
        return HttpResponse("Email not found in session.")


def send_otp(request):
    s = ""
    for x in range(0, 4):
        s += str(random.randint(0, 9))
    print(s)
    request.session["otp"] = s
    email = request.session.get("email")

    send_mail(
        "otp for sign up",
        s,
        "bisherp2@gmail.com",
        [email],
        fail_silently=False,
    )
    return render(request, "accounts/verify_otp.html", {"email": email})


def verify_otp(request):
    if request.method == "POST":
        otp_entered = request.POST.get("otp")
        otp_sent = request.session.get("otp")
        verification_type = request.session.get("verification_type")

        if otp_entered == otp_sent:
            username = request.session.get("uname")
            email = request.session.get("email")
            password = request.session.get("password")
            print()
            print(email, password)

            if verification_type == "signup_view":
                user = User.objects.create_user(
                    username=username, email=email, password=password
                )
                user.save()

                return redirect('login_view')
                # messages.success(request, "Registration successful. You can now log in.")

            elif verification_type == "login_view":
                user = authenticate(request, username=email, password=password)
                print(user)
                if user is not None:
                    username = user.username
                    request.session["username"] = username
                    login(request, user)
                    return redirect("home")
                else:
                    messages.error(request, "Invalid credentials")
                    return redirect("login_view")

            elif verification_type == "forgot_password":
                return redirect("confirm_password")

            elif verification_type == "profile_forget_password":
                return redirect("profile_confrim_password")

            request.session.clear()
            return redirect("login_view")
        else:
            messages.error(request, "Invalid OTP. Please try again.")
            return render(
                request,
                "accounts/verify_otp.html",
                {"email": request.session.get("email")},
            )

    return render(request, "acconts/login_view.html")


def resend_otp(request):
    new_otp = "".join([str(random.randint(0, 9)) for _ in range(4)])
    print(new_otp)
    email = request.session.get("email")
    send_mail(
        "New OTP for Sign Up",
        new_otp,
        "bisherp2@gmail.com",
        [email],
        fail_silently=False,
    )
    request.session["otp"] = new_otp
    return redirect("otp_page")



def forgot_password(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        email = request.POST["email"]
        if User.objects.filter(email=email).exists():
            request.session["verification_type"] = "forgot_password"
            request.session["email"] = email
            send_otp(request)
            return redirect("otp_page")
        else:
            messages.error(request, "Email not registered")

    return render(request, "accounts/forgot_password.html")


from django.contrib.auth import authenticate, login


def confirm_password(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        password = request.POST.get("password1")
        confirm_password = request.POST.get("password2")

        print(password)
        if password == confirm_password:
            email = request.session.get("email")
            print(email)
            user = User.objects.get(email=email)
            print(user)
            user.set_password(password)  # to change the password
            user.save()
            print("set")

            authenticated_user = authenticate(
                request, username=user.username, password=password
            )
            if authenticated_user:
                login(request, authenticated_user)

            messages.success(request, "Password reset successful")
            return redirect("login_view")
        else:
            messages.warning(request, "Passwords do not match")
            return redirect("confirm_password")

    return render(request, "accounts/confirm_password.html")


def profile_forget_password(request, user_id):
    user = User.objects.get(id=user_id)
    if request.user.id != user.id:
        return render(
            request, "accounts/login_view.html", {"error_message": "Unauthorized access"}
        )
    request.session["email"] = user.email
    request.session["verification_type"] = "profile_forget_password"
    send_otp(request)
    return render(request, "accounts/verify_otp.html")


def profile_confrim_password(request):
    if request.method == "POST":
        password = request.POST.get("password1")
        confirm_password = request.POST.get("password2")

        print(password)
        if password == confirm_password:
            email = request.session.get("email")
            print(email)
            user = User.objects.get(email=email)
            print(user)
            user.set_password(password)
            user.save()
            print("set")

            authenticated_user = authenticate(
                request, username=user.username, password=password
            )
            if authenticated_user:
                login(request, authenticated_user)

            messages.success(request, "Password reset successful")
            return redirect("profile_view")
        else:
            messages.warning(request, "Passwords do not match")
            return redirect("confirm_password")
    return render(request, "accounts/confirm_password.html")



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('login_view')



def product_list(request):
    products = Product.objects.all()
    print(products)

    return render(request, 'admin/product_list.html', {'products': products})

def category_list(request):
    category_list = Category.objects.all()
    print(category_list)
    return render(request, 'admin/admin_category.html', {'category_list': category_list})

from django.core.exceptions import ObjectDoesNotExist

def product_detials(request, product_id):
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        # Handle the case where the product doesn't exist
        return render(request, 'accounts/home.html')

    # Get quantities for each size associated with the product
    sizes_with_quantities = []
    for size in product.sizes.all():
        product_sizes = product.productsizes.filter(size=size)

        if product_sizes.exists():
            # If there are instances for the given size, sum the quantities
            quantity = product_sizes.aggregate(Sum('quantity'))['quantity__sum']
        else:
            # If there are no instances, set quantity to 0
            quantity = 0

        sizes_with_quantities.append({'size': size, 'quantity': quantity})

    # Placeholder for selected_size_id (replace it with the actual logic to get the selected size ID)
    selected_size_id = None  # Update this line with the logic to get the selected size ID

    related_products = Product.objects.filter(brand=product.brand).exclude(id=product.id)[:4]

    context = {
        'product': product,
        'sizes_with_quantities': sizes_with_quantities,
        'selected_size_id': selected_size_id,
        'related_products': related_products,
    }
    return render(request, 'accounts/product_detials.html', context)

    # Get related products with the same brand, excluding the current product
   

 # Import the Color and Size models from the admin app

def size_color_options(request):
    size_options = Size.objects.filter(is_active=True)
    context = {'size_options': size_options,}
    return render(request, 'product_list.html',context)





@login_required
def view_profile(request):
    try:
        # Assuming the user profile is related to the logged-in user
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        # If the profile does not exist, you can handle it here.
        # For example, you can redirect to a profile creation page or show an error message.
        # For simplicity, setting user_profile to None in this case.
        user_profile = None

    context = {
        'user_profile': user_profile,
    }

    return render(request, 'accounts/dashboard.html', context)


@login_required
def change_image_view(request):
    try:
        # Assuming the user profile is related to the logged-in user
        user_profile = request.user.profile
    except UserProfile.DoesNotExist:
        # If the profile does not exist, create a new one
        user_profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST' and 'new_image' in request.FILES:
        new_image = request.FILES['new_image']
        user_profile.image = new_image
        user_profile.save()
        return redirect('view_profile')  # Redirect to the profile view after changing the image

    return render(request, 'accounts/dashboard.html', {'user_profile': user_profile})

@login_required
def add_address(request):
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        address_1 = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip_code')

        # Validate all required fields
        if not all([first_name, last_name, address_1, city, state, zip_code]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'accounts/add_address.html')

        try:
            new_address = AddressUS.objects.create(
                first_name=first_name,
                last_name=last_name,
                address_1=address_1,
                city=city,
                state=state,
                zipcode=zip_code,
                user_profile=request.user.profile
            )

            # If no address is marked default, set this one as default
            user_addresses = AddressUS.objects.filter(user_profile=request.user.profile)
            if not any(address.is_default for address in user_addresses):
                with transaction.atomic():
                    new_address.is_default = True
                    new_address.save()

            messages.success(request, 'Address added successfully.')
            return redirect('view_profile')

        except Exception as e:
            print(f"Error creating address: {e}")
            messages.error(request, 'Error adding address. Please try again.')

    return render(request, 'accounts/add_address.html')



# @login_required
# def addresses(request):
#     user_profile = get_object_or_404(UserProfile, user=request.user)
#     addresses = AddressUS.objects.filter(user_profile=user_profile)

#     # Check if there is no default address set, and set the first address as default
#     if not any(address.is_default for address in addresses):
#         first_address = addresses.first()
#         if first_address:
#             with transaction.atomic():
#                 first_address.is_default = True
#                 first_address.save()

#     return render(request, 'accounts/address.html', {'addresses': addresses})
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




def set_default_address(request, address_id):
    address = get_object_or_404(AddressUS, id=address_id)
    address.is_default = True

    # Unset the "is_default" field for other addresses
    AddressUS.objects.filter(user_profile=address.user_profile).exclude(id=address_id).update(is_default=False)

    # Corrected redirect statement
    return redirect('addresses')




@login_required
def delete_address(request, address_id):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    address = get_object_or_404(AddressUS, id=address_id, user_profile=user_profile)

    if request.method == 'POST':
        address.delete()
        return redirect('addresses')  # Replace with the actual name of your address list view

    return render(request, 'accounts/confirm_delete.html', {'address': address})



def order_list(request):
    # Assuming you want to fetch all orders for the logged-in user
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # Set the number of orders you want to display per page
    orders_per_page = 10
    paginator = Paginator(orders, orders_per_page)

    page = request.GET.get('page')
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver the first page
        orders = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g., 9999), deliver the last page
        orders = paginator.page(paginator.num_pages)

    context = {
        'orders': orders,
    }

    return render(request, 'accounts/order_list.html', context)


def view_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_products = ProductOrder.objects.filter(order=order)

    context = {
        'order': order,
        'order_products': order_products,
        
    }

    return render(request, 'accounts/order_view.html',context)

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



@login_required(login_url="login_view")
def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.status = "Returned"
    order.save()

    # Redirect to the reason_view for the given order_id
    return redirect('order_list')

    # Handle the case where the order status is not "Returned"
   
@login_required(login_url="login_view")
def add_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    # Get or create user profile
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Add the product to the wishlist
    user_profile.wishlist.add(product)

    return redirect('home')



@login_required(login_url="login_view")
def wishlist_view(request):
    # Get the user's profile and wishlist items
    user_profile = UserProfile.objects.get(user=request.user)
    wishlist_items = user_profile.wishlist.all()

    if request.method == 'POST':
        # Assuming there's a form or some trigger to complete the order
        # You might need to adjust this based on your actual implementation
        # For example, you might have a dedicated view or endpoint for completing orders

        orders = Order.objects.filter(user=request.user, is_ordered=True)

        for order in orders:
            for item in wishlist_items:
                # Assuming you have a relationship between products in the wishlist
                # and products in the order (e.g., matching by product id)
                if item.product.id == order.product.id:
                    # Delete the product from the wishlist
                    item.delete()

        messages.success(request, "Order completed successfully! Wishlist updated.")
        return redirect('wishlist_view')

    # Render the wishlist template with the wishlist items
    return render(request, 'accounts/wishlist.html', {'wishlist_items': wishlist_items})



    
@login_required(login_url="login_view")
def delete_wishlist_item(request, product_id):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    wishlist_item = get_object_or_404(user_profile.wishlist, pk=product_id)

    # Check if the wishlist item belongs to the current user
    if request.user == user_profile.user:
        # Remove the product from the wishlist
        user_profile.wishlist.remove(wishlist_item)
        messages.success(request, "Item removed from wishlist.")
        return redirect('wishlist')
    else:
        messages.error(request, "Wishlist item does not belong to the current user.")
        return redirect('home')
from decimal import Decimal

# ...
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


# views.py
from django.shortcuts import render
from django.db.models import Sum, DecimalField
from django.http import HttpResponseServerError
from decimal import Decimal
from django.db import IntegrityError

@login_required
def wallet(request):
    # Fetch the list of orders for the user
    order_list = Order.objects.filter(user=request.user).order_by('-created_at')

    # Get or create user profile
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    # Try to get the user's wallet or create one if it doesn't exist
    try:
        user_wallet = Wallet.objects.get(user_profile=user_profile)
    except Wallet.DoesNotExist:
        try:
            user_wallet = Wallet.objects.create(user_profile=user_profile, user=request.user)
        except IntegrityError:
            # Handle IntegrityError, in case another thread created the wallet at the same time
            user_wallet = Wallet.objects.get(user_profile=user_profile)

    # Check if there are existing wallets with null user and update them
    Wallet.objects.filter(user_profile=user_profile, user=None).update(user=request.user)

    # Check if the updated wallet balance is present in the session
    updated_wallet_balance = request.session.get('updated_wallet_balance', None)

    # Initialize total_returned_amount and total_canceled_amount
    total_returned_amount = Decimal('0.00')
    total_canceled_amount = Decimal('0.00')

    if updated_wallet_balance is not None:
        # If present, use the value from the session
        user_wallet.balance = Decimal(updated_wallet_balance)
        user_wallet.save()

        # Remove 'updated_wallet_balance' from the session
        # del request.session['updated_wallet_balance']
        # request.session.save()
    else:
        # Otherwise, calculate the total amount of returned and canceled orders
        total_returned_amount = Decimal(Order.objects.filter(user=request.user, status="Returned").aggregate(Sum('order_total'))['order_total__sum'] or '0.00')
        total_canceled_amount = Decimal(Order.objects.filter(user=request.user, status="Cancelled").aggregate(Sum('order_total'))['order_total__sum'] or '0.00')
        user_wallet.balance = total_returned_amount + total_canceled_amount
        user_wallet.save()

        # Update the wallet balance by setting it to the sum of returned and canceled amounts
        request.session['user_wallet.balance'] = str(user_wallet.balance)
        request.session.save()
        updated_wallet_balance = request.session['user_wallet.balance']
        print(updated_wallet_balance)

    # Fetch the latest wallet balance from the database
    user_wallet.refresh_from_db()

    # Print statements for debugging
    print(f'User ID: {request.user.id}')
    print(f'Wallet Balance (from database): {user_wallet.balance}')
    print(f'Updated Wallet Balance (from session): {updated_wallet_balance}')
    print(f'Total Returned Amount: {total_returned_amount}')
    print(f'Total Canceled Amount: {total_canceled_amount}')

    # Prepare the context for rendering
    context = {
        'user_wallet': user_wallet,
        'order_list': order_list,
        'total_returned_amount': total_returned_amount,
        'total_canceled_amount': total_canceled_amount,
        'updated_wallet_balance': str(user_wallet.balance)
    }

    return render(request, 'accounts/wallet.html', context)
 
# def reason_view(request, order_id):
#     # Implement logic for the reason_view here
#     # This could include rendering a template for the user to provide the return reason
#     # or any other logic you need

#     context = {'order_id': order_id}
    
#     # Render the reason template with the context
#     return render(request,'accounts/reason_view.html', context)




# def email_valid(request):
#     if request.method == 'POST':
#         provided_email = request.POST.get('email')
#         print(f"Provided Email: {provided_email}")

#         try:
#             validate_email(provided_email)
#             users = User.objects.filter(email=provided_email)

#             if users.exists():
#                 if users.count() == 1:
#                     user = users.first()

#                     # Store user and email in session for verification in otp_verification view
#                     request.session['user_id'] = user.id
#                     request.session['email'] = provided_email
#                     request.session['verification_type'] = 'forgot_password'  # Set the correct verification_type for forgot password

#                     # Call send_otp function from your utils module
#                     send_otp(request)

#                     print("Redirecting to otp_verification")
#                     return redirect('otp_verification')

#                 else:
#                     messages.error(request, 'Multiple users with the same email. Contact support.')
#                     print("Redirect failed: Multiple users")
#                     return render(request, 'accounts/email_valid.html')

#             else:
#                 messages.error(request, 'User with this email does not exist.')
#                 print("Redirect failed: User does not exist")
#                 return render(request, 'accounts/email_valid.html')

#         except ValidationError as e:
#             print(f"Email validation error: {e}")
#             messages.error(request, 'Invalid email address.')
#             print("Redirect failed: Invalid email address")
#             return render(request, 'accounts/email_valid.html')

#         except Exception as e:
#             print(f"Error sending OTP: {e}")
#             messages.error(request, 'Error sending OTP. Please try again.')
#             print("Redirect failed: Error sending OTP")
#             return render(request, 'accounts/email_valid.html')

#     # If the request method is GET, handle it here
#     return render(request, 'accounts/email_valid.html')


# def forgot_password(request):
#     if request.method == 'POST':
#         # Get user details from session
#         user_id = request.session.get('user_id')
#         email = request.session.get('email')

#         try:
#             # Update the user's password
#             user = User.objects.get(id=user_id, email=email)

#             # Retrieve the new password and confirmation password from the form
#             new_password = request.POST.get('new_password')
#             confirm_password = request.POST.get('confirm_password')

#             # Validate that the new password matches the confirmation password
#             if new_password != confirm_password:
#                 messages.error(request, 'New password and confirmation password do not match.')
#                 return redirect('forgot_password')

#             # Validate the new password
#             if len(new_password) < 8:
#                 messages.error(request, 'Password must be at least 8 characters long.')
#                 return redirect('forgot_password')

#             # Update the user's password
#             user.set_password(new_password)
#             user.save()

#             # Clear only the specific session data related to password reset
            

#             # Redirect to the login page
#             messages.success(request, 'Password updated successfully!')
#             return redirect('login_view')

#         except User.DoesNotExist:
#             messages.error(request, 'User does not exist.')
#             return redirect('login_view')

#         except Exception as e:
#             messages.error(request, f'Error updating password: {e}')

#     return render(request, 'accounts/forgot_password.html')

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(AddressUS, id=address_id, user_profile=request.user.profile)

    if request.method == "POST":
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        address_1 = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip_code')

        # Validation
        if not all([first_name, last_name, address_1, city, state, zip_code]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'accounts/edit_address.html', {'address': address})

        try:
            address.first_name = first_name
            address.last_name = last_name
            address.address_1 = address_1
            address.city = city
            address.state = state
            address.zipcode = zip_code
            address.save()

            messages.success(request, 'Address updated successfully.')
            return redirect('view_profile')

        except Exception as e:
            print(f"Error updating address: {e}")
            messages.error(request, 'Error updating address. Please try again.')

    return render(request, 'accounts/edit_address.html', {'address': address})



from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
def shop_lists(request):
    products = Product.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    categories = Category.objects.filter(is_blocked=True)

    search_query=request.GET.get('search','')
    if search_query:

        products = products.filter(
            Q(product_name__icontains=search_query) |
            Q(product_description__icontains=search_query)
        )


    min_price = float(request.GET.get('min_price', 0))

    max_price_param = request.GET.get('max_price')
    if max_price_param is not None:
        max_price = float(max_price_param)
    else:
        # Use a large number instead of infinity
        max_price = 1e20

    # Filter products based on the offer price range
    filtered_products = Product.objects.filter(offer_price__gte=min_price, offer_price__lte=max_price)
    # selected_brand =request.GET.get('brand')
    # selected_category= request.GET.get('caategory')

    # if selected_category:
    #     products = products.filter(category__category_name=selected_category)
    # if selected_brand:
    #     products = products.filter(brand__brand_name=selected_brand)

     # Pagination logic
    page = request.GET.get('page', 1)
    paginator = Paginator(products, 12)  # Show 12 products per page
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    



    context = {
        "products": filtered_products,
        "brands": brands,
        'categories': categories,
        
    }

    return render(request, 'accounts/shop.html', context)


def filter_products_by_category(request, category_name):
    # Filter products based on the selected category
    category_products = Product.objects.filter(category__category_name=category_name, is_active=True)

    # Get the selected price range
    min_price = float(request.GET.get('min_price', 0))
    max_price_param = request.GET.get('max_price')

    if max_price_param is not None:
        max_price = float(max_price_param)
    else:
        # Use a large number instead of infinity
        max_price = 1e20

    # Filter products based on the offer price range
    filtered_products = category_products.filter(offer_price__gte=min_price, offer_price__lte=max_price)

    return render(request, 'accounts/shop.html', {'products': filtered_products})


def filter_products_by_brand(request, brand_name):
    # Filter products based on the selected brand
    brand_products = Product.objects.filter(brand__brand_name=brand_name, is_active=True)

    # Get the selected price range
    min_price = float(request.GET.get('min_price', 0))
    max_price_param = request.GET.get('max_price')

    if max_price_param is not None:
        max_price = float(max_price_param)
    else:
        # Use a large number instead of infinity
        max_price = 1e20

    # Filter products based on the offer price range
    filtered_products = brand_products.filter(offer_price__gte=min_price, offer_price__lte=max_price)

    return render(request, 'accounts/shop.html', {'products': filtered_products})



def about(request):
    return render(request,'accounts/about.html')


def contact(request):
    return render(request,'accounts/contact.html')