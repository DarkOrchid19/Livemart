# store/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Product, Category, CartItem
from .forms import ProductForm
from .utils import get_or_create_cart

def landing_page(request):
    """
    Renders the main landing page (f1.png, f2.png).
    """
    if request.user.is_authenticated:
        # If user is already logged in, send them to their dashboard
        return redirect("dashboard_redirect")
    return render(request, "landing_page.html")


@login_required
def retailer_dashboard(request):
    """
    Displays the Retailer's "My Products" page (f5.png, f8.png).
    Handles adding, editing, and deleting products.
    """
    if not request.user.is_retailer:
        return HttpResponseForbidden("You are not authorized to view this page.")

    # Get all products for the *current* logged-in retailer
    products = Product.objects.filter(retailer=request.user)
    categories = Category.objects.all()

    # This view will also handle the POST request from the "Add New Product" modal
    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "add_product":
            form = ProductForm(request.POST)
            if form.is_valid():
                product = form.save(commit=False)
                product.retailer = request.user
                product.save()
                # We can add a success message here
                return redirect("store:retailer_dashboard")
            else:
                # Fall through and show form errors in context
                add_form = form

        elif form_type == "edit_product":
            product_id = request.POST.get("product_id")
            product = get_object_or_404(Product, id=product_id, retailer=request.user)
            form = ProductForm(request.POST, instance=product)
            if form.is_valid():
                form.save()
                return redirect("store:retailer_dashboard")
            else:
                # If edit fails, keep the add_form as a fresh one and include edit errors via JS/template
                add_form = ProductForm()
        else:
            add_form = ProductForm()
    else:
        add_form = ProductForm()

    # Pre-populate the forms for the modal
    context = {
        "products": products,
        "categories": categories,
        "add_form": add_form,
    }
    return render(request, "store/retailer_dashboard.html", context)


@login_required
def delete_product(request, product_id):
    """
    Handles the POST request to delete a product.
    """
    if not request.user.is_retailer:
        return HttpResponseForbidden()

    product = get_object_or_404(Product, id=product_id, retailer=request.user)
    if request.method == "POST":
        product.delete()
        return redirect("store:retailer_dashboard")

    # Should not be reached via GET
    return redirect("store:retailer_dashboard")


@login_required
def customer_product_list(request):
    """
    The main customer dashboard.
    A grid of all available products from all retailers.
    Includes the Pincode filter.
    """
    products = Product.objects.filter(is_available=True, stock_quantity__gt=0)

    pincode = request.GET.get("pincode")
    if pincode:
        # Filter products based on retailers in that pincode
        products = products.filter(retailer__pincode=pincode)

    context = {
        "products": products,
        "search_pincode": pincode,
    }
    return render(request, "store/customer_product_list.html", context)


# -------------------------------
# Cart-related views
# -------------------------------

@require_POST
def add_to_cart(request, product_id):
    """
    Add a product to the current cart (session or authenticated user).
    Returns JSON when called via AJAX with helpful snapshot data.
    """
    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Invalid quantity")

    if qty < 1:
        return HttpResponseBadRequest("Quantity must be >= 1")

    product = get_object_or_404(Product, id=product_id)

    if not getattr(product, "is_available", True):
        return HttpResponseBadRequest("Product is not available")

    cart = get_or_create_cart(request)

    # --- START: stock-safe add/update logic ---
    existing_qty = 0
    existing_item = CartItem.objects.filter(cart=cart, product=product).first()
    if existing_item:
        existing_qty = existing_item.quantity

    new_total = existing_qty + qty

    if new_total > product.stock_quantity:
        # Return an error describing available units
        return HttpResponseBadRequest(f"Only {product.stock_quantity} units available.")

    # Safe add/update
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={"quantity": qty})
    if not created:
        item.quantity = new_total
    item.save()
    # --- END: stock-safe add/update logic ---

    # compute a small snapshot to return
    try:
        # try to compute unit price & subtotal
        unit_price = float(getattr(item, "price", None) or getattr(item.product, "price", 0.0))
    except Exception:
        unit_price = 0.0
    subtotal = unit_price * int(getattr(item, "quantity", 0) or 0)

    # Cart-level totals: prefer attributes if available
    total_items = getattr(cart, "total_items", None)
    total_price = getattr(cart, "total_price", None)
    if total_items is None or total_price is None:
        # best-effort compute
        try:
            total_items = sum(int(getattr(i, "quantity", 0) or 0) for i in getattr(cart, "items").all())
            total_price = sum((float(getattr(i, "price", None) or getattr(i.product, "price", 0.0)) * int(getattr(i, "quantity", 0) or 0)) for i in getattr(cart, "items").all())
        except Exception:
            total_items = int(getattr(item, "quantity", 0) or 0)
            total_price = float(subtotal)

    # item snapshot to return
    item_snapshot = {
        "id": item.id,
        "product_id": getattr(item.product, "id", None),
        "title": getattr(item.product, "name", None) or getattr(item.product, "title", "") or "",
        "quantity": int(getattr(item, "quantity", 0) or 0),
        "unit_price": float(unit_price),
        "subtotal": float(subtotal),
        "image_url": getattr(getattr(item.product, "image", None), "url", "") or "",
    }

    # Return JSON for AJAX clients
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": True,
            "created": bool(created),
            "item": item_snapshot,
            "total_items": int(total_items or 0),
            "total_price": float(total_price or 0.0),
        })

    # Non-AJAX: redirect back
    return redirect(request.POST.get("next") or request.META.get("HTTP_REFERER") or "/")


