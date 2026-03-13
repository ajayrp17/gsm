from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, Offer, Product


User = get_user_model()


class CatalogViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Fruits")
        self.offer_product = Product.objects.create(
            category=self.category,
            name="Apple",
            description="Offer item",
            price=Decimal("120.00"),
            stock=10,
            is_active=True,
        )
        self.normal_product = Product.objects.create(
            category=self.category,
            name="Banana",
            description="Regular item",
            price=Decimal("80.00"),
            stock=10,
            is_active=True,
        )
        self.offer = Offer.objects.create(
            name="Offer Apple",
            coupon_code="APPLE10",
            discount_percentage=10,
            expiry_date=timezone.now().date() + timedelta(days=10),
            active=True,
        )
        self.offer.products.add(self.offer_product)

    def test_staff_home_redirects_to_dashboard(self):
        staff = User.objects.create_user(username="staffhome", password="StrongPass123!", is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(reverse("catalog:home"))
        self.assertRedirects(response, reverse("dashboard:home"), fetch_redirect_response=False)

    def test_offer_only_filter_returns_only_offer_items(self):
        response = self.client.get(reverse("catalog:product_list"), {"offer_only": "1"})
        products = list(response.context["products"])

        self.assertIn(self.offer_product, products)
        self.assertNotIn(self.normal_product, products)
