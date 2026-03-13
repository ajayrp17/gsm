from django import forms

from catalog.models import Category, Offer, Product
from orders.models import BillingConfiguration


class DashboardCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "description")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }


class DashboardProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ("category", "name", "description", "price", "stock", "image", "expiry_date", "is_active")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }


class DashboardOfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = (
            "name",
            "coupon_code",
            "offer_type",
            "discount_percentage",
            "min_order_amount",
            "max_discount_amount",
            "min_completed_orders",
            "max_uses_per_user",
            "allow_with_other_coupon",
            "auto_apply",
            "priority",
            "expiry_date",
            "active",
            "products",
        )
        widgets = {
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
            "products": forms.SelectMultiple(attrs={"size": 8}),
        }

    def clean_coupon_code(self):
        coupon_code = (self.cleaned_data.get("coupon_code") or "").strip().upper()
        return coupon_code or None

    def clean(self):
        cleaned_data = super().clean()
        offer_type = cleaned_data.get("offer_type")

        if offer_type == Offer.TYPE_DAILY:
            if not cleaned_data.get("min_completed_orders"):
                cleaned_data["min_completed_orders"] = 5
            if not cleaned_data.get("max_uses_per_user"):
                cleaned_data["max_uses_per_user"] = 2
            cleaned_data["allow_with_other_coupon"] = True

        return cleaned_data


class DashboardBillingConfigurationForm(forms.ModelForm):
    class Meta:
        model = BillingConfiguration
        fields = ("tax_percentage", "delivery_charge", "service_charge", "extra_charge")
