#!/usr/bin/env python3
"""Unit tests for avantfax.web.views.sendfax module."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from avantfax.web.views.sendfax import SendFaxHandler


class TestWebSendFax(unittest.TestCase):
    """Test suite for WebSendFax handler."""

    def setUp(self):
        self.handler = SendFaxHandler()
        self.mock_user = MagicMock()
        self.mock_user.uid = 1
        self.mock_user.username = "alice"
        self.mock_user.superuser = True
        self.mock_user.any_modem = True
        self.mock_user.coverpage_id = 1
        self.mock_user.get_modemdevs.return_value = ["ttyS0"]

    def test_get_sendfax_options(self):
        with patch("avantfax.web.views.sendfax.FaxModem") as mock_modem_cls, \
             patch("avantfax.web.views.sendfax.Covers") as mock_covers_cls:

            modem_inst = MagicMock()
            modem_inst.get_modems.return_value = ["ttyS0"]
            modem_inst.load_device.return_value = True
            modem_inst.get_alias.return_value = "Modem 1"
            mock_modem_cls.return_value = modem_inst

            covers_inst = MagicMock()
            covers_inst.get_covers.return_value = ["cover1.ps"]
            covers_inst.load_cover.return_value = True
            covers_inst.get_title.return_value = "Standard Cover"
            mock_covers_cls.return_value = covers_inst

            opts = self.handler.get_sendfax_options(self.mock_user)
            self.assertIn("modems", opts)
            self.assertIn("covers", opts)
            self.assertEqual(len(opts["modems"]), 1)
            self.assertEqual(len(opts["covers"]), 1)

    def test_send_fax_missing_destinations(self):
        res = self.handler.send_fax(
            self.mock_user,
            form_data={"destinations": ""},
            file_paths=[],
        )
        self.assertFalse(res["success"])
        self.assertIn("destination", res["error"].lower())

    def test_send_fax_success(self):
        with patch("avantfax.web.views.sendfax.clean_faxnum", return_value="12345678"):
            res = self.handler.send_fax(
                self.mock_user,
                form_data={
                    "destinations": "12345678",
                    "regarding": "Test Fax",
                    "comments": "Hello World",
                },
                file_paths=["/tmp/doc.pdf"],
            )
            self.assertTrue(res["success"])
            self.assertEqual(len(res["job_ids"]), 1)


if __name__ == "__main__":
    unittest.main()
