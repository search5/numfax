"""NamiFAX SQLite schema initialization and table creation."""

from __future__ import annotations

import os
from typing import Optional
from namifax.db.engine import DatabaseEngine

SCHEMA_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS UserAccount (
        uid INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT NOT NULL UNIQUE,
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
        faxperpageinbox INTEGER DEFAULT 10,
        faxperpagearchive INTEGER DEFAULT 10,
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
    );""",
    """CREATE TABLE IF NOT EXISTS UserPasswords (
        upid INTEGER PRIMARY KEY AUTOINCREMENT,
        uid INTEGER NOT NULL,
        pwdhash TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS Modems (
        devid INTEGER PRIMARY KEY AUTOINCREMENT,
        device TEXT NOT NULL UNIQUE,
        alias TEXT,
        contact TEXT,
        printer TEXT,
        faxcatid INTEGER
    );""",
    """CREATE TABLE IF NOT EXISTS DIDRoute (
        didr_id INTEGER PRIMARY KEY AUTOINCREMENT,
        routecode TEXT NOT NULL UNIQUE,
        alias TEXT,
        contact TEXT,
        printer TEXT,
        faxcatid INTEGER
    );""",
    """CREATE TABLE IF NOT EXISTS BarcodeRoute (
        barcode_id INTEGER PRIMARY KEY AUTOINCREMENT,
        bcr_id INTEGER,
        barcode TEXT NOT NULL UNIQUE,
        alias TEXT,
        contact TEXT,
        printer TEXT,
        faxcatid INTEGER
    );""",
    """CREATE TABLE IF NOT EXISTS DynConf (
        dynconf_id INTEGER PRIMARY KEY AUTOINCREMENT,
        device TEXT,
        callid TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS FaxCategory (
        catid INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );""",
    """CREATE TABLE IF NOT EXISTS CoverPages (
        cover_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        file TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS DistroList (
        dl_id INTEGER PRIMARY KEY AUTOINCREMENT,
        listname TEXT NOT NULL,
        listdata TEXT,
        lastmod_date TEXT,
        lastmod_user INTEGER
    );""",
    """CREATE TABLE IF NOT EXISTS AddressBook (
        abook_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT,
        description TEXT,
        faxtype TEXT,
        faxnum TEXT,
        phonenum TEXT,
        email TEXT,
        address TEXT,
        city TEXT,
        state TEXT,
        zip TEXT,
        country TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS AddressBookFAX (
        abookfax_id INTEGER PRIMARY KEY AUTOINCREMENT,
        abook_id INTEGER,
        faxnumber TEXT NOT NULL,
        email TEXT,
        description TEXT,
        to_person TEXT,
        to_location TEXT,
        to_voicenumber TEXT,
        faxcatid INTEGER,
        faxfrom INTEGER DEFAULT 0,
        faxto INTEGER DEFAULT 0,
        printer TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS AddressBookEmail (
        abookemail_id INTEGER PRIMARY KEY AUTOINCREMENT,
        abook_id INTEGER,
        contact_name TEXT,
        contact_email TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS AddressBookDistro (
        dl_id INTEGER,
        ab_id INTEGER,
        fax_id INTEGER
    );""",
    """CREATE TABLE IF NOT EXISTS FaxArchive (
        fid INTEGER PRIMARY KEY AUTOINCREMENT,
        faxnum TEXT,
        cid_name TEXT,
        cid_number TEXT,
        pages INTEGER DEFAULT 1,
        archivetime TEXT,
        lastmod TEXT,
        assignedby TEXT,
        assignedto TEXT,
        category INTEGER,
        callid1 TEXT,
        callid2 TEXT,
        callid3 TEXT,
        callid4 TEXT,
        callid5 TEXT,
        callid6 TEXT,
        callid7 TEXT,
        did_id INTEGER,
        description TEXT,
        company TEXT,
        origfaxnum TEXT,
        status TEXT,
        filename TEXT,
        thumbnail TEXT,
        inbox INTEGER DEFAULT 0
    );""",
    """CREATE TABLE IF NOT EXISTS SysLog (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        logdate TEXT NOT NULL,
        logtext TEXT NOT NULL
    );""",
    """CREATE TABLE IF NOT EXISTS SystemSettings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        smtp_host TEXT DEFAULT 'localhost',
        smtp_port INTEGER DEFAULT 25,
        smtp_security TEXT DEFAULT 'NONE',
        smtp_auth INTEGER DEFAULT 0,
        smtp_username TEXT,
        smtp_password TEXT,
        from_email TEXT DEFAULT 'root@localhost',
        from_name TEXT DEFAULT 'NamiFAX',
        email_sig_text TEXT,
        email_sig_html TEXT,
        updated_at TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS NetworkPrinters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        protocol TEXT DEFAULT 'RAW',
        host TEXT NOT NULL,
        port INTEGER DEFAULT 9100,
        queue_name TEXT,
        description TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS UserTOTP (
        uid INTEGER PRIMARY KEY,
        secret_key TEXT NOT NULL,
        is_enabled INTEGER DEFAULT 0,
        backup_codes TEXT,
        created_at TEXT
    );""",
    """CREATE TABLE IF NOT EXISTS SystemConfig (
        key TEXT PRIMARY KEY,
        value TEXT
    );""",
]


def init_database_tables(db: DatabaseEngine) -> bool:
    """Execute DDL statements to ensure all tables exist."""
    for stmt in SCHEMA_STATEMENTS:
        res = db.query(stmt)
        if not res.executed:
            return False
    _rename_user_passwords_columns(db)
    _migrate_address_book_keys(db)
    _apply_schema_migrations(db)
    _backfill_alias_columns(db)
    _normalize_boolean_flags(db)
    seed_database_if_empty(db)
    _backfill_alias_columns(db)  # rows created by the seed
    return True


_USER_ACCOUNT_FLAGS = ("superuser", "can_del", "pwd_reuse", "is_admin", "wasreset", "acc_enabled", "deleted", "any_modem")


def _normalize_boolean_flags(db: DatabaseEngine) -> None:
    """Turn flags the old code stored as the text 'True'/'False' back into 0/1 (SQLite; idempotent).

    Text is only converted where it really is text, so correct rows are not touched.
    """
    if getattr(db, "dialect", "sqlite") != "sqlite":
        return
    for flag in _USER_ACCOUNT_FLAGS:
        db.query(
            f"UPDATE UserAccount SET {flag} = CASE WHEN lower({flag}) IN ('1', 'true', 't', 'yes', 'y', 'on') "
            f"THEN 1 ELSE 0 END WHERE typeof({flag}) = 'text'"
        )


def _backfill_alias_columns(db: DatabaseEngine) -> None:
    """Fill the duplicate id columns the port added (abook_id, barcode_id, ...) from the legacy ones.

    Structural only: it touches NULL values and nothing else. It runs after the migrations and again
    after seeding, so rows created by the seed are complete on the very first start.
    """
    db.query("UPDATE BarcodeRoute SET barcode_id = bcr_id WHERE barcode_id IS NULL AND bcr_id IS NOT NULL")
    db.query("UPDATE FaxArchive SET archstamp = archivetime WHERE archstamp IS NULL AND archivetime IS NOT NULL")


def _has_column(db: DatabaseEngine, table: str, column: str) -> bool:
    db.query(f"SELECT 1 AS present FROM pragma_table_info('{table}') WHERE name = '{column}'")
    return bool(db.get_records())


def _primary_key_columns(db: DatabaseEngine, table: str) -> list[str]:
    db.query(f"SELECT name FROM pragma_table_info('{table}') WHERE pk = 1")
    return [r["name"] for r in db.get_records()]


_ADDRESS_BOOK_COLUMNS = ["company", "description", "faxtype", "faxnum", "phonenum", "email", "address", "city",
                         "state", "zip", "country"]


def _migrate_address_book_keys(db: DatabaseEngine) -> None:
    """Older port versions made ab_id the key of AddressBook while the code (and the legacy schema) use
    abook_id, so a new company could not be found by id until the next start filled a copy of it.

    Rebuild AddressBook with abook_id as the key, keeping every id (so the links from the fax numbers and
    e-mail contacts stay valid), and fill the link columns of the two child tables from their old copies.
    """
    if _primary_key_columns(db, "AddressBook") == ["ab_id"]:
        db.query("SELECT name FROM pragma_table_info('AddressBook')")
        old = {r["name"] for r in db.get_records()}
        selects = ["COALESCE(abook_id, ab_id)" if "abook_id" in old else "ab_id"] + [
            c if c in old else "NULL" for c in _ADDRESS_BOOK_COLUMNS]
        db.query("DROP TABLE IF EXISTS AddressBook_rebuild")
        db.query("CREATE TABLE AddressBook_rebuild (abook_id INTEGER PRIMARY KEY AUTOINCREMENT, "
                 + ", ".join(f"{c} TEXT" for c in _ADDRESS_BOOK_COLUMNS) + ")")
        db.query("INSERT INTO AddressBook_rebuild (abook_id, " + ", ".join(_ADDRESS_BOOK_COLUMNS) + ") SELECT "
                 + ", ".join(selects) + " FROM AddressBook")
        db.query("DROP TABLE AddressBook")
        db.query("ALTER TABLE AddressBook_rebuild RENAME TO AddressBook")
    for table in ("AddressBookFAX", "AddressBookEmail"):
        if _has_column(db, table, "ab_id"):
            db.query(f"UPDATE {table} SET abook_id = ab_id WHERE abook_id IS NULL AND ab_id IS NOT NULL")
    if _has_column(db, "AddressBookEmail", "to_person"):
        db.query("UPDATE AddressBookEmail SET contact_name = to_person WHERE contact_name IS NULL")
    if _has_column(db, "AddressBookEmail", "email"):
        db.query("UPDATE AddressBookEmail SET contact_email = email WHERE contact_email IS NULL")


def _rename_user_passwords_columns(db: DatabaseEngine) -> None:
    """Older port versions created UserPasswords(pwd_id, uid, password, date) while the service uses the
    legacy names (upid, uid, pwdhash), so nothing was ever stored. Rename the columns in place."""
    db.query("SELECT name FROM pragma_table_info('UserPasswords')")
    columns = {r["name"] for r in db.get_records()}
    if "pwd_id" in columns and "upid" not in columns:
        db.query("ALTER TABLE UserPasswords RENAME COLUMN pwd_id TO upid")
    if "password" in columns and "pwdhash" not in columns:
        db.query("ALTER TABLE UserPasswords RENAME COLUMN password TO pwdhash")


def _apply_schema_migrations(db: DatabaseEngine) -> None:
    """Apply column and view migrations for legacy database compatibility."""
    # 1. DIDRoute / DIDRouting
    db.query("SELECT name FROM sqlite_master WHERE type='table' AND name='DIDRouting'")
    if db.get_records():
        db.query("SELECT name FROM sqlite_master WHERE type='table' AND name='DIDRoute'")
        if not db.get_records():
            db.query("ALTER TABLE DIDRouting RENAME TO DIDRoute")
    db.query("CREATE VIEW IF NOT EXISTS DIDRouting AS SELECT * FROM DIDRoute")

    # 2. FaxCategory / FaxPDFCategory
    db.query("SELECT name FROM sqlite_master WHERE type='table' AND name='FaxPDFCategory'")
    if db.get_records():
        db.query("SELECT name FROM sqlite_master WHERE type='table' AND name='FaxCategory'")
        if not db.get_records():
            db.query("ALTER TABLE FaxPDFCategory RENAME TO FaxCategory")
    db.query("CREATE VIEW IF NOT EXISTS FaxPDFCategory AS SELECT * FROM FaxCategory")

    # 3. AddressBookEmail columns
    for col in ['abookemail_id INTEGER', 'contact_name TEXT', 'contact_email TEXT', 'abook_id INTEGER']:
        try:
            db.query(f"ALTER TABLE AddressBookEmail ADD COLUMN {col}")
        except Exception:
            pass

    # 3-2. AddressBookFAX columns
    for col in ['email TEXT', 'printer TEXT', 'faxcatid INTEGER', 'description TEXT', 'faxfrom INTEGER DEFAULT 0', 'faxto INTEGER DEFAULT 0']:
        try:
            db.query(f"ALTER TABLE AddressBookFAX ADD COLUMN {col}")
        except Exception:
            pass

    # 3-3. BarcodeRoute barcode_id column
    try:
        db.query("ALTER TABLE BarcodeRoute ADD COLUMN barcode_id INTEGER")
    except Exception:
        pass

    # 3-4. DynConf (the port once kept an unused twin table "DynamicConfig"; it is no longer created)
    db.query("CREATE TABLE IF NOT EXISTS DynConf (dynconf_id INTEGER PRIMARY KEY AUTOINCREMENT, device TEXT, callid TEXT NOT NULL)")


    # 5. FaxArchive legacy columns
    fax_archive_cols = [
        "faxpath TEXT",
        "faxnumid INTEGER",
        "companyid INTEGER",
        "faxcatid INTEGER",
        "didr_id INTEGER",
        "lastoperation TEXT",
        "lastmoduser INTEGER",
        "lastmoddate TEXT",
        "archstamp TEXT",
        "modemdev TEXT",
        "userid INTEGER",
        "origfaxnum TEXT",
        "faxcontent TEXT",
    ]
    for col in fax_archive_cols:
        try:
            db.query(f"ALTER TABLE FaxArchive ADD COLUMN {col}")
        except Exception:
            pass


def seed_database_if_empty(db: DatabaseEngine) -> None:
    """Provide default records and, in a brand-new database, demo records.

    Runs on every application start, so it must never alter data that already exists:
    * default cover pages and fax categories are added only while their table is empty;
    * demo data (users, address book, faxes, routes, ...) is added only when there are no users yet.
    """
    res = db.query("SELECT COUNT(*) as cnt FROM UserAccount")
    brand_new = bool(res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0)
    _seed_default_records(db)
    if brand_new:
        _seed_demo_records(db)


def _seed_default_records(db: DatabaseEngine) -> None:
    """Default cover pages and fax categories, only while the table is empty."""
    res = db.query("SELECT COUNT(*) as cnt FROM FaxCategory")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query("INSERT OR IGNORE INTO FaxCategory (catid, name) VALUES (1, 'General')")
        db.query("INSERT OR IGNORE INTO FaxCategory (catid, name) VALUES (2, 'Invoices')")
        db.query("INSERT OR IGNORE INTO FaxCategory (catid, name) VALUES (3, 'Legal')")

    res = db.query("SELECT COUNT(*) as cnt FROM CoverPages")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query("INSERT OR IGNORE INTO CoverPages (cover_id, title, file) VALUES (1, 'standard', 'standard.ps')")
        db.query("INSERT OR IGNORE INTO CoverPages (cover_id, title, file) VALUES (2, 'urgent', 'urgent.ps')")


def _seed_demo_records(db: DatabaseEngine) -> None:
    """Demo data for a brand-new database (development and the test suites)."""
    # 1. UserAccount
    res = db.query("SELECT COUNT(*) as cnt FROM UserAccount")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT INTO UserAccount (uid, name, username, password, email, superuser, is_admin, can_del, any_modem, acc_enabled) "
            "VALUES (1, 'System Administrator', 'admin', '5f4dcc3b5aa765d61d8327deb882cf99', 'admin@namifax.local', 1, 1, 1, 1, 1)"
        )
        db.query(
            "INSERT INTO UserAccount (uid, name, username, password, email, superuser, is_admin, can_del, any_modem, acc_enabled) "
            "VALUES (2, 'Operator User', 'operator', '5f4dcc3b5aa765d61d8327deb882cf99', 'operator@namifax.local', 0, 0, 0, 1, 1)"  # gitleaks:allow
        )

    # 2. Modems
    res = db.query("SELECT COUNT(*) as cnt FROM Modems")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) < 2:
        db.query(
            "INSERT OR IGNORE INTO Modems (devid, device, alias, contact, printer) "
            "VALUES (1, 'ttyS0', 'Sales Inbound', 'sales@avantfax.local', 'lp1')"
        )
        db.query(
            "INSERT OR IGNORE INTO Modems (devid, device, alias, contact, printer) "
            "VALUES (2, 'ttyS1', 'Support Outbound', 'support@avantfax.local', 'lp2')"
        )

    # 3. DIDRoute
    res = db.query("SELECT COUNT(*) as cnt FROM DIDRoute")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) < 2:
        db.query(
            "INSERT OR IGNORE INTO DIDRoute (didr_id, routecode, alias, contact, printer) "
            "VALUES (1, '1000', 'Main Trunk', 'sales@namifax.local', 'lp_sales')"
        )
        db.query(
            "INSERT OR IGNORE INTO DIDRoute (didr_id, routecode, alias, contact, printer) "
            "VALUES (2, '1001', 'Accounting Direct', 'billing@namifax.local', 'lp_billing')"
        )

    # 4. BarcodeRoute
    res = db.query("SELECT COUNT(*) as cnt FROM BarcodeRoute")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT INTO BarcodeRoute (barcode_id, bcr_id, barcode, alias, contact, printer) "
            "VALUES (1, 1, 'BC-1001', 'Sales Barcode', 'sales@company.com', 'HPLaserJet')"
        )

    # 6-1. DynConf demo rule: only into an empty table, never over the administrator's rules
    res = db.query("SELECT COUNT(*) as cnt FROM DynConf")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query("INSERT INTO DynConf (dynconf_id, callid, device) VALUES (1, '01012345678', 'ttyS0')")

    # 7. AddressBook
    res = db.query("SELECT COUNT(*) as cnt FROM AddressBook WHERE company = 'Acme Corp' OR company = 'Acme Global'")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT INTO AddressBook (company, faxnum, phonenum, email, address, city, state, zip) "
            "VALUES ('Acme Corp', '1234567', '555-0100', 'info@acmeglobal.com', '100 Enterprise Way', 'Metropolis', 'CA', '90210')"
        )
        res_ins = db.query("SELECT abook_id FROM AddressBook WHERE company = 'Acme Corp'")
        acme_id = db.get_records()[0].get("abook_id") if db.get_records() else 1
        db.query(
            f"INSERT OR IGNORE INTO AddressBookFAX (abookfax_id, abook_id, faxnumber, to_person, email, printer) "
            f"VALUES (1, {acme_id}, '1234567', 'Acme Main', 'faxes@acme.com', 'OfficePrinter')"
        )
        db.query(
            f"INSERT OR IGNORE INTO AddressBookEmail (abookemail_id, abook_id, contact_name, contact_email) "
            f"VALUES (1, {acme_id}, 'Jane Doe', 'jane@example.com')"
        )

    res = db.query("SELECT COUNT(*) as cnt FROM AddressBook WHERE company = 'Initech Corp'")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT INTO AddressBook (company, faxnum, phonenum, email, address, city, state, zip) "
            "VALUES ('Initech Corp', '9876543', '555-0200', 'contact@initech.com', '200 Tech Park', 'Silicon Valley', 'CA', '94025')"
        )
        res_ins = db.query("SELECT abook_id FROM AddressBook WHERE company = 'Initech Corp'")
        initech_id = db.get_records()[0].get("abook_id") if db.get_records() else 2
        db.query(
            f"INSERT OR IGNORE INTO AddressBookFAX (abookfax_id, abook_id, faxnumber, to_person, email, printer) "
            f"VALUES (2, {initech_id}, '9876543', 'Initech Main', 'faxes@cyberdyne.com', 'MainLaser')"
        )
        db.query(
            f"INSERT OR IGNORE INTO AddressBookEmail (abookemail_id, abook_id, contact_name, contact_email) "
            f"VALUES (2, {initech_id}, 'John Smith', 'user@example.com')"
        )

    # 8. DistroList
    res = db.query("SELECT COUNT(*) as cnt FROM DistroList")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT INTO DistroList (dl_id, listname, listdata, lastmod_date, lastmod_user) "
            "VALUES (1, 'Executive Team', '1234567; 9876543', '2026-09-29 10:00:00', 1)"
        )

    # 9. SysLog
    res = db.query("SELECT COUNT(*) as cnt FROM SysLog")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT INTO SysLog (logdate, logtext) "
            "VALUES ('2026-09-29 12:35:10', 'Fax job #12 dispatched to destination +1-555-0199: SUCCESS')"
        )
        db.query(
            "INSERT INTO SysLog (logdate, logtext) "
            "VALUES ('2026-09-29 12:40:22', 'User ''admin'' successfully authenticated from IP 127.0.0.1')"
        )

    # 10. FaxArchive (Inbox item & Archived item)
    res = db.query("SELECT COUNT(*) as cnt FROM FaxArchive WHERE inbox = 1")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT OR IGNORE INTO FaxArchive (fid, faxpath, faxnumid, companyid, origfaxnum, pages, modemdev, archstamp, description, inbox) "
            "VALUES (1, 'faxes/2026/09/29/fax001', 1, (SELECT abook_id FROM AddressBook WHERE company LIKE 'Acme%' LIMIT 1), '+1-555-0199', 2, 'ttyS0', '2026-09-29 10:00:00', 'Monthly Financial Report', 1)"
        )

    res_arc = db.query("SELECT COUNT(*) as cnt FROM FaxArchive WHERE inbox = 0")
    if res_arc.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT OR IGNORE INTO FaxArchive (fid, faxpath, faxnumid, companyid, origfaxnum, pages, modemdev, archstamp, description, inbox, faxcatid) "
            "VALUES (2, 'faxes/2026/09/29/fax002', 1, (SELECT abook_id FROM AddressBook WHERE company LIKE 'Acme%' LIMIT 1), '+1-555-0199', 2, 'ttyS0', '2026-09-29 09:30:00', 'Quarterly Financial Fax Transmission', 0, 1)"
        )

    # Ensure valid fixture files exist on disk for fid=1
    # Link the demo inbox fax to the demo company once both rows exist. On a brand-new database
    # the address book is seeded after the fax, so the link made earlier found no company.
    db.query(
        "UPDATE FaxArchive SET companyid = (SELECT abook_id FROM AddressBook WHERE company LIKE 'Acme%' LIMIT 1) "
        "WHERE fid = 1 AND companyid IS NULL"
    )
    db.query("UPDATE FaxArchive SET company = 'Acme Corp' WHERE fid = 1 AND company IS NULL")

    fax1_dir = os.path.join("faxes", "2026", "09", "29", "fax001")
    os.makedirs(fax1_dir, exist_ok=True)
    pdf_path = os.path.join(fax1_dir, "fax.pdf")
    if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
        with open(pdf_path, "wb") as f:
            f.write(
                b"%PDF-1.4\n"
                b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
                b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
                b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
                b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n"
            )
    tif_path = os.path.join(fax1_dir, "fax.tif")
    if not os.path.exists(tif_path) or os.path.getsize(tif_path) == 0:
        with open(tif_path, "wb") as f:
            f.write(b"II*\x00\x08\x00\x00\x00\x00\x00")

