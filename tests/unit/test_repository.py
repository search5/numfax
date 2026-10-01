"""Unit tests for avantfax.db.repository (MDBOData layer)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from namifax.db.engine import DatabaseEngine
from namifax.db.repository import MDBOData, Repository
from namifax.models.entities import UserAccount


class TestRepository(unittest.TestCase):
    def setUp(self):
        self.engine = DatabaseEngine()
        self.engine.connect_sqlite(":memory:")

        # Create UserAccount test table
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

    def tearDown(self):
        self.engine.disconnect()

    def test_repo_new_entry_and_load(self):
        """Verify new_entry creation and loading by id."""
        repo = MDBOData("UserAccount", db=self.engine)

        payload = {
            "username": "user10",
            "password": "hashed_pass_10",
            "email": "user10@example.com",
            "is_admin": 0,
        }
        self.assertTrue(repo.new_entry(payload))
        self.assertEqual(repo.get_id(), 1)

        # Inspect get_info
        info = repo.get_info()
        self.assertEqual(info["username"], "user10")
        self.assertEqual(info["email"], "user10@example.com")

        # Load fresh repository
        fresh_repo = Repository(UserAccount, db=self.engine)
        self.assertTrue(fresh_repo.load(1))
        self.assertEqual(fresh_repo.data.username, "user10")
        self.assertEqual(fresh_repo.data.email, "user10@example.com")

    def test_repo_update_and_find(self):
        """Verify update_entry and find with condition."""
        repo = MDBOData(UserAccount, db=self.engine)
        repo.new_entry({"username": "user20", "password": "pwd", "email": "user20@test.com"})

        # Update
        self.assertTrue(repo.update_entry({"email": "updated20@test.com"}))

        # Find
        found = repo.find({"email": "updated20@test.com"}, reduce_single=True)
        self.assertIsNotNone(found)
        self.assertEqual(found["username"], "user20")

    def test_repo_delete_entry(self):
        """Verify deleting loaded record."""
        repo = MDBOData("UserAccount", db=self.engine)
        repo.new_entry({"username": "todelete", "password": "pwd", "email": "del@test.com"})
        uid = repo.get_id()

        self.assertTrue(repo.delete_entry())
        self.assertFalse(repo.load(uid))

    def test_repo_query(self):
        """Verify arbitrary SQL execution via repository."""
        repo = MDBOData(UserAccount, db=self.engine)
        repo.new_entry({"username": "q1", "password": "pwd", "email": "q1@test.com"})
        repo.new_entry({"username": "q2", "password": "pwd", "email": "q2@test.com"})

        rows = repo.query("SELECT username FROM UserAccount ORDER BY uid", reduce_single=False)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["username"], "q1")
        self.assertEqual(rows[1]["username"], "q2")


if __name__ == "__main__":
    unittest.main()
