from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("products/", views.product_list_view, name="product_list"),
    path("products/<slug:slug>/", views.product_detail_view, name="product_detail"),
]
