"""Unit tests for avantfax.db.engine (SQL layer) using Python unittest."""

import os
import sys
import unittest

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from avantfax.db.engine import DatabaseEngine, SQL_ALL, SQL_NONE


class TestDatabaseEngine(unittest.TestCase):
    def setUp(self):
        """Create in-memory SQLite database engine for testing."""
        self.engine = DatabaseEngine()
        success = self.engine.connect_sqlite(":memory:")
        self.assertTrue(success)

        # Initialize test schema
        self.engine.query(
            """
            CREATE TABLE test_users (
                uid INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL
            )
            """
        )

    def tearDown(self):
        self.engine.disconnect()

    def test_insert_and_last_insert_id(self):
        """Test insert query execution and retrieving last inserted ID."""
        res1 = self.engine.query("INSERT INTO test_users (username, email) VALUES ('admin', 'admin@example.com')")
        self.assertTrue(res1.executed)
        self.assertEqual(self.engine.get_insert_id(), 1)
        self.assertEqual(self.engine.affected_rows, 1)

        res2 = self.engine.query("INSERT INTO test_users (username, email) VALUES ('guest', 'guest@example.com')")
        self.assertTrue(res2.executed)
        self.assertEqual(self.engine.get_insert_id(), 2)
        self.assertEqual(self.engine.affected_rows, 1)

    def test_select_all(self):
        """Test SELECT query with SQL_ALL mode."""
        self.engine.query("INSERT INTO test_users (username, email) VALUES ('user1', 'u1@example.com')")
        self.engine.query("INSERT INTO test_users (username, email) VALUES ('user2', 'u2@example.com')")

        res = self.engine.query("SELECT * FROM test_users ORDER BY uid", fetch_type=SQL_ALL)
        self.assertTrue(res.executed)
        self.assertEqual(res.row_count, 2)

        records = self.engine.get_records()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["username"], "user1")
        self.assertEqual(records[1]["username"], "user2")

    def test_select_iterative_get_result(self):
        """Test SELECT query and iterative get_result()."""
        self.engine.query("INSERT INTO test_users (username, email) VALUES ('a', 'a@test.com')")
        self.engine.query("INSERT INTO test_users (username, email) VALUES ('b', 'b@test.com')")

        self.engine.query("SELECT username FROM test_users ORDER BY uid", fetch_type=SQL_NONE)

        row1 = self.engine.get_result()
        self.assertNotEqual(row1, False)
        self.assertEqual(row1["username"], "a")

        row2 = self.engine.get_result()
        self.assertNotEqual(row2, False)
        self.assertEqual(row2["username"], "b")

        row3 = self.engine.get_result()
        self.assertFalse(row3)

    def test_quote(self):
        """Test literal escaping with quote()."""
        quoted = self.engine.quote("O'Reilly")
        self.assertEqual(quoted, "'O''Reilly'")
        self.assertEqual(self.engine.quote(None), "NULL")

    def test_gen_xml(self):
        """Test generating XML from records matching legacy genXML format."""
        self.engine.query("INSERT INTO test_users (username, email) VALUES ('xml_user', 'xml@example.com')")
        self.engine.query("SELECT username, email FROM test_users", fetch_type=SQL_ALL)

        xml = self.engine.gen_xml(xml_title=True, root_tag="response", row_tag="row")
        self.assertIn('<?xml version="1.0" encoding="utf-8" ?>', xml)
        self.assertIn("<response>", xml)
        self.assertIn("<row>", xml)
        self.assertIn("<username>xml_user</username>", xml)
        self.assertIn("<email>xml@example.com</email>", xml)
        self.assertIn("</response>", xml)

    def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        with self.assertRaises(RuntimeError):
            with self.engine.transaction():
                self.engine._cursor.execute("INSERT INTO test_users (username, email) VALUES ('temp', 'temp@test.com')")
                raise RuntimeError("Force Rollback")

        self.engine.query("SELECT * FROM test_users WHERE username = 'temp'", fetch_type=SQL_ALL)
        self.assertEqual(len(self.engine.get_records()), 0)


if __name__ == "__main__":
    unittest.main()
