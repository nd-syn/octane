"""Backup the SQLite database to S3-compatible storage.

Usage:
    python scripts/backup_db.py

Uses environment variables:
    BACKUP_S3_URL (e.g. s3://bucket-name/path)
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_ENDPOINT_URL (optional, for B2 / MinIO)
    AWS_REGION (optional)
"""
from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime, timezone

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    s3_url = settings.backup_s3_url

    if not s3_url:
        print("BACKUP_S3_URL not set, skipping backup")
        return

    try:
        import boto3
    except ImportError:
        print("boto3 not installed. Install with: pip install boto3")
        return

    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_key = f"backups/messaging_{timestamp}.db"

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        shutil.copy2(db_path, tmp.name)
        tmp_path = tmp.name

    try:
        session = boto3.session.Session()
        client = session.client(
            "s3",
            endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )

        bucket = s3_url.split("/")[2] if "://" in s3_url else s3_url.split("/")[0]
        if bucket.startswith("s3://"):
            bucket = bucket[5:]

        client.upload_file(tmp_path, bucket, backup_key)
        print(f"Backup uploaded to s3://{bucket}/{backup_key}")
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    main()
