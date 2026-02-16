import secrets
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent


def get_csv(name: str, default: str = "") -> list[str]:
    return [item for item in config(name, cast=Csv(), default=default) if item]


DEBUG = config("DJANGO_DEBUG", cast=bool, default=False)
SECRET_KEY = config("DJANGO_SECRET_KEY", default="")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = secrets.token_urlsafe(64)
    else:
        raise ValueError("DJANGO_SECRET_KEY must be configured when DJANGO_DEBUG is False.")
ALLOWED_HOSTS = get_csv("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "project_settings.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "project_settings.wsgi.application"


def get_database_config():
    # First try individual configs
    db_name = config("DB_NAME", default="")
    db_user = config("DB_USER", default="")
    db_password = config("DB_PASSWORD", default="")
    db_host = config("DB_HOST", default="")
    db_port = config("DB_PORT", default="")

    if db_name and db_user and db_password:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
        }

    database_url = config("DATABASE_URL", default="")
    if not database_url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }

    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()
    if scheme == "sqlite":
        if database_url.startswith("sqlite:////"):
            name = parsed.path
        elif parsed.path and parsed.path != "/":
            name = parsed.path[1:] if parsed.path.startswith("/") else parsed.path
        else:
            name = BASE_DIR / "db.sqlite3"
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": name,
        }

    if scheme in {"postgres", "postgresql"}:
        database = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/") or "",
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
        }
        options = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
        if options:
            database["OPTIONS"] = options
        return database

    raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}")


DATABASES = {"default": get_database_config()}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = get_csv("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = config("CORS_ALLOW_CREDENTIALS", cast=bool, default=True)
if DEBUG and not CORS_ALLOWED_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = get_csv("CSRF_TRUSTED_ORIGINS")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "api.tools.auth.authentication.ClerkJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("DRF_THROTTLE_ANON", default="120/min"),
        "user": config("DRF_THROTTLE_USER", default="1500/hour"),
        "checkout_create": config("DRF_THROTTLE_CHECKOUT_CREATE", default="60/hour"),
        "order_confirm": config("DRF_THROTTLE_ORDER_CONFIRM", default="60/hour"),
        "download_access": config("DRF_THROTTLE_DOWNLOAD_ACCESS", default="180/hour"),
    },
}

CLERK_DOMAIN = config("CLERK_DOMAIN", default="")
CLERK_JWKS_URL = config(
    "CLERK_JWKS_URL",
    default=f"https://{CLERK_DOMAIN}/.well-known/jwks.json" if CLERK_DOMAIN else "",
)
CLERK_JWT_ISSUER = config(
    "CLERK_JWT_ISSUER",
    default=f"https://{CLERK_DOMAIN}" if CLERK_DOMAIN else "",
)
CLERK_JWT_AUDIENCE = config("CLERK_JWT_AUDIENCE", default="")
CLERK_AUTHORIZED_PARTIES = get_csv("CLERK_AUTHORIZED_PARTIES")
CLERK_BILLING_CLAIM = config("CLERK_BILLING_CLAIM", default="entitlements")
CLERK_SECRET_KEY = config("CLERK_SECRET_KEY", default="")
CLERK_WEBHOOK_SIGNING_SECRET = config("CLERK_WEBHOOK_SIGNING_SECRET", default="")

SUPABASE_URL = config("SUPABASE_URL", default="")
SUPABASE_ANON_KEY = config("SUPABASE_ANON_KEY", default="")
SUPABASE_SERVICE_ROLE_KEY = config("SUPABASE_SERVICE_ROLE_KEY", default="")
ASSET_STORAGE_BACKEND = config("ASSET_STORAGE_BACKEND", default="supabase").strip().lower()
ASSET_STORAGE_BUCKET = config("ASSET_STORAGE_BUCKET", default="")
ASSET_STORAGE_SIGNED_URL_TTL_SECONDS = config(
    "ASSET_STORAGE_SIGNED_URL_TTL_SECONDS",
    cast=int,
    default=600,
)

