from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .models import WholesaleProduct
from store.models import Category # Reuse categories
from .forms import WholesaleProductForm

@login_required
def wholesaler_dashboard(request):
    """
    Displays the Wholesaler's "My Products" page.
    Handles adding, editing, and deleting products.
    """
    if not request.user.is_wholesaler:
        return HttpResponseForbidden("You are not authorized to view this page.")

    products = WholesaleProduct.objects.filter(wholesaler=request.user)
    categories = Category.objects.all()
    
    if request.method == "POST":
        form_type = request.POST.get("form_type")
        
        if form_type == "add_product":
            form = WholesaleProductForm(request.POST)
            if form.is_valid():
                product = form.save(commit=False)
                product.wholesaler = request.user
                product.save()
                return redirect("wholesale:wholesaler_dashboard")
        
        elif form_type == "edit_product":
            product_id = request.POST.get("product_id")
            product = get_object_or_404(WholesaleProduct, id=product_id, wholesaler=request.user)
            form = WholesaleProductForm(request.POST, instance=product)
            if form.is_valid():
                form.save()
                return redirect("wholesale:wholesaler_dashboard")
    
    add_form = WholesaleProductForm()
    
    context = {
        "products": products,
        "categories": categories,
        "add_form": add_form,
    }
    return render(request, "wholesale/wholesaler_dashboard.html", context)

@login_required
def delete_wholesale_product(request, product_id):
    """
    Handles the POST request to delete a wholesale product.
    """
    if not request.user.is_wholesaler:
        return HttpResponseForbidden()
        
    product = get_object_or_404(WholesaleProduct, id=product_id, wholesaler=request.user)
    if request.method == "POST":
        product.delete()
        return redirect("wholesale:wholesaler_dashboard")
    
    return redirect("wholesale:wholesaler_dashboard")

# We will add views for retailers to browse and order from wholesalers next