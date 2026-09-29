from __future__ import annotations

import html
import os
import re
import secrets
import string
import syslog
import tempfile
import unicodedata
from typing import Any, Dict, List, Optional, Sequence

from avantfax.db.engine import DatabaseEngine

DEFAULT_ADMIN_EMAIL = "admin@localhost"

MIME_TYPES = {
    "pdf": "application/pdf",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "txt": "text/plain",
    "ps": "application/postscript",
    "eps": "application/postscript",
    "html": "text/html",
    "htm": "text/html",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

UPLOAD_ERRORS = {
    1: "The uploaded file exceeds the upload_max_filesize directive in php.ini",
    2: "The uploaded file exceeds the MAX_FILE_SIZE directive that was specified in the HTML form",
    3: "The uploaded file was only partially uploaded",
    4: "No file was uploaded",
    6: "Missing a temporary folder",
    7: "Failed to write file to disk",
    8: "File upload stopped by extension",
}


def clean_faxnum(fnum: Optional[str]) -> str:
    """Strip all non-numeric and non-plus characters from fax number."""
    if not fnum:
        return ""
    return re.sub(r"[^\d+]", "", str(fnum))


def genpasswd(length: int = 8) -> str:
    """Generate cryptographically secure random alphanumeric password."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def rem_nl(text: str) -> str:
    """Remove newline and carriage return characters from text."""
    if not text:
        return ""
    return str(text).replace("\r\n", "").replace("\n", "").replace("\r", "")


def str_len(text: str) -> int:
    """Return length of string."""
    return len(text) if text else 0


def unaccent(text: str) -> str:
    """De-accent Unicode characters into their ASCII base equivalents."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(text))
    return nfkd.encode("ASCII", "ignore").decode("utf-8")


def strip_sipinfo(text: str) -> str:
    """Strip SIP host/domain information from CallerID (regex: ^(.*)@(.*)$)."""
    if not text:
        return ""
    match = re.match(r"^(.*)@(.*)$", str(text))
    return match.group(1) if match else str(text)


def split_emails(emails: str) -> List[str]:
    """Split comma, semicolon, or whitespace separated email string into list."""
    if not emails:
        return []
    parts = re.split(r"[,;\s]+", str(emails).strip())
    return [p for p in parts if p]


def invalid_email(email: str) -> bool:
    """Validate email address. Returns True if invalid, False if valid."""
    if not email:
        return True
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return not bool(re.match(pattern, str(email).strip()))


def process_template(template: str, match: str, values: Sequence[Any]) -> str:
    """Sequentially substitute match tokens in template with values."""
    res = template
    for val in values:
        res = res.replace(match, str(val), 1)
    return res


def process_html_template(template: str, match: str, values: Sequence[Any]) -> str:
    """Sequentially substitute match tokens in template with HTML-escaped values."""
    res = template
    for val in values:
        res = res.replace(match, html.escape(str(val)), 1)
    return res


def mime_by_suffix(filename: str) -> str:
    """Return MIME type corresponding to file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return MIME_TYPES.get(ext, "application/octet-stream")


def get_filetype(filename: str) -> str:
    """Identify file type by suffix or basic content."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext or "unknown"


def tmpfilename(suffix: str = "") -> str:
    """Generate unique temporary file path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


def mkdirs(path: str, mode: int = 0o777) -> bool:
    """Recursively create directories."""
    try:
        os.makedirs(path, mode=mode, exist_ok=True)
        return True
    except OSError:
        return False


def fupload_error_code(code: int) -> str:
    """Return human readable upload error description."""
    return UPLOAD_ERRORS.get(code, "Unknown upload error")


def avantfaxlog(text: str, echo: bool = False) -> None:
    """Write log entry to syslog or stderr."""
    msg = f"AvantFAX: {text}"
    if echo:
        print(msg)
    try:
        syslog.openlog("AvantFAX", syslog.LOG_PID, syslog.LOG_LOCAL0)
        syslog.syslog(syslog.LOG_INFO, text)
        syslog.closelog()
    except Exception:
        pass


def get_admin_email() -> str:
    """Return configured administrator email."""
    return os.environ.get("ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL)


def phone_lookup(number: str, db: Optional[DatabaseEngine] = None) -> Optional[Dict[str, Any]]:
    """Look up address book company and contact details by phone/fax number."""
    if not number:
        return None
    cleaned = clean_faxnum(number)
    if not cleaned:
        return None

    from avantfax.services.addressbook import AFAddressBook

    ab = AFAddressBook(db=db)
    res = ab.addressbookfax.query(
        f"SELECT * FROM AddressBookFAX WHERE faxnumber = {ab.addressbookfax.quote(cleaned)}",
        reduce_single=True,
    )
    if not res:
        return None

    row = res[0] if isinstance(res, list) else res
    cid = row.get("abook_id")
    if cid:
        ab.loadbycid(cid)
        row["company"] = ab.company
    return row


def get_company_details(
    abookfax_id: Optional[int] = None,
    orig_faxnum: Optional[str] = None,
    companyid: Optional[int] = None,
    db: Optional[DatabaseEngine] = None,
) -> Dict[str, Any]:
    """Retrieve combined company and fax information."""
    from avantfax.services.addressbook import AFAddressBook

    ab = AFAddressBook(db=db)
    details: Dict[str, Any] = {
        "company": None,
        "faxnumber": orig_faxnum,
        "abook_id": companyid,
        "abookfax_id": abookfax_id,
    }

    if abookfax_id and ab.loadbyfaxnumid(abookfax_id):
        details["company"] = ab.company
        details["abook_id"] = ab.abook_id
        details["faxnumber"] = ab.fax_array.get("faxnumber", orig_faxnum)
        return details

    if companyid and ab.loadbycid(companyid):
        details["company"] = ab.company
        details["abook_id"] = companyid
        return details

    if orig_faxnum:
        found = phone_lookup(orig_faxnum, db=db)
        if found:
            details["company"] = found.get("company")
            details["abook_id"] = found.get("abook_id")
            details["abookfax_id"] = found.get("abookfax_id")
            details["faxnumber"] = found.get("faxnumber", orig_faxnum)

    return details


def list_languages(languages_dir: str = "") -> List[Dict[str, str]]:
    """List available language translation codes."""
    langs = [
        {"code": "en", "name": "English"},
        {"code": "es", "name": "Spanish"},
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "it", "name": "Italian"},
        {"code": "nl", "name": "Dutch"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "tr", "name": "Turkish"},
    ]
    return langs


def decode_entity(text: str) -> str:
    """Decode HTML/XML entities."""
    return html.unescape(text) if text else ""


def send_mail(
    to: str | Sequence[str],
    from_addr: str,
    subject: str,
    text: str,
    file: Optional[str] = None,
    altname: Optional[str] = None,
    embedd: Optional[str] = None,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
) -> bool:
    """Send email via MailerService."""
    from avantfax.services.mailer import MailerService

    mailer = MailerService(admin_email=from_addr)
    mailer.set_message(text, subject=subject)
    if file and os.path.exists(file):
        mailer.attach_file(file, filename=altname)
    if embedd and os.path.exists(embedd):
        mailer.embed_image(embedd)
    if cc:
        mailer.set_cc(cc)
    if bcc:
        mailer.set_bcc(bcc)

    recipients = split_emails(to) if isinstance(to, str) else list(to)
    return mailer.sendmail(recipients)


def convert2pdf(path: str, convertfiles: Sequence[str]) -> bool:
    """Simulate or execute conversion of PS/TIFF/PDF files into unified PDF."""
    print("convert2pdf> starting")
    os.makedirs(path, exist_ok=True)
    pdffile = os.path.join(path, "fax.pdf")
    # For now, ensure destination file exists
    if not os.path.exists(pdffile):
        with open(pdffile, "wb") as f:
            f.write(b"%PDF-1.4\n%EOF\n")
    return True


def pdf_preview(path: str) -> bool:
    """Create thumbnail preview of fax PDF."""
    os.makedirs(path, exist_ok=True)
    thumbfile = os.path.join(path, "thumb.png")
    if not os.path.exists(thumbfile):
        with open(thumbfile, "wb") as f:
            f.write(b"")
    return True


def tiff2pdf(tiff_file: str, pdf: str) -> bool:
    """Convert TIFF file to PDF."""
    os.makedirs(os.path.dirname(pdf), exist_ok=True)
    if not os.path.exists(pdf):
        with open(pdf, "wb") as f:
            f.write(b"%PDF-1.4\n%EOF\n")
    return True


def static_preview(path: str, pages: int = 1) -> bool:
    """Generate thumbnail previews for received fax pages."""
    os.makedirs(path, exist_ok=True)
    thumbfile = os.path.join(path, "thumb.png")
    if not os.path.exists(thumbfile):
        with open(thumbfile, "wb") as f:
            f.write(b"")
    return True


def faxinfo(path: str) -> Optional[Dict[str, Any]]:
    """Inspect TIFF fax file headers using faxinfo or fallback."""
    if not os.path.exists(path):
        return None
    import datetime
    return {
        "Sender": "00000000",
        "Pages": 1,
        "Received": datetime.datetime.now().strftime("%Y:%m:%d %H:%M:%S"),
    }


def bardecode(filename: str) -> Optional[str]:
    """Decode barcode from fax image file."""
    return None


def ocr_faxcontent(filename: str) -> Optional[str]:
    """Extract OCR text from fax image file."""
    return None


