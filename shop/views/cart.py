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
from shop.models import Product, Order, OrderItem, Receipt, Report, Review, calculate_delivery_fee
from shop.utils.mpesa import get_mpesa_access_token
from django.template.loader import render_to_string
from io import BytesIO
import datetime
import base64
import requests
import json
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import PasswordResetForm




# displays shopping cart page with all current items
def cart(request):
    # load cart from session
    cart_items = request.session.get("cart", [])
    
    # calculate total price for each item
    for item in cart_items:
        item["total_price"] = item["price"] * item.get("quantity", 1)
    
    # calculate overall cart total
    total = sum(item["total_price"] for item in cart_items)

    # Get last visited shop page for "Continue Shopping" button
    continue_shopping_url = request.session.get('last_shop_url', reverse('women'))

    order = None

    if cart_items:
        # Try to find the most recent order for authenticated or guest user
        if request.user.is_authenticated:
            order = Order.objects.filter(buyer=request.user).order_by("-id").first()
        else:
            order_id = request.session.get("guest_order_id")
            if order_id:
                order = Order.objects.filter(id=order_id).first()

        # Create new  pending order, if none exists or previous is not pending
        if not order or order.status != "PENDING":
            if request.user.is_authenticated:
                order = Order.objects.create(
                    buyer=request.user, status="PENDING", delivery_fee=0
                )
            else:
                # create guest order and store ID in session
                order = Order.objects.create(status="PENDING", delivery_fee=0)
                request.session["guest_order_id"] = order.id

        # Sync cart items with database order and update delivery fee 
        if order and order.status == "PENDING":
            sync_order_items(request, order)

            # Calculate delivery fee from location
            location = request.POST.get("location") or order.location
            if location:
                order.delivery_fee = calculate_delivery_fee(location)
                order.save()

    return render(request, "shop/cart.html", {"cart": cart_items, "total": total, "order": order, "continue_shopping_url": continue_shopping_url}
    )





def add_to_cart(request):
    if request.method == "POST":
        # retreive/load existing cart from session
        try:
            cart = request.session.get("cart", [])
            if not isinstance(cart, list):
                cart = []
        except:
            cart = []

        # read input from form 
        product_id = request.POST.get("product_id")
        size = request.POST.get("size", "")
        quantity = int(request.POST.get("quantity", 1))
        should_redirect = request.POST.get("redirect") == "true"

        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                
                # Check if product has any stock available
                if product.stock <= 0:
                    return HttpResponse(f"""
                        <div style="color: red; padding: 10px; text-align: center;">
                            Sorry, "{product.name}" is out of stock!
                        </div>
                    """, status=400)
                
                # Check  available stock and requested quantity
                available_stock = product.stock
                requested_qty = quantity
                
                # Calculate how many of this items are already in the cart
                current_qty_in_cart = 0
                for item in cart:
                    if item.get("product_id") == str(product_id) and item.get("size") == size:
                        current_qty_in_cart = item.get("quantity", 0)
                        break
                
                # If adding more than available, limit it to prevent exceeding stock
                if current_qty_in_cart + requested_qty > available_stock:
                    requested_qty = max(0, available_stock - current_qty_in_cart)
                    if requested_qty == 0:
                        return HttpResponse(f"""
                            <div style="color: red; padding: 10px; text-align: center;">
                                Sorry, only {available_stock} items available for "{product.name}"
                            </div>
                        """, status=400)
                    quantity = requested_qty
                
                # if item  with same product and size exists, increase quantity
                found = False
                for item in cart:
                    if item.get("product_id") == str(product_id) and item.get("size") == size:
                        item["quantity"] = item.get("quantity", 0) + quantity
                        found = True
                        break
                # if not found, add new item to cart
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
            # Fallback just incase: add by name instead of product_id
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

        request.session["cart"] = cart # save updated cart back to session
        
        # If redirect is set, send user to cart page
        if should_redirect:
            response = HttpResponse("")
            response["HX-Redirect"] = reverse("cart")
            return response

        return HttpResponse(f'''
            <a href="{reverse("cart")}" id="cart-icon" style="position: relative; display: inline-block; font-size: 20px;">
                <i class="fa fa-shopping-cart"></i>
                <span style="position: absolute; top: -8px; right: -8px; background: red; color: white; border-radius: 50%; padding: 2px 6px; font-size: 12px; font-weight: bold;">{len(cart)}</span>
            </a>
        ''')  #return updated cart icon







# updates item quantities in the cart (increase or decrease)
def update_cart(request):
    if request.method == "POST": 
        cart_items = request.session.get("cart", []) # load session cart
        # read user input
        action = request.POST.get("action")
        name = request.POST.get("name")
        # Find item and update its quantity
        for item in cart_items:
            if item["name"] == name:
                if "quantity" not in item:
                    item["quantity"] = 1
                if action == "increase":
                    item["quantity"] += 1
                elif action == "decrease" and item["quantity"] > 1:
                    # prevent quantity from going below 1 or negative
                    item["quantity"] -= 1
                break
        request.session["cart"] = cart_items # save updated cart to session based on action
        
        # recalculate totals for all items
        for item in cart_items:
            item["total_price"] = item["price"] * item.get("quantity", 1)
            
        total = sum(item["total_price"] for item in cart_items)

        # find pending order and sync updated quantities to database
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




# removes a specific item from the shopping cart by name
def remove_item(request):
    if request.method == "POST":
        cart_items = request.session.get("cart", [])  # load cart from session
        name = request.POST.get("name") # read item to remove

        # remove the items with matching name from cart
        cart_items = [item for item in cart_items if item["name"] != name]
        request.session["cart"] = cart_items # save updated cart back to session
        
        #find  pending order for current user
        order = None
        if request.user.is_authenticated:
            order = Order.objects.filter(buyer=request.user, status="PENDING").first()
        else:
            order_id = request.session.get("guest_order_id")
            if order_id:
                order = Order.objects.filter(id=order_id, status="PENDING").first()

        # Delete order from database if cart is now empty
        if not cart_items:
            if order:
                order.delete()
                if not request.user.is_authenticated:
                    if "guest_order_id" in request.session:
                        del request.session["guest_order_id"]
            order = None
        elif order:
            # sync remaining items with database
            sync_order_items(request, order)

        # recalculate totals
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
    





def sync_order_items(request, order):
    """Helper to sync session cart items with database OrderItems"""
    if not order:
        return
        
    cart_items = request.session.get("cart", []) # load cart from session
    # delete all existing order items and rebuild from session cart
    order.items.all().delete()
    
    #loop cart items
    for item in cart_items:
        try:
            # Find product by name to create order item
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