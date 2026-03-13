from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home_view, name="home"),
    path("items/", views.manage_items_view, name="manage_items"),
    path("coupons/", views.manage_coupons_view, name="manage_coupons"),
    path("billing/", views.manage_billing_view, name="manage_billing"),
    path("orders/", views.manage_orders_view, name="manage_orders"),
    path("orders/<int:order_id>/", views.order_detail_view, name="order_detail"),
    path("payments/", views.manage_payments_view, name="manage_payments"),
    path("users/", views.manage_users_view, name="manage_users"),
]
