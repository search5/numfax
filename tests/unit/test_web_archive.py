#!/usr/bin/env python3
"""Unit tests for avantfax.web.views.archive module."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from avantfax.web.views.archive import ArchiveHandler


class TestWebArchive(unittest.TestCase):
    """Test suite for WebArchive handler."""

    def setUp(self):
        self.handler = ArchiveHandler()
        self.mock_user = MagicMock()
        self.mock_user.uid = 1
        self.mock_user.superuser = True
        self.mock_user.get_modemdevs.return_value = ["ttyS0"]
        self.mock_user.get_didrouting.return_value = []
        self.mock_user.get_faxcats.return_value = []

    def test_search_archive(self):
        with patch("avantfax.web.views.archive.FaxPDFArchive") as mock_arch_cls:
            arch_inst = MagicMock()
            arch_inst.get_results_count.return_value = 1
            arch_inst.search_results.side_effect = [True, False]
            arch_inst.get_fid.return_value = 201
            arch_inst.get_pages.return_value = 4
            arch_inst.get_tiffpath.return_value = "/tmp/sent201.tif"
            arch_inst.get_thumbnail.return_value = "/thumb201.png"
            arch_inst.get_archstamp.return_value = "2026-09-29 11:00:00"
            arch_inst.get_inbox.return_value = False
            arch_inst.get_faxnumid.return_value = 1
            arch_inst.get_origfaxnum.return_value = "987654"
            arch_inst.get_companyid.return_value = 2
            mock_arch_cls.return_value = arch_inst

            res = self.handler.search_archive(
                self.mock_user,
                filters={"kw": "invoice"},
                page=0,
                limit=10,
            )
            self.assertEqual(res["total_count"], 1)
            self.assertEqual(len(res["items"]), 1)
            self.assertEqual(res["items"][0]["fid"], 201)

    def test_delete_archive_fax(self):
        with patch("avantfax.web.views.archive.FaxPDFArchive") as mock_arch_cls:
            arch_inst = MagicMock()
            arch_inst.load_fax.return_value = True
            arch_inst.user_has_rights.return_value = True
            arch_inst.del_fax.return_value = True
            mock_arch_cls.return_value = arch_inst

            self.assertTrue(self.handler.delete_archive_fax(201, self.mock_user))


if __name__ == "__main__":
    unittest.main()
