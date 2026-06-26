# livemart/settings.py

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-txk=xo6v*)21fx2irtqgt*%h5)d9w6u233(+p2x4+k)07-))u@'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party apps
    "django.contrib.sites",  # required by allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # Local apps
    "users.apps.UsersConfig",
    "store.apps.StoreConfig",
    "orders.apps.OrdersConfig",
    "wholesale.apps.WholesaleConfig",
]

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "livemart.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",  # required by allauth
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "store.context_processors.cart_counts",
            ],
        },
    },
]

WSGI_APPLICATION = "livemart.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Custom settings ---
AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# allauth canonical settings
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_SIGNUP_FIELDS = ["email*"]
ACCOUNT_UNIQUE_EMAIL = True
# If your user model doesn't have a username field, keep this None
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# For development; set to "mandatory" in production if you want email verification
ACCOUNT_EMAIL_VERIFICATION = "none"

# IMPORTANT: register the SignupForm subclass so allauth renders password1/password2
ACCOUNT_FORMS = {"signup": "users.forms.CustomSignupForm"}

# Development email backend (prints emails to console)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Redirects
LOGIN_REDIRECT_URL = "dashboard_redirect"
LOGOUT_REDIRECT_URL = "landing_page"
ACCOUNT_LOGOUT_ON_GET = True
#razorpay
RAZORPAY_KEY_ID = "rzp_test_RhEvUU6eQLgDCa"
RAZORPAY_KEY_SECRET = "C2IsKYrCyeFoDxiBTx3uFrW2"


# Social provider config (Google) — replace client_id/secret with real values
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
        "APP": {
            "client_id": "YOUR_GOOGLE_CLIENT_ID",
            "secret": "YOUR_GOOGLE_CLIENT_SECRET",
        },
    }
}