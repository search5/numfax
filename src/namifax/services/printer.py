import os
import re
import socket
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from namifax.models.networkprinters import NetworkPrinters


@dataclass
class NetworkPrinter:
    id: int
    name: str
    protocol: str = "RAW"  # RAW, LPD, IPP
    host: str = "localhost"
    port: int = 9100
    queue_name: Optional[str] = None
    description: Optional[str] = None


class NetworkPrinterService:
    """Manages physical network printers and direct socket printing dispatch.

    Printers are stored through an ORM session, so the same code runs on SQLite, MySQL, MariaDB
    and PostgreSQL.
    """

    def __init__(self, session: Optional[Session] = None) -> None:
        self.session = session

    def _require_session(self) -> Session:
        if self.session is None:
            raise RuntimeError("NetworkPrinterService: no database session injected (pass request.dbsession)")
        return self.session

    def list_printers(self) -> List[NetworkPrinter]:
        rows = self._require_session().scalars(select(NetworkPrinters).order_by(NetworkPrinters.id.asc()))
        return [
            NetworkPrinter(
                id=int(r.id),
                name=r.name,
                protocol=r.protocol or "RAW",
                host=r.host,
                port=int(r.port or 9100),
                queue_name=r.queue_name,
                description=r.description,
            )
            for r in rows
        ]

    def create_printer(
        self,
        name: str,
        protocol: str = "RAW",
        host: str = "localhost",
        port: int = 9100,
        queue_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> int:
        session = self._require_session()
        printer = NetworkPrinters(
            name=name,
            protocol=protocol.upper(),
            host=host,
            port=int(port),
            queue_name=queue_name or None,
            description=description or None,
        )
        session.add(printer)
        session.flush()
        return int(printer.id)

    def delete_printer(self, printer_id: int) -> bool:
        """Delete a printer; True when a printer with that id existed."""
        session = self._require_session()
        printer = session.get(NetworkPrinters, int(printer_id))
        if printer is None:
            return False
        session.delete(printer)
        session.flush()
        return True

    def send_raw_print(self, host: str, port: int, data: bytes, timeout: int = 10) -> Dict[str, Any]:
        """Dispatch print stream directly to printer RAW 9100 socket."""
        try:
            with socket.create_connection((host, int(port)), timeout=timeout) as sock:
                sock.sendall(data)
            return {
                "success": True,
                "message": f"Successfully sent {len(data)} bytes to {host}:{port}",
            }
        except Exception as exc:
            return {
                "success": False,
                "message": f"Failed to send print job to {host}:{port} - {exc}",
            }

    def test_print(self, host: str, port: int, protocol: str = "RAW") -> Dict[str, Any]:
        """Generate and send an ASCII / PostScript test print page."""
        test_payload = (
            b"\x1b%-12345X@PJL\r\n"
            b"@PJL ENTER LANGUAGE = POSTSCRIPT\r\n"
            b"%!PS-Adobe-3.0\r\n"
            b"/Helvetica findfont 20 scalefont setfont\r\n"
            b"100 700 moveto\r\n"
            b"(NamiFAX Network Printer Diagnostic Page) show\r\n"
            b"/Helvetica findfont 12 scalefont setfont\r\n"
            b"100 660 moveto\r\n"
            b"(Test print successfully communicated over RAW 9100 socket.) show\r\n"
            b"showpage\r\n"
            b"\x1b%-12345X"
        )
        res = self.send_raw_print(host, port, test_payload)
        if res["success"]:
            res["message"] = f"Test print page dispatched successfully to {host}:{port}"
        return res


def extract_fax_tags(text_content: str) -> List[str]:
    """Parse embedded [[FAX: ...]] routing tags from print text stream."""
    pattern = r"\[\[FAX:\s*([\d\-\+\(\)\s]+)\]\]"
    matches = re.findall(pattern, text_content, flags=re.IGNORECASE)
    cleaned = [m.strip() for m in matches if m.strip()]
    return cleaned


def process_inbound_print_job(
    print_data: bytes,
    sender_user: str = "guest",
    db: Any = None,
) -> Dict[str, Any]:
    """Process inbound print stream from CUPS virtual queue and persist files."""
    import tempfile
    import uuid

    # Attempt text extraction from raw PostScript/Text stream
    text_content = ""
    try:
        text_content = print_data.decode("utf-8", errors="ignore")
    except Exception:
        pass

    fax_numbers = extract_fax_tags(text_content)

    tmp_dir = os.environ.get("NAMIFAX_TMPDIR") or tempfile.gettempdir()
    ext = ".ps" if print_data.startswith(b"%!PS") else ".pdf" if print_data.startswith(b"%PDF") else ".prn"
    job_token = uuid.uuid4().hex[:8]

    if fax_numbers:
        destination = fax_numbers[0]
        spool_dir = os.path.join(tmp_dir, "namifax_spool")
        os.makedirs(spool_dir, exist_ok=True)
        file_path = os.path.join(spool_dir, f"printjob_{job_token}_{sender_user}{ext}")
        with open(file_path, "wb") as f_out:
            f_out.write(print_data)

        return {
            "dispatched": True,
            "status": "QUEUED",
            "destination": destination,
            "sender": sender_user,
            "bytes_received": len(print_data),
            "file_path": file_path,
            "job_id": job_token,
        }
    else:
        # Fallback to web drafts repository
        drafts_dir = os.path.join(tmp_dir, "namifax_drafts")
        os.makedirs(drafts_dir, exist_ok=True)
        file_path = os.path.join(drafts_dir, f"draft_{job_token}_{sender_user}{ext}")
        with open(file_path, "wb") as f_out:
            f_out.write(print_data)

        return {
            "dispatched": False,
            "status": "DRAFT",
            "sender": sender_user,
            "bytes_received": len(print_data),
            "file_path": file_path,
            "message": "No [[FAX: ...]] tag found in print data. Saved to drafts for manual dispatch.",
        }
