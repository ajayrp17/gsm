from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from catalog.models import Offer

from .forms import AddressForm, LoginForm, ProfileForm, RegistrationForm, UserUpdateForm
from .models import Address, Profile


class ThemedLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "registration/login.html"

    def get_success_url(self):
        if self.request.user.is_staff:
            return reverse("dashboard:home")
        return super().get_success_url()


def register_view(request):
    if request.user.is_authenticated:
        return redirect("catalog:home")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect("catalog:home")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    active_offers = (
        Offer.objects.filter(active=True, coupon_code__isnull=False)
        .exclude(coupon_code="")
        .filter(expiry_date__gte=timezone.now().date())
        .order_by("-discount_percentage", "expiry_date")[:6]
    )

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)

    return render(
        request,
        "accounts/profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "active_offers": active_offers,
        },
    )


@login_required
def address_list_view(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Address saved.")
            return redirect("accounts:addresses")
    else:
        form = AddressForm()

    addresses = request.user.addresses.all()
    return render(
        request,
        "accounts/address_list.html",
        {
            "addresses": addresses,
            "form": form,
        },
    )


@login_required
def address_edit_view(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated.")
            return redirect("accounts:addresses")
    else:
        form = AddressForm(instance=address)

    return render(request, "accounts/address_form.html", {"form": form, "address": address})


@login_required
def address_delete_view(request, pk):
    if request.method == "POST":
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.delete()
        messages.info(request, "Address deleted.")
    return redirect("accounts:addresses")


@login_required
def set_default_address_view(request, pk):
    if request.method == "POST":
        address = get_object_or_404(Address, pk=pk, user=request.user)
        address.is_default = True
        address.save()
        messages.success(request, "Default address updated.")
    return redirect("accounts:addresses")
