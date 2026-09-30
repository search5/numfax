"""NamiFAX SQLite schema initialization and table creation."""

from __future__ import annotations

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
        pwd_id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid INTEGER NOT NULL,
        password TEXT NOT NULL,
        date TEXT
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
        bcr_id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT NOT NULL UNIQUE,
        alias TEXT,
        contact TEXT,
        printer TEXT,
        faxcatid INTEGER
    );""",
    """CREATE TABLE IF NOT EXISTS DynamicConfig (
        dynconf_id INTEGER PRIMARY KEY AUTOINCREMENT,
        device TEXT NOT NULL,
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
        ab_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        fax_id INTEGER,
        abook_id INTEGER,
        ab_id INTEGER,
        faxnumber TEXT,
        to_person TEXT,
        default_num INTEGER DEFAULT 0
    );""",
    """CREATE TABLE IF NOT EXISTS AddressBookEmail (
        abookemail_id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id INTEGER,
        abook_id INTEGER,
        ab_id INTEGER,
        contact_name TEXT,
        to_person TEXT,
        contact_email TEXT,
        email TEXT,
        default_email INTEGER DEFAULT 0
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
]


def init_database_tables(db: DatabaseEngine) -> bool:
    """Execute DDL statements to ensure all tables exist."""
    for stmt in SCHEMA_STATEMENTS:
        res = db.query(stmt)
        if not res.executed:
            return False
    _apply_schema_migrations(db)
    seed_database_if_empty(db)
    return True


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
    db.query("UPDATE AddressBookEmail SET contact_name = to_person WHERE contact_name IS NULL")
    db.query("UPDATE AddressBookEmail SET contact_email = email WHERE contact_email IS NULL")
    db.query("UPDATE AddressBookEmail SET abookemail_id = email_id WHERE abookemail_id IS NULL")
    db.query("UPDATE AddressBookEmail SET abook_id = ab_id WHERE abook_id IS NULL")

    # 3-1. AddressBook abook_id column
    try:
        db.query("ALTER TABLE AddressBook ADD COLUMN abook_id INTEGER")
    except Exception:
        pass
    db.query("UPDATE AddressBook SET abook_id = ab_id WHERE abook_id IS NULL")

    # 4. AddressBookFAX view
    db.query("SELECT name FROM sqlite_master WHERE name='AddressBookFAX'")
    if not db.get_records():
        db.query("CREATE VIEW AddressBookFAX AS SELECT fax_id AS abookfax_id, ab_id AS abook_id, * FROM AddressBookFax")

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
    db.query("UPDATE FaxArchive SET archstamp = archivetime WHERE archstamp IS NULL AND archivetime IS NOT NULL")
    db.query("UPDATE FaxArchive SET modemdev = 'ttyS0' WHERE modemdev IS NULL")
    db.query("UPDATE FaxArchive SET companyid = (SELECT abook_id FROM AddressBook WHERE company LIKE 'Acme%' LIMIT 1) WHERE fid = 1")
    db.query("UPDATE FaxArchive SET company = 'Acme Corp' WHERE fid = 1")
    db.query("UPDATE FaxArchive SET faxnumid = 1 WHERE faxnumid IS NULL")


