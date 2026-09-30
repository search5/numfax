import unittest
from unittest.mock import patch, MagicMock
from pyramid import testing
from pyramid.httpexceptions import HTTPForbidden, HTTPFound
from avantfax.db.engine import DatabaseEngine
from src.namifax.db.schema import init_database_tables
from src.namifax.views.admin import admin_smtp_view


class TestAdminSmtpView(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        self.db = DatabaseEngine()
        self.db.connect_sqlite(":memory:")
        init_database_tables(self.db)

    def tearDown(self):
        testing.tearDown()

    def test_permission_denied_for_non_admin(self):
        req = testing.DummyRequest()
        req.session["user_id"] = 2
        req.session["is_admin"] = False
        req.session["is_superadmin"] = False
        req.db = self.db

        with self.assertRaises(HTTPForbidden):
            admin_smtp_view(req)

    def test_get_smtp_view_for_superadmin(self):
        req = testing.DummyRequest()
        req.session["user_id"] = 1
        req.session["is_admin"] = True
        req.session["is_superadmin"] = True
        req.db = self.db
        req.method = "GET"

        res = admin_smtp_view(req)
        self.assertIn("config", res)
        self.assertEqual(res["config"].smtp_host, "localhost")
        self.assertEqual(res["config"].smtp_port, 25)

    def test_post_save_smtp_settings(self):
        req = testing.DummyRequest(post={
            "action": "save",
            "smtp_host": "smtp.office365.com",
            "smtp_port": "587",
            "smtp_security": "STARTTLS",
            "smtp_auth": "on",
            "smtp_username": "notify@company.com",
            "smtp_password": "supersecretpassword",
            "from_email": "notify@company.com",
            "from_name": "NamiFAX Alert",
            "email_sig_text": "Signature text",
        })
        req.session["user_id"] = 1
        req.session["is_superadmin"] = True
        req.db = self.db
        req.method = "POST"

        res = admin_smtp_view(req)
        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.location, "/admin/smtp")

    @patch("namifax.services.smtp_settings.SmtpSettingsService.test_connection")
    def test_post_test_smtp_connection(self, mock_test):
        mock_test.return_value = MagicMock(success=True, message="SMTP Handshake OK", details=["Log 1"])

        req = testing.DummyRequest(post={
            "action": "test",
            "test_email": "test@domain.com",
            "smtp_host": "smtp.office365.com",
            "smtp_port": "587",
            "smtp_security": "STARTTLS",
            "smtp_auth": "on",
            "smtp_username": "notify@company.com",
            "smtp_password": "supersecretpassword",
            "from_email": "notify@company.com",
        })
        req.session["user_id"] = 1
        req.session["is_superadmin"] = True
        req.db = self.db
        req.method = "POST"

        res = admin_smtp_view(req)
        self.assertIn("test_result", res)
        self.assertTrue(res["test_result"]["success"])
        self.assertIn("SMTP Handshake OK", res["test_result"]["message"])


if __name__ == "__main__":
    unittest.main()
