#!/usr/bin/env python3
"""Unit tests for avantfax.web.views.outbox module."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from avantfax.web.views.outbox import OutboxHandler


class TestWebOutbox(unittest.TestCase):
    """Test suite for WebOutbox handler."""

    def setUp(self):
        self.handler = OutboxHandler()
        self.mock_user = MagicMock()
        self.mock_user.username = "alice"
        self.mock_user.superuser = False

    def test_get_outbox_queue_user(self):
        with patch("avantfax.web.views.outbox.FaxQueue") as mock_fq_cls, \
             patch("avantfax.web.views.outbox.AFAddressBook") as mock_ab_cls:

            fq_inst = MagicMock()
            fq_inst.list_owner.return_value = [
                {"jid": "101", "owner": "alice", "number": "123456", "status": "Sending"},
            ]
            mock_fq_cls.return_value = fq_inst

            ab_inst = MagicMock()
            ab_inst.loadbyfaxnum.return_value = True
            ab_inst.get_company.return_value = "Acme Global"
            mock_ab_cls.return_value = ab_inst

            res = self.handler.get_outbox_queue(self.mock_user)
            self.assertEqual(len(res["active_queue"]), 1)
            self.assertEqual(res["active_queue"][0]["company"], "Acme Global")
            self.assertEqual(res["active_queue"][0]["jid"], "101")

    def test_kill_job_permission(self):
        with patch("avantfax.web.views.outbox.FaxQueue") as mock_fq_cls:
            fq_inst = MagicMock()
            fq_inst.list_owner.return_value = [
                {"jid": "101", "owner": "alice", "number": "123456"},
            ]
            fq_inst.killjob.return_value = True
            mock_fq_cls.return_value = fq_inst

            # Allowed
            self.assertTrue(self.handler.kill_job("101", self.mock_user))

            # Not allowed (non-existent or not owned)
            self.assertFalse(self.handler.kill_job("999", self.mock_user))


if __name__ == "__main__":
    unittest.main()
