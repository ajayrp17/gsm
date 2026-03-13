from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cart.models import CartItem
from catalog.models import Offer

from .forms import CheckoutForm
from .models import BillingConfiguration, Order, OrderItem, Payment

MONEY_DECIMAL = Decimal("0.01")
FREE_DELIVERY_THRESHOLD = Decimal("200.00")


def _money(value):
    return Decimal(value).quantize(MONEY_DECIMAL, rounding=ROUND_HALF_UP)


def _offer_usage_count(user, offer):
    return (
        Order.objects.filter(user=user)
        .exclude(status=Order.STATUS_CANCELLED)
        .filter(Q(coupon=offer) | Q(coupon_secondary=offer))
        .count()
    )


def _is_offer_eligible(offer, user, subtotal, user_order_count, delivered_order_count):
    today = timezone.now().date()
    if not offer.active or offer.expiry_date < today:
        return False, "Coupon is inactive or expired."

    if subtotal < offer.min_order_amount:
        return False, f"Minimum order for this coupon is INR {offer.min_order_amount}."

    if offer.offer_type == Offer.TYPE_FIRST_ORDER and user_order_count > 0:
        return False, "First-order coupon can be used only on your first order."

    if delivered_order_count < offer.min_completed_orders:
        return (
            False,
            f"This coupon requires at least {offer.min_completed_orders} delivered orders.",
        )

    usage_count = _offer_usage_count(user, offer)
    if offer.max_uses_per_user and usage_count >= offer.max_uses_per_user:
        return False, "Coupon usage limit reached for your account."

    return True, None


def _offer_discount_amount(offer, amount):
    discount = (amount * Decimal(offer.discount_percentage)) / Decimal("100")
    if offer.max_discount_amount:
        discount = min(discount, offer.max_discount_amount)
    return max(_money(discount), Decimal("0.00"))


def _find_manual_coupon(coupon_code, user, subtotal, user_order_count, delivered_order_count):
    if not coupon_code:
        return None, Decimal("0.00"), None

    offer = Offer.objects.filter(coupon_code__iexact=coupon_code.strip(), active=True).first()
    if not offer:
        return None, Decimal("0.00"), "Invalid coupon code."

    eligible, error_message = _is_offer_eligible(
        offer,
        user=user,
        subtotal=subtotal,
        user_order_count=user_order_count,
        delivered_order_count=delivered_order_count,
    )
    if not eligible:
        return None, Decimal("0.00"), error_message

    discount_amount = _offer_discount_amount(offer, subtotal)
    return offer, discount_amount, None


def _find_best_auto_coupon(
    user,
    amount_for_discount,
    user_order_count,
    delivered_order_count,
    exclude_offer_ids=None,
    require_stackable=False,
):
    today = timezone.now().date()
    offers = Offer.objects.filter(active=True, auto_apply=True, expiry_date__gte=today)

    if exclude_offer_ids:
        offers = offers.exclude(id__in=exclude_offer_ids)
    if require_stackable:
        offers = offers.filter(allow_with_other_coupon=True)

    best_offer = None
    best_discount = Decimal("0.00")

    for offer in offers.order_by("-priority", "-discount_percentage", "expiry_date"):
        eligible, _ = _is_offer_eligible(
            offer,
            user=user,
            subtotal=amount_for_discount,
            user_order_count=user_order_count,
            delivered_order_count=delivered_order_count,
        )
        if not eligible:
            continue

        discount = _offer_discount_amount(offer, amount_for_discount)
        if discount > best_discount:
            best_offer = offer
            best_discount = discount

    return best_offer, best_discount