@require_POST
def update_cart_item(request, item_id):
    """
    Update a cart item's quantity (or remove if quantity <= 0).
    """
    cart = get_or_create_cart(request)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)

    try:
        qty = int(request.POST.get("quantity", 0))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Invalid quantity")

    if qty <= 0:
        item.delete()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({
                "ok": True,
                "total_items": cart.total_items,
                "total_price": float(cart.total_price),
            })
        return redirect("store:view_cart")

    # Stock validation: do not allow a cart item to exceed product stock
    if qty > item.product.stock_quantity:
        return HttpResponseBadRequest(f"Only {item.product.stock_quantity} units available.")

    item.quantity = qty
    item.save()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "ok": True,
            "total_items": cart.total_items,
            "total_price": float(cart.total_price),
        })

    return redirect("store:view_cart")


def view_cart(request):
    """
    Render the cart page and compute numeric totals for each item and the cart.
    Do NOT assign attributes on the Cart model if it defines read-only properties.
    """
    cart = get_or_create_cart(request)

    # Get items (safe list)
    items = list(cart.items.select_related("product", "product__retailer").all()) if getattr(cart, "pk", None) else []

    # Compute numeric subtotal for each item and cart totals
    cart_total_items = 0
    cart_total_price = 0.0

    for item in items:
        # safe quantity
        try:
            qty = int(item.quantity)
        except Exception:
            qty = 0
        cart_total_items += qty

        # unit price: prefer item.price if stored on the cart item
        try:
            unit_price = float(getattr(item, "price", None) or getattr(item.product, "price", 0.0))
        except Exception:
            unit_price = 0.0

        subtotal = qty * unit_price

        # attach numeric fields to the item for template use (safe)
        item.unit_price = unit_price
        item.subtotal = subtotal

        cart_total_price += subtotal

    context = {
        "cart": cart,
        "items": items,
        "cart_total_items": cart_total_items,
        "cart_total_price": cart_total_price,
    }
    return render(request, "store/cart.html", context)

@require_GET
def cart_summary_json(request):
    """
    Return a small JSON snapshot of the cart for client-side rendering.
    """
    snapshot = {"cart_total_items": 0, "cart_total_price": 0.0, "cart_items": []}

    try:
        cart = get_or_create_cart(request)
    except Exception:
        return JsonResponse(snapshot)

    # total items via property if available
    try:
        snapshot["cart_total_items"] = int(getattr(cart, "total_items", 0) or 0)
    except Exception:
        snapshot["cart_total_items"] = 0

    total_price = 0.0
    items_list = []
    try:
        items_qs = getattr(cart, "items", None)
        iterator = items_qs.all() if hasattr(items_qs, "all") else items_qs or []
        for item in iterator:
            try:
                qty = int(getattr(item, "quantity", 0) or 0)
            except Exception:
                qty = 0
            try:
                unit_price = float(getattr(item, "price", None) or getattr(item.product, "price", 0.0))
            except Exception:
                unit_price = 0.0
            subtotal = qty * unit_price
            total_price += subtotal

            image_url = ""
            try:
                prod = getattr(item, "product", None)
                if prod is not None:
                    image_field = getattr(prod, "image", None)
                    if image_field:
                        try:
                            image_url = image_field.url
                        except Exception:
                            image_url = str(image_field)
                    else:
                        try:
                            image_url = prod.image_url or ""
                        except Exception:
                            image_url = ""
            except Exception:
                image_url = ""

            title = ""
            try:
                title = getattr(item.product, "name", "") or getattr(item.product, "title", "") or ""
            except Exception:
                title = ""

            items_list.append({
                "id": getattr(item, "id", None),
                "product_id": getattr(item.product, "id", None) if getattr(item, "product", None) else None,
                "title": title,
                "quantity": qty,
                "unit_price": unit_price,
                "subtotal": subtotal,
                "image_url": image_url,
            })
    except Exception:
        items_list = []

    snapshot["cart_items"] = items_list
    snapshot["cart_total_price"] = float(total_price or 0.0)
    # If total_items was not set earlier, ensure consistent value
    if snapshot["cart_total_items"] == 0:
        snapshot["cart_total_items"] = sum(it["quantity"] for it in items_list) if items_list else 0

    return JsonResponse(snapshot)
