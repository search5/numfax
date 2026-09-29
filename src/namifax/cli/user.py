"""NamiFAX User management CLI."""

from __future__ import annotations

import argparse
from datetime import datetime
import sys
from typing import Sequence

from namifax.db.engine import get_default_engine
from namifax.db.schema import init_database_tables
from namifax.services.user_account import AFUserAccount


def run_createuser(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="namifax createuser",
        description="Create or update a NamiFAX user account",
    )
    parser.add_argument("-u", "--username", default="admin", help="Username (default: admin)")
    parser.add_argument("-p", "--password", default="admin1234!", help="Password (default: admin1234!)")
    parser.add_argument("-e", "--email", default="admin@namifax.local", help="Email address")
    parser.add_argument("-n", "--name", default="Administrator", help="Full name")
    parser.add_argument("--admin", action="store_true", default=True, help="Grant admin & superuser privileges")
    parser.add_argument("--user-only", action="store_false", dest="admin", help="Create as regular user")

    args = parser.parse_args(argv)

    # Ensure DB is initialized
    engine = get_default_engine()
    init_database_tables(engine)

    user_svc = AFUserAccount(db=engine)

    # Check if username already exists
    if user_svc.load_username(args.username):
        print(f"[*] User '{args.username}' already exists. Updating credentials...")
        user_svc.set_newpassword(args.password, args.password)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_svc.useraccount.update_entry({
            "uid": user_svc.get_uid(),
            "name": args.name,
            "email": args.email,
            "is_admin": 1 if args.admin else 0,
            "superuser": 1 if args.admin else 0,
            "acc_enabled": 1,
            "wasreset": 0,
            "last_login": now_str,
            "pwdexpire": None,
        })
        print(f"[+] User '{args.username}' updated successfully.")
        return 0

    user_data = {
        "username": args.username,
        "password": args.password,
        "name": args.name,
        "email": args.email,
        "is_admin": 1 if args.admin else 0,
        "superuser": 1 if args.admin else 0,
        "acc_enabled": 1,
        "wasreset": 0,
        "last_login": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pwdexpire": None,
    }

    if user_svc.create(user_data):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_svc.useraccount.update_entry({
            "uid": user_svc.get_uid(),
            "is_admin": 1 if args.admin else 0,
            "superuser": 1 if args.admin else 0,
            "acc_enabled": 1,
            "wasreset": 0,
            "last_login": now_str,
            "pwdexpire": None,
        })
        print(f"[+] Created user '{args.username}' (UID: {user_svc.get_uid()}, Admin: {args.admin}) successfully.")
        return 0
    else:
        print(f"[-] Failed to create user: {user_svc.get_error()}", file=sys.stderr)
        return 1
