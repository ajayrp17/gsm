from django import forms

from accounts.models import Address
from orders.models import Order


class CheckoutForm(forms.Form):
    address = forms.ModelChoiceField(queryset=Address.objects.none(), empty_label=None)
    payment_method = forms.ChoiceField(choices=Order.PAYMENT_METHOD_CHOICES)
    coupon_code = forms.CharField(max_length=30, required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        initial_coupon = (kwargs.pop("initial_coupon", "") or "").strip().upper()
        super().__init__(*args, **kwargs)
        self.fields["address"].queryset = user.addresses.all()
        default_address = user.addresses.filter(is_default=True).first()
        if default_address:
            self.fields["address"].initial = default_address.pk
        self.fields["address"].widget.attrs.update(
            {
                "class": "form-select address-short-select",
            }
        )
        self.fields["payment_method"].widget.attrs.update({"class": "form-select"})
        self.fields["coupon_code"].initial = initial_coupon
        self.fields["coupon_code"].widget.attrs.update(
            {
                "placeholder": "Enter coupon code",
                "style": "text-transform: uppercase;",
            }
        )
