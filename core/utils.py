from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import ProductOrder


def send_order_confirmation_email(order):
    try:
        user = order.user
        print(user, "requested user")

        order_products = ProductOrder.objects.filter(order=order).select_related('product')

        subject = f"Order #{order.order_number} Confirmation"
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]

        # Build full URLs for product images
        order_products_with_urls = []
        
        for product_order in order_products:
            product_data = {
                'product_order': product_order,
                'product': product_order.product,
                'quantity': product_order.quantity,
                'product_price': product_order.product_price,
            }
            
            # Build full image URL
            if product_order.product.product_img1:
                # Create absolute URL for email
                image_url = f"https://shoespace.site{product_order.product.product_img1.url}"
                print(f"Image URL created: {image_url}")
                product_data['image_url'] = image_url
            else:
                product_data['image_url'] = None
                print(f"No image for product: {product_order.product.product_name}")
                
            order_products_with_urls.append(product_data)

        context = {
            'user': user,
            'order': order,
            'order_products': order_products_with_urls,  # Updated to use enhanced data
        }

        html_content = render_to_string('emails/order_confirmation_email.html', context)
        text_content = f"Hi {user.first_name},\nThanks for your order #{order.order_number}."

        email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
        email.attach_alternative(html_content, "text/html")
        print("Sending email...", flush=True)
        email.send(fail_silently=False)
        print("Order confirmation email sent to", user.email, flush=True)
    except Exception as e:
        # Log the error or print it out for now
        print(f"Error sending order confirmation email: {str(e)}")
        import traceback
        traceback.print_exc()  # This will show the full error traceback
