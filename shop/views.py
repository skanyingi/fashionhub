from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.mail import send_mail, EmailMultiAlternatives
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.conf import settings
from .models import Product, Order, OrderItem, Receipt, Report, Review, calculate_delivery_fee
from .utils.mpesa import get_mpesa_access_token
from django.template.loader import render_to_string
from io import BytesIO
import datetime
import base64
import requests
import json
from django.views.decorators.http import require_POST


def generate_receipt_pdf(order):
    """Generate professional PDF receipt for an order"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
            HRFlowable,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, leftMargin=0.5*inch, rightMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle("Title", fontSize=28, textColor=colors.HexColor("#04AA6D"), alignment=1, spaceAfter=10, fontName="Helvetica-Bold")
        success_style = ParagraphStyle("Success", fontSize=18, textColor=colors.black, alignment=1, spaceAfter=5, fontName="Helvetica-Bold")
        subtitle_style = ParagraphStyle("Subtitle", fontSize=12, textColor=colors.grey, alignment=1, spaceAfter=25)
        section_header = ParagraphStyle("SectionHeader", fontSize=10, textColor=colors.HexColor("#333333"), fontName="Helvetica-Bold", spaceAfter=8, leading=12)
        normal_text = ParagraphStyle("NormalText", fontSize=10, textColor=colors.HexColor("#555555"), leading=14)

        # Header
        elements.append(Paragraph("FASHIONHUB", title_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Success Icon (Styled Large Checkmark)
        # icon_style = ParagraphStyle("Icon", fontSize=44, textColor=colors.HexColor("#04AA6D"), alignment=1)
        # elements.append(Paragraph("✔", icon_style))
        elements.append(Spacer(1, 0.1 * inch))

        elements.append(Paragraph("Payment Successful!", success_style))
        elements.append(Spacer(1, 0.05 * inch))
        elements.append(Paragraph("Thank you for your purchase. Your order is being processed.", subtitle_style))
        elements.append(Spacer(1, 0.2 * inch))
        
        # Info Box (Order + Shipping)
        info_data = [
            [
                Paragraph("<b>ORDER DETAILS</b>", section_header),
                Paragraph("<b>SHIPPING TO</b>", section_header)
            ],
            [
                Paragraph(f"Order Number: <b>{order.tracking_number}</b><br/>M-Pesa Receipt: <b>{order.mpesa_receipt or 'N/A'}</b><br/>Date: {order.created_at.strftime('%b %d, %Y %H:%M')}<br/>Status: <font color='#04AA6D'><b>PAID</b></font>", normal_text),
                Paragraph(f"Customer: <b>{order.buyer.username if order.buyer else (order.email or 'Guest')}</b><br/>Phone: {order.phone or 'N/A'}<br/>Location: {order.location or 'N/A'}<br/>Address: {order.address or 'N/A'}", normal_text)
            ]
        ]
        
        info_table = Table(info_data, colWidths=[3.5*inch, 3.5*inch])
        info_table.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f9f9f9")),
            ("TOPPADDING", (0,0), (-1,-1), 15),
            ("BOTTOMPADDING", (0,0), (-1,-1), 15),
            ("LEFTPADDING", (0,0), (-1,-1), 15),
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#eeeeee")),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.4 * inch))

        # Items Header
        elements.append(Paragraph("ITEMS PURCHASED", section_header))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#eeeeee"), spaceAfter=10))
        
        # Items Table
        items_data = [["Product", "Size", "Qty", "Total"]]
        for item in order.items.all():
            items_data.append([
                item.product.name,
                item.size or "N/A",
                str(item.quantity),
                f"KES {item.get_total()}"
            ])

        items_table = Table(items_data, colWidths=[3.8*inch, 1*inch, 0.8*inch, 1.4*inch])
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fdfdfd")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#888888")),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#f0f0f0")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Totals Section (Aligned Right)
        totals_data = [
            ["Subtotal:", f"KES {order.get_total_amount()}"],
            ["Delivery Fee:", f"KES {order.delivery_fee or 0}"],
            ["Grand Total:", f"KES {order.get_grand_total()}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[5.6*inch, 1.4*inch])
        totals_table.setStyle(TableStyle([
            ("ALIGN", (0,0), (-1,-1), "RIGHT"),
            ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
            ("FONTSIZE", (0, 2), (-1, 2), 16),
            ("TEXTCOLOR", (1, 2), (1, 2), colors.HexColor("#04AA6D")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#eeeeee")),
        ]))
        elements.append(totals_table)

        # Footer
        elements.append(Spacer(1, 1.5 * inch))
        footer_style = ParagraphStyle("Footer", fontSize=9, textColor=colors.grey, alignment=1, leading=12)
        elements.append(Paragraph("A copy of this receipt has been sent to your email.<br/>Your order will be delivered within 1-2 days.<br/>Thank you for shopping with <b>FashionHub</b>!<br/>© 2026 FashionHub. All rights reserved.", footer_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    except ImportError:
        print("reportlab not installed. Install with: pip install reportlab")
        return None
    except Exception as e:
        print(f"PDF generation error: {e}")
        return None


def search(request):
    try:
        cart = request.session.get("cart", [])
        if not isinstance(cart, list):
            cart = []
            request.session["cart"] = cart
    except:
        cart = []
        request.session["cart"] = cart

    query = request.GET.get("q", "")
    products = (
        Product.objects.filter(name__icontains=query)
        if query
        else Product.objects.none()
    )

    return render(
        request,
        "shop/search.html",
        {
            "cart": cart,
            "products": products,
            "query": query,
        },
    )


def index(request):
    try:
        cart = request.session.get("cart", [])
        if not isinstance(cart, list):
            cart = []
            request.session["cart"] = cart
    except:
        cart = []
        request.session["cart"] = cart

    return render(request, "shop/index.html", {"cart": cart})


def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        print("Username:", username)
        print("Email:", email)
        print("Password:", password)
        print("Confirm Password:", confirm_password)
        print(username)

        if password != confirm_password:
            return HttpResponse(
                '<div style="color: red; margin-bottom: 10px"> Passwords do not match</div>'
            )

        if User.objects.filter(username=username).exists():
            return HttpResponse(
                '<div style="color: red; margin-bottom: 10px"> Username already taken</div>'
            )
        User.objects.create_user(username=username, email=email, password=password)

        response = HttpResponse("redirect... ")
        response["HX-Redirect"] = "/login"
        return response
    return render(request, "shop/register.html")


from django.contrib.auth.forms import PasswordResetForm

def login_user(request):
    if request.method == "POST":
        # ... (rest of method) ...
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Check if username exists
        try:
            User.objects.get(username=username)
            # Username exists, now check password
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get("next", "index")
                response = HttpResponse("")

                if "/" not in next_url:
                    response["HX-Redirect"] = reverse(next_url)
                else:
                    response["HX-Redirect"] = next_url
                return response
            else:
                return HttpResponse(
                    '<div style="color:red; padding-bottom: 20px;">Invalid password</div>'
                )
        except User.DoesNotExist:
            return HttpResponse(
                '<div style="color:red; padding-bottom: 20px;">Invalid username</div>'
            )

    form = PasswordResetForm()
    return render(request, "shop/login.html", {"form": form})


def women(request):
    try:
        cart = request.session.get("cart", [])
        if not isinstance(cart, list):
            cart = []
            request.session["cart"] = cart
    except:
        cart = []
        request.session["cart"] = cart

    sort = request.GET.get("sort")
    subcategory = request.GET.get("sub")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    products = Product.objects.filter(category__iexact="women")
    if subcategory:
        products = products.filter(subcategory__iexact=subcategory)

    if min_price:
        products = products.filter(price__gte=int(min_price))
    if max_price:
        products = products.filter(price__lte=int(max_price))

    if sort == "low-to-high":
        products = products.order_by("price")
    elif sort == "high-to-low":
        products = products.order_by("-price")

    is_htmx = request.headers.get("HX-Request") == "true"
    template = "shop/product_grid.html" if is_htmx else "shop/women.html"

    # Save current shop page to session for "Continue Shopping" logic
    request.session['last_shop_url'] = request.get_full_path()

    return render(
        request,
        template,
        {
            "cart": cart,
            "products": products,
            "subcategories": ["clothing", "shoes", "handbags"],
            "subcategory": subcategory,
            "min_price": min_price,
            "max_price": max_price,
            "gender": "women",
        },
    )


def men(request):
    try:
        cart = request.session.get("cart", [])
        if not isinstance(cart, list):
            cart = []
            request.session["cart"] = cart
    except:
        cart = []
        request.session["cart"] = cart

    sort = request.GET.get("sort")
    subcategory = request.GET.get("sub")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    products = Product.objects.filter(category__iexact="men")
    if subcategory:
        products = products.filter(subcategory__iexact=subcategory)

    if min_price:
        products = products.filter(price__gte=int(min_price))
    if max_price:
        products = products.filter(price__lte=int(max_price))

    if sort == "low-to-high":
        products = products.order_by("price")
    elif sort == "high-to-low":
        products = products.order_by("-price")

    is_htmx = request.headers.get("HX-Request") == "true"
    template = "shop/product_grid.html" if is_htmx else "shop/men.html"

    # Save current shop page to session for "Continue Shopping" logic
    request.session['last_shop_url'] = request.get_full_path()

    return render(
        request,
        template,
        {
            "cart": cart,
            "products": products,
            "subcategories": ["clothing", "shoes", "watches"],
            "subcategory": subcategory,
            "min_price": min_price,
            "max_price": max_price,
            "gender": "men",
        },
    )


def add_to_cart(request):
    if request.method == "POST":
        try:
            cart = request.session.get("cart", [])
            if not isinstance(cart, list):
                cart = []
        except:
            cart = []

        product_id = request.POST.get("product_id")
        size = request.POST.get("size", "")
        quantity = int(request.POST.get("quantity", 1))
        should_redirect = request.POST.get("redirect") == "true"

        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                
                # Check if product is in stock
                if product.stock <= 0:
                    return HttpResponse(f"""
                        <div style="color: red; padding: 10px; text-align: center;">
                            Sorry, "{product.name}" is out of stock!
                        </div>
                    """, status=400)
                
                # Check if requested quantity exceeds available stock
                available_stock = product.stock
                requested_qty = quantity
                
                # Check current quantity in cart
                current_qty_in_cart = 0
                for item in cart:
                    if item.get("product_id") == str(product_id) and item.get("size") == size:
                        current_qty_in_cart = item.get("quantity", 0)
                        break
                
                # If adding more than available, limit it
                if current_qty_in_cart + requested_qty > available_stock:
                    requested_qty = max(0, available_stock - current_qty_in_cart)
                    if requested_qty == 0:
                        return HttpResponse(f"""
                            <div style="color: red; padding: 10px; text-align: center;">
                                Sorry, only {available_stock} items available for "{product.name}"
                            </div>
                        """, status=400)
                    quantity = requested_qty
                
                # Check if item already exists in cart with same size
                found = False
                for item in cart:
                    if item.get("product_id") == str(product_id) and item.get("size") == size:
                        item["quantity"] = item.get("quantity", 0) + quantity
                        found = True
                        break
                
                if not found:
                    item = {
                        "product_id": str(product_id),
                        "name": product.name,
                        "price": int(product.price),
                        "image": product.image.url if product.image else "",
                        "quantity": quantity,
                        "size": size,
                        "description": product.description,
                    }
                    cart.append(item)
            except Product.DoesNotExist:
                return HttpResponse("Product not found", status=404)
        else:
            # Fallback for old implementation if needed
            name = request.POST.get("name")
            found = False
            for item in cart:
                if item["name"] == name and item.get("size") == size:
                    item["quantity"] = item.get("quantity", 0) + quantity
                    found = True
                    break
            
            if not found:
                item = {
                    "name": name,
                    "price": int(request.POST.get("price", 0)),
                    "image": request.POST.get("image"),
                    "quantity": quantity,
                    "size": size,
                }
                cart.append(item)

        request.session["cart"] = cart
        
        if should_redirect:
            response = HttpResponse("")
            response["HX-Redirect"] = reverse("cart")
            return response

        return HttpResponse(f'''
            <a href="{reverse("cart")}" id="cart-icon" style="position: relative; display: inline-block; font-size: 20px;">
                <i class="fa fa-shopping-cart"></i>
                <span style="position: absolute; top: -8px; right: -8px; background: red; color: white; border-radius: 50%; padding: 2px 6px; font-size: 12px; font-weight: bold;">{len(cart)}</span>
            </a>
        ''')


def sync_order_items(request, order):
    """Helper to sync session cart items with database OrderItems"""
    if not order:
        return
        
    cart_items = request.session.get("cart", [])
    # Clear existing items and rebuild to ensure accuracy
    order.items.all().delete()
    
    for item in cart_items:
        try:
            # Try to find product by name (how session currently stores it)
            product = Product.objects.get(name=item["name"])
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item.get("quantity", 1),
                price=product.price,
                size=item.get("size", ""),
            )
        except Product.DoesNotExist:
            print(f"Sync error: Product {item['name']} not found")
        except Exception as e:
            print(f"Sync error: {e}")
            
    order.save()


def cart(request):
    cart_items = request.session.get("cart", [])

    for item in cart_items:
        item["total_price"] = item["price"] * item.get("quantity", 1)

    total = sum(item["total_price"] for item in cart_items)

    # Use session-stored shop URL for "Continue Shopping"
    continue_shopping_url = request.session.get('last_shop_url', reverse('women'))

    order = None

    if cart_items:
        # 1. Try to find the most recent order
        if request.user.is_authenticated:
            order = Order.objects.filter(buyer=request.user).order_by("-id").first()
        else:
            order_id = request.session.get("guest_order_id")
            if order_id:
                order = Order.objects.filter(id=order_id).first()

        # 2. If we have items but no pending order, create one
        if not order or order.status != "PENDING":
            if request.user.is_authenticated:
                order = Order.objects.create(
                    buyer=request.user, status="PENDING", delivery_fee=0
                )
            else:
                order = Order.objects.create(status="PENDING", delivery_fee=0)
                request.session["guest_order_id"] = order.id

        # 3. Sync and update if it's a pending order
        if order and order.status == "PENDING":
            sync_order_items(request, order)

            # Calculate delivery fee from location
            location = request.POST.get("location") or order.location
            if location:
                order.delivery_fee = calculate_delivery_fee(location)
                order.save()

    return render(        request, "shop/cart.html", {"cart": cart_items, "total": total, "order": order, "continue_shopping_url": continue_shopping_url}
    )


def update_cart(request):
    if request.method == "POST":
        cart_items = request.session.get("cart", [])
        action = request.POST.get("action")
        name = request.POST.get("name")

        for item in cart_items:
            if item["name"] == name:
                if "quantity" not in item:
                    item["quantity"] = 1
                if action == "increase":
                    item["quantity"] += 1
                elif action == "decrease" and item["quantity"] > 1:
                    item["quantity"] -= 1
                break
        request.session["cart"] = cart_items
        
        for item in cart_items:
            item["total_price"] = item["price"] * item.get("quantity", 1)
            
        total = sum(item["total_price"] for item in cart_items)

        order = None
        if request.user.is_authenticated:
            order = Order.objects.filter(buyer=request.user, status="PENDING").first()
        else:
            order_id = request.session.get("guest_order_id")
            if order_id:
                order = Order.objects.filter(id=order_id, status="PENDING").first()

        if order:
            sync_order_items(request, order)

        # Determine where to send user back when they click "Continue Shopping"
        referer = request.META.get('HTTP_REFERER', '')
        continue_shopping_url = reverse('women')
        if 'men' in referer:
            continue_shopping_url = reverse('men')
        elif 'women' in referer:
            continue_shopping_url = reverse('women')

        return render(
            request,
            "shop/cart_items.html",
            {"cart": cart_items, "total": total, "order": order, "continue_shopping_url": continue_shopping_url},
        )


def remove_item(request):
    if request.method == "POST":
        cart_items = request.session.get("cart", [])
        name = request.POST.get("name")

        cart_items = [item for item in cart_items if item["name"] != name]
        request.session["cart"] = cart_items

        order = None
        if request.user.is_authenticated:
            order = Order.objects.filter(buyer=request.user, status="PENDING").first()
        else:
            order_id = request.session.get("guest_order_id")
            if order_id:
                order = Order.objects.filter(id=order_id, status="PENDING").first()

        # Delete order if cart is empty
        if not cart_items:
            if order:
                order.delete()
                if not request.user.is_authenticated:
                    if "guest_order_id" in request.session:
                        del request.session["guest_order_id"]
            order = None
        elif order:
            sync_order_items(request, order)

        for item in cart_items:
            item["total_price"] = item["price"] * item.get("quantity", 1)

        total = sum(item["total_price"] for item in cart_items)

        # Determine where to send user back when they click "Continue Shopping"
        referer = request.META.get('HTTP_REFERER', '')
        continue_shopping_url = reverse('women')
        if 'men' in referer:
            continue_shopping_url = reverse('men')
        elif 'women' in referer:
            continue_shopping_url = reverse('women')

        return render(
            request,
            "shop/cart_items.html",
            {"cart": cart_items, "total": total, "order": order, "continue_shopping_url": continue_shopping_url},
        )


@login_required(login_url="login")
def stk_push(request, order_id):
    # Verify ownership before proceeding
    if request.user.is_authenticated:
        order = get_object_or_404(Order, id=order_id, buyer=request.user)
    else:
        # This part should theoretically not be reached if @login_required works,
        # but kept for robustness.
        guest_order_id = request.session.get("guest_order_id")
        if guest_order_id and str(guest_order_id) == str(order_id):
            order = get_object_or_404(Order, id=order_id, buyer__isnull=True)
        else:
            return JsonResponse({"error": "Unauthorized access to this order"}, status=403)

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
    
    # Use frontend-calculated delivery fee if provided
    delivery_fee_input = request.POST.get("delivery_fee")
    if delivery_fee_input is not None and delivery_fee_input != "":
        order.delivery_fee = int(float(delivery_fee_input))
    elif order.location and order.delivery_fee is None:
        # Fallback to calculated fee if not provided at all
        order.delivery_fee = calculate_delivery_fee(order.location)

    order.save()

    # Recalculate total for M-Pesa to ensure accuracy
    total_amount = order.get_grand_total()
    
    # Debug log to verify calculation
    print(f"STK Push: Subtotal={order.get_total_amount()}, Delivery={order.delivery_fee}, Total={total_amount}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(
        f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()
    ).decode()

    access_token = get_mpesa_access_token()

    if not order.phone:
        return JsonResponse({"error": "Phone number is required"}, status=400)

    phone = order.phone.strip()

    phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("7") or phone.startswith("1"):
        phone = "254" + phone

    # ALWAYS use the order's calculated total, not the form's submitted amount
    # This ensures correct amount is charged regardless of what was submitted
    order_total = int(order.get_grand_total())
    
    # Ensure minimum amount is 1 (M-Pesa requirement)
    if order_total < 1:
        order_total = 1
    
    print(f"Payment - Order {order.id}: Total items: {order.items.count()}, Subtotal: {order.get_total_amount()}, Delivery: {order.delivery_fee}, Grand Total: {order_total}")

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
            # Store CheckoutRequestID so the callback can find this exact order
            order.checkout_request_id = response_data.get("CheckoutRequestID")
            order.save()
            
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
            error_message = response_data.get("CustomerMessage", "Payment request failed")
            return HttpResponse(f"""
                <div style="text-align: center; padding: 20px; background: #f8d7da; color: #721c24; border-radius: 6px; margin: 20px 0;">
                    <h3 style="margin: 0 0 10px 0;">✗ Error</h3>
                    <p style="margin: 0;">{error_message}</p>
                </div>
            """)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return HttpResponse(f"""
            <div style="text-align: center; padding: 20px; background: #f8d7da; color: #721c24; border-radius: 6px; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0;">✗ Error</h3>
                <p style="margin: 0;">Invalid response from payment service. Please try again.</p>
            </div>
        """)
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return HttpResponse(f"""
            <div style="text-align: center; padding: 20px; background: #f8d7da; color: #721c24; border-radius: 6px; margin: 20px 0;">
                <h3 style="margin: 0 0 10px 0;">✗ Error</h3>
                <p style="margin: 0;">Connection error. Please check your internet and try again.</p>
            </div>
        """)


@csrf_exempt
def mpesa_callback(request):
    try:
        data = json.loads(request.body)
        print("M-Pesa callback received:", data)

        callback = data.get("Body", {}).get("stkCallback", {})

        if callback.get("ResultCode") == 0:
            metadata = callback.get("CallbackMetadata", {}).get("Item", [])
            mpesa_receipt_num = None

            for item in metadata:
                if item.get("Name") == "MpesaReceiptNumber":
                    mpesa_receipt_num = item.get("Value")
                    break

            # FIND THE EXACT ORDER using CheckoutRequestID
            checkout_request_id = callback.get("CheckoutRequestID")
            order = None
            if checkout_request_id:
                order = Order.objects.filter(checkout_request_id=checkout_request_id).first()
            
            # Fallback to latest pending if ID not found (for older transactions)
            if not order:
                order = Order.objects.filter(status="PENDING").order_by("-id").first()

            if order and mpesa_receipt_num:
                # Ensure the order isn't empty before marking paid
                if not order.items.exists():
                    print(f"Warning: Attempting to mark empty order {order.id} as PAID. Syncing now...")
                    # Try to sync from session if possible, but callback is often asynchronous
                    # Better to log this as a warning for now
                
                order.mpesa_receipt = mpesa_receipt_num
                order.status = "PAID"
                order.save()
                print(f"✓ Order {order.tracking_number} updated - Receipt: {mpesa_receipt_num}, Status: PAID")

                # DECREMENT STOCK for each item in the order
                for item in order.items.all():
                    product = item.product
                    if product.stock >= item.quantity:
                        product.stock -= item.quantity
                        product.save()
                        print(f"  - Stock updated for {product.name}: {product.stock} left")
                    else:
                        print(f"  - Warning: Low stock for {product.name} ({product.stock} left), cannot decrement fully")
                        product.stock = 0 # Empty stock
                        product.save()

                # Create platform receipt
                try:
                    pdf_buffer = generate_receipt_pdf(order)
                    platform_receipt = Receipt.objects.create(
                        order=order,
                        pdf_file=pdf_buffer.getvalue() if pdf_buffer else None,
                    )
                    print(
                        f"✓ Platform receipt created: {platform_receipt.receipt_number}"
                    )
                except Exception as e:
                    print(f"✗ Platform receipt creation failed: {e}")

                # Send confirmation email (backup)
                email = order.email or (order.buyer.email if order.buyer else None)
                if email:
                    try:
                        subject = f"Payment Confirmed - FashionHub Order {order.tracking_number}"
                        
                        # Render HTML message
                        html_content = render_to_string("shop/email_receipt.html", {"order": order})
                        
                        # Create email with both text and HTML versions
                        buyer_name = order.buyer.username if order.buyer else (order.email or "Guest")
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
                        print(f"✓ Receipt HTML email sent to {email}")
                    except Exception as e:
                        print(f"✗ Email sending failed: {e}")
            else:
                print("No pending order found or no receipt number")
        else:
            result_desc = callback.get("ResultDesc", "Payment failed")
            print(f"Payment failed: {result_desc}")

    except Exception as e:
        print(f"Callback error: {e}")

    return HttpResponse("OK")


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get("cart", [])
    
    # Get related products (same subcategory first, then same category, excluding current product)
    related_products = Product.objects.filter(
        subcategory__iexact=product.subcategory,
        category__iexact=product.category
    ).exclude(id=product.id)[:4]
    
    # If not enough in same subcategory, pad with items from same category
    if related_products.count() < 4:
        additional_count = 4 - related_products.count()
        additional_products = Product.objects.filter(
            category__iexact=product.category
        ).exclude(
            id__in=[product.id] + [p.id for p in related_products]
        )[:additional_count]
        related_products = list(related_products) + list(additional_products)
    
    # Get reviews from database
    reviews = Review.objects.filter(product=product).order_by("-created_at")
    
    # Calculate average rating
    avg_rating = 0
    if reviews.exists():
        avg_rating = round(sum(r.rating for r in reviews) / reviews.count(), 1)
    
    return render(request, "shop/product_detail.html", {
        "product": product,
        "cart": cart,
        "related_products": related_products,
        "reviews": reviews,
        "avg_rating": avg_rating,
        "review_count": reviews.count(),
    })


@require_POST
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    name = request.POST.get("name", "").strip()
    rating = int(request.POST.get("rating", 5))
    comment = request.POST.get("comment", "").strip()
    
    if not name or not comment:
        return JsonResponse({"success": False, "error": "Please fill in all fields"})
    
    if rating < 1 or rating > 5:
        rating = 5
    
    Review.objects.create(
        product=product,
        name=name,
        rating=rating,
        comment=comment
    )
    
    return JsonResponse({"success": True})


def featured_products(request):
    sort_order = request.GET.get("sort", "default")

    if sort_order == "low-to-high":
        products = Product.objects.all().order_by("price")
    elif sort_order == "high-to-low":
        products = Product.objects.all().order_by("-price")
    else:
        products = Product.objects.all()

    return render(
        request, "shop/featured.html", {"products": products, "sort_order": sort_order}
    )


@csrf_exempt
def subscribe(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            return JsonResponse(
                {"success": False, "message": "Please enter a valid email address"}
            )

        try:
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


def faq(request):
    return render(request, "shop/faq.html")


def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        # Send contact email to admin
        try:
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

    return render(request, "shop/contact.html")


def shipping_info(request):
    return render(request, "shop/shipping_info.html")


def returns(request):
    return render(request, "shop/returns.html")


def logout_view(request):
    logout(request)
    return redirect("index")


# @user_passes_test(lambda u: u.is_staff)
def inventory(request):
    """Dashboard for tracking orders and product inventory - Admin only"""
    # Get all orders
    orders = Order.objects.all().order_by("-id")[:20]

    # Get statistics
    total_orders = Order.objects.count()
    paid_orders = Order.objects.filter(status="PAID").count()
    pending_orders = Order.objects.filter(status="PENDING").count()

    # Calculate total revenue from OrderItems (3NF compliant)
    paid_order_ids = Order.objects.filter(status="PAID").values_list("id", flat=True)
    total_revenue = (
        OrderItem.objects.filter(order_id__in=paid_order_ids).aggregate(
            total=models.Sum(models.F("quantity") * models.F("price"))
        )["total"]
        or 0
    )

    # Get products by category
    women_products = Product.objects.filter(category="women").order_by("name")
    men_products = Product.objects.filter(category="men").order_by("name")

    return render(
        request,
        "shop/inventory.html",
        {
            "orders": orders,
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "pending_orders": pending_orders,
            "total_revenue": total_revenue,
            "women_products": women_products,
            "men_products": men_products,
        },
    )


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
            # ONLY clear the session cart if it actually has items.
            # This prevents clearing the cart for subsequent shopping trips
            # if this polling view is somehow still active or triggered.
            if request.session.get("cart"):
                request.session["cart"] = []
            
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


@login_required(login_url="login")
def receipt(request, order_id):
    """Display receipt for a paid order"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)

    if order.status != "PAID":
        return redirect("cart")

    # Clear the session cart when viewing receipt
    request.session["cart"] = []
    
    return render(request, "shop/receipt.html", {"order": order})


