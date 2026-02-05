#!/usr/bin/env python3
"""
R2 Upload Script - Command line tool for uploading files to R2/S3
Usage: python3 r2-upload.py <file> [--key path] [--bucket name] [--public]
"""

import argparse
import os
import sys

from upload import R2UploadError, upload_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Upload files to R2/S3-compatible storage and return a URL. "
            "If no key is provided, uses YYYY/MM/DD/<filename>."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 scripts/r2-upload.py ./photo.jpg --public\n"
            "  python3 scripts/r2-upload.py ./photo.jpg --key images/2026/02/05/photo.jpg --public\n"
            "  python3 scripts/r2-upload.py ./report.pdf --key reports/2026/02/05/report.pdf\n"
            "  python3 scripts/r2-upload.py ./image.png --key-prefix images/2026/02/05 --public\n"
        ),
    )

    parser.add_argument("file", help="File to upload")
    parser.add_argument("--key", help="Custom key/path for the file")
    parser.add_argument("--key-prefix", help="Prefix to prepend to the file name")
    parser.add_argument("--bucket", help="Bucket to use")
    parser.add_argument("--public", action="store_true", help="Return public URL")
    parser.add_argument("--expires", type=int, default=300, help="Presigned URL expiration (seconds)")
    parser.add_argument("--config", help="Path to config file (defaults to ~/.r2-upload.yml)")
    parser.add_argument("--content-type", help="Override content type")
    parser.add_argument("--cache-control", help="Set Cache-Control header")
    parser.add_argument("--content-disposition", help="Set Content-Disposition header")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout (seconds)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.key and args.key_prefix:
        parser.error("--key and --key-prefix are mutually exclusive")

    if not os.path.isfile(args.file):
        parser.error(f"File not found: {args.file}")

    try:
        url = upload_file(
            local_path=args.file,
            key=args.key,
            key_prefix=args.key_prefix,
            bucket=args.bucket,
            make_public=args.public,
            config_path=args.config,
            expires=args.expires,
            timeout=args.timeout,
            content_type=args.content_type,
            cache_control=args.cache_control,
            content_disposition=args.content_disposition,
        )
        print(url)
    except R2UploadError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
