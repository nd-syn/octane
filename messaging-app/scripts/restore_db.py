"""Restore the SQLite database from an S3 backup.

Usage:
    python scripts/restore_db.py <backup_key>

Example:
    python scripts/restore_db.py backups/messaging_20260704_120000.db

Uses environment variables:
    BACKUP_S3_URL (e.g. s3://bucket-name)
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_ENDPOINT_URL (optional, for B2 / MinIO)
    AWS_REGION (optional)
"""
from __future__ import annotations

import os
import sys
import tempfile

from app.config import get_settings


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/restore_db.py <backup_key>")
        sys.exit(1)

    backup_key = sys.argv[1]
    settings = get_settings()
    s3_url = settings.backup_s3_url

    if not s3_url:
        print("BACKUP_S3_URL not set")
        sys.exit(1)

    try:
        import boto3
    except ImportError:
        print("boto3 not installed. Install with: pip install boto3")
        sys.exit(1)

    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")

    session = boto3.session.Session()
    client = session.client(
        "s3",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )

    bucket = s3_url.split("/")[2] if "://" in s3_url else s3_url.split("/")[0]
    if bucket.startswith("s3://"):
        bucket = bucket[5:]

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        client.download_file(bucket, backup_key, tmp.name)
        tmp_path = tmp.name

    import shutil
    shutil.copy2(tmp_path, db_path)
    os.unlink(tmp_path)
    print(f"Restored {backup_key} to {db_path}")


if __name__ == "__main__":
    main()
