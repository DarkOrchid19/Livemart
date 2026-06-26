from django.db import models
from django.conf import settings
from store.models import Category # Reuse category from store app

class WholesaleProduct(models.Model):
    """
    A product sold by a Wholesaler to a Retailer.
    """
    wholesaler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wholesale_products",
        limit_choices_to={"role": "WHOLESALER"}
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="wholesale_products")
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit/case")
    stock_quantity = models.PositiveIntegerField(help_text="Available units/cases")
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (Wholesaler: {self.wholesaler.full_name})"

class WholesaleOrder(models.Model):
    """
    An order placed by a Retailer to a Wholesaler.
    """
    class OrderStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        SHIPPED = "SHIPPED", "Shipped"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    retailer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="wholesale_orders_placed",
        limit_choices_to={"role": "RETAILER"}
    )
    wholesaler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="wholesale_orders_received",
        limit_choices_to={"role": "WHOLESALER"}
    )
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Order {self.id} from {self.retailer} to {self.wholesaler}"

class WholesaleOrderItem(models.Model):
    order = models.ForeignKey(WholesaleOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(WholesaleProduct, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price at time of order")

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"