from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent


def get_csv(name: str, default: str = "") -> list[str]:
    return [item for item in config(name, cast=Csv(), default=default) if item]


SECRET_KEY = config("DJANGO_SECRET_KEY", default="change-me-before-production")
DEBUG = config("DJANGO_DEBUG", cast=bool, default=True)
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
    "DEFAULT_AUTHENTICATION_CLASSES": ("api.authentication.ClerkJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
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
DIGITAL_ASSET_BASE_URL = config("DIGITAL_ASSET_BASE_URL", default="")
