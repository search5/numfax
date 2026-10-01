"""Unit tests for avantfax.models.entities (classes_entities layer)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from namifax.db.engine import DatabaseEngine
from namifax.models.entities import (
    AddressBook,
    AddressBookEmail,
    AddressBookFAX,
    BarcodeRoute,
    CoverPages,
    DIDRoute,
    DistroList,
    DynConf,
    FaxArchive,
    FaxCategory,
    Modems,
    SysLog,
    UserAccount,
    UserPasswords,
)


class TestModels(unittest.TestCase):
    def setUp(self):
        self.engine = DatabaseEngine()
        self.engine.connect_sqlite(":memory:")

        # Create sample tables for integration test
        self.engine.query(
            """
            CREATE TABLE UserAccount (
                uid INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                email TEXT NOT NULL,
                email_sig TEXT,
                user_tsi TEXT,
                from_company TEXT,
                from_location TEXT,
                from_voicenumber TEXT,
                from_faxnumber TEXT,
                coverpage_id INTEGER,
                audiofile TEXT,
                faxperpageinbox INTEGER,
                faxperpagearchive INTEGER,
                superuser INTEGER DEFAULT 0,
                can_del INTEGER DEFAULT 0,
                last_mod TIMESTAMP,
                last_login TIMESTAMP,
                last_ip TEXT,
                language TEXT DEFAULT 'en',
                modemdevs TEXT,
                didrouting TEXT,
                faxcats TEXT,
                pwdexpire DATE,
                pwdcycle INTEGER DEFAULT 0,
                pwd_reuse INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                wasreset INTEGER DEFAULT 0,
                acc_enabled INTEGER DEFAULT 1,
                deleted INTEGER DEFAULT 0,
                any_modem INTEGER DEFAULT 0
            )
            """
        )
        self.engine.query(
            """
            CREATE TABLE DynConf (
                dynconf_id INTEGER PRIMARY KEY AUTOINCREMENT,
                device TEXT,
                callid TEXT
            )
            """
        )

    def tearDown(self):
        self.engine.disconnect()

    def test_all_entity_metadata(self):
        """Verify all 14 entity classes have correct table names and primary keys."""
        mapping = {
            DistroList: ("DistroList", "dl_id"),
            UserAccount: ("UserAccount", "uid"),
            UserPasswords: ("UserPasswords", "upid"),
            AddressBook: ("AddressBook", "abook_id"),
            AddressBookEmail: ("AddressBookEmail", "abookemail_id"),
            AddressBookFAX: ("AddressBookFAX", "abookfax_id"),
            Modems: ("Modems", "devid"),
            CoverPages: ("CoverPages", "cover_id"),
            DIDRoute: ("DIDRoute", "didr_id"),
            BarcodeRoute: ("BarcodeRoute", "barcode_id"),
            FaxArchive: ("FaxArchive", "fid"),
            FaxCategory: ("FaxCategory", "catid"),
            SysLog: ("SysLog", "syslogid"),
            DynConf: ("DynConf", "dynconf_id"),
        }

        for cls, (expected_tbl, expected_pk) in mapping.items():
            instance = cls()
            self.assertEqual(instance.get_table_name(), expected_tbl)
            self.assertEqual(instance.get_table_id(), expected_pk)

    def test_user_account_save_and_load(self):
        """Verify UserAccount ActiveRecord save, load, and delete."""
        user = UserAccount(db=self.engine)
        user.username = "testadmin"
        user.password = "5f4dcc3b5aa765d61d8327deb882cf99"
        user.email = "admin@test.com"
        user.is_admin = 1

        self.assertTrue(user.save())
        self.assertEqual(user.get_id(), 1)

        # Load newly created user
        loaded = UserAccount(db=self.engine)
        self.assertTrue(loaded.load(1))
        self.assertEqual(loaded.username, "testadmin")
        self.assertEqual(loaded.email, "admin@test.com")
        self.assertEqual(loaded.is_admin, 1)

        # Update
        loaded.email = "updated@test.com"
        self.assertTrue(loaded.save())

        reloaded = UserAccount(db=self.engine)
        reloaded.load(1)
        self.assertEqual(reloaded.email, "updated@test.com")

        # Delete
        self.assertTrue(reloaded.delete())
        not_found = UserAccount(db=self.engine)
        self.assertFalse(not_found.load(1))

    def test_dynconf_entity(self):
        """Verify DynConf blacklist entity operations."""
        dc = DynConf(db=self.engine)
        dc.device = "ttyS0"
        dc.callid = "12345678"
        self.assertTrue(dc.save())
        self.assertEqual(dc.get_id(), 1)

        query_dc = DynConf(db=self.engine)
        self.assertTrue(query_dc.load(1))
        self.assertEqual(query_dc.device, "ttyS0")
        self.assertEqual(query_dc.callid, "12345678")


if __name__ == "__main__":
    unittest.main()
