from django.urls import path
from . import views

app_name = "wholesale"

urlpatterns = [
    # Wholesaler's own product management dashboard
    path("dashboard/", views.wholesaler_dashboard, name="wholesaler_dashboard"),
    
    # Handle product deletion
    path("product/delete/<int:product_id>/", views.delete_wholesale_product, name="delete_product"),
    
    # We will add URLs for retailers to browse/order
]