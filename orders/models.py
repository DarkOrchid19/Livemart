from django.db import models
from django.conf import settings
from store.models import Product


class Order(models.Model):
    """
    A customer's order containing one or multiple items.
    """

    # Order progress status
    class OrderStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    # Payment method chosen at checkout
    class PaymentMode(models.TextChoices):
        ONLINE = "Online", "Online"
        CASH_ON_DELIVERY = "Cash on Delivery", "Cash on Delivery"

    # Payment result
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders",
        limit_choices_to={"role": "CUSTOMER"},
    )

    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )

    payment_mode = models.CharField(
        max_length=20,
        choices=PaymentMode.choices,
        default=PaymentMode.CASH_ON_DELIVERY,
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    # Razorpay identifiers (optional but recommended for tracking)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        customer_email = self.customer.email if self.customer else "unknown"
        return f"Order {self.id} by {customer_email}"


class OrderItem(models.Model):
    """
    Individual product entry within an Order.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price at time of purchase"
    )

    def __str__(self):
        product_name = self.product.name if self.product else "Unknown product"
        return f"{self.quantity} x {product_name}"