def _pricing_context_for_checkout(user, subtotal, coupon_code):
    user_order_count = Order.objects.filter(user=user).count()
    delivered_order_count = Order.objects.filter(user=user, status=Order.STATUS_DELIVERED).count()
    coupon_code = (coupon_code or "").strip().upper()

    primary_offer = None
    secondary_offer = None
    primary_discount = Decimal("0.00")
    secondary_discount = Decimal("0.00")

    primary_offer, primary_discount, coupon_error = _find_manual_coupon(
        coupon_code=coupon_code,
        user=user,
        subtotal=subtotal,
        user_order_count=user_order_count,
        delivered_order_count=delivered_order_count,
    )

    excluded_offer_ids = {primary_offer.id} if primary_offer else set()
    if primary_offer and delivered_order_count >= 5:
        secondary_offer, secondary_discount = _find_best_auto_coupon(
            user=user,
            amount_for_discount=max(subtotal - primary_discount, Decimal("0.00")),
            user_order_count=user_order_count,
            delivered_order_count=delivered_order_count,
            exclude_offer_ids=excluded_offer_ids,
            require_stackable=True,
        )
    elif not primary_offer:
        primary_offer, primary_discount = _find_best_auto_coupon(
            user=user,
            amount_for_discount=subtotal,
            user_order_count=user_order_count,
            delivered_order_count=delivered_order_count,
            exclude_offer_ids=excluded_offer_ids,
            require_stackable=False,
        )

    total_discount = _money(primary_discount + secondary_discount)
    discounted_subtotal = max(_money(subtotal - total_discount), Decimal("0.00"))

    billing_config = BillingConfiguration.get_solo()
    tax_amount = _money((discounted_subtotal * billing_config.tax_percentage) / Decimal("100"))
    delivery_charge = _money(billing_config.delivery_charge)
    if subtotal > FREE_DELIVERY_THRESHOLD:
        delivery_charge = Decimal("0.00")
    service_charge = _money(billing_config.service_charge)
    extra_charge = _money(billing_config.extra_charge)

    final_amount = _money(discounted_subtotal + tax_amount + delivery_charge + service_charge + extra_charge)

    return {
        "primary_offer": primary_offer,
        "secondary_offer": secondary_offer,
        "primary_discount": _money(primary_discount),
        "secondary_discount": _money(secondary_discount),
        "discount_amount": total_discount,
        "discounted_subtotal": discounted_subtotal,
        "tax_amount": tax_amount,
        "delivery_charge": delivery_charge,
        "service_charge": service_charge,
        "extra_charge": extra_charge,
        "final_amount": final_amount,
        "coupon_error": coupon_error,
        "billing_config": billing_config,
        "delivered_order_count": delivered_order_count,
        "free_delivery_applied": subtotal > FREE_DELIVERY_THRESHOLD,
    }


