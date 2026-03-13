from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class LoginRedirectTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        self.normal_user = User.objects.create_user(
            username="normaluser",
            email="normal@example.com",
            password="StrongPass123!",
        )

    def test_staff_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("login"),
            {"username": "staffuser", "password": "StrongPass123!"},
        )
        self.assertRedirects(response, reverse("dashboard:home"), fetch_redirect_response=False)

    def test_normal_login_redirects_to_catalog_home(self):
        response = self.client.post(
            reverse("login"),
            {"username": "normaluser", "password": "StrongPass123!"},
        )
        self.assertRedirects(response, reverse("catalog:home"), fetch_redirect_response=False)
