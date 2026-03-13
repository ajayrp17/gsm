from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import DecimalField, F, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from catalog.models import Offer, Product
from orders.models import BillingConfiguration, Order, OrderItem, Payment
from .forms import (
    DashboardBillingConfigurationForm,
    DashboardCategoryForm,
    DashboardOfferForm,
    DashboardProductForm,
)

DISPATCH_MODE_DISPATCHED = "dispatched"
DISPATCH_MODE_NOT_DISPATCHED = "not_dispatched"


@staff_member_required
def dashboard_home_view(request):
    total_sales = (
        Order.objects.exclude(status=Order.STATUS_CANCELLED).aggregate(total=Sum("final_amount"))["total"] or 0
    )
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status=Order.STATUS_PENDING).count()
    total_products = Product.objects.count()
    active_offers = Offer.objects.filter(active=True).count()
    active_coupons = Offer.objects.filter(active=True, coupon_code__isnull=False).exclude(coupon_code="").count()
    pending_payments = Payment.objects.filter(payment_status=Order.PAYMENT_STATUS_PENDING).count()
    billing_config = BillingConfiguration.get_solo()

    monthly_revenue_queryset = (
        Order.objects.exclude(status=Order.STATUS_CANCELLED)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(revenue=Sum("final_amount"))
        .order_by("month")
    )

    monthly_revenue = [
        {
            "month": entry["month"].strftime("%b %Y"),
            "revenue": entry["revenue"],
        }
        for entry in monthly_revenue_queryset
        if entry["month"]
    ]

    top_products = (
        OrderItem.objects.values("product__name")
        .annotate(
            total_qty=Sum("quantity"),
            total_revenue=Sum(F("price") * F("quantity"), output_field=DecimalField(max_digits=12, decimal_places=2)),
        )
        .order_by("-total_qty")[:5]
    )

    recent_orders = Order.objects.select_related("user")[:10]
    recent_payments = Payment.objects.select_related("order", "order__user").order_by("-created_at")[:5]

    return render(
        request,
        "dashboard/dashboard_home.html",
        {
            "total_sales": total_sales,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "total_products": total_products,
            "active_offers": active_offers,
            "active_coupons": active_coupons,
            "pending_payments": pending_payments,
            "monthly_revenue": monthly_revenue,
            "top_products": top_products,
            "recent_orders": recent_orders,
            "recent_payments": recent_payments,
            "status_choices": Order.STATUS_CHOICES,
            "billing_config": billing_config,
        },
    )


@staff_member_required
def manage_orders_view(request):
    if request.method == "POST":
        order = get_object_or_404(Order, pk=request.POST.get("order_id"))
        new_status = request.POST.get("status")
        new_payment_status = request.POST.get("payment_status")
        dispatch_mode = request.POST.get("dispatch_mode")
        updated_fields = ["updated_at"]

        def _mark_updated(field_name):
            if field_name not in updated_fields:
                updated_fields.append(field_name)

        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            _mark_updated("status")

        if new_payment_status in dict(Order.PAYMENT_STATUS_CHOICES):
            order.payment_status = new_payment_status
            _mark_updated("payment_status")

        # Processing orders are auto-dispatched and dispatch mode is not editable.
        if order.status == Order.STATUS_PROCESSING:
            dispatch_mode = DISPATCH_MODE_DISPATCHED

        if dispatch_mode == DISPATCH_MODE_DISPATCHED:
            if not order.dispatched_at:
                order.dispatched_at = timezone.now()
                _mark_updated("dispatched_at")
            if not order.dispatched_by_id:
                order.dispatched_by = request.user
                _mark_updated("dispatched_by")
        elif dispatch_mode == DISPATCH_MODE_NOT_DISPATCHED and order.status != Order.STATUS_PROCESSING:
            if order.dispatched_at:
                order.dispatched_at = None
                _mark_updated("dispatched_at")
            if order.dispatched_by_id:
                order.dispatched_by = None
                _mark_updated("dispatched_by")

        # Delivered COD orders are always treated as paid.
        if order.status == Order.STATUS_DELIVERED and order.payment_method == Order.PAYMENT_COD:
            order.payment_status = Order.PAYMENT_STATUS_PAID
            _mark_updated("payment_status")

        if len(updated_fields) == 1:
            messages.error(request, "No valid update was provided.")
            return redirect("dashboard:manage_orders")

        order.save(update_fields=updated_fields)

        try:
            payment = order.payment
        except Payment.DoesNotExist:
            payment = None
        if payment:
            payment.payment_status = order.payment_status
            if payment.payment_status == Order.PAYMENT_STATUS_PAID and not payment.paid_at:
                payment.paid_at = timezone.now()
            payment.save(update_fields=["payment_status", "paid_at"])

        messages.success(request, f"Order {order.id} updated.")
        return redirect("dashboard:manage_orders")

    orders = (
        Order.objects.select_related("user", "address", "dispatched_by")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )
    return render(
        request,
        "dashboard/manage_orders.html",
        {
            "orders": orders,
            "status_choices": Order.STATUS_CHOICES,
            "payment_status_choices": Order.PAYMENT_STATUS_CHOICES,
            "dispatch_mode_dispatched": DISPATCH_MODE_DISPATCHED,
            "dispatch_mode_not_dispatched": DISPATCH_MODE_NOT_DISPATCHED,
            "processing_status": Order.STATUS_PROCESSING,
        },
    )


