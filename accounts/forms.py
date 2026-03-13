from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Address, Profile


class StyledFormMixin:
    """Attach consistent classes/placeholders for themed UI."""

    field_placeholders = {}

    def _apply_styles(self):
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            else:
                css_class = "form-control"

            existing_class = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing_class} {css_class}".strip()
            widget.attrs["placeholder"] = self.field_placeholders.get(name, field.label)

            if name in ("password1", "password2", "password"):
                widget.attrs["autocomplete"] = "new-password"


class RegistrationForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)
    field_placeholders = {
        "username": "Choose a username",
        "first_name": "First name",
        "last_name": "Last name",
        "email": "you@example.com",
        "password1": "Create password",
        "password2": "Confirm password",
    }

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_styles()
        self.fields["username"].help_text = "Use letters, numbers, and @/./+/-/_ only."
        self.fields["password1"].help_text = "Use 8+ characters and avoid common or numeric-only passwords."
        self.fields["password2"].help_text = "Re-enter the same password for confirmation."


class LoginForm(StyledFormMixin, AuthenticationForm):
    field_placeholders = {
        "username": "Enter username",
        "password": "Enter password",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_styles()
        self.fields["password"].widget.attrs["autocomplete"] = "current-password"


class UserUpdateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_styles()


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("phone", "avatar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_styles()


class AddressForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            "label",
            "full_name",
            "phone",
            "line1",
            "line2",
            "city",
            "state",
            "postal_code",
            "landmark",
            "is_default",
        )

    field_placeholders = {
        "label": "Home / Work / Other",
        "full_name": "Full name",
        "phone": "Phone number",
        "line1": "House number, street",
        "line2": "Apartment, suite, etc. (optional)",
        "city": "City",
        "state": "State",
        "postal_code": "Postal code",
        "landmark": "Nearby landmark (optional)",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_styles()
