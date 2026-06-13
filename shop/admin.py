from django.contrib import admin
from .models import Product, Order, OrderItem, Receipt, Report, Transaction, Review, ReviewHelpful
from django.urls import reverse
from django.utils.html import format_html


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "buyer", "rating", "created_at", "is_verified_purchase")
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "buyer__username", "comment")
    readonly_fields = ("created_at",)


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ("review", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "review__id")



@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id","name", "category", "subcategory", "price", "stock")
    list_filter = ("category", "subcategory")
    search_fields = ("name", "subcategory")
    list_editable = ("stock",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("id","product", "quantity", "unit_price_at_purchase", "size", "get_total")
    can_delete = False


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = (
        "id",
        "checkout_request_id",
        "mpesa_receipt_number",
        "amount",
        "status",
        "created_at",
    )
    can_delete = False


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "checkout_request_id",
        "mpesa_receipt_number",
        "amount",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("order__tracking_number", "mpesa_receipt_number", "checkout_request_id")
    readonly_fields = ("created_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tracking_number",
        "buyer",
        "display_amount",
        "delivery_fee",
        "status",
        "display_receipt",
        "phone",
    )
    list_filter = ("status",)
    search_fields = ("tracking_number", "buyer__username", "phone")
    readonly_fields = ("tracking_number", "display_amount")
    inlines = [OrderItemInline, TransactionInline]

    def display_amount(self, obj):
        return obj.get_total_amount()

    display_amount.short_description = "Amount"

    def display_receipt(self, obj):
        transaction = obj.transactions.filter(status="SUCCESS").first()
        return transaction.mpesa_receipt_number if transaction else "N/A"

    display_receipt.short_description = "M-Pesa Receipt"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["inventory_url"] = reverse("inventory")
        return super().changelist_view(request, extra_context)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "unit_price_at_purchase", "size", "get_total")
    list_filter = ("product",)
    search_fields = ("order__tracking_number", "product__name")


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "receipt_number", "order", "generated_at")
    search_fields = ("receipt_number", "order__tracking_number")
    readonly_fields = ("receipt_number", "order", "generated_at")



@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "report_type", "generated_at")
    list_filter = ("report_type",)
    #readonly_fields = ("report_type", "title", "generated_at", "data")
    readonly_fields = ("generated_at",)


admin.site.site_header = "FashionHub Administration"
admin.site.site_title = "FashionHub Admin"
admin.site.index_title = "Welcome to FashionHub Admin Panel"
