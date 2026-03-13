from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Address
from catalog.models import Category, Product
from orders.models import BillingConfiguration, Order

from .views import DISPATCH_MODE_NOT_DISPATCHED


User = get_user_model()


class DashboardOrderManagementTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="dashboardstaff",
            password="StrongPass123!",
            is_staff=True,
        )
        self.customer = User.objects.create_user(username="cust1", password="StrongPass123!")
        self.address = Address.objects.create(
            user=self.customer,
            label="Home",
            full_name="Customer One",
            phone="7777777777",
            line1="Street 1",
            city="Hyderabad",
            state="TS",
            postal_code="500001",
        )
        self.category = Category.objects.create(name="Daily Needs")
        self.product = Product.objects.create(
            category=self.category,
            name="Bread",
            description="Bread item",
            price=Decimal("40.00"),
            stock=10,
            is_active=True,
        )
        self.order = Order.objects.create(
            user=self.customer,
            address=self.address,
            total_amount=Decimal("40.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            delivery_charge=Decimal("0.00"),
            service_charge=Decimal("0.00"),
            extra_charge=Decimal("0.00"),
            final_amount=Decimal("40.00"),
            status=Order.STATUS_PENDING,
            payment_method=Order.PAYMENT_COD,
            payment_status=Order.PAYMENT_STATUS_PENDING,
        )
        self.client.force_login(self.staff_user)

    def test_processing_status_forces_dispatch(self):
        response = self.client.post(
            reverse("dashboard:manage_orders"),
            {
                "order_id": self.order.id,
                "status": Order.STATUS_PROCESSING,
                "payment_status": Order.PAYMENT_STATUS_PENDING,
                "dispatch_mode": DISPATCH_MODE_NOT_DISPATCHED,
            },
        )

        self.assertRedirects(response, reverse("dashboard:manage_orders"), fetch_redirect_response=False)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PROCESSING)
        self.assertIsNotNone(self.order.dispatched_at)
        self.assertEqual(self.order.dispatched_by, self.staff_user)


class DashboardBillingTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="billingstaff",
            password="StrongPass123!",
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    def test_manage_billing_updates_configuration(self):
        response = self.client.post(
            reverse("dashboard:manage_billing"),
            {
                "tax_percentage": "8.50",
                "delivery_charge": "25.00",
                "service_charge": "3.00",
                "extra_charge": "1.50",
            },
        )

        self.assertRedirects(response, reverse("dashboard:manage_billing"), fetch_redirect_response=False)
        config = BillingConfiguration.get_solo()
        self.assertEqual(config.tax_percentage, Decimal("8.50"))
        self.assertEqual(config.delivery_charge, Decimal("25.00"))
