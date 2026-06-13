import datetime
from django.shortcuts import render, redirect
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from shop.models import Product, Order, OrderItem, Report


# Admin Dashboard for managing orders and product inventory
def inventory(request):
    """Dashboard for tracking orders and product inventory - Admin only"""
    # Get most receent 20 orders
    orders = Order.objects.all().order_by("-id")[:20]

    # Calculate order statistics
    total_orders = Order.objects.count()
    paid_orders = Order.objects.filter(status="PAID").count()
    pending_orders = Order.objects.filter(status="PENDING").count()

    # Calculate total revenue from paid order items 
    paid_order_ids = Order.objects.filter(status="PAID").values_list("id", flat=True)
    total_revenue = (
        OrderItem.objects.filter(order_id__in=paid_order_ids).aggregate(
            total=models.Sum(models.F("quantity") * models.F("unit_price_at_purchase"))
        )["total"]
        or 0
    )

    # Get products by gender category
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









# generates or updates all six standard business reports
def run_report_generation():
    """Helper to update or create the 5 standard reports with latest data"""
    now = datetime.datetime.now()
    timestamp_str = now.strftime('%b %d, %I:%M:%S %p')
    
    # clean up duplicate reports of same type before regenerating 
    for r_type in ["sales", "inventory", "orders", "customers", "products", "bestsellers"]:
        existing = Report.objects.filter(report_type=r_type)
        if existing.count() > 1:
            existing.delete()

    #  1. Sales Report - revenue and order summary for paid orders with items
    paid_orders = Order.objects.filter(status="PAID").order_by("-created_at")
    valid_paid_orders = [o for o in paid_orders if o.items.exists()] # filter orders that atually contain items 
    total_revenue = sum(o.get_grand_total() for o in valid_paid_orders)
    #save /update sales reports
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

    # 2. Inventory Report - stock levels with low stock alerts
    products = Product.objects.all().order_by("stock") # gt products sorted by stock
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

    # 3. Orders Report with all order statuses and counts
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

    # 4. Customer Report -  users ranked by number of paid orders
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

    # 5. Product Report - products ranked by avearate customer rating
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

    # 6. Best Sellers Report - products ranked by quantity sold incuding zero sales
    from django.db.models import Sum, F, Q, OuterRef, Subquery
    from django.db.models.functions import Coalesce
    
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
        # Get total sunits sold from paid orders
        sold_data = OrderItem.objects.filter(
            product=product,
            order__status="PAID"
        ).aggregate(
            total_sold=Sum("quantity"),
            total_revenue=Sum(F("quantity") * F("unit_price_at_purchase"))
        )
        
        total_sold = sold_data["total_sold"] or 0
        revenue = sold_data["total_revenue"] or 0
        
        best_sellers_items.append({
            "Product Name": product.name,
            "Selling Price": product.price,
            "Quantity Sold": total_sold,
            "Revenue": revenue,
            "Current Stock": product.stock
        })
    
    # Sort by quantity sold descending order
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

# generate all reports
@login_required
def generate_all_reports(request):
    """Manual trigger to refresh reports (now just calls the helper)"""
    if not request.user.is_staff:
        return redirect("index")
    run_report_generation()
    return redirect("reports")


from django.contrib.admin.views.decorators import staff_member_required

#displays all generated bsuiness reports to staff members
@staff_member_required
def reports(request):
    """View all reports - auto-updates data on page load"""
    
    # always regenrate report with latest data when page loads
    run_report_generation()
        
    cart = request.session.get("cart", [])
    reports = Report.objects.all().order_by("report_type")  # Stable order
    return render(request, "shop/reports.html", {"reports": reports, "cart": cart})

# displays detailed data for a single specific report
@staff_member_required
def report_detail(request, report_id):
    """View a specific report"""
    cart = request.session.get("cart", [])
    report = Report.objects.get(id=report_id)
    return render(request, "shop/report_detail.html", {"report": report, "cart": cart})
