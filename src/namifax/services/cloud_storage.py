import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class StorageConfig:
    storage_type: str = "LOCAL"  # LOCAL, S3, GCS
    endpoint_url: Optional[str] = None
    region_name: Optional[str] = None
    bucket_name: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    prefix: str = ""


class StorageProvider(ABC):
    """Abstract Base Class defining enterprise multi-cloud storage operations."""

    @abstractmethod
    def upload_file(self, local_path: str, remote_key: str) -> bool:
        pass

    @abstractmethod
    def download_file(self, remote_key: str, target_path: str) -> bool:
        pass

    @abstractmethod
    def delete_file(self, remote_key: str) -> bool:
        pass

    @abstractmethod
    def delete_fax(self, fid: Any) -> bool:
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        pass


class LocalStorageProvider(StorageProvider):
    """Default on-premise local filesystem storage provider."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = base_dir or os.environ.get("NAMIFAX_ARCHIVE_DIR", "/var/spool/hylafax/archive")
        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except OSError:
            pass

    def _full_path(self, key: str) -> str:
        clean_key = key.lstrip("/")
        return os.path.join(self.base_dir, clean_key)

    def upload_file(self, local_path: str, remote_key: str) -> bool:
        if not os.path.exists(local_path):
            return False
        dest_path = self._full_path(remote_key)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        try:
            shutil.copy2(local_path, dest_path)
            return True
        except OSError:
            return False

    def download_file(self, remote_key: str, target_path: str) -> bool:
        src_path = self._full_path(remote_key)
        if not os.path.exists(src_path):
            return False
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        try:
            shutil.copy2(src_path, target_path)
            return True
        except OSError:
            return False

    def delete_file(self, remote_key: str) -> bool:
        target = self._full_path(remote_key)
        if os.path.exists(target):
            try:
                os.remove(target)
                return True
            except OSError:
                return False
        return True

    def delete_fax(self, fid: Any) -> bool:
        target_name = f"fax{fid}"
        for root, dirs, _ in os.walk(self.base_dir):
            if target_name in dirs:
                full_dir = os.path.join(root, target_name)
                try:
                    shutil.rmtree(full_dir, ignore_errors=True)
                    return True
                except OSError:
                    return False
        return True

    def test_connection(self) -> Dict[str, Any]:
        try:
            can_write = os.access(self.base_dir, os.W_OK)
            return {
                "success": can_write,
                "provider": "LOCAL",
                "message": f"Local storage accessible at {self.base_dir}",
            }
        except Exception as exc:
            return {
                "success": False,
                "provider": "LOCAL",
                "message": f"Local storage access error: {exc}",
            }


class S3CompatibleStorageProvider(StorageProvider):
    """High-performance S3 & S3-compatible (MinIO, GCS, Cloudflare R2) storage provider."""

    def __init__(self, config: StorageConfig) -> None:
        self.config = config
        self._client = None

    def _get_client(self) -> Any:
        if self._client is None:
            import boto3
            kwargs: Dict[str, Any] = {}
            if self.config.endpoint_url:
                kwargs["endpoint_url"] = self.config.endpoint_url
            if self.config.region_name:
                kwargs["region_name"] = self.config.region_name
            if self.config.access_key and self.config.secret_key:
                kwargs["aws_access_key_id"] = self.config.access_key
                kwargs["aws_secret_access_key"] = self.config.secret_key

            self._client = boto3.client("s3", **kwargs)
        return self._client

    def _resolve_key(self, remote_key: str) -> str:
        prefix = self.config.prefix or ""
        clean_key = remote_key.lstrip("/")
        if prefix:
            if not prefix.endswith("/"):
                prefix += "/"
            return f"{prefix}{clean_key}"
        return clean_key

    def upload_file(self, local_path: str, remote_key: str) -> bool:
        if not os.path.exists(local_path):
            return False
        key = self._resolve_key(remote_key)
        bucket = self.config.bucket_name or ""
        try:
            client = self._get_client()
            client.upload_file(local_path, bucket, key)
            return True
        except Exception:
            return False

    def download_file(self, remote_key: str, target_path: str) -> bool:
        key = self._resolve_key(remote_key)
        bucket = self.config.bucket_name or ""
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        try:
            client = self._get_client()
            client.download_file(bucket, key, target_path)
            return True
        except Exception:
            return False

    def delete_file(self, remote_key: str) -> bool:
        key = self._resolve_key(remote_key)
        bucket = self.config.bucket_name or ""
        try:
            client = self._get_client()
            client.delete_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False

    def delete_fax(self, fid: Any) -> bool:
        fax_prefix = self._resolve_key(f"fax{fid}/")
        bucket = self.config.bucket_name or ""
        try:
            client = self._get_client()
            res = client.list_objects_v2(Bucket=bucket, Prefix=fax_prefix)
            contents = res.get("Contents", [])
            if not contents:
                # Also check parent directory style
                parent_prefix = self._resolve_key(f"fax{fid}")
                res2 = client.list_objects_v2(Bucket=bucket, Prefix=parent_prefix)
                contents = res2.get("Contents", [])

            if contents:
                delete_keys = [{"Key": obj["Key"]} for obj in contents]
                client.delete_objects(Bucket=bucket, Delete={"Objects": delete_keys})
            return True
        except Exception:
            return False

    def test_connection(self) -> Dict[str, Any]:
        bucket = self.config.bucket_name or ""
        try:
            client = self._get_client()
            client.head_bucket(Bucket=bucket)
            return {
                "success": True,
                "provider": "S3",
                "message": f"Successfully connected to S3 bucket '{bucket}'.",
            }
        except Exception as exc:
            return {
                "success": False,
                "provider": "S3",
                "message": f"Failed to access S3 bucket '{bucket}': {exc}",
            }


class CloudStorageManager:
    """Factory manager for active cloud storage providers."""

    @staticmethod
    def get_provider(config: StorageConfig) -> StorageProvider:
        stype = (config.storage_type or "LOCAL").upper()
        if stype in ("S3", "GCS"):
            return S3CompatibleStorageProvider(config)
        return LocalStorageProvider()
