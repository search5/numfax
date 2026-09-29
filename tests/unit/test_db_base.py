"""Unit tests for avantfax.db.base (MDBObject layer)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from avantfax.db.base import MDBObject


class SampleUser(MDBObject):
    """Sample entity representing a table row."""
    table_name = "UserAccount"
    table_id_name = "uid"

    def __init__(self, uid=None, username=None, email=None):
        super().__init__()
        self.uid = uid
        self.username = username
        self.email = email


class TestMDBObject(unittest.TestCase):
    def test_metadata_accessors(self):
        """Test get_table_name and get_table_id."""
        user = SampleUser()
        self.assertEqual(user.get_table_name(), "UserAccount")
        self.assertEqual(user.get_table_id(), "uid")

    def test_id_accessors(self):
        """Test setting and getting primary key id."""
        user = SampleUser()
        self.assertIsNone(user.get_id())

        self.assertTrue(user.set_id(42))
        self.assertEqual(user.get_id(), 42)
        self.assertEqual(user.uid, 42)

        # Invalid non-numeric ID
        self.assertFalse(user.set_id("not_a_number"))

    def test_set_vars(self):
        """Test batch property injection via set_vars."""
        user = SampleUser()
        payload = {
            "uid": 101,
            "username": "superadmin",
            "email": "admin@example.com",
            "extra_field": "custom_value",
        }
        user.set_vars(payload)

        self.assertEqual(user.get_id(), 101)
        self.assertEqual(user.username, "superadmin")
        self.assertEqual(user.email, "admin@example.com")
        self.assertEqual(user.extra_field, "custom_value")

    def test_to_dict(self):
        """Test serialization to dictionary."""
        user = SampleUser(uid=1, username="testuser", email="test@test.com")
        d = user.to_dict()

        self.assertEqual(d["uid"], 1)
        self.assertEqual(d["username"], "testuser")
        self.assertEqual(d["email"], "test@test.com")
        self.assertNotIn("table_name", d)
        self.assertNotIn("table_id_name", d)


if __name__ == "__main__":
    unittest.main()