@login_required(login_url="login")
def download_receipt_pdf(request, order_id):
    """Download receipt as PDF"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)

    if order.status != "PAID":
        return redirect("cart")

    pdf_buffer = generate_receipt_pdf(order)

    if pdf_buffer:
        response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Receipt_{order.tracking_number}.pdf"'
        )
        return response
    else:
        return HttpResponse(
            "Error generating PDF. Please install reportlab: pip install reportlab",
            status=500,
        )


@login_required(login_url="login")
def test_payment(request, order_id):
    """Test endpoint to simulate successful payment (FOR TESTING ONLY)"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)

    order.status = "PAID"
    order.mpesa_receipt = f"TEST{order_id}RECEIPT"
    order.save()
    return redirect("cart")


@csrf_exempt
@require_POST
@login_required(login_url="login")
def update_shipping(request):
    # Find order for logged in user
    order = Order.objects.filter(buyer=request.user, status="PENDING").first()

    if not order:
        return JsonResponse({"error": "No pending order found"}, status=404)

    location = request.POST.get("location", "")
    address = request.POST.get("address", "")
    landmark = request.POST.get("landmark", "")
    email = request.POST.get("email")
    phone_input = request.POST.get("phone")

    # Update order details
    if location:
        order.location = location
        order.delivery_fee = calculate_delivery_fee(location)
    if address:
        order.address = address
    if landmark:
        order.landmark = landmark
    if email:
        order.email = email
    if phone_input:
        order.phone = phone_input
        
    order.save()
    
    # Sync items from session just in case
    sync_order_items(request, order)
    
    return JsonResponse({
        "status": "success", 
        "delivery_fee": order.delivery_fee,
        "grand_total": order.get_grand_total()
    })

