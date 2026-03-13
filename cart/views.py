from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from catalog.models import Product

from .forms import CartQuantityForm
from .models import CartItem, WishlistItem


@login_required
def cart_detail_view(request):
    items = CartItem.objects.filter(user=request.user).select_related("product")
    total = sum(item.subtotal for item in items)
    return render(request, "cart/cart_detail.html", {"items": items, "total": total})


@login_required
def add_to_cart_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)

    item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.quantity += 1

    if item.quantity > product.stock:
        item.quantity = product.stock
        messages.warning(request, "Stock limit reached for this item.")

    item.save()
    messages.success(request, f"{product.name} added to cart.")
    return redirect(request.META.get("HTTP_REFERER", "catalog:product_list"))


@login_required
def update_cart_item_view(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, user=request.user)

    if request.method == "POST":
        form = CartQuantityForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data["quantity"]
            item.quantity = min(quantity, item.product.stock)
            item.save()
            messages.success(request, "Cart updated.")
    return redirect("cart:cart_detail")


@login_required
def remove_cart_item_view(request, item_id):
    if request.method == "POST":
        item = get_object_or_404(CartItem, pk=item_id, user=request.user)
        item.delete()
        messages.info(request, "Item removed from cart.")
    return redirect("cart:cart_detail")


@login_required
def wishlist_view(request):
    items = WishlistItem.objects.filter(user=request.user).select_related("product")
    return render(request, "cart/wishlist.html", {"items": items})


@login_required
def add_to_wishlist_view(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    WishlistItem.objects.get_or_create(user=request.user, product=product)
    messages.success(request, f"{product.name} added to wishlist.")
    return redirect(request.META.get("HTTP_REFERER", "catalog:product_list"))


@login_required
def remove_from_wishlist_view(request, item_id):
    if request.method == "POST":
        item = get_object_or_404(WishlistItem, pk=item_id, user=request.user)
        item.delete()
        messages.info(request, "Removed from wishlist.")
    return redirect("cart:wishlist")
