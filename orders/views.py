# orders/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

import json
import razorpay

from store.models import Product, CartItem
from store.utils import get_or_create_cart  # reuse existing cart logic
from .models import Order, OrderItem


@require_POST
@login_required
def add_to_cart(request, product_id):
    """
    (Optional) Separate add-to-cart for orders app – you can ignore this
    if you're using the store.add_to_cart view instead.
    """
    product = get_object_or_404(Product, id=product_id)
    # For simplicity, always add 1
    cart = get_or_create_cart(request)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": 1},
    )
    if not created:
        item.quantity += 1
        item.save()

    request.session["message"] = f"Added {product.name} to cart."
    return redirect("store:product_list")


@login_required
def view_cart(request):
    """
    You probably don't need this if you're using store:view_cart.
    Keeping it here for completeness.
    """
    cart = get_or_create_cart(request)
    items = list(
        cart.items.select_related("product", "product__retailer").all()
    ) if getattr(cart, "pk", None) else []

    cart_total_items = 0
    cart_total_price = 0.0

    for item in items:
        try:
            qty = int(item.quantity)
        except Exception:
            qty = 0
        cart_total_items += qty

        try:
            unit_price = float(getattr(item, "price", None) or getattr(item.product, "price", 0.0))
        except Exception:
            unit_price = 0.0

        subtotal = qty * unit_price
        item.unit_price = unit_price
        item.subtotal = subtotal
        cart_total_price += subtotal

    context = {
        "cart": cart,
        "items": items,
        "cart_total_items": cart_total_items,
        "cart_total_price": cart_total_price,
    }
    return render(request, "orders/cart_orders.html", context)


@login_required
@transaction.atomic
def checkout(request):
    """
    GET  -> Show checkout page with order summary + payment mode.
    POST -> 
        - If COD: create Order + OrderItems, reduce stock, clear cart, success page.
        - If Online: create pending Order + Razorpay order, show Razorpay payment page.
    """
    cart = get_or_create_cart(request)
    items_qs = cart.items.select_related("product", "product__retailer").all() if getattr(cart, "pk", None) else []
    items = list(items_qs)

    # Compute totals like in store.view_cart
    cart_total_items = 0
    cart_total_price = 0.0

    for item in items:
        try:
            qty = int(item.quantity)
        except Exception:
            qty = 0
        cart_total_items += qty

        try:
            unit_price = float(getattr(item, "price", None) or getattr(item.product, "price", 0.0))
        except Exception:
            unit_price = 0.0

        subtotal = qty * unit_price
        item.unit_price = unit_price
        item.subtotal = subtotal
        cart_total_price += subtotal

    # If cart is empty, redirect back to product list
    if not items:
        return redirect("store:product_list")

    # ---------- GET: show checkout page ----------
    if request.method == "GET":
        return render(
            request,
            "orders/checkout.html",
            {
                "items": items,
                "cart_total_items": cart_total_items,
                "cart_total_price": cart_total_price,
            },
        )

    # ---------- POST: place order / init payment ----------
    payment_mode = request.POST.get("payment_mode")

    if payment_mode not in ["Online", "Cash on Delivery"]:
        return render(
            request,
            "orders/checkout.html",
            {
                "items": items,
                "cart_total_items": cart_total_items,
                "cart_total_price": cart_total_price,
                "error": "Please select a valid payment mode.",
            },
        )

    customer = request.user

    # Create the Order (status/payment_status fields are optional if you added them)
    order = Order.objects.create(
        customer=customer,
        payment_mode=payment_mode,
        # status=Order.OrderStatus.PENDING,            # if you want
        # payment_status=Order.PaymentStatus.PENDING,  # if you added this field
    )

    # Create OrderItems but DON'T touch stock yet for Online payments
    for item in items:
        product = item.product
        if not product:
            continue

        qty = int(item.quantity)

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            price=item.unit_price,
        )

    # ---------- If COD: fulfil immediately ----------
    if payment_mode == "Cash on Delivery":
        _fulfil_order_and_clear_cart(order, cart)
        return render(request, "orders/checkout_success.html", {"order": order})

    # ---------- If Online: create Razorpay order & show payment page ----------
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    except AttributeError:
        # Keys not configured properly
        return HttpResponseBadRequest("Razorpay keys not configured in settings.")

    razorpay_order = client.order.create({
        "amount": int(cart_total_price * 100),  # amount in paise
        "currency": "INR",
        "payment_capture": 1,  # auto capture
        "notes": {
            "internal_order_id": str(order.id),
            "customer_email": customer.email or "",
        }
    })

    # Optional: store Razorpay order id on our Order model (requires field)
    # Make sure you added this field in models.py:
    # razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    if hasattr(order, "razorpay_order_id"):
        order.razorpay_order_id = razorpay_order["id"]
        order.save()

    return render(
        request,
        "orders/payment_razorpay.html",
        {
            "order": order,
            "items": items,
            "cart_total_price": cart_total_price,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "razorpay_order_id": razorpay_order["id"],
            "amount": int(cart_total_price * 100),
            "currency": "INR",
        },
    )


def _fulfil_order_and_clear_cart(order, cart):
    """
    Deduct stock, clear cart, and update order status.
    Used for COD immediately and for Online AFTER successful payment.
    """
    products_to_update = []

    for item in order.items.select_related("product").all():
        product = item.product
        if not product:
            continue

        qty = item.quantity

        # Stock check
        if product.stock_quantity < qty:
            if product.stock_quantity <= 0:
                continue
            qty = product.stock_quantity
            item.quantity = qty
            item.save()

        product.stock_quantity -= qty
        products_to_update.append(product)

    if products_to_update:
        Product.objects.bulk_update(products_to_update, ["stock_quantity"])

    # Clear DB cart
    try:
        cart.items.all().delete()
    except Exception:
        pass

    # Optionally update statuses if you added fields
    if hasattr(order, "status"):
        order.status = Order.OrderStatus.PENDING  # or CONFIRMED if you add it
    if hasattr(order, "payment_status") and order.payment_mode == "Online":
        order.payment_status = getattr(Order.PaymentStatus, "PAID", None) or "PAID"
    order.save()


@csrf_exempt
@transaction.atomic
def razorpay_verify(request):
    """
    Endpoint hit from JS after Razorpay payment success.
    Verifies signature and then fulfils the order.
    """
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Invalid method"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    order_id = data.get("order_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")

    if not all([order_id, razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return JsonResponse({"ok": False, "error": "Missing parameters"}, status=400)

    order = get_object_or_404(Order, id=order_id)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        if hasattr(order, "payment_status"):
            order.payment_status = getattr(Order.PaymentStatus, "FAILED", None) or "FAILED"
            order.save()
        return JsonResponse({"ok": False, "error": "Signature verification failed"}, status=400)

    # Mark paid and fulfil
    if hasattr(order, "razorpay_payment_id"):
        order.razorpay_payment_id = razorpay_payment_id
    if hasattr(order, "razorpay_signature"):
        order.razorpay_signature = razorpay_signature
    if hasattr(order, "payment_status"):
        order.payment_status = getattr(Order.PaymentStatus, "PAID", None) or "PAID"
    order.save()

    # Recreate cart from request to clear it properly
    cart = get_or_create_cart(request)
    _fulfil_order_and_clear_cart(order, cart)

    # You can change this to reverse("orders:success", args=[order.id])
    return JsonResponse({
        "ok": True,
        "redirect_url": f"/orders/success/{order.id}/"
    })
