"""Unit tests for avantfax.db.query (MDBO layer)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from namifax.db.engine import DatabaseEngine
from namifax.db.query import QueryBuilder, SQL_AND, SQL_OR


class TestQueryBuilder(unittest.TestCase):
    def setUp(self):
        self.engine = DatabaseEngine()
        self.engine.connect_sqlite(":memory:")
        self.qb = QueryBuilder(self.engine)

        # Setup sample table
        self.engine.query(
            """
            CREATE TABLE users (
                uid INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            )
            """
        )

    def tearDown(self):
        self.engine.disconnect()

    def test_quote_special_functions(self):
        """Verify SQL date/timestamp functions are passed unquoted."""
        self.assertEqual(self.qb.quote("NOW()"), "NOW()")
        self.assertEqual(self.qb.quote("CURRENT_TIMESTAMP()"), "CURRENT_TIMESTAMP()")
        self.assertEqual(self.qb.quote("CURDATE()"), "CURDATE()")
        self.assertEqual(self.qb.quote("regular_text"), "'regular_text'")
        self.assertEqual(self.qb.quote("O'Connor"), "'O''Connor'")

    def test_insert_and_get(self):
        """Verify inserting record and fetching by primary key."""
        uid = self.qb.insert("users", {"username": "alice", "email": "alice@test.com", "status": "active"}, id_col="uid")
        self.assertEqual(uid, 1)

        row = self.qb.get("users", id_col="uid", id_val=1)
        self.assertIsNotNone(row)
        self.assertEqual(row["username"], "alice")
        self.assertEqual(row["email"], "alice@test.com")

    def test_update(self):
        """Verify updating existing record."""
        uid = self.qb.insert("users", {"username": "bob", "email": "bob@test.com"}, id_col="uid")
        self.assertEqual(uid, 1)

        success = self.qb.update("users", {"email": "bob_new@test.com"}, where={"uid": uid})
        self.assertTrue(success)

        updated = self.qb.get("users", id_col="uid", id_val=uid)
        self.assertEqual(updated["email"], "bob_new@test.com")

    def test_find_with_reduce_single(self):
        """Verify find with single result reducing to dict."""
        self.qb.insert("users", {"username": "user1", "email": "u1@test.com", "status": "active"})
        self.qb.insert("users", {"username": "user2", "email": "u2@test.com", "status": "inactive"})

        # Single match with reduce_single=True
        single = self.qb.find("users", conditions={"username": "user1"}, reduce_single=True)
        self.assertIsInstance(single, dict)
        self.assertEqual(single["username"], "user1")

        # Multiple matches
        multiple = self.qb.find("users", conditions={"status": "active"}, reduce_single=True)
        self.assertIsInstance(multiple, dict) # only 1 active so far

        self.qb.insert("users", {"username": "user3", "email": "u3@test.com", "status": "active"})
        multiple = self.qb.find("users", conditions={"status": "active"}, reduce_single=True)
        self.assertIsInstance(multiple, list)
        self.assertEqual(len(multiple), 2)

    def test_find_with_or_logic_and_limit(self):
        """Verify find with OR logic and limit/offset."""
        self.qb.insert("users", {"username": "u1", "email": "u1@test.com"})
        self.qb.insert("users", {"username": "u2", "email": "u2@test.com"})
        self.qb.insert("users", {"username": "u3", "email": "u3@test.com"})

        res = self.qb.find(
            "users",
            conditions={"username": "u1", "email": "u2@test.com"},
            logic=SQL_OR,
            limit=2,
            reduce_single=False,
        )
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 2)

    def test_delete(self):
        """Verify deleting record."""
        uid = self.qb.insert("users", {"username": "del_user", "email": "del@test.com"}, id_col="uid")
        self.assertIsNotNone(self.qb.get("users", id_col="uid", id_val=uid))

        success = self.qb.delete("users", id_col="uid", id_val=uid)
        self.assertTrue(success)
        self.assertIsNone(self.qb.get("users", id_col="uid", id_val=uid))


if __name__ == "__main__":
    unittest.main()
