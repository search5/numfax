#!/usr/bin/env python3
"""Unit tests for avantfax.web.views.auth module."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from avantfax.web.session import SessionManager
from avantfax.web.views.auth import AuthHandler


class TestWebAuth(unittest.TestCase):
    """Test suite for WebAuth session and authentication handlers."""

    def setUp(self):
        self.session_mgr = SessionManager()
        self.handler = AuthHandler(session_manager=self.session_mgr)

    def test_session_lifecycle(self):
        sess = self.session_mgr.create_session(user_id=1, username="admin", is_admin=True)
        self.assertIsNotNone(sess.token)
        self.assertEqual(sess.username, "admin")

        retrieved = self.session_mgr.get_session(sess.token)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.user_id, 1)

        self.assertTrue(self.session_mgr.destroy_session(sess.token))
        self.assertIsNone(self.session_mgr.get_session(sess.token))

    def test_login_success(self):
        with patch("avantfax.web.views.auth.AFUserAccount") as mock_user_cls:
            user_inst = MagicMock()
            user_inst.login.return_value = True
            user_inst.is_expired.return_value = False
            user_inst.get_uid.return_value = 10
            user_inst.username = "alice"
            user_inst.is_admin = False
            user_inst.superuser = False
            mock_user_cls.return_value = user_inst

            res = self.handler.login("alice", "secret123")
            self.assertTrue(res["success"])
            self.assertIn("token", res)
            self.assertEqual(res["username"], "alice")

            # Check check_login
            checked = self.handler.check_login(res["token"])
            self.assertIsNotNone(checked)
            self.assertEqual(checked.user_id, 10)

    def test_login_failure(self):
        with patch("avantfax.web.views.auth.AFUserAccount") as mock_user_cls:
            user_inst = MagicMock()
            user_inst.login.return_value = False
            user_inst.get_error.return_value = "Invalid credentials"
            mock_user_cls.return_value = user_inst

            res = self.handler.login("alice", "wrongpwd")
            self.assertFalse(res["success"])
            self.assertEqual(res["error"], "Invalid credentials")
            self.assertIsNone(res.get("token"))

    def test_logout(self):
        sess = self.session_mgr.create_session(user_id=5, username="bob", is_admin=False)
        self.assertTrue(self.handler.logout(sess.token))
        self.assertIsNone(self.handler.check_login(sess.token))


if __name__ == "__main__":
    unittest.main()
