from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import ProductOrder  # import this

def send_order_confirmation_email(order):
    user = order.user
    # ⬇ Use same logic as your view
    order_products = ProductOrder.objects.filter(order=order).select_related('product')

    subject = f"Order #{order.order_number} Confirmation"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    context = {
        'user': user,
        'order': order,
        'order_products': order_products,
    }

    html_content = render_to_string('emails/order_confirmation_email.html', context)
    text_content = f"Hi {user.first_name},\nThanks for your order #{order.order_number}."

    email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    email.attach_alternative(html_content, "text/html")
    email.send()

