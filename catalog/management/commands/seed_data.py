import os
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Address
from catalog.models import Category, Offer, Product, Review


class Command(BaseCommand):
    help = "Seed database with sample grocery data"

    def handle(self, *args, **options):
        category_data = {
            "Fruits": "Fresh seasonal fruits",
            "Vegetables": "Farm fresh vegetables",
            "Dairy": "Milk, cheese and daily essentials",
            "Snacks": "Crunchy snacks and ready-to-eat options",
            "Beverages": "Juices, soft drinks and healthy beverages",
        }

        product_data = [
            ("Fruits", "Organic Bananas", "Naturally ripened organic bananas.", Decimal("40.00"), 100),
            ("Fruits", "Apple Pack", "Premium red apples (1kg).", Decimal("160.00"), 50),
            ("Vegetables", "Fresh Tomatoes", "Farm-picked tomatoes (1kg).", Decimal("55.00"), 80),
            ("Vegetables", "Green Spinach", "Clean spinach bunch.", Decimal("35.00"), 60),
            ("Dairy", "Cow Milk 1L", "Pasteurized full cream milk.", Decimal("62.00"), 120),
            ("Dairy", "Paneer 200g", "Soft and fresh paneer.", Decimal("95.00"), 40),
            ("Snacks", "Classic Potato Chips", "Salted crispy chips 150g.", Decimal("50.00"), 90),
            ("Snacks", "Roasted Nuts Mix", "Healthy roasted nuts 200g.", Decimal("180.00"), 45),
            ("Beverages", "Orange Juice 1L", "No added preservatives.", Decimal("110.00"), 75),
            ("Beverages", "Sparkling Water", "Refreshing sparkling water 750ml.", Decimal("65.00"), 70),
        ]

        categories = {}
        for name, description in category_data.items():
            category, _ = Category.objects.get_or_create(name=name, defaults={"description": description})
            categories[name] = category

        for category_name, name, description, price, stock in product_data:
            Product.objects.update_or_create(
                name=name,
                defaults={
                    "category": categories[category_name],
                    "description": description,
                    "price": price,
                    "stock": stock,
                    "is_active": True,
                },
            )

        offer, _ = Offer.objects.update_or_create(
            coupon_code="SAVE10",
            defaults={
                "name": "Starter Coupon",
                "discount_percentage": 10,
                "expiry_date": timezone.now().date() + timezone.timedelta(days=120),
                "active": True,
            },
        )
        offer.products.set(Product.objects.all()[:5])

        admin_user, admin_created = User.objects.get_or_create(username="admin", defaults={"email": "admin@grogin.local"})
        if admin_created:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.set_password(os.getenv("GROGIN_ADMIN_PASSWORD", "admin123"))
            admin_user.save()

        demo_user, demo_created = User.objects.get_or_create(
            username="demo_user",
            defaults={
                "email": "demo@grogin.local",
                "first_name": "Demo",
                "last_name": "User",
            },
        )
        if demo_created:
            demo_user.set_password("demo12345")
            demo_user.save()

        Address.objects.get_or_create(
            user=demo_user,
            label="Home",
            defaults={
                "full_name": "Demo User",
                "phone": "9876543210",
                "line1": "221B Baker Street",
                "line2": "Near City Mall",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": "560001",
                "landmark": "Metro Gate 2",
                "is_default": True,
            },
        )

        first_product = Product.objects.first()
        if first_product:
            Review.objects.update_or_create(
                user=demo_user,
                product=first_product,
                defaults={"rating": 5, "comment": "Great quality and quick delivery."},
            )

        self.stdout.write(self.style.SUCCESS("Sample data seeded successfully."))
        self.stdout.write("Admin login: admin / admin123")
        self.stdout.write("Demo login: demo_user / demo12345")
