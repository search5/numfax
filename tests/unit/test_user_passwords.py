import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from avantfax.db.engine import DatabaseEngine
from avantfax.services.user_passwords import AFUserPasswords, PasswordHistoryService


class TestAFUserPasswords(unittest.TestCase):
    def setUp(self):
        self.engine = DatabaseEngine()
        self.engine.connect_sqlite(":memory:")

        self.engine.query(
            """
            CREATE TABLE UserPasswords (
                upid INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER NOT NULL,
                pwdhash TEXT NOT NULL
            );
            """
        )
        self.service = AFUserPasswords(db=self.engine)

    def tearDown(self):
        self.engine.disconnect()

    def test_log_and_check_password(self):
        # Initial check
        self.assertFalse(self.service.password_used("secret123", 1))

        # Log password
        ok = self.service.log_password("secret123", 1)
        self.assertTrue(ok)

        # Check again
        self.assertTrue(self.service.password_used("secret123", 1))

        # Different password
        self.assertFalse(self.service.password_used("otherpassword", 1))

        # Different user
        self.assertFalse(self.service.password_used("secret123", 2))

    def test_multiple_passwords(self):
        self.service.log_password("pass_one", 10)
        self.service.log_password("pass_two", 10)

        self.assertTrue(self.service.password_used("pass_one", 10))
        self.assertTrue(self.service.password_used("pass_two", 10))
        self.assertFalse(self.service.password_used("pass_three", 10))

    def test_clear_hashes(self):
        self.service.log_password("pass_user1", 1)
        self.service.log_password("pass_user2", 2)

        self.assertTrue(self.service.password_used("pass_user1", 1))
        self.assertTrue(self.service.password_used("pass_user2", 2))

        # Clear hashes for user 1
        ok = self.service.clear_hashes(1)
        self.assertTrue(ok)

        # User 1 should have no history
        self.assertFalse(self.service.password_used("pass_user1", 1))

        # User 2 history should remain intact
        self.assertTrue(self.service.password_used("pass_user2", 2))


if __name__ == "__main__":
    unittest.main()
