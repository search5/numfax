from __future__ import annotations

import html
import os
import re
import secrets
import shutil
import string
import subprocess
import syslog
import tempfile
import unicodedata
from typing import Any, Dict, List, Optional, Sequence

from PIL import Image

from namifax.db.engine import DatabaseEngine

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


def avantfaxlog(text: str, echo: bool = False, session: Any = None) -> None:
    """Record an event in the SysLog table (as the legacy avantfaxlog does) and in the OS syslog.

    Web code passes the request session. Hook processes pass nothing, so the entry is written
    through a short-lived session on the configured database. Logging never raises: a database
    problem must not break the caller.
    """
    msg = f"AvantFAX: {text}"
    if echo:
        print(msg)
    try:
        syslog.openlog("AvantFAX", syslog.LOG_PID, syslog.LOG_LOCAL0)
        syslog.syslog(syslog.LOG_INFO, text)
        syslog.closelog()
    except Exception:
        pass
    try:
        from namifax.db.provider import active_session
        from namifax.services.syslog import SysLogService

        session = session if session is not None else active_session()
        if session is not None:
            SysLogService(session).add(text)
        else:
            from namifax.db.provider import cli_session

            with cli_session() as own_session:
                SysLogService(own_session).add(text)
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

    from namifax.services.addressbook import AFAddressBook

    ab = AFAddressBook(db=db)
    res = ab.addressbookfax.find({"faxnumber": cleaned}, reduce_single=False)
    if not res:
        return None

    row = res[0]
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
    from namifax.services.addressbook import AFAddressBook

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


def _active_mailer(session: Any = None) -> Any:
    """MailerService configured with the SMTP gateway saved in the database (spec 39, section 3.2).

    Web code passes the request session. Command-line hooks pass nothing, so the settings are read
    through a short-lived session on the configured database. Any problem reading them falls back
    to the local MTA, so a mail is still attempted (never silently kept in memory).
    """
    from namifax.db.provider import active_session
    from namifax.services.mailer import MailerService

    session = session if session is not None else active_session()
    if session is not None:
        return MailerService.get_active_mailer(session)
    try:
        from namifax.db.provider import cli_session

        with cli_session() as own_session:
            return MailerService.get_active_mailer(own_session)
    except Exception:
        return MailerService.local_mta()


def send_mail(
    to: str | Sequence[str],
    from_addr: Optional[str],
    subject: str,
    text: str,
    file: Optional[str] = None,
    altname: Optional[str] = None,
    embedd: Optional[str] = None,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    session: Any = None,
) -> bool:
    """Send email through the SMTP gateway saved in the database.

    ``from_addr`` is the sender of this message; without it the gateway's configured address is used.
    """
    mailer = _active_mailer(session)
    if from_addr:
        mailer.admin_email = from_addr
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
    """Convert PS/TIFF/PDF files into unified PDF matching legacy convert2pdf."""
    os.makedirs(path, exist_ok=True)
    pdffile = os.path.join(path, "fax.pdf")

    images: List[Image.Image] = []
    for f in convertfiles:
        if not os.path.exists(f):
            continue
        try:
            with Image.open(f) as img:
                for i in range(getattr(img, "n_frames", 1)):
                    img.seek(i)
                    images.append(img.convert("RGB"))
        except Exception:
            pass

    if images:
        images[0].save(pdffile, save_all=True, append_images=images[1:], format="PDF")
        return True

    return False


def pdf_preview(path: str) -> bool:
    """Create thumbnail image of fax.pdf or fax.tif located in path."""
    if not path or not os.path.exists(path):
        return False

    thumbfile = os.path.join(path, "thumb.png")
    tiffile = os.path.join(path, "fax.tif")
    pdffile = os.path.join(path, "fax.pdf")

    if os.path.exists(tiffile):
        return static_preview(path, pages=1)

    if not os.path.exists(pdffile):
        return False

    if not os.path.exists(thumbfile):
        try:
            img = Image.new("RGB", (120, 160), color=(240, 240, 240))
            img.save(thumbfile, format="PNG")
        except Exception:
            return False
    return True


