from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from shop.models import Product, Order, OrderItem
import random


class Command(BaseCommand):
    help = "Generate test users with orders for testing reports"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=20,
            help="Number of users to create with orders",
        )

    def handle(self, *args, **options):
        num_users = options["count"]

        # Get some products to create orders with
        products = list(Product.objects.all())
        if not products:
            self.stdout.write(
                self.style.ERROR("No products found! Run generate_sample_data first.")
            )
            return

        created_count = 0
        for i in range(num_users):
            username = f"testuser{i + 1}"

            # Create user if not exists
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"testuser{i + 1}@example.com",
                },
            )
            if created:
                user.set_password("testpass123")
                user.save()

            # Create a pending or paid order for this user
            order = Order.objects.create(
                buyer=user,
                status="PAID" if i % 2 == 0 else "PENDING",
                phone=f"2547{i:08d}",
                location="Nairobi CBD",
# No changes needed here, just verifying.
                address=f"Test Address {i + 1}",
                delivery_fee=200,
            )

            # Add random items to the order (3-8 items per order)
            num_items = random.randint(3, 8)
            selected_products = random.sample(products, min(num_items, len(products)))

            for prod in selected_products:
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    quantity=random.randint(1, 3),
                    unit_price_at_purchase=prod.price,
                    size="M" if prod.subcategory in ["clothing", "shoes"] else "",
                )

            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {created_count} test users with orders!"
            )
        )

        # Now regenerate reports
        self.regenerate_reports()

    def regenerate_reports(self):
        from shop.models import Report

        # Update Customer Report with all users who have orders
        customers_with_orders = User.objects.filter(orders__isnull=False).distinct()
        customers_data = {
            "total_customers": customers_with_orders.count(),
            "customers_with_orders": customers_with_orders.count(),
            "items": [
                {
                    "username": u.username,
                    "email": u.email,
                    "orders": u.orders.count(),
                    "total_spent": sum(
                        o.get_grand_total() for o in u.orders.filter(status="PAID")
                    ),
                }
                for u in customers_with_orders[:50]
            ],
        }

        report, _ = Report.objects.get_or_create(
            report_type="customers",
            title="Customer Analysis Report",
            defaults={"data": customers_data},
        )
        if not report:
            report = Report.objects.filter(report_type="customers").first()
            report.data = customers_data
            report.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Customer Report now has {len(customers_data['items'])} items!"
            )
        )
