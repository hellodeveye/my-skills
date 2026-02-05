"""
R2 Upload Library - Python module for integration into other skills.
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import mimetypes
import os
import urllib.error
import urllib.request
import uuid
from typing import Dict, Iterable, Optional, Tuple
from urllib.parse import quote, urlparse

DEFAULT_TIMEOUT = 60
MAX_PRESIGN_EXPIRES = 604800  # 7 days
REQUIRED_BUCKET_FIELDS = ("endpoint", "access_key_id", "secret_access_key", "bucket_name")
DEFAULT_USER_AGENT = "r2-upload/2.1"
DEFAULT_DATE_FORMAT = "%Y/%m/%d"


class R2UploadError(RuntimeError):
    """Raised when upload or configuration fails."""


def load_config(config_path: Optional[str] = None) -> dict:
    """Load R2/S3 configuration from YAML file."""
    try:
        import yaml
    except ImportError as exc:
        raise R2UploadError("PyYAML is required. Install with: python3 -m pip install pyyaml") from exc

    path = config_path or os.environ.get("R2_UPLOAD_CONFIG") or os.path.expanduser("~/.r2-upload.yml")
    path = os.path.expanduser(path)

    if not os.path.exists(path):
        raise R2UploadError(f"Config file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise R2UploadError(f"Invalid YAML in config: {path}") from exc

    if not isinstance(config, dict):
        raise R2UploadError("Config must be a YAML mapping with a 'buckets' key")

    buckets = config.get("buckets")
    if not isinstance(buckets, dict) or not buckets:
        raise R2UploadError("Config missing 'buckets' mapping")

    return config


def resolve_bucket_config(config: dict, bucket: Optional[str] = None) -> Tuple[str, dict]:
    """Return (bucket_name, bucket_config) after validating required fields."""
    bucket_name = bucket or config.get("default")
    if not bucket_name:
        raise R2UploadError("No bucket specified and no 'default' bucket in config")

    buckets = config.get("buckets", {})
    bucket_config = buckets.get(bucket_name)
    if not bucket_config:
        available = ", ".join(sorted(buckets.keys()))
        raise R2UploadError(f"Bucket '{bucket_name}' not found. Available: {available}")

    missing = [field for field in REQUIRED_BUCKET_FIELDS if not bucket_config.get(field)]
    if missing:
        raise R2UploadError(
            f"Bucket '{bucket_name}' missing required fields: {', '.join(missing)}"
        )

    return bucket_name, bucket_config


def _normalize_endpoint(endpoint: str) -> Tuple[str, str]:
    endpoint = endpoint.strip().rstrip("/")
    if not endpoint.startswith("http://") and not endpoint.startswith("https://"):
        endpoint = f"https://{endpoint}"

    parsed = urlparse(endpoint)
    if not parsed.netloc:
        raise R2UploadError(f"Invalid endpoint: {endpoint}")
    if parsed.path not in ("", "/"):
        raise R2UploadError("Endpoint should not include a path. Use bucket_name/public_url instead.")

    return f"{parsed.scheme}://{parsed.netloc}", parsed.netloc


def _normalize_key(key: str) -> str:
    key = key.replace("\\", "/").lstrip("/")
    return key


def _join_url(base: str, key: str) -> str:
    base = base.rstrip("/")
    key = _normalize_key(key)
    return f"{base}/{key}"


def _guess_content_type(name: str, override: Optional[str] = None) -> str:
    if override:
        return override

    mime, _ = mimetypes.guess_type(name)
    if mime:
        return mime

    ext = os.path.splitext(name)[1].lower()
    fallback = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".yml": "text/yaml",
        ".yaml": "text/yaml",
        ".json": "application/json",
        ".txt": "text/plain",
    }
    return fallback.get(ext, "application/octet-stream")


def _aws_encode_uri(value: str) -> str:
    return quote(value, safe="/~")


def _aws_encode_query_param(value: str) -> str:
    return quote(str(value), safe="-_.~")


def _normalize_header_value(value: str) -> str:
    return " ".join(str(value).strip().split())


def sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_signature_key(secret: str, date_stamp: str, region: str, service: str) -> bytes:
    k_date = sign(("AWS4" + secret).encode("utf-8"), date_stamp)
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, "aws4_request")
    return k_signing


def _validate_expires(expires: int) -> int:
    try:
        expires = int(expires)
    except (TypeError, ValueError) as exc:
        raise R2UploadError("expires must be an integer (seconds)") from exc

    if expires < 1 or expires > MAX_PRESIGN_EXPIRES:
        raise R2UploadError(
            f"expires must be between 1 and {MAX_PRESIGN_EXPIRES} seconds"
        )
    return expires


def default_key_prefix(now: Optional[datetime.datetime] = None) -> str:
    """Return default prefix (local date, YYYY/MM/DD)."""
    if now is None:
        now = datetime.datetime.now()
    return now.strftime(DEFAULT_DATE_FORMAT)


def build_public_url(key: str, bucket_config: dict) -> str:
    """Return a public URL for the object key."""
    endpoint, _ = _normalize_endpoint(bucket_config["endpoint"])
    public_base = bucket_config.get("public_url")
    if not public_base:
        public_base = f"{endpoint}/{bucket_config['bucket_name']}"
    return _join_url(public_base, key)


def generate_presigned_url(key: str, bucket_config: dict, expires: int = 300) -> str:
    """Generate a presigned GET URL for temporary access."""
    key = _normalize_key(key)
    expires = _validate_expires(expires)

    endpoint, host = _normalize_endpoint(bucket_config["endpoint"])
    access_key = bucket_config["access_key_id"]
    secret_key = bucket_config["secret_access_key"]
    bucket_name = bucket_config["bucket_name"]
    region = bucket_config.get("region", "auto")
    session_token = bucket_config.get("session_token")

    now = datetime.datetime.now(datetime.timezone.utc)
    date_stamp = now.strftime("%Y%m%d")
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")

    canonical_uri = f"/{bucket_name}/{_aws_encode_uri(key)}"
    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"

    params = {
        "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
        "X-Amz-Credential": f"{access_key}/{credential_scope}",
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(expires),
        "X-Amz-SignedHeaders": "host",
    }
    if session_token:
        params["X-Amz-Security-Token"] = session_token

    canonical_query = "&".join(
        f"{_aws_encode_query_param(k)}={_aws_encode_query_param(v)}"
        for k, v in sorted(params.items())
    )

    canonical_request = (
        f"GET\n{canonical_uri}\n{canonical_query}\n"
        f"host:{host}\n\n"
        "host\nUNSIGNED-PAYLOAD"
    )

    string_to_sign = (
        "AWS4-HMAC-SHA256\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    signing_key = get_signature_key(secret_key, date_stamp, region, "s3")
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    presigned_query = f"{canonical_query}&X-Amz-Signature={signature}"
    return f"{endpoint}/{bucket_name}/{_aws_encode_uri(key)}?{presigned_query}"


def upload_bytes(
    data: bytes,
    key: Optional[str] = None,
    bucket: Optional[str] = None,
    make_public: bool = False,
    config: Optional[dict] = None,
    *,
    config_path: Optional[str] = None,
    expires: int = 300,
    timeout: int = DEFAULT_TIMEOUT,
    content_type: Optional[str] = None,
    cache_control: Optional[str] = None,
    content_disposition: Optional[str] = None,
) -> str:
    """Upload in-memory bytes and return a URL (default key: YYYY/MM/DD/upload-<id>.bin)."""
    if config is None:
        config = load_config(config_path)

    bucket_name, bucket_config = resolve_bucket_config(config, bucket)
    if key is None:
        prefix = default_key_prefix()
        key = f"{prefix}/upload-{uuid.uuid4().hex[:8]}.bin"
    key = _normalize_key(key)

    endpoint, host = _normalize_endpoint(bucket_config["endpoint"])
    access_key = bucket_config["access_key_id"]
    secret_key = bucket_config["secret_access_key"]
    region = bucket_config.get("region", "auto")
    session_token = bucket_config.get("session_token")

    content_type = _guess_content_type(key, content_type)

    now = datetime.datetime.now(datetime.timezone.utc)
    date_stamp = now.strftime("%Y%m%d")
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")

    payload_hash = hashlib.sha256(data).hexdigest()

    headers: Dict[str, str] = {
        "host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "content-type": content_type,
    }
    if cache_control:
        headers["cache-control"] = cache_control
    if content_disposition:
        headers["content-disposition"] = content_disposition
    if session_token:
        headers["x-amz-security-token"] = session_token

    canonical_headers = "".join(
        f"{k}:{_normalize_header_value(v)}\n" for k, v in sorted(headers.items())
    )
    signed_headers = ";".join(sorted(headers.keys()))
    canonical_uri = f"/{bucket_name}/{_aws_encode_uri(key)}"

    canonical_request = (
        f"PUT\n{canonical_uri}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )

    credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
    string_to_sign = (
        "AWS4-HMAC-SHA256\n"
        f"{amz_date}\n"
        f"{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    signing_key = get_signature_key(secret_key, date_stamp, region, "s3")
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    auth_header = (
        "AWS4-HMAC-SHA256 "
        f"Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )

    url = f"{endpoint}/{bucket_name}/{_aws_encode_uri(key)}"
    req = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={**headers, "Authorization": auth_header},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status not in (200, 201, 204):
                raise R2UploadError(f"Upload failed: HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        message = f"HTTP {exc.code}: {exc.reason}"
        if body:
            message = f"{message} - {body.strip()[:500]}"
        raise R2UploadError(message) from exc
    except urllib.error.URLError as exc:
        raise R2UploadError(f"Network error: {exc.reason}") from exc

    if make_public:
        return build_public_url(key, bucket_config)

    return generate_presigned_url(key, bucket_config, expires=expires)


def upload_file(
    local_path: str,
    key: Optional[str] = None,
    bucket: Optional[str] = None,
    make_public: bool = False,
    config: Optional[dict] = None,
    *,
    config_path: Optional[str] = None,
    key_prefix: Optional[str] = None,
    expires: int = 300,
    timeout: int = DEFAULT_TIMEOUT,
    content_type: Optional[str] = None,
    cache_control: Optional[str] = None,
    content_disposition: Optional[str] = None,
) -> str:
    """
    Upload a file to R2/S3 storage.

    If key is omitted, uses YYYY/MM/DD/<filename>.

    Returns:
        URL string: public URL if make_public, otherwise presigned URL.
    """
    if key and key_prefix:
        raise R2UploadError("Provide either key or key_prefix, not both")

    if key is None:
        filename = os.path.basename(local_path)
        resolved_prefix = default_key_prefix() if key_prefix is None else key_prefix
        prefix = resolved_prefix.strip("/")
        key = f"{prefix}/{filename}" if prefix else filename

    with open(local_path, "rb") as f:
        data = f.read()

    content_type = _guess_content_type(local_path, content_type)

    return upload_bytes(
        data,
        key=key,
        bucket=bucket,
        make_public=make_public,
        config=config,
        config_path=config_path,
        expires=expires,
        timeout=timeout,
        content_type=content_type,
        cache_control=cache_control,
        content_disposition=content_disposition,
    )


def batch_upload(
    files: Iterable[str],
    key_prefix: str = "",
    bucket: Optional[str] = None,
    make_public: bool = False,
    config: Optional[dict] = None,
    *,
    config_path: Optional[str] = None,
    expires: int = 300,
    timeout: int = DEFAULT_TIMEOUT,
) -> list:
    """Upload multiple files and return a list of URLs."""
    if config is None:
        config = load_config(config_path)

    urls = []
    prefix = key_prefix.strip("/")

    for file_path in files:
        filename = os.path.basename(file_path)
        key = f"{prefix}/{filename}" if prefix else None
        url = upload_file(
            file_path,
            key=key,
            bucket=bucket,
            make_public=make_public,
            config=config,
            expires=expires,
            timeout=timeout,
        )
        urls.append(url)
    return urls


def fetch_and_upload(
    image_url: str,
    key: Optional[str] = None,
    bucket: Optional[str] = None,
    make_public: bool = False,
    config: Optional[dict] = None,
    *,
    config_path: Optional[str] = None,
    expires: int = 300,
    timeout: int = DEFAULT_TIMEOUT,
    user_agent: str = DEFAULT_USER_AGENT,
    content_type: Optional[str] = None,
) -> str:
    """
    Download a remote image and upload to R2/S3.

    Returns:
        URL string: public URL if make_public, otherwise presigned URL.
    """
    headers = {"User-Agent": user_agent}
    req = urllib.request.Request(image_url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            response_type = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        raise R2UploadError(f"HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise R2UploadError(f"Network error: {exc.reason}") from exc

    if not content_type and response_type:
        content_type = response_type.split(";")[0].strip() or None

    if not content_type:
        content_type = _guess_content_type(image_url)

    return upload_bytes(
        data,
        key=key,
        bucket=bucket,
        make_public=make_public,
        config=config,
        config_path=config_path,
        expires=expires,
        timeout=timeout,
        content_type=content_type,
    )
