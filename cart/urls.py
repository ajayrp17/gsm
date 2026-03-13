from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail_view, name="cart_detail"),
    path("add/<int:product_id>/", views.add_to_cart_view, name="add_to_cart"),
    path("update/<int:item_id>/", views.update_cart_item_view, name="update_cart_item"),
    path("remove/<int:item_id>/", views.remove_cart_item_view, name="remove_cart_item"),
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/add/<int:product_id>/", views.add_to_wishlist_view, name="add_to_wishlist"),
    path("wishlist/remove/<int:item_id>/", views.remove_from_wishlist_view, name="remove_from_wishlist"),
]
