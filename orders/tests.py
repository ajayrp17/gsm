from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Address
from cart.models import CartItem
from catalog.models import Category, Offer, Product

from .models import BillingConfiguration, Order, OrderItem
from .views import _pricing_context_for_checkout


User = get_user_model()


class OrderPricingRuleTests(TestCase):
    def setUp(self):
        Offer.objects.all().delete()
        self.user = User.objects.create_user(username="orderuser", password="StrongPass123!")
        self.category = Category.objects.create(name="Groceries")
        self.product = Product.objects.create(
            category=self.category,
            name="Milk",
            description="Fresh milk",
            price=Decimal("50.00"),
            stock=50,
            is_active=True,
        )
        self.address = Address.objects.create(
            user=self.user,
            label="Home",
            full_name="Order User",
            phone="9999999999",
            line1="Line 1",
            city="Chennai",
            state="TN",
            postal_code="600001",
            is_default=True,
        )
        self.config = BillingConfiguration.get_solo()
        self.config.tax_percentage = Decimal("10.00")
        self.config.delivery_charge = Decimal("40.00")
        self.config.service_charge = Decimal("5.00")
        self.config.extra_charge = Decimal("2.00")
        self.config.save()

    def _create_delivered_order(self):
        return Order.objects.create(
            user=self.user,
            address=self.address,
            total_amount=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            delivery_charge=Decimal("0.00"),
            service_charge=Decimal("0.00"),
            extra_charge=Decimal("0.00"),
            final_amount=Decimal("100.00"),
            status=Order.STATUS_DELIVERED,
            payment_method=Order.PAYMENT_COD,
            payment_status=Order.PAYMENT_STATUS_PAID,
        )

    def test_free_delivery_for_subtotal_above_200(self):
        pricing_low = _pricing_context_for_checkout(self.user, Decimal("199.00"), "")
        pricing_high = _pricing_context_for_checkout(self.user, Decimal("250.00"), "")

        self.assertEqual(pricing_low["delivery_charge"], Decimal("40.00"))
        self.assertFalse(pricing_low["free_delivery_applied"])
        self.assertEqual(pricing_high["delivery_charge"], Decimal("0.00"))
        self.assertTrue(pricing_high["free_delivery_applied"])

    def test_first_order_auto_coupon_applies(self):
        Offer.objects.create(
            name="First Join Offer",
            coupon_code="NEWJOIN10",
            offer_type=Offer.TYPE_FIRST_ORDER,
            discount_percentage=10,
            min_order_amount=0,
            expiry_date=timezone.now().date() + timedelta(days=30),
            auto_apply=True,
            active=True,
        )

        pricing = _pricing_context_for_checkout(self.user, Decimal("500.00"), "")
        self.assertIsNotNone(pricing["primary_offer"])
        self.assertEqual(pricing["primary_offer"].coupon_code, "NEWJOIN10")
        self.assertEqual(pricing["discount_amount"], Decimal("50.00"))

    def test_second_daily_coupon_auto_applies_after_five_delivered_orders(self):
        primary = Offer.objects.create(
            name="Primary Coupon",
            coupon_code="SAVE10",
            offer_type=Offer.TYPE_GENERAL,
            discount_percentage=10,
            expiry_date=timezone.now().date() + timedelta(days=30),
            active=True,
        )
        Offer.objects.create(
            name="Daily Stack",
            coupon_code="DAILY5",
            offer_type=Offer.TYPE_DAILY,
            discount_percentage=5,
            min_order_amount=0,
            min_completed_orders=5,
            allow_with_other_coupon=True,
            auto_apply=True,
            expiry_date=timezone.now().date() + timedelta(days=30),
            active=True,
            priority=100,
        )

        for _ in range(5):
            self._create_delivered_order()

        pricing = _pricing_context_for_checkout(self.user, Decimal("500.00"), primary.coupon_code)
        self.assertIsNotNone(pricing["primary_offer"])
        self.assertIsNotNone(pricing["secondary_offer"])
        self.assertEqual(pricing["secondary_offer"].coupon_code, "DAILY5")


class OrderFlowTests(TestCase):
    def setUp(self):
        Offer.objects.all().delete()
        BillingConfiguration.get_solo()
        self.user = User.objects.create_user(username="flowuser", password="StrongPass123!")
        self.category = Category.objects.create(name="Snacks")
        self.product = Product.objects.create(
            category=self.category,
            name="Chips",
            description="Potato chips",
            price=Decimal("30.00"),
            stock=20,
            is_active=True,
        )
        self.address = Address.objects.create(
            user=self.user,
            label="Office",
            full_name="Flow User",
            phone="8888888888",
            line1="Office line1",
            city="Bangalore",
            state="KA",
            postal_code="560001",
            is_default=True,
        )
        self.client.force_login(self.user)

    def test_reorder_adds_items_to_cart(self):
        order = Order.objects.create(
            user=self.user,
            address=self.address,
            total_amount=Decimal("60.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            delivery_charge=Decimal("0.00"),
            service_charge=Decimal("0.00"),
            extra_charge=Decimal("0.00"),
            final_amount=Decimal("60.00"),
            status=Order.STATUS_DELIVERED,
            payment_method=Order.PAYMENT_COD,
            payment_status=Order.PAYMENT_STATUS_PAID,
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=2, price=Decimal("30.00"))

        response = self.client.post(reverse("orders:reorder", args=[order.id]))
        self.assertRedirects(response, reverse("cart:cart_detail"), fetch_redirect_response=False)

        cart_item = CartItem.objects.get(user=self.user, product=self.product)
        self.assertEqual(cart_item.quantity, 2)

    def test_checkout_creates_order_with_charge_breakdown(self):
        CartItem.objects.create(user=self.user, product=self.product, quantity=3)
        config = BillingConfiguration.get_solo()
        config.tax_percentage = Decimal("10.00")
        config.delivery_charge = Decimal("20.00")
        config.service_charge = Decimal("5.00")
        config.extra_charge = Decimal("2.00")
        config.save()

        response = self.client.post(
            reverse("orders:checkout"),
            {
                "address": self.address.id,
                "payment_method": Order.PAYMENT_COD,
                "coupon_code": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        order = Order.objects.filter(user=self.user).latest("id")
        self.assertEqual(order.total_amount, Decimal("90.00"))
        self.assertEqual(order.tax_amount, Decimal("9.00"))
        self.assertEqual(order.delivery_charge, Decimal("20.00"))
        self.assertEqual(order.service_charge, Decimal("5.00"))
        self.assertEqual(order.extra_charge, Decimal("2.00"))
