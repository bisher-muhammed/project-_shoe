import random
import re
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.cache import cache_control, never_cache
from django.http import HttpResponse
from django.conf import settings

# Import your models
from adminapp.models import Product, Category, Offer, Brand, Banner  








@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
def home(request):
    if request.user.is_superuser:
        return redirect('admin_home') 
    

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
            Q(product_description__icontains=search_query)|
            Q(category__category_name__icontains=search_query) |
            Q(brand__brand_name__icontains=search_query)
            
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

    



@never_cache
def login_view(request):
    if "username" in request.session:
        return redirect("home")

    context = {
        "email_value": "",  # to retain entered email on form reload
    }

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        context["email_value"] = email  # Preserve input on failed attempt

        # Server-side validations
        if not email or not password:
            messages.warning(request, "Please fill in both email and password.")
            return render(request, "accounts/login_view.html", context)

        if len(password) < 8:
            messages.warning(request, "Password must be at least 8 characters.")
            return render(request, "accounts/login_view.html", context)

        user = authenticate(request, username=email, password=password)

        if user is not None and user.is_active:
            login(request, user)
            request.session["username"] = user.username
            messages.success(request, "Logged in successfully.")
            return redirect("home")
        else:
            messages.error(request, "Invalid email or password.")
            return render(request, "accounts/login_view.html", context)

    return render(request, "accounts/login_view.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
def signup_view(request):
    context = {
        "username_value": "",
        "email_value": "",
    }

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        # Pre-fill form fields with user input in case of error
        context["username_value"] = username
        context["email_value"] = email

        # Required field check
        if not username or not email or not password or not confirm_password:
            messages.error(request, "All fields are required.")
            return render(request, "accounts/signup_view.html", context)

        # Username checks
        if len(username) > 20:
            messages.error(request, "Username must be under 20 characters.")
            return render(request, "accounts/signup_view.html", context)

        if not username.isalnum():
            messages.warning(request, "Username must be alphanumeric.")
            return render(request, "accounts/signup_view.html", context)

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, "accounts/signup_view.html", context)

        # Email validation
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email format.")
            return render(request, "accounts/signup_view.html", context)

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return render(request, "accounts/signup_view.html", context)

        # Password checks
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "accounts/signup_view.html", context)

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, "accounts/signup_view.html", context)

        password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).+$'
        if not re.match(password_pattern, password):
            messages.error(
                request,
                "Password must contain uppercase, lowercase, number, and special character."
            )
            return render(request, "accounts/signup_view.html", context)

        # Save safe values to session if needed for OTP or next steps
        request.session["uname"] = username
        request.session["email"] = email
        request.session['password'] = password
        request.session["verification_type"] = "signup_view"

        send_otp(request)
        return render(request, "accounts/verify_otp.html", {"email": email})

    return render(request, "accounts/signup_view.html", context)


@never_cache
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
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
        "bisherp297@gmail.com",
        [email],
        fail_silently=False,
    )
    return render(request, "accounts/verify_otp.html", {"email": email})



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
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



@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
def resend_otp(request):
    new_otp = "".join([str(random.randint(0, 9)) for _ in range(4)])
    print(new_otp)
    email = request.session.get("email")
    send_mail(
        "New OTP for Sign Up",
        new_otp,
        "bisherp297@gmail.com",
        [email],
        fail_silently=False,
    )
    request.session["otp"] = new_otp
    return redirect("otp_page")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
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

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
def confirm_password(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        password = request.POST.get("password1")
        confirm_password = request.POST.get("password2")

        if password != confirm_password:
            messages.warning(request, "Passwords do not match")
            return redirect("confirm_password")

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, "accounts/confirm_password.html")

        password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).+$'
        if not re.match(password_pattern, password):
            messages.error(
                request,
                "Password must contain uppercase, lowercase, number, and special character."
            )
            return render(request, "accounts/confirm_password.html")

        email = request.session.get("email")
        if not email:
            messages.error(request, "Session expired or invalid email.")
            return redirect("signup_view")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect("signup_view")

        user.set_password(password)
        user.save()

        authenticated_user = authenticate(request, username=user.username, password=password)
        if authenticated_user:
            login(request, authenticated_user)

        messages.success(request, "Password reset successful.")
        return redirect("login_view")

    return render(request, "accounts/confirm_password.html")






@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('login_view')


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
def about(request):
    return render(request,'accounts/about.html')

