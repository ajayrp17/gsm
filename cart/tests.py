from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product

from .models import CartItem


User = get_user_model()


class CartFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cartuser", password="StrongPass123!")
        self.category = Category.objects.create(name="Vegetables")
        self.product = Product.objects.create(
            category=self.category,
            name="Tomato",
            description="Fresh tomato",
            price=Decimal("20.00"),
            stock=2,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_add_to_cart_respects_stock_limit(self):
        add_url = reverse("cart:add_to_cart", args=[self.product.id])

        self.client.get(add_url)
        self.client.get(add_url)
        self.client.get(add_url)  # Should not exceed stock.

        item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(item.quantity, 2)

    def test_cart_detail_shows_total(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        response = self.client.get(reverse("cart:cart_detail"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total"], Decimal("40.00"))
