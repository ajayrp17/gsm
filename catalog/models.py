from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def average_rating(self):
        return self.reviews.aggregate(avg=Avg("rating"))["avg"] or 0

    @property
    def review_count(self):
        return self.reviews.count()

    @property
    def active_offer(self):
        today = timezone.now().date()
        return (
            self.offers.filter(active=True, expiry_date__gte=today)
            .order_by("-discount_percentage")
            .first()
        )

    @property
    def discounted_price(self):
        offer = self.active_offer
        if not offer:
            return self.price
        discount_amount = (self.price * Decimal(offer.discount_percentage)) / Decimal("100")
        return max(self.price - discount_amount, Decimal("0.00"))


class Offer(models.Model):
    TYPE_GENERAL = "general"
    TYPE_FIRST_ORDER = "first_order"
    TYPE_DAILY = "daily"
    TYPE_SYSTEM = "system"

    OFFER_TYPE_CHOICES = [
        (TYPE_GENERAL, "General Coupon"),
        (TYPE_FIRST_ORDER, "First Order Offer"),
        (TYPE_DAILY, "Daily / Loyalty Offer"),
        (TYPE_SYSTEM, "System Default Offer"),
    ]

    name = models.CharField(max_length=120)
    coupon_code = models.CharField(max_length=30, unique=True, blank=True, null=True)
    discount_percentage = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(90)]
    )
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE_CHOICES, default=TYPE_GENERAL)
    expiry_date = models.DateField()
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    min_completed_orders = models.PositiveIntegerField(default=0)
    max_uses_per_user = models.PositiveIntegerField(default=0)
    allow_with_other_coupon = models.BooleanField(default=False)
    auto_apply = models.BooleanField(default=False)
    priority = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    products = models.ManyToManyField(Product, related_name="offers", blank=True)

    class Meta:
        ordering = ["-priority", "-expiry_date"]

    def __str__(self):
        return self.coupon_code or self.name

    @property
    def is_valid(self):
        return self.active and self.expiry_date >= timezone.now().date()


class Review(models.Model):
    RATING_CHOICES = [(i, f"{i} Star") for i in range(1, 6)]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} - {self.rating}"
