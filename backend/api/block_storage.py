from __future__ import annotations

from functools import lru_cache
from urllib.parse import urljoin

from django.conf import settings

from .supabase_client import SupabaseConfigurationError, get_supabase_client


class BlockStorageError(RuntimeError):
    """Raised when generating a block-storage download URL fails."""


class BlockStorageConfigurationError(BlockStorageError):
    """Raised when block-storage settings are missing or invalid."""


def _setting(name: str, default: str = "") -> str:
    return str(getattr(settings, name, default) or "").strip()


def _ensure_https(url: str) -> str:
    if url and not url.startswith(("http://", "https://")):
        return f"https://{url}"
    return url


def _signed_url_ttl_seconds() -> int:
    raw_value = getattr(settings, "ASSET_STORAGE_SIGNED_URL_TTL_SECONDS", 600)
    try:
        ttl = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise BlockStorageConfigurationError(
            "ASSET_STORAGE_SIGNED_URL_TTL_SECONDS must be an integer."
        ) from exc

    if ttl < 60:
        raise BlockStorageConfigurationError(
            "ASSET_STORAGE_SIGNED_URL_TTL_SECONDS must be at least 60 seconds."
        )
    return ttl


def _normalize_storage_key(file_path: str) -> str:
    key = str(file_path or "").strip().lstrip("/")
    if not key:
        raise BlockStorageError("Digital asset file_path is empty.")
    return key


def _require_bucket() -> str:
    bucket = _setting("ASSET_STORAGE_BUCKET")
    if not bucket:
        raise BlockStorageConfigurationError("ASSET_STORAGE_BUCKET is required.")
    return bucket


def _resolve_supabase_signed_url(value: str) -> str:
    signed_url = str(value or "").strip()
    if not signed_url:
        raise BlockStorageError("Supabase storage did not return a signed URL.")
    if signed_url.startswith(("http://", "https://")):
        return signed_url

    supabase_url = _ensure_https(_setting("SUPABASE_URL"))
    if not supabase_url:
        raise BlockStorageConfigurationError(
            "SUPABASE_URL is required for ASSET_STORAGE_BACKEND=supabase."
        )
    return urljoin(f"{supabase_url.rstrip('/')}/", signed_url.lstrip("/"))


def _create_supabase_signed_url(bucket: str, file_path: str, ttl_seconds: int) -> str:
    try:
        client = get_supabase_client(use_service_role=True)
    except SupabaseConfigurationError as exc:
        raise BlockStorageConfigurationError(
            "Supabase storage requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
        ) from exc

    payload = client.storage.from_(bucket).create_signed_url(file_path, ttl_seconds)
    if not isinstance(payload, dict):
        raise BlockStorageError("Supabase create_signed_url returned an unexpected payload.")

    raw_url = (
        payload.get("signedURL")
        or payload.get("signedUrl")
        or payload.get("signed_url")
        or payload.get("url")
    )
    return _resolve_supabase_signed_url(str(raw_url or ""))


@lru_cache(maxsize=1)
def _cached_s3_client(
    endpoint_url: str,
    region: str,
    access_key_id: str,
    secret_access_key: str,
):
    try:
        import boto3
    except ImportError as exc:
        raise BlockStorageConfigurationError(
            "boto3 is required for ASSET_STORAGE_BACKEND=s3."
        ) from exc

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or None,
        region_name=region or "us-east-1",
        aws_access_key_id=access_key_id or None,
        aws_secret_access_key=secret_access_key or None,
    )


def _create_s3_signed_url(bucket: str, file_path: str, ttl_seconds: int) -> str:
    access_key_id = _setting("ASSET_STORAGE_S3_ACCESS_KEY_ID")
    secret_access_key = _setting("ASSET_STORAGE_S3_SECRET_ACCESS_KEY")
    if not access_key_id or not secret_access_key:
        raise BlockStorageConfigurationError(
            "S3 storage requires ASSET_STORAGE_S3_ACCESS_KEY_ID and ASSET_STORAGE_S3_SECRET_ACCESS_KEY."
        )

    endpoint_url = _ensure_https(_setting("ASSET_STORAGE_S3_ENDPOINT_URL"))
    region = _setting("ASSET_STORAGE_S3_REGION", default="us-east-1")
    client = _cached_s3_client(endpoint_url, region, access_key_id, secret_access_key)
    return client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": file_path},
        ExpiresIn=ttl_seconds,
    )


def build_digital_asset_download_url(file_path: str) -> str:
    backend = _setting("ASSET_STORAGE_BACKEND", default="supabase").lower()
    bucket = _require_bucket()
    ttl_seconds = _signed_url_ttl_seconds()
    key = _normalize_storage_key(file_path)

    if backend == "supabase":
        return _create_supabase_signed_url(bucket, key, ttl_seconds)
    if backend in {"s3", "s3-compatible", "s3_compatible"}:
        return _create_s3_signed_url(bucket, key, ttl_seconds)

    raise BlockStorageConfigurationError(
        "ASSET_STORAGE_BACKEND must be either 'supabase' or 's3'."
    )
