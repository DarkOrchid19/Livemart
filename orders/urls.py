from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.view_cart, name="view_cart"),
    path("add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("razorpay/verify/", views.razorpay_verify, name="razorpay_verify"),
]
