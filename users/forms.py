from django import forms
from allauth.account.forms import SignupForm
from .models import User

INPUT_CLASS = (
    "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm "
    "placeholder-gray-400 focus:outline-none focus:ring-cyan-500 focus:border-cyan-500 sm:text-sm"
)

class CustomSignupForm(SignupForm):
    # explicitly add password fields
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        required=True,
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
        required=True,
    )

    full_name = forms.CharField(label="Full name", max_length=255, required=True)

    role = forms.ChoiceField(
        choices=[
            (User.Role.CUSTOMER, "I am a Customer"),
            (User.Role.RETAILER, "I am a Retailer"),
            (User.Role.WHOLESALER, "I am a Wholesaler"),
        ],
        widget=forms.RadioSelect,
        label="I am a",
        required=True,
    )

    pincode = forms.CharField(
        label="Pincode",
        required=False,
        help_text="Required if you are a Retailer or Wholesaler.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add classes/placeholder to all input fields
        for name, field in self.fields.items():
            widget = field.widget
            if not isinstance(widget, forms.RadioSelect):
                widget.attrs["class"] = INPUT_CLASS

            if name == "email":
                widget.attrs.setdefault("placeholder", "Email address")
            if name == "full_name":
                widget.attrs.setdefault("placeholder", "Full name")
            if name == "pincode":
                widget.attrs.setdefault("placeholder", "Pincode (if applicable)")
            if name == "password1":
                widget.attrs.setdefault("placeholder", "Password")
            if name == "password2":
                widget.attrs.setdefault("placeholder", "Confirm password")

    def clean(self):
        cleaned = super().clean()

        # Check password match
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")

        # Check pincode requirement
        role = cleaned.get("role")
        pincode = cleaned.get("pincode")
        if role in (User.Role.RETAILER, User.Role.WHOLESALER) and not pincode:
            self.add_error("pincode", "Pincode is required for Retailers and Wholesalers.")

        return cleaned

    def signup(self, request, user):
        user.full_name = self.cleaned_data.get("full_name")
        user.role = self.cleaned_data.get("role")
        user.pincode = self.cleaned_data.get("pincode")
        user.save()
        return user
