from django.shortcuts import redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import User

class DashboardRedirectView(LoginRequiredMixin, View):
    """
    Redirects users to their appropriate dashboard based on their role.
    This is the view mapped to LOGIN_REDIRECT_URL.
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        
        if user.is_retailer:
            return redirect("store:retailer_dashboard")
        elif user.is_wholesaler:
            return redirect("wholesale:wholesaler_dashboard")
        elif user.is_customer:
            return redirect("store:product_list")
        else:
            # Fallback for admins or other roles
            return redirect("admin:index")

# We don't need many other views here, as allauth and app-specific
# views will handle the rest.