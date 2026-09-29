"""avantfax.cli.import_users

Batch user import tool matching legacy tools/import_users.php and specs/38-tools-batch.md.
"""

from __future__ import annotations

import os
import sys

from avantfax.services.user_account import AFUserAccount


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    if len(args) < 1:
        print("""usage: import_users.php filename
Example: import_users.php users.txt
One user entry per line with fields: name, username, password, and email separated by 1 tab
Example:
John Doe\tjohndoe\tpassw0rd\tjohn.doe@mycompany.com
NOTE: Be sure to set $AVANTFAX_SERVERNAME in includes/local_config.php before running this script""")
        return 0

    filename = args[0]
    if not os.path.isfile(filename):
        print(f"Error: File not found: {filename}")
        return 1

    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    user_details_base = {
        "name": None,
        "username": None,
        "password": None,
        "email": None,
        "superuser": 0,
        "can_del": 0,
        "language": "en",
        "pwdcycle": 0,
        "pwd_reuse": 0,
        "is_admin": 0,
        "acc_enabled": 1,
    }

    for line in lines:
        line = line.rstrip("\r\n")
        if not line:
            continue

        parts = line.split("\t")
        if len(parts) < 4:
            continue

        name, username, password, email = parts[0], parts[1], parts[2], parts[3]
        user_details = dict(user_details_base)
        user_details["name"] = name
        user_details["username"] = username
        user_details["password"] = password
        user_details["email"] = email

        user = AFUserAccount()
        if user.create(user_details):
            print(f"user> {name}: User details saved")
        else:
            print(f"Error> {name}: {user.get_error()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
