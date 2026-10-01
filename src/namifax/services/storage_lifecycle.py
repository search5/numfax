import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from namifax.db.engine import DatabaseEngine


@dataclass
class StorageLifecyclePolicy:
    purge_tiff_after_days: int = 7        # Purge local TIFF if valid PDF exists after N days (0 = immediate)
    full_retention_days: int = 365        # Purge entire fax record & files after N days (0 = keep forever)
    remote_sync_delete: bool = True        # Also purge object on remote S3/GCS when fax is deleted
    delete_remote_tiff_only: bool = False  # Purge only TIFF objects in remote cloud storage


class StorageLifecycleService:
    """Enterprise Storage Lifecycle Engine for NamiFAX."""

    def __init__(
        self,
        db: Optional[DatabaseEngine] = None,
        storage_provider: Optional[Any] = None,
        archive_dir: Optional[str] = None,
    ) -> None:
        self.db = db or DatabaseEngine()
        self.storage_provider = storage_provider
        self.archive_dir = archive_dir or os.environ.get(
            "NAMIFAX_ARCHIVE_DIR", "/var/spool/hylafax/archive"
        )

    def purge_local_tiffs(self, days_old: int = 7) -> Dict[str, Any]:
        """Purge raw TIFF files where a valid, non-empty PDF counterpart exists."""
        if not os.path.exists(self.archive_dir):
            return {"purged_count": 0, "reclaimed_bytes": 0}

        cutoff_timestamp = time.time() - (days_old * 86400)
        purged_count = 0
        reclaimed_bytes = 0

        for root, _, files in os.walk(self.archive_dir):
            if "fax.tif" in files:
                tif_path = os.path.join(root, "fax.tif")
                pdf_path = os.path.join(root, "fax.pdf")

                # Safeguard 1: PDF must exist and be non-empty (> 0 bytes)
                if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
                    continue

                # Safeguard 2: Check modification time
                try:
                    stat = os.stat(tif_path)
                    if stat.st_mtime <= cutoff_timestamp:
                        file_size = stat.st_size
                        os.remove(tif_path)
                        purged_count += 1
                        reclaimed_bytes += file_size
                except OSError:
                    continue

        return {
            "purged_count": purged_count,
            "reclaimed_bytes": reclaimed_bytes,
        }

    def purge_expired_faxes(self, retention_days: int) -> Dict[str, Any]:
        """Purge fax database entries, local directories, and sync with remote cloud storage."""
        if retention_days <= 0:
            return {"purged_faxes_count": 0}

        cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        res = self.db.query(
            f"SELECT fid, lastmod FROM FaxArchive WHERE lastmod < {self.db.quote(cutoff_date)}"
        )
        records = self.db.get_records() if res.executed else []
        purged_faxes_count = 0

        for row in records:
            fid = row.get("fid")
            if not fid:
                continue

            # 1. Locate and remove local directory if exists
            # Search within archive_dir for directory ending with fax{fid}
            found_dir = None
            for root, dirs, _ in os.walk(self.archive_dir):
                for d in dirs:
                    if d == f"fax{fid}":
                        found_dir = os.path.join(root, d)
                        break
                if found_dir:
                    break

            if found_dir and os.path.exists(found_dir):
                try:
                    shutil.rmtree(found_dir, ignore_errors=True)
                except OSError:
                    pass

            # 2. Remote storage notification
            if self.storage_provider and hasattr(self.storage_provider, "delete_fax"):
                try:
                    self.storage_provider.delete_fax(fid)
                except Exception:
                    pass

            # 3. Remove DB record
            self.db.query(f"DELETE FROM FaxArchive WHERE fid = {fid}")
            purged_faxes_count += 1

        return {"purged_faxes_count": purged_faxes_count}

    def run_lifecycle(self, policy: StorageLifecyclePolicy) -> Dict[str, Any]:
        """Execute complete storage lifecycle sequence based on active policy."""
        tiff_res = self.purge_local_tiffs(days_old=policy.purge_tiff_after_days)
        fax_res = self.purge_expired_faxes(retention_days=policy.full_retention_days)

        return {
            "tiffs_purged": tiff_res["purged_count"],
            "reclaimed_bytes": tiff_res["reclaimed_bytes"],
            "faxes_purged": fax_res["purged_faxes_count"],
            "executed_at": datetime.now().isoformat(),
        }
