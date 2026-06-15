import datetime
import base64
import json
import requests
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from shop.models import Product, Order, OrderItem, Receipt, Transaction, calculate_delivery_fee
from shop.utils.mpesa import get_mpesa_access_token
from shop.utils.pdf import generate_receipt_pdf


# initiates an M-Pesa STK push payment request
@login_required(login_url="login")
def stk_push(request, order_id):
    # Verify the order belongs to the current user
    if request.user.is_authenticated:
        order = get_object_or_404(Order, id=order_id, buyer=request.user)
    else:
        guest_order_id = request.session.get("guest_order_id")
        if guest_order_id and str(guest_order_id) == str(order_id):
            order = get_object_or_404(Order, id=order_id, buyer__isnull=True)
        else:
            return JsonResponse({"error": "Unauthorized access to this order"}, status=403)

    # extract and save delivery details from form submission 
    email = request.POST.get("email")
    location = request.POST.get("location")
    address = request.POST.get("address")
    landmark = request.POST.get("landmark")
    phone_input = request.POST.get("phone")

    if phone_input:
        order.phone = phone_input
    if email:
        order.email = email
    if location:
        order.location = location
    if address:
        order.address = address
    if landmark:
        order.landmark = landmark
    
    # Use frontend-calculated delivery fee or but i prefer mostly calculate from location since i use maps API
    delivery_fee_input = request.POST.get("delivery_fee")
    if delivery_fee_input is not None and delivery_fee_input != "":
        order.delivery_fee = int(float(delivery_fee_input))
    elif order.location and order.delivery_fee is None:
        # Fallback to calculated fee if not provided at all
        order.delivery_fee = calculate_delivery_fee(order.location)

    order.save()

    # Get grand total to charge via M-Pesa
    total_amount = order.get_grand_total()
  
    # Generate M-Pesa API authentication timestamp and password
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()
    ).decode() #encrypted authentication string acting as password

    access_token = get_mpesa_access_token() # Get mpesa token access

    if not order.phone:
        return JsonResponse({"error": "Phone number is required"}, status=400)

    # Normalize phone number to 254XXXXXXXX format for M-Pesa
    phone = order.phone.strip()
    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("7") or phone.startswith("1"):
        phone = "254" + phone

    # use order total as amount minimum is 1 KES
    order_total = int(order.get_grand_total())    
    if order_total < 1:
        order_total = 1
    
    print(f"Payment - Order {order.id}: Total items: {order.items.count()}, Subtotal: {order.get_total_amount()}, Delivery: {order.delivery_fee}, Grand Total: {order_total}")

    # Build an STK Push payload for Daraja API to make requests
    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": order_total,
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": f"ORDER-{order.id}",
        "TransactionDesc": "FashionHub Escrow",
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    print("Payload:", payload)
    print("Headers:", headers)

    try:
        # send STK Push request to Safaricom sandbox API  triggers STK prompt on user phone
        response = requests.post(
            "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print("Response status:", response.status_code)
        print("Response text:", response.text[:500] if response.text else "Empty")
        
        if not response.text:
            return HttpResponse("""
                <div style="text-align: center; padding: 20px; background: #f8d7da; color: #721c24; border-radius: 6px; margin: 20px 0;">
                    <h3 style="margin: 0 0 10px 0;">✗ Error</h3>
                    <p style="margin: 0;">Payment service returned empty response. Please try again.</p>
                </div>
            """)
        
        response_data = response.json()
        
        if response_data.get("ResponseCode") == "0":
            # Payment request is sent successfully then store CheckoutRequestID for callback matching 
            checkout_request_id = response_data.get("CheckoutRequestID")
            
            # 3NF Migration: Create a Transaction record
            Transaction.objects.create(
                order=order,
                checkout_request_id=checkout_request_id,
                amount=order_total,
                status="PENDING"
            )
            
            return HttpResponse(f"""
                <div style="text-align: center; padding: 20px; background: #d4edda; color: #155724; border-radius: 6px; margin: 20px 0;">
                    <h3 style="margin: 0 0 10px 0;">✓ Success</h3>
                    <p style="margin: 0;">Payment request sent! Check your phone for the M-Pesa prompt.</p>
                    <div style="margin-top: 15px; padding: 10px; background: white; border-radius: 5px;">
                        <p style="margin: 0 0 5px 0; font-size: 14px;"><strong>Order Number:</strong> {order.tracking_number}</p>
                        <p style="margin: 0; font-size: 12px; color: #666;">Save this to track your order!</p>
                    </div>
                </div>
            """)
        else:
            # M-Pesa returned an error response
            error_message = response_data.get("CustomerMessage", "Payment request failed")
            return HttpResponse(f"""
                <div style="text-align: center; padding: 20px; background: #f8d7da; color: #721c24; border-radius: 6px; margin: 20px 0;">
                    <h3 style="margin: 0 0 10px 0;">✗ Error</h3>
                    <p style="margin: 0;">{error_message}</p>
                </div>
            """)
    except json.JSONDecodeError as e:
        # Response from API was not valid JSON
        print(f"JSON decode error: {e}")
        return HttpResponse(f"""
            <div style="text-align: center; padding: 20px; background: #f8d7da; color: #721c24; border-radius: 6px; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0;">✗ Error</h3>
                <p style="margin: 0;">Invalid response from payment service. Please try again.</p>
            </div>
        """)
    except requests.exceptions.RequestException as e:
        
        print(f"Request error: {e}") # for debugging purposes
        # Network or connection error
        return HttpResponse(f"""
            <div style="text-align: center; padding: 20px; background: #f8d7da; color: #721c24; border-radius: 6px; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0;">✗ Error</h3>
                <p style="margin: 0;">Connection error. Please check your internet and try again.</p>
            </div>
        """)

# Receives and processes M-Pesa payment callback from safaricom after a transaction is completed
@csrf_exempt #  crsf_exempt because django block post requests without CSRF token but safaricom sends external POST requests
def mpesa_callback(request):
    try:
        data = json.loads(request.body) # parse incoming safaricom JSON
        #print("M-Pesa callback received:", data)

        callback = data.get("Body", {}).get("stkCallback", {}) # Extract callbackObject to isolate payment result data
        # ResultCode 0 means payment was successful
        if callback.get("ResultCode") == 0:
            metadata = callback.get("CallbackMetadata", {}).get("Item", []) # Extract callback metadata
            mpesa_receipt_num = None

            # Extract M-Pesa receipt number from callback metadata
            for item in metadata:
                if item.get("Name") == "MpesaReceiptNumber":
                    mpesa_receipt_num = item.get("Value")
                    break

            # Find the exact transaction using CheckoutRequestID
            checkout_request_id = callback.get("CheckoutRequestID")
            transaction = None
            if checkout_request_id:
                transaction = Transaction.objects.filter(checkout_request_id=checkout_request_id).first()
            
            order = None
            if transaction:
                order = transaction.order
            
            # Final fallback to latest pending if ID not found especially for older transactions
            if not order:
                order = Order.objects.filter(status="PENDING").order_by("-id").first()

            if order and mpesa_receipt_num:
                #  Update or create Transaction record
                if transaction:
                    transaction.mpesa_receipt_number = mpesa_receipt_num
                    transaction.status = "SUCCESS"
                    transaction.save()
                else:
                    Transaction.objects.create(
                        order=order,
                        checkout_request_id=checkout_request_id,
                        mpesa_receipt_number=mpesa_receipt_num,
                        amount=order.get_grand_total(),
                        status="SUCCESS"
                    )

                #Mark the order as PAID
                order.status = "PAID"
                order.save()
                #print(f" Order {order.tracking_number} updated - Receipt: {mpesa_receipt_num}, Status: PAID")

                # decrement stock for each product in the order
                for item in order.items.all():
                    product = item.product
                    if product.stock >= item.quantity:
                        product.stock -= item.quantity
                        product.save()
                        print(f"  - Stock updated for {product.name}: {product.stock} left")
                    else:
                        print(f"  - Warning: Low stock for {product.name} ({product.stock} left), cannot decrement fully")
                        product.stock = 0 # Stock Insufficient - set to zero
                        product.save()

                # Generate and save PDF receipt to database
                try:
                    pdf_buffer = generate_receipt_pdf(order)
                    platform_receipt = Receipt.objects.create(
                        order=order,
                        pdf_file=pdf_buffer.getvalue() if pdf_buffer else None,
                    )
                    print(
                        f" Platform receipt created: {platform_receipt.receipt_number}"
                    )

                except Exception as e:
                    print(f" Platform receipt creation failed: {e}")

                # Send confirmation email (backup)
                email = order.email or (order.buyer.email if order.buyer else None)
                if email:
                    try:
                        subject = f"Payment Confirmed - FashionHub Order {order.tracking_number}"
                        
                        # Render HTML message
                        html_content = render_to_string("shop/email_receipt.html", {"order": order})
                        
                        # Create email with both text and HTML versions
                        buyer_name = order.buyer.username if order.buyer else "Guest"
                        text_message = f"Hi {buyer_name}, your payment for order {order.tracking_number} was successful!"
                        
                        email_msg = EmailMultiAlternatives(
                            subject, text_message, settings.EMAIL_HOST_USER, [email]
                        )
                        email_msg.attach_alternative(html_content, "text/html")
                        
                        if pdf_buffer:
                            email_msg.attach(
                                f"Receipt_{order.tracking_number}.pdf",
                                pdf_buffer.getvalue(),
                                "application/pdf",
                            )
                        email_msg.send(fail_silently=False)
                        print(f" Receipt HTML email sent to {email}")
                    except Exception as e:
                        print(f" Email sending failed: {e}")
            else:
                print("No pending order found or no receipt number")
        else:
            # payment was canceled or failed
            result_desc = callback.get("ResultDesc", "Payment failed")
            print(f"Payment failed: {result_desc}")

    except Exception as e:
        print(f"Callback error: {e}")

    return HttpResponse("OK") 


# polls the current order status for HTMX live updates
def check_order_status(request):
    order = None
    if request.user.is_authenticated:
        order = Order.objects.filter(buyer=request.user).order_by("-id").first()
    else:
        order_id = request.session.get("guest_order_id")
        if order_id:
            order = Order.objects.filter(id=order_id).first()

    if order:
        if order.status == "PAID":
            #  clear cart from session cart if it actually has items
            if request.session.get("cart"):
                request.session["cart"] = []
        # continue polling every 3 seconds if order is still pending    
        polling_attr = (
            'hx-get="/check-order-status/" hx-trigger="every 3s" hx-swap="outerHTML"'
            if order.status == "PENDING"
            else ""
        )
        icon = "check-circle" if order.status == "PAID" else "clock-o"
        status_class = order.status.lower()

        return HttpResponse(f"""
        <div id="order-status" {polling_attr}>
            <div class="order-status-badge {status_class}">
                <i class="fa fa-{icon}"></i>
                {order.status}
            </div>
        </div>
        """)
    return HttpResponse("")


# displays order receipt page for a completed paid order
@login_required(login_url="login")
def receipt(request, order_id):
    """Display receipt for a paid order"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)

    # Only show receipt for paid orders
    if order.status != "PAID":
        return redirect("cart")

    # Clear the session cart after successful payment
    request.session["cart"] = []
    
    return render(request, "shop/receipt.html", {"order": order})


# Generate and downloads pdf receipt for a paid order
@login_required(login_url="login")
def download_receipt_pdf(request, order_id):
    """Download receipt as PDF"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)

    if order.status != "PAID":
        return redirect("cart")

    pdf_buffer = generate_receipt_pdf(order)

    if pdf_buffer:
        # return PDF as downloadable file attachment
        response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Receipt_{order.tracking_number}.pdf"'
        )
        return response
    else:
        return HttpResponse(
            "Error generating PDF.",
            status=500,
        )

# tesing endpoint to simulate successful payment
@login_required(login_url="login")
def test_payment(request, order_id):
    """Test endpoint to simulate successful payment """
    order = get_object_or_404(Order, id=order_id, buyer=request.user)

    order.status = "PAID"
    order.save()

    # Create test transaction
    receipt_num = f"TEST{order_id}RECEIPT"
    Transaction.objects.get_or_create(
        order=order,
        mpesa_receipt_number=receipt_num,
        defaults={
            'amount': order.get_grand_total(),
            'status': 'SUCCESS'
        }
    )
    
    return redirect("cart")
