import os
import unittest
from unittest.mock import patch, MagicMock
from pyramid import testing
from pyramid.httpexceptions import HTTPFound

from namifax.db.engine import DatabaseEngine
from namifax.db.schema import init_database_tables
from namifax.services.user_account import AFUserAccount, md5_hash
from namifax.services.faxqueue import FaxQueue
from namifax.views.auth import login_post_view
from namifax.views.admin import get_all_syslogs


class TestSecurityAuditPhase1(unittest.TestCase):
    """Test suite covering Phase 1 security audit fixes (AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-18)."""

    def setUp(self):
        self.config = testing.setUp()
        self.db = DatabaseEngine()
        self.db.connect_sqlite(":memory:")
        init_database_tables(self.db)

    def tearDown(self):
        testing.tearDown()
        self.db.disconnect()

    # =========================================================================
    # AUDIT-01: Admin Authentication Backdoor Removal
    # =========================================================================
    def test_admin_login_rejects_backdoor_password_when_password_changed(self):
        """Verify that admin login fails with initial 'password' once password has changed."""
        # 1. Update admin password to 'NewSecret123!'
        new_pwd_hash = md5_hash("NewSecret123!")
        self.db.query(f"UPDATE UserAccount SET password = '{new_pwd_hash}' WHERE username = 'admin'")

        # 2. Attempt login with old default password 'password'
        req_old = testing.DummyRequest(post={"username": "admin", "password": "password"})
        req_old.method = "POST"
        req_old.db = self.db

        with patch("namifax.views.auth.AFUserAccount", return_value=AFUserAccount(db=self.db)):
            res_old = login_post_view(req_old)

        # Must reject login (render error dict instead of redirect)
        self.assertIsInstance(res_old, dict)
        self.assertEqual(res_old.get("error"), "Invalid username or password")

        # 3. Attempt login with new password 'NewSecret123!'
        req_new = testing.DummyRequest(post={"username": "admin", "password": "NewSecret123!"})
        req_new.method = "POST"
        req_new.db = self.db

        with patch("namifax.views.auth.AFUserAccount", return_value=AFUserAccount(db=self.db)):
            res_new = login_post_view(req_new)

        # Must succeed and redirect to inbox
        self.assertIsInstance(res_new, HTTPFound)
        self.assertEqual(res_new.location, "/inbox")

    def test_default_seeded_admin_login_succeeds(self):
        """Verify that default admin login works via standard user_svc.login without backdoor."""
        # Ensure default seed has 'password' hash
        default_hash = md5_hash("password")
        self.db.query(f"UPDATE UserAccount SET password = '{default_hash}' WHERE username = 'admin'")

        req = testing.DummyRequest(post={"username": "admin", "password": "password"})
        req.method = "POST"
        req.db = self.db

        with patch("namifax.views.auth.AFUserAccount", return_value=AFUserAccount(db=self.db)):
            res = login_post_view(req)

        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.location, "/inbox")

    # =========================================================================
    # AUDIT-02: HylaFAX CLI Subprocess Injection Prevention
    # =========================================================================
    @patch("subprocess.run")
    def test_killjob_safe_execution_and_meta_char_safety(self, mock_run):
        """Verify killjob uses list arguments without shell=True and handles meta-chars safely."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        fq = FaxQueue(auto_process=False)
        malicious_user = "admin; rm -rf /"
        job_id = 999

        ret = fq.killjob(malicious_user, job_id)

        self.assertTrue(ret)
        self.assertEqual(mock_run.call_count, 1)

        called_args, called_kwargs = mock_run.call_args
        cmd_list = called_args[0]

        # Must be passed as a list of strings
        self.assertIsInstance(cmd_list, list)
        self.assertEqual(cmd_list, ["faxrm", "999"])

        # shell must be False or not True
        self.assertFalse(called_kwargs.get("shell", False))

        # FAXUSER must be in environment safely
        self.assertIn("env", called_kwargs)
        self.assertEqual(called_kwargs["env"].get("FAXUSER"), malicious_user)

    @patch("subprocess.run")
    def test_killjob_returns_false_on_failure(self, mock_run):
        """Verify killjob returns False when subprocess exits non-zero."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_run.return_value = mock_proc

        fq = FaxQueue(auto_process=False)
        ret = fq.killjob("admin", 123)
        self.assertFalse(ret)

    @patch("subprocess.run")
    def test_faxalter_safe_execution_and_meta_char_safety(self, mock_run):
        """Verify faxalter parses operations as list args without shell=True."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        fq = FaxQueue(auto_process=False)
        ops = {
            "sendtime": '12:00"; rm -rf /',
            "destination": "01012345678",
            "priority": "normal",
        }

        ret = fq.faxalter("admin", 101, ops)

        self.assertTrue(ret)
        self.assertEqual(mock_run.call_count, 1)

        called_args, called_kwargs = mock_run.call_args
        cmd_list = called_args[0]

        # Must be a list of args
        self.assertIsInstance(cmd_list, list)
        self.assertEqual(cmd_list[0], "faxalter")
        self.assertIn("-a", cmd_list)
        self.assertIn('12:00"; rm -rf /', cmd_list)
        self.assertIn("-d", cmd_list)
        self.assertIn("01012345678", cmd_list)
        self.assertIn("-P", cmd_list)
        self.assertIn("normal", cmd_list)
        self.assertEqual(cmd_list[-1], "101")

        # shell must not be True
        self.assertFalse(called_kwargs.get("shell", False))

    @patch("subprocess.run")
    def test_faxalter_returns_false_on_failure(self, mock_run):
        """Verify faxalter returns False when subprocess fails."""
        mock_proc = MagicMock()
        mock_proc.returncode = 2
        mock_run.return_value = mock_proc

        fq = FaxQueue(auto_process=False)
        ret = fq.faxalter("admin", 101, {"priority": "high"})
        self.assertFalse(ret)

    # =========================================================================
    # AUDIT-03: System Logs SQL Injection Prevention
    # =========================================================================
    def test_get_all_syslogs_handles_sql_injection_payload(self):
        """Verify get_all_syslogs escapes quotes and avoids SQL syntax errors or injections."""
        # Insert known log
        self.db.query("INSERT INTO SysLog (logdate, logtext) VALUES ('2026-10-01 10:00:00', 'Legitimate security test log')")

        # Attack payload in kw
        malicious_kw = "' OR '1'='1"
        rows = get_all_syslogs(kw=malicious_kw, db=self.db)
        # Should safely search for the literal string and return 0 results
        self.assertEqual(len(rows), 0)

        # Legitimate search should find the record
        legit_rows = get_all_syslogs(kw="security test", db=self.db)
        self.assertEqual(len(legit_rows), 1)
        self.assertEqual(legit_rows[0]["logtext"], "Legitimate security test log")

        # Attack payload in date parts
        malicious_day = "01' OR '1'='1"
        date_rows = get_all_syslogs(day=malicious_day, month="10", year="2026", db=self.db)
        self.assertEqual(len(date_rows), 0)

    # =========================================================================
    # AUDIT-18: Package Import Path Verification
    # =========================================================================
    def test_audit_18_imports_namifax_db_engine(self):
        """Verify that all AUDIT-18 affected modules import from namifax.db.engine."""
        import ast

        files_to_check = [
            "src/namifax/services/ocr.py",
            "src/namifax/services/storage_lifecycle.py",
            "src/namifax/services/cover_studio.py",
            "src/namifax/services/printer.py",
            "src/namifax/views/admin.py",
        ]

        for rel_path in files_to_check:
            abs_path = os.path.abspath(rel_path)
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertNotIn(
                "from avantfax.db.engine import DatabaseEngine",
                content,
                f"File {rel_path} still imports DatabaseEngine from avantfax.db.engine!",
            )

        # Dynamic import test
        from namifax.services.ocr import DatabaseEngine as OcrEngine
        from namifax.services.storage_lifecycle import DatabaseEngine as StorageEngine
        from namifax.services.cover_studio import DatabaseEngine as CoverEngine
        from namifax.services.printer import DatabaseEngine as PrinterEngine
        from namifax.db.engine import DatabaseEngine as MainEngine

        self.assertIs(OcrEngine, MainEngine)
        self.assertIs(StorageEngine, MainEngine)
        self.assertIs(CoverEngine, MainEngine)
        self.assertIs(PrinterEngine, MainEngine)


if __name__ == "__main__":
    unittest.main()
