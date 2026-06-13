from django.db import models
from django.contrib.auth.models import User
from .utils.shipping import calculate_delivery_fee
import uuid

class Product(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.IntegerField()
    image = models.ImageField(upload_to="products/")
    category = models.CharField(
        max_length=50,
        choices=[
            ("women", "Women"),
            ("men", "Men"),
        ],
        default="men",
    )
    subcategory = models.CharField(max_length=50)
    stock = models.IntegerField(default=0)

    def get_avg_rating(self):
        reviews = self.reviews.all()
        if not reviews.exists():
            return 0
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)

    def get_review_count(self):
        return self.reviews.count()

    def __str__(self):
        return self.name


class Order(models.Model):
    id = models.AutoField(primary_key=True)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders", null=True, blank=True, db_column="user_id")
    location = models.CharField(max_length=200, null=True, blank=True)
    delivery_fee = models.IntegerField(null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    landmark = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)
    tracking_number = models.CharField(max_length=20, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            self.tracking_number = str(uuid.uuid4()).split("-")[0].upper()
        
        if self.location and self.delivery_fee is None:
            self.delivery_fee = calculate_delivery_fee(self.location)
        super().save(*args, **kwargs)

    def get_total_amount(self):
        """Calculate total from OrderItems (3NF compliant)"""
        return sum(item.get_total() for item in self.items.all())

    def get_grand_total(self):
        """Total including delivery fee"""
        return self.get_total_amount() + (self.delivery_fee or 0)

    def get_mpesa_receipt_number(self):
        transaction = self.transactions.filter(status="SUCCESS").order_by("-created_at").first()
        return transaction.mpesa_receipt_number if transaction else None

    def __str__(self):
        #return f"Order {self.tracking_number} - {self.buyer.username}"
        return f"Order {self.tracking_number} - {self.buyer.username if self.buyer else self.email}"


class OrderItem(models.Model):
    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", db_column="order_id")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, db_column="product_id")
    quantity = models.IntegerField()
    unit_price_at_purchase = models.IntegerField() # 3NF compliant field
    size = models.CharField(max_length=20, blank=True)

    def __str__(self):
        size_info = f" - Size {self.size}" if self.size else ""
        return f"{self.quantity}x {self.product.name}{size_info} - Order {self.order.tracking_number}"

    def get_total(self):
        if self.quantity is None or self.unit_price_at_purchase is None:
            return 0
        return self.quantity * self.unit_price_at_purchase


class Transaction(models.Model):
    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions", db_column="order_id")
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, null=True)
    amount = models.IntegerField()
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.id} for Order {self.order.tracking_number} - {self.status}"


class Receipt(models.Model):

    id = models.AutoField(primary_key=True)
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="platform_receipt", db_column="order_id"
    )
    receipt_number = models.CharField(max_length=50, unique=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.BinaryField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"RCP-{self.order.tracking_number}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Receipt {self.receipt_number}"


class Report(models.Model):
    REPORT_TYPES = [
        ("sales", "Sales Report"),
        ("inventory", "Inventory Report"),
        ("orders", "Orders Report"),
        ("customers", "Customer Report"),
        ("products", "Product Report"),
        ("bestsellers", "Best Sellers Report"),
    ]

    id = models.AutoField(primary_key=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=100)
    generated_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.generated_at.strftime('%Y-%m-%d')}"


class Review(models.Model):
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", db_column="product_id")
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="product_reviews", db_column="user_id", null=True, blank=True)
    rating = models.IntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.buyer.username if self.buyer else 'Unknown'} for {self.product.name}"

    def is_verified_purchase(self):
        """Checks if the user has a PAID order for this specific product"""
        if not self.buyer:
            return False
        return Order.objects.filter(
            buyer=self.buyer,
            items__product=self.product,
            status="PAID"
        ).exists()

    def get_helpful_count(self):
        return self.helpful_votes.count()


class ReviewHelpful(models.Model):
    id = models.AutoField(primary_key=True)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="helpful_votes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="review_votes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("review", "user")
        verbose_name_plural = "Review Helpful Votes"

    def __str__(self):
        return f"{self.user.username} helpful vote on {self.review.id}"