def seed_database_if_empty(db: DatabaseEngine) -> None:
    """Populate baseline fixture records into database if tables are empty."""
    # 1. UserAccount
    res = db.query("SELECT COUNT(*) as cnt FROM UserAccount")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT INTO UserAccount (uid, name, username, password, email, superuser, is_admin, can_del, any_modem, acc_enabled) "
            "VALUES (1, 'System Administrator', 'admin', 'password', 'admin@namifax.local', 1, 1, 1, 1, 1)"
        )
        db.query(
            "INSERT INTO UserAccount (uid, name, username, password, email, superuser, is_admin, can_del, any_modem, acc_enabled) "
            "VALUES (2, 'Operator User', 'operator', 'password', 'operator@namifax.local', 0, 0, 0, 1, 1)"
        )

    # 2. Modems
    res = db.query("SELECT COUNT(*) as cnt FROM Modems")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) < 2:
        db.query(
            "INSERT OR REPLACE INTO Modems (devid, device, alias, contact, printer) "
            "VALUES (1, 'ttyS0', 'Sales Inbound', 'sales@avantfax.local', 'lp1')"
        )
        db.query(
            "INSERT OR REPLACE INTO Modems (devid, device, alias, contact, printer) "
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
    else:
        db.query("UPDATE DIDRoute SET alias = 'Main Trunk' WHERE didr_id = 1")

    # 4. BarcodeRoute
    res = db.query("SELECT COUNT(*) as cnt FROM BarcodeRoute")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT INTO BarcodeRoute (bcr_id, barcode, alias, contact) "
            "VALUES (1, 'BC-001', 'Order Processing', 'orders@namifax.local')"
        )

    # 5. FaxCategory
    res = db.query("SELECT COUNT(*) as cnt FROM FaxCategory")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) < 2:
        db.query("INSERT OR IGNORE INTO FaxCategory (catid, name) VALUES (1, 'Invoices')")
        db.query("INSERT OR IGNORE INTO FaxCategory (catid, name) VALUES (2, 'Contracts')")

    # 6. CoverPages
    res = db.query("SELECT COUNT(*) as cnt FROM CoverPages")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query("INSERT INTO CoverPages (cover_id, title, file) VALUES (1, 'Standard Cover', 'cover.ps')")

    # 7. AddressBook
    res = db.query("SELECT COUNT(*) as cnt FROM AddressBook WHERE company = 'Acme Corp' OR company = 'Acme Global'")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT INTO AddressBook (company, faxnum, phonenum, email, address, city, state, zip) "
            "VALUES ('Acme Corp', '1234567', '555-0100', 'info@acmeglobal.com', '100 Enterprise Way', 'Metropolis', 'CA', '90210')"
        )
        res_ins = db.query("SELECT ab_id FROM AddressBook WHERE company = 'Acme Corp'")
        acme_id = db.get_records()[0].get("ab_id") if db.get_records() else 1
        db.query(
            f"INSERT OR REPLACE INTO AddressBookFAX (abookfax_id, fax_id, abook_id, ab_id, faxnumber, to_person, default_num) "
            f"VALUES (1, 1, {acme_id}, {acme_id}, '1234567', 'Acme Main', 1)"
        )
        db.query(
            f"INSERT OR REPLACE INTO AddressBookEmail (abookemail_id, email_id, abook_id, ab_id, contact_name, to_person, contact_email, email, default_email) "
            f"VALUES (1, 1, {acme_id}, {acme_id}, 'Jane Doe', 'Jane Doe', 'jane@example.com', 'jane@example.com', 1)"
        )
    else:
        db.query("UPDATE AddressBook SET company = 'Acme Corp' WHERE company = 'Acme Global'")

    res = db.query("SELECT COUNT(*) as cnt FROM AddressBook WHERE company = 'Initech Corp'")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT INTO AddressBook (company, faxnum, phonenum, email, address, city, state, zip) "
            "VALUES ('Initech Corp', '9876543', '555-0200', 'contact@initech.com', '200 Tech Park', 'Silicon Valley', 'CA', '94025')"
        )
        res_ins = db.query("SELECT ab_id FROM AddressBook WHERE company = 'Initech Corp'")
        initech_id = db.get_records()[0].get("ab_id") if db.get_records() else 2
        db.query(
            f"INSERT OR REPLACE INTO AddressBookFAX (abookfax_id, fax_id, abook_id, ab_id, faxnumber, to_person, default_num) "
            f"VALUES (2, 2, {initech_id}, {initech_id}, '9876543', 'Initech Main', 1)"
        )
        db.query(
            f"INSERT OR REPLACE INTO AddressBookEmail (abookemail_id, email_id, abook_id, ab_id, contact_name, to_person, contact_email, email, default_email) "
            f"VALUES (2, 2, {initech_id}, {initech_id}, 'John Smith', 'John Smith', 'user@example.com', 'user@example.com', 1)"
        )

    # 8. DistroList
    res = db.query("SELECT COUNT(*) as cnt FROM DistroList")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT INTO DistroList (dl_id, listname, listdata, lastmod_date, lastmod_user) "
            "VALUES (1, 'Executive Team', '1234567; 9876543', '2026-09-29 10:00:00', 1)"
        )
    else:
        db.query("UPDATE DistroList SET listname = 'Executive Team' WHERE dl_id = 1")

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

    # 10. FaxArchive (Inbox item)
    res = db.query("SELECT COUNT(*) as cnt FROM FaxArchive WHERE inbox = 1")
    if res.executed and db.get_records() and db.get_records()[0].get("cnt", 0) == 0:
        db.query(
            "INSERT OR REPLACE INTO FaxArchive (fid, faxpath, faxnumid, companyid, origfaxnum, pages, modemdev, archstamp, description, inbox) "
            "VALUES (1, 'faxes/2026/09/29/fax001', 1, (SELECT abook_id FROM AddressBook WHERE company LIKE 'Acme%' LIMIT 1), '+1-555-0199', 2, 'ttyS0', '2026-09-29 10:00:00', 'Monthly Financial Report', 1)"
        )
    else:
        db.query(
            "UPDATE FaxArchive SET "
            "faxpath = COALESCE(faxpath, 'faxes/2026/09/29/fax001'), "
            "faxnumid = COALESCE(faxnumid, 1), "
            "companyid = (SELECT abook_id FROM AddressBook WHERE company LIKE 'Acme%' LIMIT 1), "
            "origfaxnum = COALESCE(origfaxnum, '+1-555-0199'), "
            "pages = COALESCE(pages, 2), "
            "modemdev = COALESCE(modemdev, 'ttyS0'), "
            "archstamp = COALESCE(archstamp, '2026-09-29 10:00:00'), "
            "description = COALESCE(description, 'Monthly Financial Report'), "
            "inbox = 1 "
            "WHERE fid = 1"
        )

