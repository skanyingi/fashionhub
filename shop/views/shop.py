from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from shop.models import Product, Review, ReviewHelpful


def index(request):
    # Redirect to onboarding screen if user has not seen it
    # if not request.session.get("has_seen_onboarding"):
    #     return redirect("onboarding")
    
    # Retrieve cart from session
    try:
        cart = request.session.get("cart", [])
        if not isinstance(cart, list):
            cart = []
            request.session["cart"] = cart
    except:
        cart = []
        request.session["cart"] = cart

    return render(request, "shop/index.html", {"cart": cart})




# Handle product search functionality
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




# Display women fashion products with filtering
def women(request):
    # # Redirect to onboarding if not yet seen
    # if not request.session.get("has_seen_onboarding"):
    #     return redirect("onboarding")
    #retrieve cart from session
    try:
        cart = request.session.get("cart", [])
        if not isinstance(cart, list):
            cart = []
            request.session["cart"] = cart
    except:
        cart = []
        request.session["cart"] = cart

    # Get filter and sort parameters from URL query string
    sort = request.GET.get("sort")
    subcategory = request.GET.get("sub")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    # start with all women products then apply filters 
    products = Product.objects.filter(category__iexact="women")
    if subcategory:
        products = products.filter(subcategory__iexact=subcategory)
    # price filter
    if min_price:
        products = products.filter(price__gte=int(min_price))
    if max_price:
        products = products.filter(price__lte=int(max_price))

    #Apply sort order
    if sort == "low-to-high":
        products = products.order_by("price")
    elif sort == "high-to-low":
        products = products.order_by("-price")

    # Return partial template from HTMX requests, full template otherwise i.e normal browser request return full page otherwise HTMX request returns only product grid
    is_htmx = request.headers.get("HX-Request") == "true" # check if request came from HTMX for partial page update
    template = "shop/product_grid.html" if is_htmx else "shop/women.html"

    # Save current URL to session for "Continue Shopping"button i.e save last visited page
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

# displays men fashion with filtering and sorting
def men(request):
    try:
        cart = request.session.get("cart", [])
        if not isinstance(cart, list):
            cart = []
            request.session["cart"] = cart
    except:
        cart = []
        request.session["cart"] = cart
    # Apply sort
    sort = request.GET.get("sort")
    subcategory = request.GET.get("sub")
    min_price = request.GET.get("min_price")
    max_price = request.GET.get("max_price")

    # Filter for men products only
    products = Product.objects.filter(category__iexact="men")
    if subcategory:
        products = products.filter(subcategory__iexact=subcategory)
    # price filter
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

    # Save current URL for "Continue Shopping" button
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







# displays the detail page for a single product
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get("cart", [])
    
    # Get up to 4 related products from the same subcategory
    related_products = Product.objects.filter(
        subcategory__iexact=product.subcategory,
        category__iexact=product.category
    ).exclude(id=product.id)[:4]
    
    # If not enough related products, pad with items from same category
    if related_products.count() < 4:
        additional_count = 4 - related_products.count()
        additional_products = Product.objects.filter(
            category__iexact=product.category
        ).exclude(
            id__in=[product.id] + [p.id for p in related_products]
        )[:additional_count]
        related_products = list(related_products) + list(additional_products)
    
    # Get all reviews for this product ordered by most recent
    reviews = Review.objects.filter(product=product).order_by("-created_at")
    
    # Calculate average rating from all reviews
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





# Display all products as featured items with sortng ptions
def featured_products(request):
    sort_order = request.GET.get("sort", "default")

    # Apply sort order to all products
    if sort_order == "low-to-high":
        products = Product.objects.all().order_by("price")
    elif sort_order == "high-to-low":
        products = Product.objects.all().order_by("-price")
    else:
        products = Product.objects.all()

    return render(
        request, "shop/featured.html", {"products": products, "sort_order": sort_order}
    )



# handle submission of a peoduct review by a customer
@require_POST
def submit_review(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "error": "Authentication required"})

    product = get_object_or_404(Product, id=product_id)

    rating = int(request.POST.get("rating", 5))
    comment = request.POST.get("comment", "").strip()

    # validate that required fields are not empty
    if not comment:
        return JsonResponse({"success": False, "error": "Please provide a comment"})

    # calmp rating to valid range of 1 to 5
    if rating < 1 or rating > 5:
        rating = 5
    # save review to database
    Review.objects.create(
        product=product,
        buyer=request.user,
        rating=rating,
        comment=comment
    )

    return JsonResponse({"success": True})


# toggle helpful vote on a review
@login_required(login_url="login")
@require_POST
def toggle_review_helpful(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    vote, created = ReviewHelpful.objects.get_or_create(review=review, user=request.user)
    
    if not created:
        # If vote already exists, delete it (unlike)
        vote.delete()
        action = "unvoted"
    else:
        action = "voted"
    
    # If request is from HTMX, return a partial fragment, otherwise return JSON
    if request.headers.get("HX-Request") == "true":
        return render(request, "shop/helpful_button.html", {
            "review": review,
            "user_has_voted": created
        })
        
    return JsonResponse({
        "success": True, 
        "action": action, 
        "count": review.get_helpful_count()
    })

