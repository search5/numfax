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
    """CREATE TABLE IF NOT EXISTS DIDRouting (
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
    """CREATE TABLE IF NOT EXISTS FaxPDFCategory (
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
    """CREATE TABLE IF NOT EXISTS AddressBookFax (
        fax_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ab_id INTEGER,
        faxnumber TEXT,
        description TEXT,
        to_person TEXT,
        to_location TEXT,
        to_voicenumber TEXT,
        default_num INTEGER DEFAULT 0
    );""",
    """CREATE TABLE IF NOT EXISTS AddressBookEmail (
        email_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ab_id INTEGER,
        email TEXT,
        description TEXT,
        to_person TEXT,
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
]


def init_database_tables(db: DatabaseEngine) -> bool:
    """Execute DDL statements to ensure all tables exist."""
    for stmt in SCHEMA_STATEMENTS:
        res = db.query(stmt)
        if not res.executed:
            return False
    return True
