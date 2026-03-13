from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("profile/", views.profile_view, name="profile"),
    path("addresses/", views.address_list_view, name="addresses"),
    path("addresses/<int:pk>/edit/", views.address_edit_view, name="address_edit"),
    path("addresses/<int:pk>/delete/", views.address_delete_view, name="address_delete"),
    path("addresses/<int:pk>/default/", views.set_default_address_view, name="address_default"),
]