# S3 compatible storage (Cloudflare R2, MinIO, DigitalOcean Spaces, etc).
ASSET_STORAGE_S3_ENDPOINT_URL = config("ASSET_STORAGE_S3_ENDPOINT_URL", default="")
ASSET_STORAGE_S3_REGION = config("ASSET_STORAGE_S3_REGION", default="us-east-1")
ASSET_STORAGE_S3_ACCESS_KEY_ID = config("ASSET_STORAGE_S3_ACCESS_KEY_ID", default="")
ASSET_STORAGE_S3_SECRET_ACCESS_KEY = config("ASSET_STORAGE_S3_SECRET_ACCESS_KEY", default="")

# Frontend links used in transactional emails.
FRONTEND_APP_URL = config("FRONTEND_APP_URL", default="http://127.0.0.1:5173").strip()

# Resend transactional email settings.
RESEND_API_KEY = config("RESEND_API_KEY", default="")
RESEND_FROM_EMAIL = config("RESEND_FROM_EMAIL", default="")
RESEND_REPLY_TO_EMAIL = config("RESEND_REPLY_TO_EMAIL", default="")
RESEND_TIMEOUT_SECONDS = config("RESEND_TIMEOUT_SECONDS", cast=int, default=10)

# AI integration placeholders (optional).
OPENROUTER_API_KEY = config("OPENROUTER_API_KEY", default="")
OPENROUTER_BASE_URL = config("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
OPENROUTER_DEFAULT_MODEL = config("OPENROUTER_DEFAULT_MODEL", default="")
OLLAMA_BASE_URL = config("OLLAMA_BASE_URL", default="http://127.0.0.1:11434")
OLLAMA_MODEL = config("OLLAMA_MODEL", default="")

# Order confirmation controls.
# Keep client-side payment confirmation disabled by default; rely on verified webhooks.
ORDER_CONFIRM_ALLOW_MANUAL = config("ORDER_CONFIRM_ALLOW_MANUAL", cast=bool, default=False)
ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM = config(
    "ORDER_CONFIRM_ALLOW_CLIENT_SIDE_CLERK_CONFIRM",
    cast=bool,
    default=False,
)
ORDER_CONFIRM_SHARED_SECRET = config("ORDER_CONFIRM_SHARED_SECRET", default="")

# Production security defaults.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = config(
    "DJANGO_SECURE_HSTS_SECONDS",
    cast=int,
    default=0 if DEBUG else 31536000,
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    cast=bool,
    default=not DEBUG,
)
SECURE_HSTS_PRELOAD = config(
    "DJANGO_SECURE_HSTS_PRELOAD",
    cast=bool,
    default=not DEBUG,
)
SECURE_SSL_REDIRECT = config(
    "DJANGO_SECURE_SSL_REDIRECT",
    cast=bool,
    default=not DEBUG,
)
SESSION_COOKIE_SECURE = config(
    "DJANGO_SESSION_COOKIE_SECURE",
    cast=bool,
    default=not DEBUG,
)
CSRF_COOKIE_SECURE = config(
    "DJANGO_CSRF_COOKIE_SECURE",
    cast=bool,
    default=not DEBUG,
)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = config(
    "DJANGO_SECURE_REFERRER_POLICY",
    default="strict-origin-when-cross-origin",
)
X_FRAME_OPTIONS = config("DJANGO_X_FRAME_OPTIONS", default="DENY")

# Logging defaults prioritize clear operational visibility without exposing secrets.
DJANGO_LOG_LEVEL = config("DJANGO_LOG_LEVEL", default="DEBUG" if DEBUG else "INFO").upper()
API_LOG_LEVEL = config("API_LOG_LEVEL", default=DJANGO_LOG_LEVEL).upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": DJANGO_LOG_LEVEL,
    },
    "loggers": {
        "api": {
            "handlers": ["console"],
            "level": API_LOG_LEVEL,
            "propagate": False,
        },
    },
}
