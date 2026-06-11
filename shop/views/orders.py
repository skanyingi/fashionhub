from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from shop.models import Order
from django.http import JsonResponse                  
from django.views.decorators.csrf import csrf_exempt           
from shop.models import Order, calculate_delivery_fee              

from .cart import sync_order_items                        

@login_required(login_url="login")
def my_receipts(request):
    """Show all paid orders for the logged-in user."""
    if request.user.is_authenticated:
        orders = Order.objects.filter(buyer=request.user, status="PAID").order_by("-id")
    else:
        orders = []
    return render(request, "shop/my_receipts.html", {"orders": orders})



# display all orders pending or paid for the logged in user
@login_required
def order_history(request):
    """View all pending and paid orders for the logged-in user"""
    orders = Order.objects.filter(buyer=request.user).order_by("-created_at")
    cart = request.session.get("cart", [])
    return render(request, "shop/order_history.html", {"orders": orders, "cart": cart})

# allow user to cance and delete a pending order
@login_required
@require_POST
def delete_pending_order(request, order_id):
    """Allow user to delete/cancel a pending order from their history"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user, status="PENDING")
    order.delete()
    return redirect("order_history")

# allows user to track order
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
            # Look up by email - returns only paid orders
            order = Order.objects.filter(email__iexact=email_input, status="PAID").first()
            if not order:
                error = "No paid order found with that email."
        else:
            error = "Please enter a tracking number or email."
    
    return render(request, "shop/track_order.html", {"cart": cart, "order": order, "error": error})




#update shipping and delivery details for a pending order
@csrf_exempt
@require_POST
@login_required(login_url="login")
def update_shipping(request):
    # Find pending order for logged in user
    order = Order.objects.filter(buyer=request.user, status="PENDING").first()

    if not order:
        return JsonResponse({"error": "No pending order found"}, status=404)

    location = request.POST.get("location", "")
    address = request.POST.get("address", "")
    landmark = request.POST.get("landmark", "")
    email = request.POST.get("email")
    phone_input = request.POST.get("phone")

    # Update order fields with provided shipping details
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