@login_required(login_url="login")
def my_receipts(request):
    """Show all paid orders for the logged-in user."""
    if request.user.is_authenticated:
        orders = Order.objects.filter(buyer=request.user, status="PAID").order_by("-id")
    else:
        orders = []
    return render(request, "shop/my_receipts.html", {"orders": orders})


def run_report_generation():
    """Helper to update or create the 5 standard reports with latest data"""
    now = datetime.datetime.now()
    timestamp_str = now.strftime('%b %d, %I:%M:%S %p')
    
    # Pre-clean: If there are multiple reports of the same type (from previous clutter), 
    # delete them so update_or_create doesn't crash.
    for r_type in ["sales", "inventory", "orders", "customers", "products", "bestsellers"]:
        existing = Report.objects.filter(report_type=r_type)
        if existing.count() > 1:
            existing.delete()

    # 1. Sales Report - Only include orders that actually have items
    paid_orders = Order.objects.filter(status="PAID").order_by("-created_at")
    valid_paid_orders = [o for o in paid_orders if o.items.exists()]
    total_revenue = sum(o.get_grand_total() for o in valid_paid_orders)
    
    Report.objects.update_or_create(
        report_type="sales",
        defaults={
            "title": f"Sales Summary Report ({timestamp_str})",
            "data": {
                "last_updated": timestamp_str,
                "total_orders": len(valid_paid_orders),
                "total_revenue": total_revenue,
                "items": [
                    {"tracking": o.tracking_number, "amount": o.get_grand_total(), "date": o.created_at.strftime("%Y-%m-%d %H:%M")}
                    for o in valid_paid_orders[:20]
                ],
            }
        }
    )

    # 2. Inventory Report
    products = Product.objects.all().order_by("stock")
    Report.objects.update_or_create(
        report_type="inventory",
        defaults={
            "title": f"Stock Alert Report ({timestamp_str})",
            "data": {
                "last_updated": timestamp_str,
                "total_products": products.count(),
                "low_stock": products.filter(stock__lt=10).count(),
                "items": [{"name": p.name, "stock": p.stock, "price": p.price} for p in products[:20]],
            }
        }
    )

    # 3. Orders Report
    all_orders = Order.objects.all().order_by("-created_at")
    Report.objects.update_or_create(
        report_type="orders",
        defaults={
            "title": f"Order Status Report ({timestamp_str})",
            "data": {
                "last_updated": timestamp_str,
                "total_orders": all_orders.count(),
                "pending": all_orders.filter(status="PENDING").count(),
                "paid": all_orders.filter(status="PAID").count(),
                "items": [
                    {
                        "tracking": o.tracking_number, 
                        "email": o.email or (o.buyer.email if o.buyer else "N/A"),
                        "status": o.status, 
                        "total": o.get_grand_total()
                    }
                    for o in all_orders[:20]
                ],
            }
        }
    )

    # 4. Customer Report
    customers = User.objects.annotate(
        total_orders_count=models.Count("orders"),
        paid_orders_count=models.Count("orders", filter=models.Q(orders__status="PAID"))
    ).filter(total_orders_count__gt=0).order_by("-paid_orders_count", "-total_orders_count")
    
    Report.objects.update_or_create(
        report_type="customers",
        defaults={
            "title": f"Customer Leaders Report ({timestamp_str})",
            "data": {
                "last_updated": timestamp_str,
                "total_customers": User.objects.count(),
                "users_with_orders": customers.count(),
                "items": [
                    {
                        "Username": u.username, 
                        "Email": u.email,
                        "Total Orders": u.total_orders_count,
                        "Paid Orders": u.paid_orders_count
                    } 
                    for u in customers[:20]
                ],
            }
        }
    )

    # 5. Product Report
    all_products = list(Product.objects.all())
    all_products.sort(key=lambda p: p.get_avg_rating(), reverse=True)
    Report.objects.update_or_create(
        report_type="products",
        defaults={
            "title": f"Top Rated Products Report ({timestamp_str})",
            "data": {
                "last_updated": timestamp_str,
                "items": [{"name": p.name, "rating": p.get_avg_rating(), "reviews": p.get_review_count()} for p in all_products[:20]]
            }
        }
    )

    # 6. Best Sellers Report - Show ALL products including those with 0 sales
    from django.db.models import Sum, F, Q, OuterRef, Subquery
    
    # Get products that have been sold
    products_with_sales = OrderItem.objects.filter(
        order__status="PAID"
    ).values(
        "product"
    ).annotate(
        total_sold=Sum("quantity")
    )
    
    # Get all products
    all_products = Product.objects.all()
    
    # Build the list - include all products
    best_sellers_items = []
    for product in all_products:
        # Get total sold for this product
        sold_data = OrderItem.objects.filter(
            product=product,
            order__status="PAID"
        ).aggregate(total_sold=Sum("quantity"))
        
        total_sold = sold_data["total_sold"] or 0
        
        best_sellers_items.append({
            "Product Name": product.name,
            "Selling Price": product.price,
            "Quantity Sold": total_sold,
            "Revenue": total_sold * product.price,
            "Current Stock": product.stock
        })
    
    # Sort by quantity sold (highest first), take top 30
    best_sellers_items = sorted(best_sellers_items, key=lambda x: x["Quantity Sold"], reverse=True)[:30]

    Report.objects.update_or_create(
        report_type="bestsellers",
        defaults={
            "title": f"Top Best Sellers Report ({timestamp_str})",
            "data": {
                "last_updated": timestamp_str,
                "items": best_sellers_items,
            }
        }
    )


