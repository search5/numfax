import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from avantfax.db.engine import DatabaseEngine
from avantfax.services.user_account import AFUserAccount, UserAccountService
from avantfax.services.user_passwords import AFUserPasswords


class TestAFUserAccount(unittest.TestCase):
    def setUp(self):
        self.engine = DatabaseEngine()
        self.engine.connect_sqlite(":memory:")

        self.engine.query(
            """
            CREATE TABLE UserAccount (
                uid INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                username TEXT,
                password TEXT,
                email TEXT,
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
                last_mod TEXT,
                last_login TEXT,
                last_ip TEXT,
                language TEXT DEFAULT 'en',
                modemdevs TEXT,
                didrouting TEXT,
                faxcats TEXT,
                pwdexpire TEXT,
                pwdcycle INTEGER DEFAULT 0,
                pwd_reuse INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                wasreset INTEGER DEFAULT 0,
                acc_enabled INTEGER DEFAULT 1,
                deleted INTEGER DEFAULT 0,
                any_modem INTEGER DEFAULT 0
            );
            """
        )
        self.engine.query(
            """
            CREATE TABLE UserPasswords (
                upid INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER NOT NULL,
                pwdhash TEXT NOT NULL
            );
            """
        )

        self.passwords_svc = AFUserPasswords(db=self.engine)
        self.user_svc = AFUserAccount(db=self.engine, user_passwords=self.passwords_svc)

    def tearDown(self):
        self.engine.disconnect()

    def test_create_account(self):
        ok = self.user_svc.create({
            "name": "Alice Smith",
            "email": "alice@example.com",
            "username": "asmith",
            "password": "Password123",
            "pwdcycle": 0,
        })
        self.assertTrue(ok)
        uid = self.user_svc.get_uid()
        self.assertIsNotNone(uid)

        # Duplicate username
        dup_user = AFUserAccount(db=self.engine, user_passwords=self.passwords_svc)
        ok2 = dup_user.create({
            "name": "Alice 2",
            "email": "alice2@example.com",
            "username": "asmith",
            "password": "Password123",
        })
        self.assertFalse(ok2)
        self.assertIn("username", dup_user.get_error().lower())

        # Duplicate email
        dup_email = AFUserAccount(db=self.engine, user_passwords=self.passwords_svc)
        ok3 = dup_email.create({
            "name": "Alice 3",
            "email": "alice@example.com",
            "username": "asmith3",
            "password": "Password123",
        })
        self.assertFalse(ok3)

        # Invalid username characters
        bad_name = AFUserAccount(db=self.engine, user_passwords=self.passwords_svc)
        ok4 = bad_name.create({
            "name": "Bad User",
            "email": "bad@example.com",
            "username": "bad user!",
            "password": "Password123",
        })
        self.assertFalse(ok4)

    def test_login_and_roles(self):
        self.user_svc.create({
            "name": "Admin User",
            "email": "admin@example.com",
            "username": "admin",
            "password": "SecretPassword1",
            "is_admin": 1,
            "acc_enabled": 1,
        })

        client = AFUserAccount(db=self.engine, user_passwords=self.passwords_svc)

        # 1. Successful regular login
        ok = client.login("admin", "SecretPassword1")
        self.assertTrue(ok)
        self.assertTrue(client.check_login())
        self.assertTrue(client.check_admin_login())

        # 2. Failed password
        fail_client = AFUserAccount(db=self.engine, user_passwords=self.passwords_svc)
        self.assertFalse(fail_client.login("admin", "WrongPassword"))
        self.assertFalse(fail_client.check_login())

        # 3. Disabled account
        self.engine.query("UPDATE UserAccount SET acc_enabled = 0 WHERE username = 'admin'")
        dis_client = AFUserAccount(db=self.engine, user_passwords=self.passwords_svc)
        self.assertFalse(dis_client.login("admin", "SecretPassword1"))

    def test_change_password_and_history(self):
        self.user_svc.create({
            "name": "Bob",
            "email": "bob@example.com",
            "username": "bob",
            "password": "InitPassword1",
            "pwd_reuse": 0,
        })
        uid = self.user_svc.get_uid()
        self.passwords_svc.log_password("InitPassword1", uid)

        # 1. Too short
        self.assertFalse(self.user_svc.change_password("short"))

        # 2. Reuse old password
        self.assertFalse(self.user_svc.change_password("InitPassword1"))

        # 3. Valid new password
        self.assertTrue(self.user_svc.change_password("BrandNewPassword1"))

        # 4. Verify login with new password
        tester = AFUserAccount(db=self.engine, user_passwords=self.passwords_svc)
        self.assertTrue(tester.login("bob", "BrandNewPassword1"))

    def test_reset_password(self):
        self.user_svc.create({
            "name": "Charlie",
            "email": "charlie@example.com",
            "username": "charlie",
            "password": "CharliePassword1",
        })

        ok, newpwd = self.user_svc.reset_password("charlie@example.com")
        self.assertTrue(ok)
        self.assertIsNotNone(newpwd)

        tester = AFUserAccount(db=self.engine, user_passwords=self.passwords_svc)
        self.assertTrue(tester.login("charlie", newpwd))
        self.assertTrue(tester.is_expired())  # wasreset requires password change

    def test_remove_account(self):
        self.user_svc.create({
            "name": "Dave",
            "email": "dave@example.com",
            "username": "dave",
            "password": "DavePassword1",
        })
        uid = self.user_svc.get_uid()

        self.assertTrue(self.user_svc.remove(uid))

        self.engine.query("SELECT * FROM UserAccount WHERE uid = :uid", {"uid": uid})
        rec = self.engine.get_records()[0]
        self.assertEqual(rec["deleted"], 1)
        self.assertEqual(rec["acc_enabled"], 0)
        self.assertIsNone(rec["username"])
        self.assertIsNone(rec["email"])

    def test_devices_and_routes_serialization(self):
        self.user_svc.create({
            "name": "Eve",
            "email": "eve@example.com",
            "username": "eve",
            "password": "EvePassword1",
        })

        self.user_svc.set_modemdevs(["ttyS0", "ttyS1"])
        self.user_svc.set_faxcats([1, 2])
        self.user_svc.set_didrouting([10, 20])
        self.user_svc.update()

        reloaded = AFUserAccount(db=self.engine, user_passwords=self.passwords_svc)
        reloaded.load(self.user_svc.get_uid())

        self.assertEqual(reloaded.get_modemdevs(), ["ttyS0", "ttyS1"])
        self.assertEqual(reloaded.get_faxcats(), ["1", "2"])
        self.assertEqual(reloaded.get_didrouting(), ["10", "20"])


if __name__ == "__main__":
    unittest.main()
