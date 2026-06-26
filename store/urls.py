from django.urls import path
from . import views

app_name = "store"

urlpatterns = [
    # Retailer Dashboard
    path("dashboard/", views.retailer_dashboard, name="retailer_dashboard"),
    
    # Handle product deletion
    path("product/delete/<int:product_id>/", views.delete_product, name="delete_product"),
    
    # Customer Dashboard (Product List)
    path("products/", views.customer_product_list, name="product_list"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart_item, name="update_cart_item"),
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/summary/", views.cart_summary_json, name="cart_summary"),
]