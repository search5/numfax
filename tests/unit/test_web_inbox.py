#!/usr/bin/env python3
"""Unit tests for avantfax.web.views.inbox module."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from avantfax.web.views.inbox import InboxHandler


class TestWebInbox(unittest.TestCase):
    """Test suite for WebInbox handler."""

    def setUp(self):
        self.handler = InboxHandler()
        self.mock_user = MagicMock()
        self.mock_user.uid = 1
        self.mock_user.superuser = True
        self.mock_user.get_modemdevs.return_value = ["ttyS0"]
        self.mock_user.get_didrouting.return_value = []
        self.mock_user.get_faxcats.return_value = []

    def test_list_inbox(self):
        with patch("avantfax.web.views.inbox.ArchiveIn") as mock_inbox_cls, \
             patch("avantfax.web.views.inbox.FaxModem") as mock_modem_cls:

            inbox_inst = MagicMock()
            inbox_inst.get_num_faxes.return_value = 2
            inbox_inst.list_inbox.side_effect = [True, True, False]
            inbox_inst.get_fid.side_effect = [101, 102]
            inbox_inst.get_pages.side_effect = [1, 2]
            inbox_inst.get_tiffpath.side_effect = ["/tmp/fax1.tif", "/tmp/fax2.tif"]
            inbox_inst.get_thumbnail.side_effect = ["/thumb1.png", "/thumb2.png"]
            inbox_inst.get_archstamp.side_effect = ["2026-09-29 10:00:00", "2026-09-29 10:05:00"]
            inbox_inst.get_modemdev.return_value = "ttyS0"
            inbox_inst.get_didr_id.return_value = 0
            inbox_inst.get_faxnumid.return_value = 1
            inbox_inst.get_origfaxnum.return_value = "123456"
            inbox_inst.get_companyid.return_value = 1
            mock_inbox_cls.return_value = inbox_inst

            modem_inst = MagicMock()
            modem_inst.get_modems.return_value = ["ttyS0"]
            modem_inst.load_device.return_value = True
            modem_inst.get_alias.return_value = "Main Modem"
            mock_modem_cls.return_value = modem_inst

            res = self.handler.list_inbox(self.mock_user, page=0, limit=10)
            self.assertEqual(res["total_count"], 2)
            self.assertEqual(len(res["items"]), 2)
            self.assertEqual(res["items"][0]["fid"], 101)
            self.assertEqual(res["items"][1]["fid"], 102)

    def test_get_fax_detail(self):
        with patch("avantfax.web.views.inbox.ArchiveIn") as mock_inbox_cls:
            inbox_inst = MagicMock()
            inbox_inst.load_fax.return_value = True
            inbox_inst.get_inbox.return_value = True
            inbox_inst.user_has_rights.return_value = True
            inbox_inst.get_fid.return_value = 101
            inbox_inst.get_pages.return_value = 3
            inbox_inst.get_tiffpath.return_value = "/tmp/fax101.tif"
            inbox_inst.get_faximages.return_value = ["/tmp/fax101-1.png", "/tmp/fax101-2.png"]
            inbox_inst.get_fid_prev.return_value = 100
            inbox_inst.get_fid_next.return_value = 102
            inbox_inst.get_archstamp.return_value = "2026-09-29 12:00:00"
            inbox_inst.get_faxnumid.return_value = 1
            inbox_inst.get_origfaxnum.return_value = "123456"
            inbox_inst.get_companyid.return_value = 1
            mock_inbox_cls.return_value = inbox_inst

            detail = self.handler.get_fax_detail(101, self.mock_user)
            self.assertIsNotNone(detail)
            self.assertEqual(detail["fid"], 101)
            self.assertEqual(detail["pages"], 3)
            self.assertEqual(len(detail["images"]), 2)

    def test_delete_and_archive_fax(self):
        with patch("avantfax.web.views.inbox.ArchiveIn") as mock_inbox_cls:
            inbox_inst = MagicMock()
            inbox_inst.load_fax.return_value = True
            inbox_inst.get_inbox.return_value = True
            inbox_inst.archivefax.return_value = True
            mock_inbox_cls.return_value = inbox_inst

            self.assertTrue(self.handler.archive_fax(101, self.mock_user))


if __name__ == "__main__":
    unittest.main()