@login_required
def generate_all_reports(request):
    """Manual trigger to refresh reports (now just calls the helper)"""
    if not request.user.is_staff:
        return redirect("index")
    run_report_generation()
    return redirect("reports")


from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def reports(request):
    """View all reports - auto-updates data on page load"""
    run_report_generation()
        
    cart = request.session.get("cart", [])
    reports = Report.objects.all().order_by("report_type")  # Stable order
    return render(request, "shop/reports.html", {"reports": reports, "cart": cart})


@staff_member_required
def report_detail(request, report_id):
    """View a specific report"""
    cart = request.session.get("cart", [])
    report = Report.objects.get(id=report_id)
    return render(request, "shop/report_detail.html", {"report": report, "cart": cart})


@login_required
def order_history(request):
    """View all pending and paid orders for the logged-in user"""
    orders = Order.objects.filter(buyer=request.user).order_by("-created_at")
    cart = request.session.get("cart", [])
    return render(request, "shop/order_history.html", {"orders": orders, "cart": cart})


@login_required
@require_POST
def delete_pending_order(request, order_id):
    """Allow user to delete/cancel a pending order from their history"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user, status="PENDING")
    order.delete()
    return redirect("order_history")


def track_order(request):
    """Track order by tracking number or email"""
    cart = request.session.get("cart", [])
    order = None
    error = None
    
    if request.method == "POST":
        tracking_input = request.POST.get("tracking_number", "").strip()
        email_input = request.POST.get("email", "").strip()
        
        if tracking_input:
            # Look up by tracking number
            order = Order.objects.filter(tracking_number__iexact=tracking_input).first()
            if not order:
                error = "No order found with that tracking number."
        elif email_input:
            # Look up by email
            order = Order.objects.filter(email__iexact=email_input, status="PAID").first()
            if not order:
                error = "No paid order found with that email."
        else:
            error = "Please enter a tracking number or email."
    
    return render(request, "shop/track_order.html", {"cart": cart, "order": order, "error": error})
