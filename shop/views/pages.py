from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

# handles newsletter email subscriptions
@csrf_exempt
def subscribe(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            return JsonResponse(
                {"success": False, "message": "Please enter a valid email address"}
            )

        try:
            # send a welcome email to new subscriber
            subject = "Welcome to FashionHub Newsletter!"
            message = f"""
            Dear Subscriber,

            Thank you for subscribing to FashionHub's newsletter!

            You'll now be the first to know about:
            - Fashion tips and styling advice
            - Upcoming sales and events

            Stay stylish!

            Best regards,
            The FashionHub Team
            """

            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Successfully subscribed! Check your email for confirmation.",
                }
            )

        except Exception as e:
            return JsonResponse(
                {
                    "success": False,
                    "message": f"Subscription failed. Please try again later.",
                }
            )

    return JsonResponse({"success": False, "message": "Invalid request method"})

# display frequently asked questions page
def faq(request):
    return render(request, "shop/faq.html")

# handles contact form submission
def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        # Send contact email to admin email
        try:
            # forward contact message to admin email
            subject = f"Contact Form: Message from {name}"
            admin_message = f"""
            You have received a new contact form submission:
            
            Name: {name}
            Email: {email}
            
            Message:
            {message}
            
            ---
            Reply directly to: {email}
            """

            send_mail(
                subject,
                admin_message,
                settings.EMAIL_HOST_USER,
                [settings.EMAIL_HOST_USER],  # Send to myself
                fail_silently=False,
            )
            # Return success confirmaion HTML
            index_url = reverse("index")
            return HttpResponse(f"""
                <div style="padding: 20px;">
                    <div style="margin-bottom: 20px;">
                        <a href="{index_url}" style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; font-weight: 500;">
                            ← Back to Home
                        </a>
                    </div>
                    <hr style="border: none; border-top: 2px solid #ddd; margin: 20px 0;">
                    <div style="text-align: center; padding: 40px; background: #d4edda; color: #155724; border-radius: 8px;">
                        <h2 style="margin: 0 0 15px 0;">✓ Thank You for Contacting Us!</h2>
                        <p style="margin: 0; font-size: 16px;">We've received your message and will get back to you soon.</p>
                    </div>
                </div>
            """)
        except Exception as e:
            index_url = reverse("index")
            return HttpResponse(f"""
                <div style="padding: 20px;">
                    <div style="margin-bottom: 20px;">
                        <a href="{index_url}" style="display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; font-weight: 500;">
                            ← Back to Home
                        </a>
                    </div>
                    <hr style="border: none; border-top: 2px solid #ddd; margin: 20px 0;">
                    <div style="text-align: center; padding: 40px; background: #f8d7da; color: #721c24; border-radius: 8px;">
                        <h2 style="margin: 0 0 15px 0;">✗ Error</h2>
                        <p style="margin: 0; font-size: 16px;">Failed to send message. Please try again.</p>
                    </div>
                </div>
            """)
    # GET request to display contact form
    return render(request, "shop/contact.html")




#view shipping information page
def shipping_info(request):
    return render(request, "shop/shipping_info.html")

# view returns and refund policy page
def returns(request):
    return render(request, "shop/returns.html")