@login_required
def checkout_view(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related("product")
    if not cart_items.exists():
        messages.info(request, "Your cart is empty.")
        return redirect("catalog:product_list")

    subtotal = _money(sum(item.subtotal for item in cart_items))
    selected_coupon = (request.GET.get("coupon") or "").strip().upper()
    active_offers = Offer.objects.filter(
        active=True,
        expiry_date__gte=timezone.now().date(),
        coupon_code__isnull=False,
    ).exclude(coupon_code="").exclude(
        offer_type=Offer.TYPE_DAILY,
        auto_apply=True,
    ).order_by("-priority", "-discount_percentage", "expiry_date")[:8]

    if request.method == "POST":
        if request.POST.get("address") == "__add_new__":
            messages.info(request, "Please add a new address and continue checkout.")
            return redirect("accounts:addresses")

        form = CheckoutForm(request.POST, user=request.user, initial_coupon=selected_coupon)
        if form.is_valid():
            address = form.cleaned_data["address"]
            payment_method = form.cleaned_data["payment_method"]
            coupon_code = (form.cleaned_data["coupon_code"] or "").strip().upper()

            pricing = _pricing_context_for_checkout(
                user=request.user,
                subtotal=subtotal,
                coupon_code=coupon_code,
            )
            if pricing["coupon_error"]:
                messages.error(request, pricing["coupon_error"])
                return redirect("orders:checkout")

            with transaction.atomic():
                for item in cart_items:
                    if item.quantity > item.product.stock:
                        messages.error(
                            request,
                            f"Insufficient stock for {item.product.name}. Please update your cart.",
                        )
                        return redirect("cart:cart_detail")

                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    coupon=pricing["primary_offer"],
                    coupon_secondary=pricing["secondary_offer"],
                    total_amount=subtotal,
                    discount_amount=pricing["discount_amount"],
                    tax_amount=pricing["tax_amount"],
                    delivery_charge=pricing["delivery_charge"],
                    service_charge=pricing["service_charge"],
                    extra_charge=pricing["extra_charge"],
                    final_amount=pricing["final_amount"],
                    payment_method=payment_method,
                    payment_status=(
                        Order.PAYMENT_STATUS_PAID
                        if payment_method == Order.PAYMENT_ONLINE
                        else Order.PAYMENT_STATUS_PENDING
                    ),
                    status=Order.STATUS_PENDING,
                )

                for item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.discounted_price,
                    )
                    item.product.stock -= item.quantity
                    item.product.save(update_fields=["stock"])

                Payment.objects.create(
                    order=order,
                    payment_method=payment_method,
                    payment_status=order.payment_status,
                    transaction_id=(
                        f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}-{order.id}"
                        if payment_method == Order.PAYMENT_ONLINE
                        else ""
                    ),
                    paid_at=timezone.now() if payment_method == Order.PAYMENT_ONLINE else None,
                )

                cart_items.delete()

            if pricing["secondary_offer"]:
                messages.success(
                    request,
                    f"Order placed with 2 coupons: {pricing['primary_offer']} + {pricing['secondary_offer']}.",
                )
            elif pricing["primary_offer"]:
                messages.success(request, f"Order placed with coupon {pricing['primary_offer']}.")
            else:
                messages.success(request, "Order placed successfully.")
            return redirect("orders:order_confirmation", order_id=order.id)
    else:
        form = CheckoutForm(user=request.user, initial_coupon=selected_coupon)

    pricing = _pricing_context_for_checkout(
        user=request.user,
        subtotal=subtotal,
        coupon_code=selected_coupon,
    )

    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "cart_items": cart_items,
            "subtotal": subtotal,
            "primary_discount": pricing["primary_discount"],
            "secondary_discount": pricing["secondary_discount"],
            "discount_amount": pricing["discount_amount"],
            "discounted_subtotal": pricing["discounted_subtotal"],
            "tax_amount": pricing["tax_amount"],
            "delivery_charge": pricing["delivery_charge"],
            "service_charge": pricing["service_charge"],
            "extra_charge": pricing["extra_charge"],
            "final_amount": pricing["final_amount"],
            "applied_offer": pricing["primary_offer"],
            "applied_secondary_offer": pricing["secondary_offer"],
            "active_offers": active_offers,
            "selected_coupon": selected_coupon,
            "coupon_error": pricing["coupon_error"],
            "selected_address_id": str(form["address"].value() or form.fields["address"].initial or ""),
            "free_delivery_applied": pricing["free_delivery_applied"],
            "free_delivery_threshold": FREE_DELIVERY_THRESHOLD,
        },
    )


@login_required
def order_confirmation_view(request, order_id):
    order = get_object_or_404(Order.objects.select_related("address"), pk=order_id, user=request.user)
    return render(request, "orders/order_confirmation.html", {"order": order})


@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items__product")
    return render(request, "orders/order_history.html", {"orders": orders})


@login_required
def reorder_view(request, order_id):
    if request.method != "POST":
        return redirect("orders:order_history")

    order = get_object_or_404(Order.objects.prefetch_related("items__product"), pk=order_id, user=request.user)

    added_items = 0
    limited_items = 0
    skipped_items = 0

    for ordered_item in order.items.select_related("product"):
        product = ordered_item.product

        if not product.is_active or product.stock <= 0:
            skipped_items += 1
            continue

        cart_item, _ = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={"quantity": 0},
        )

        available_to_add = max(product.stock - cart_item.quantity, 0)
        if available_to_add <= 0:
            skipped_items += 1
            continue

        quantity_to_add = min(ordered_item.quantity, available_to_add)
        if quantity_to_add < ordered_item.quantity:
            limited_items += 1

        cart_item.quantity += quantity_to_add
        cart_item.save(update_fields=["quantity"])
        added_items += 1

    if added_items:
        message = f"Re-order added for {added_items} item(s)."
        if limited_items or skipped_items:
            message += f" Limited: {limited_items}, skipped: {skipped_items}."
        messages.success(request, message)
    else:
        messages.warning(request, "No items could be re-ordered (out of stock or inactive).")

    return redirect("cart:cart_detail")


@login_required
def order_tracking_view(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    status_order = [
        Order.STATUS_PENDING,
        Order.STATUS_PROCESSING,
        Order.STATUS_OUT_FOR_DELIVERY,
        Order.STATUS_DELIVERED,
    ]
    return render(
        request,
        "orders/order_tracking.html",
        {
            "order": order,
            "status_order": status_order,
        },
    )
