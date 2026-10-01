import os
import shutil
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from namifax.db.engine import DatabaseEngine
from src.namifax.db.schema import init_database_tables
from src.namifax.services.storage_lifecycle import (
    StorageLifecyclePolicy,
    StorageLifecycleService,
)


class TestStorageLifecycleService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.archive_dir = os.path.join(self.temp_dir, "archive")
        os.makedirs(self.archive_dir, exist_ok=True)

        self.db = DatabaseEngine()
        self.db.connect_sqlite(":memory:")
        init_database_tables(self.db)

        self.mock_remote = MagicMock()
        self.service = StorageLifecycleService(
            db=self.db,
            storage_provider=self.mock_remote,
            archive_dir=self.archive_dir,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_purge_local_tiffs_when_valid_pdf_exists(self):
        # Create a sample fax directory with old tif and valid pdf
        fax_dir = os.path.join(self.archive_dir, "2026", "09", "20", "fax100")
        os.makedirs(fax_dir, exist_ok=True)
        tif_path = os.path.join(fax_dir, "fax.tif")
        pdf_path = os.path.join(fax_dir, "fax.pdf")

        with open(tif_path, "wb") as f:
            f.write(b"TIFF_DATA_12345")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\nsome content\n%%EOF")

        # Set modification time to 10 days ago
        old_mtime = time.time() - (10 * 86400)
        os.utime(tif_path, (old_mtime, old_mtime))

        res = self.service.purge_local_tiffs(days_old=7)
        self.assertEqual(res["purged_count"], 1)
        self.assertFalse(os.path.exists(tif_path))
        self.assertTrue(os.path.exists(pdf_path))

    def test_purge_local_tiffs_safeguard_if_no_pdf(self):
        # Create a sample fax directory with tif but NO pdf
        fax_dir = os.path.join(self.archive_dir, "2026", "09", "20", "fax101")
        os.makedirs(fax_dir, exist_ok=True)
        tif_path = os.path.join(fax_dir, "fax.tif")

        with open(tif_path, "wb") as f:
            f.write(b"TIFF_DATA_SAFEGUARD")

        old_mtime = time.time() - (10 * 86400)
        os.utime(tif_path, (old_mtime, old_mtime))

        res = self.service.purge_local_tiffs(days_old=7)
        self.assertEqual(res["purged_count"], 0)
        self.assertTrue(os.path.exists(tif_path), "TIFF must be preserved if PDF is missing")

    def test_purge_local_tiffs_safeguard_if_pdf_empty(self):
        # Create a sample fax directory with tif and 0-byte pdf
        fax_dir = os.path.join(self.archive_dir, "2026", "09", "20", "fax102")
        os.makedirs(fax_dir, exist_ok=True)
        tif_path = os.path.join(fax_dir, "fax.tif")
        pdf_path = os.path.join(fax_dir, "fax.pdf")

        with open(tif_path, "wb") as f:
            f.write(b"TIFF_DATA_SAFEGUARD")
        with open(pdf_path, "wb") as f:
            pass  # 0 bytes

        old_mtime = time.time() - (10 * 86400)
        os.utime(tif_path, (old_mtime, old_mtime))

        res = self.service.purge_local_tiffs(days_old=7)
        self.assertEqual(res["purged_count"], 0)
        self.assertTrue(os.path.exists(tif_path), "TIFF must be preserved if PDF is empty")

    def test_purge_local_tiffs_not_yet_expired(self):
        # Create a sample fax directory modified 2 days ago
        fax_dir = os.path.join(self.archive_dir, "2026", "09", "28", "fax103")
        os.makedirs(fax_dir, exist_ok=True)
        tif_path = os.path.join(fax_dir, "fax.tif")
        pdf_path = os.path.join(fax_dir, "fax.pdf")

        with open(tif_path, "wb") as f:
            f.write(b"TIFF_RECENT")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\ncontent")

        recent_mtime = time.time() - (2 * 86400)
        os.utime(tif_path, (recent_mtime, recent_mtime))

        res = self.service.purge_local_tiffs(days_old=7)
        self.assertEqual(res["purged_count"], 0)
        self.assertTrue(os.path.exists(tif_path))

    def test_purge_expired_faxes(self):
        # Insert expired fax record in DB
        old_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d %H:%M:%S")
        self.db.query(
            f"INSERT INTO FaxArchive (lastmod, pages) "
            f"VALUES ('{old_date}', 2)"
        )
        fid = self.db.get_insert_id()

        fax_dir = os.path.join(self.archive_dir, "2025", "08", "01", f"fax{fid}")
        os.makedirs(fax_dir, exist_ok=True)
        pdf_path = os.path.join(fax_dir, "fax.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\ncontent")

        res = self.service.purge_expired_faxes(retention_days=365)
        self.assertEqual(res["purged_faxes_count"], 1)

        # Verify DB record is deleted
        self.db.query(f"SELECT fid FROM FaxArchive WHERE fid = {fid}")
        self.assertEqual(len(self.db.get_records()), 0)

        # Verify local dir is deleted
        self.assertFalse(os.path.exists(fax_dir))

        # Verify remote provider was notified to purge
        self.mock_remote.delete_fax.assert_called_once_with(fid)

    def test_run_lifecycle_full(self):
        policy = StorageLifecyclePolicy(
            purge_tiff_after_days=7,
            full_retention_days=365,
            remote_sync_delete=True,
        )
        summary = self.service.run_lifecycle(policy)
        self.assertIn("tiffs_purged", summary)
        self.assertIn("faxes_purged", summary)
        self.assertIn("reclaimed_bytes", summary)


if __name__ == "__main__":
    unittest.main()
