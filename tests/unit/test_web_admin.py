#!/usr/bin/env python3
"""Unit tests for avantfax.web.views.admin module."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from avantfax.web.views.admin import AdminHandler


class TestWebAdmin(unittest.TestCase):
    """Test suite for WebAdmin handler."""

    def setUp(self):
        self.handler = AdminHandler()

    def test_list_modems(self):
        with patch("avantfax.web.views.admin.FaxModem") as mock_modem_cls:
            modem_inst = MagicMock()
            modem_inst.get_modems.return_value = ["ttyS0"]
            modem_inst.load_device.return_value = True
            modem_inst.get_alias.return_value = "Modem 1"
            modem_inst.get_contact.return_value = "admin@example.com"
            modem_inst.get_printer.return_value = None
            modem_inst.get_faxcatid.return_value = 1
            mock_modem_cls.return_value = modem_inst

            res = self.handler.list_modems()
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["device"], "ttyS0")
            self.assertEqual(res[0]["alias"], "Modem 1")

    def test_save_category(self):
        with patch("avantfax.web.views.admin.FaxPDFCategory") as mock_cat_cls:
            cat_inst = MagicMock()
            cat_inst.create.return_value = True
            mock_cat_cls.return_value = cat_inst

            self.assertTrue(self.handler.save_category(None, "Invoices"))

    def test_dynconf_management(self):
        with patch("avantfax.web.views.admin.DynamicConfig") as mock_dc_cls:
            dc_inst = MagicMock()
            dc_inst.create.return_value = True
            dc_inst.get_dynconf.return_value = [{"device": "any", "callid": "spammer"}]
            mock_dc_cls.return_value = dc_inst

            self.assertTrue(self.handler.add_dynconf("any", "spammer"))
            items = self.handler.list_dynconf()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["callid"], "spammer")


if __name__ == "__main__":
    unittest.main()