@staff_member_required
def order_detail_view(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("user", "address", "coupon", "coupon_secondary", "dispatched_by")
        .prefetch_related("items__product"),
        pk=order_id,
    )
    return render(request, "dashboard/order_detail.html", {"order": order})


@staff_member_required
def manage_payments_view(request):
    if request.method == "POST":
        payment = get_object_or_404(Payment, pk=request.POST.get("payment_id"))
        payment_status = request.POST.get("payment_status")
        if payment_status in dict(Order.PAYMENT_STATUS_CHOICES):
            payment.payment_status = payment_status
            if payment_status == Order.PAYMENT_STATUS_PAID and not payment.paid_at:
                payment.paid_at = timezone.now()
            payment.save(update_fields=["payment_status", "paid_at"])
            payment.order.payment_status = payment_status
            payment.order.save(update_fields=["payment_status", "updated_at"])
            messages.success(request, f"Payment for Order {payment.order_id} updated.")
        return redirect("dashboard:manage_payments")

    payments = Payment.objects.select_related("order", "order__user").order_by("-created_at")
    return render(
        request,
        "dashboard/manage_payments.html",
        {
            "payments": payments,
            "payment_status_choices": Order.PAYMENT_STATUS_CHOICES,
        },
    )


@staff_member_required
def manage_items_view(request):
    edit_item = None
    edit_id = request.GET.get("edit")
    if edit_id:
        edit_item = get_object_or_404(Product, pk=edit_id)

    product_form = DashboardProductForm(instance=edit_item, prefix="product")
    category_form = DashboardCategoryForm(prefix="category")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete_item":
            item = get_object_or_404(Product, pk=request.POST.get("item_id"))
            item_name = item.name
            item.delete()
            messages.success(request, f"Item '{item_name}' deleted.")
            return redirect("dashboard:manage_items")

        if action == "save_category":
            category_form = DashboardCategoryForm(request.POST, prefix="category")
            if category_form.is_valid():
                category = category_form.save()
                messages.success(request, f"Category '{category.name}' created.")
                return redirect("dashboard:manage_items")
        else:
            item_id = request.POST.get("item_id")
            item_instance = get_object_or_404(Product, pk=item_id) if item_id else None
            edit_item = item_instance
            product_form = DashboardProductForm(
                request.POST,
                request.FILES,
                instance=item_instance,
                prefix="product",
            )
            if product_form.is_valid():
                item = product_form.save()
                action_label = "updated" if item_id else "added"
                messages.success(request, f"Item '{item.name}' {action_label} successfully.")
                return redirect("dashboard:manage_items")

    items = Product.objects.select_related("category").order_by("-created_at")
    return render(
        request,
        "dashboard/manage_items.html",
        {
            "items": items,
            "product_form": product_form,
            "category_form": category_form,
            "edit_item": edit_item,
        },
    )


@staff_member_required
def manage_coupons_view(request):
    edit_offer = None
    edit_id = request.GET.get("edit")
    if edit_id:
        edit_offer = get_object_or_404(Offer, pk=edit_id)

    offer_form = DashboardOfferForm(instance=edit_offer, prefix="offer")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete_coupon":
            offer = get_object_or_404(Offer, pk=request.POST.get("offer_id"))
            offer_name = offer.name
            offer.delete()
            messages.success(request, f"Coupon/offer '{offer_name}' deleted.")
            return redirect("dashboard:manage_coupons")

        offer_id = request.POST.get("offer_id")
        offer_instance = get_object_or_404(Offer, pk=offer_id) if offer_id else None
        edit_offer = offer_instance
        offer_form = DashboardOfferForm(request.POST, instance=offer_instance, prefix="offer")
        if offer_form.is_valid():
            offer = offer_form.save()
            action_label = "updated" if offer_id else "created"
            messages.success(request, f"Coupon/offer '{offer.name}' {action_label} successfully.")
            return redirect("dashboard:manage_coupons")

    offers = Offer.objects.prefetch_related("products").order_by("-priority", "-expiry_date", "name")
    return render(
        request,
        "dashboard/manage_coupons.html",
        {
            "offers": offers,
            "offer_form": offer_form,
            "edit_offer": edit_offer,
            "today": timezone.now().date(),
        },
    )


@staff_member_required
def manage_billing_view(request):
    config = BillingConfiguration.get_solo()

    if request.method == "POST":
        form = DashboardBillingConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Billing charges updated.")
            return redirect("dashboard:manage_billing")
    else:
        form = DashboardBillingConfigurationForm(instance=config)

    return render(request, "dashboard/manage_billing.html", {"billing_form": form, "billing_config": config})


@staff_member_required
def manage_users_view(request):
    if request.method == "POST":
        user = get_object_or_404(User, pk=request.POST.get("user_id"))
        if user.is_superuser:
            messages.error(request, "Superuser status cannot be changed here.")
        else:
            user.is_active = not user.is_active
            user.save(update_fields=["is_active"])
            state = "activated" if user.is_active else "deactivated"
            messages.success(request, f"User {user.username} {state}.")
        return redirect("dashboard:manage_users")

    users = User.objects.all().order_by("-date_joined")
    return render(request, "dashboard/manage_users.html", {"users": users})
