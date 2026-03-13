from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ReviewForm
from .models import Category, Offer, Product, Review
from orders.models import Order


def home_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("dashboard:home")

    today = timezone.now().date()
    featured_products = Product.objects.filter(is_active=True).select_related("category")[:8]
    categories = Category.objects.all()[:6]
    active_coupon_offers = (
        Offer.objects.filter(active=True, expiry_date__gte=today, coupon_code__isnull=False)
        .exclude(coupon_code="")
        .order_by("-discount_percentage", "expiry_date")[:5]
    )
    latest_order = None
    if request.user.is_authenticated:
        latest_order = Order.objects.filter(user=request.user).order_by("-created_at").first()

    return render(
        request,
        "catalog/home.html",
        {
            "featured_products": featured_products,
            "categories": categories,
            "active_coupon_offers": active_coupon_offers,
            "latest_order": latest_order,
        },
    )


def product_list_view(request):
    products = Product.objects.filter(is_active=True).select_related("category")
    categories = Category.objects.all()

    search_query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    offer_only = request.GET.get("offer_only", "").strip() == "1"
    today = timezone.now().date()

    if offer_only:
        products = products.filter(offers__active=True, offers__expiry_date__gte=today).distinct()

    if search_query:
        products = products.filter(Q(name__icontains=search_query) | Q(description__icontains=search_query))

    if category_slug:
        products = products.filter(category__slug=category_slug)

    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except (InvalidOperation, ValueError):
            messages.warning(request, "Invalid minimum price filter ignored.")

    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except (InvalidOperation, ValueError):
            messages.warning(request, "Invalid maximum price filter ignored.")

    return render(
        request,
        "catalog/product_list.html",
        {
            "products": products,
            "categories": categories,
            "search_query": search_query,
            "selected_category": category_slug,
            "min_price": min_price,
            "max_price": max_price,
            "offer_only": offer_only,
        },
    )


def product_detail_view(request, slug):
    product = get_object_or_404(Product.objects.select_related("category"), slug=slug, is_active=True)
    reviews = product.reviews.select_related("user")

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "Please login to leave a review.")
            return redirect("login")

        review_instance = Review.objects.filter(user=request.user, product=product).first()
        form = ReviewForm(request.POST, instance=review_instance)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.product = product
            review.save()
            messages.success(request, "Review submitted successfully.")
            return redirect("catalog:product_detail", slug=slug)
    else:
        existing_review = None
        if request.user.is_authenticated:
            existing_review = Review.objects.filter(user=request.user, product=product).first()
        form = ReviewForm(instance=existing_review)

    related_products = Product.objects.filter(category=product.category, is_active=True).exclude(pk=product.pk)[:4]

    return render(
        request,
        "catalog/product_detail.html",
        {
            "product": product,
            "reviews": reviews,
            "review_form": form,
            "related_products": related_products,
        },
    )
