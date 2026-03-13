from django.contrib import admin
from django.contrib import messages

from .models import Category, Offer, Product, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "is_active", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("price", "stock", "is_active")
    actions = ("activate_products", "deactivate_products")

    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} item(s) activated.", level=messages.SUCCESS)
    activate_products.short_description = "Activate selected items"

    def deactivate_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} item(s) deactivated.", level=messages.WARNING)
    deactivate_products.short_description = "Deactivate selected items"


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("name", "coupon_code", "discount_percentage", "expiry_date", "active", "is_valid")
    list_filter = ("active", "expiry_date")
    search_fields = ("name", "coupon_code")
    filter_horizontal = ("products",)
    actions = ("activate_offers", "deactivate_offers")

    def save_model(self, request, obj, form, change):
        if obj.coupon_code:
            obj.coupon_code = obj.coupon_code.strip().upper()
        super().save_model(request, obj, form, change)

    def activate_offers(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(request, f"{updated} offer(s) activated.", level=messages.SUCCESS)
    activate_offers.short_description = "Activate selected offers"

    def deactivate_offers(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(request, f"{updated} offer(s) deactivated.", level=messages.WARNING)
    deactivate_offers.short_description = "Deactivate selected offers"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("product__name", "user__username")