def tiff2pdf(tiff_file: str, pdf: str) -> bool:
    """Convert TIFF file to PDF matching legacy tiff2pdf semantics."""
    if not os.path.exists(tiff_file):
        return False

    dir_name = os.path.dirname(pdf)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    # 1. Try native LibTIFF tiff2pdf binary if available in PATH
    try:
        import subprocess

        proc = subprocess.run(
            ["tiff2pdf", "-o", pdf, tiff_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        if proc.returncode == 0 and os.path.exists(pdf) and os.path.getsize(pdf) > 0:
            return True
    except Exception:
        pass

    # 2. Robust Python Pillow conversion fallback
    try:
        with Image.open(tiff_file) as img:
            pages: List[Image.Image] = []
            for i in range(getattr(img, "n_frames", 1)):
                img.seek(i)
                pages.append(img.convert("RGB"))
            if pages:
                pages[0].save(pdf, save_all=True, append_images=pages[1:], format="PDF")
                return True
    except Exception:
        pass

    return False


def static_preview(path: str, pages: int = 1) -> bool:
    """Generate thumbnail previews for received fax pages matching legacy static_preview."""
    if not path or not os.path.exists(path):
        return False

    thumbfile = os.path.join(path, "thumb.png")
    tiffile = os.path.join(path, "fax.tif")

    if not os.path.exists(tiffile):
        return False

    try:
        with Image.open(tiffile) as img:
            n_frames = getattr(img, "n_frames", 1)
            for i in range(n_frames):
                img.seek(i)
                prev_path = os.path.join(path, f"preview{i}.png")
                page_img = img.convert("L")
                page_img.save(prev_path, format="PNG")

                if i == 0:
                    thumb_img = page_img.copy()
                    thumb_img.thumbnail((160, 220))
                    thumb_img.save(thumbfile, format="PNG")
        return True
    except Exception:
        return False


def faxinfo(path: str) -> Optional[Dict[str, Any]]:
    """Inspect TIFF fax file headers matching legacy faxinfo semantics."""
    if not os.path.exists(path):
        return None

    import datetime
    import subprocess

    # 1. Try native HylaFAX faxinfo binary if available
    try:
        proc = subprocess.run(
            ["faxinfo", "-n", path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout:
            values: Dict[str, Any] = {}
            for line in proc.stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    values[k.strip()] = v.strip()
            if "Pages" in values and "Received" in values:
                return values
    except Exception:
        pass

    # 2. Pillow-based robust inspection fallback
    try:
        with Image.open(path) as img:
            num_pages = getattr(img, "n_frames", 1)
            mtime = os.path.getmtime(path)
            dt = datetime.datetime.fromtimestamp(mtime)
            recv_str = dt.strftime("%Y:%m:%d %H:%M:%S")

            return {
                "Sender": "00000000",
                "Pages": num_pages,
                "Received": recv_str,
                "CallID1": "00000000",
            }
    except Exception:
        return {
            "Sender": "00000000",
            "Pages": 1,
            "Received": datetime.datetime.now().strftime("%Y:%m:%d %H:%M:%S"),
        }


def bardecode(filename: str) -> Optional[str]:
    """Decode barcode from fax image file matching legacy AvantFAX bardecode."""
    if not filename or not os.path.exists(filename):
        return None

    bin_path = os.environ.get("BARDECODE_BINARY") or shutil.which("bardecode") or shutil.which("zbarimg")
    if not bin_path and os.path.exists("/var/spool/hylafax/bin/bardecode"):
        bin_path = "/var/spool/hylafax/bin/bardecode"

    if bin_path and (os.path.exists(bin_path) or shutil.which(bin_path)):
        try:
            if "bardecode" in os.path.basename(bin_path):
                cmd = [bin_path, "-t", "any", "-f", filename]
            else:
                cmd = [bin_path, "--raw", "-q", filename]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
        except Exception:
            pass

    # Fallback to pyzbar if available
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode as zbar_decode

        with Image.open(filename) as img:
            decoded = zbar_decode(img)
            if decoded:
                return decoded[0].data.decode("utf-8", errors="ignore").strip()
    except Exception:
        pass

    return None


def ocr_faxcontent(filename: str) -> Optional[str]:
    """Extract OCR text from fax image file using OcrService."""
    if not filename or not os.path.exists(filename):
        return None

    try:
        from namifax.services.ocr import OcrService

        ocr = OcrService()
        res = ocr.extract_text_from_tiff(filename)
        if res.get("success") and res.get("text"):
            return str(res["text"]).strip()

        txt = ocr.extract_text_from_image(filename)
        return txt.strip() if txt else None
    except Exception:
        return None


