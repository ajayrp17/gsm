from django.contrib import admin, messages
from django.utils import timezone

from .models import Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "dispatched_at",
        "dispatched_by",
        "payment_method",
        "payment_status",
        "final_amount",
        "created_at",
    )
    list_filter = ("status", "payment_method", "payment_status", "created_at", "dispatched_at")
    search_fields = ("id", "user__username", "tracking_code")
    list_select_related = ("user", "address", "coupon", "dispatched_by")
    readonly_fields = ("tracking_code", "created_at", "updated_at", "dispatched_at", "dispatched_by")
    actions = ("mark_processing", "mark_dispatched", "mark_delivered", "mark_cancelled", "mark_paid")
    inlines = [OrderItemInline]

    @staticmethod
    def _sync_payment_from_order(order):
        try:
            payment = order.payment
        except Payment.DoesNotExist:
            return
        payment.payment_status = order.payment_status
        if order.payment_status == Order.PAYMENT_STATUS_PAID and not payment.paid_at:
            payment.paid_at = timezone.now()
        payment.save(update_fields=["payment_status", "paid_at"])

    def save_model(self, request, obj, form, change):
        if obj.status == Order.STATUS_OUT_FOR_DELIVERY and not obj.dispatched_at:
            obj.dispatched_at = timezone.now()
            obj.dispatched_by = request.user
        if obj.status == Order.STATUS_DELIVERED and obj.payment_method == Order.PAYMENT_COD:
            obj.payment_status = Order.PAYMENT_STATUS_PAID
        super().save_model(request, obj, form, change)
        self._sync_payment_from_order(obj)

    def mark_processing(self, request, queryset):
        updated = queryset.update(status=Order.STATUS_PROCESSING)
        self.message_user(request, f"{updated} order(s) moved to Processing.", level=messages.SUCCESS)
    mark_processing.short_description = "Mark selected orders as Processing"

    def mark_dispatched(self, request, queryset):
        now = timezone.now()
        updated = 0
        for order in queryset:
            if order.status in (Order.STATUS_CANCELLED, Order.STATUS_DELIVERED):
                continue
            order.status = Order.STATUS_OUT_FOR_DELIVERY
            if not order.dispatched_at:
                order.dispatched_at = now
            if not order.dispatched_by_id:
                order.dispatched_by = request.user
            order.save(update_fields=["status", "dispatched_at", "dispatched_by", "updated_at"])
            updated += 1
        self.message_user(request, f"{updated} order(s) dispatched.", level=messages.SUCCESS)
    mark_dispatched.short_description = "Dispatch selected orders"

    def mark_delivered(self, request, queryset):
        updated = 0
        for order in queryset:
            order.status = Order.STATUS_DELIVERED
            if order.payment_method == Order.PAYMENT_COD:
                order.payment_status = Order.PAYMENT_STATUS_PAID
            order.save(update_fields=["status", "payment_status", "updated_at"])
            self._sync_payment_from_order(order)
            updated += 1
        self.message_user(request, f"{updated} order(s) marked as Delivered.", level=messages.SUCCESS)
    mark_delivered.short_description = "Mark selected orders as Delivered"

    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status=Order.STATUS_CANCELLED)
        self.message_user(request, f"{updated} order(s) cancelled.", level=messages.WARNING)
    mark_cancelled.short_description = "Cancel selected orders"

    def mark_paid(self, request, queryset):
        updated = 0
        for order in queryset:
            order.payment_status = Order.PAYMENT_STATUS_PAID
            order.save(update_fields=["payment_status", "updated_at"])
            self._sync_payment_from_order(order)
            updated += 1
        self.message_user(request, f"Payment marked as paid for {updated} order(s).", level=messages.SUCCESS)
    mark_paid.short_description = "Mark payment as Paid for selected orders"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "payment_method", "payment_status", "transaction_id", "paid_at", "created_at")
    list_filter = ("payment_method", "payment_status")
    search_fields = ("transaction_id", "order__id")
    list_select_related = ("order",)
    readonly_fields = ("created_at",)
    actions = ("mark_paid", "mark_failed", "mark_pending")

    def _sync_order_from_payment(self, payment):
        order = payment.order
        order.payment_status = payment.payment_status
        order.save(update_fields=["payment_status", "updated_at"])

    def mark_paid(self, request, queryset):
        now = timezone.now()
        updated = 0
        for payment in queryset:
            payment.payment_status = Order.PAYMENT_STATUS_PAID
            if not payment.paid_at:
                payment.paid_at = now
            payment.save(update_fields=["payment_status", "paid_at"])
            self._sync_order_from_payment(payment)
            updated += 1
        self.message_user(request, f"{updated} payment(s) marked as paid.", level=messages.SUCCESS)
    mark_paid.short_description = "Mark selected payments as Paid"

    def mark_failed(self, request, queryset):
        updated = 0
        for payment in queryset:
            payment.payment_status = Order.PAYMENT_STATUS_FAILED
            payment.save(update_fields=["payment_status"])
            self._sync_order_from_payment(payment)
            updated += 1
        self.message_user(request, f"{updated} payment(s) marked as failed.", level=messages.WARNING)
    mark_failed.short_description = "Mark selected payments as Failed"

    def mark_pending(self, request, queryset):
        updated = 0
        for payment in queryset:
            payment.payment_status = Order.PAYMENT_STATUS_PENDING
            payment.save(update_fields=["payment_status"])
            self._sync_order_from_payment(payment)
            updated += 1
        self.message_user(request, f"{updated} payment(s) set to pending.", level=messages.INFO)
    mark_pending.short_description = "Mark selected payments as Pending"
