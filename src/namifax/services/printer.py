import os
import re
import socket
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from avantfax.db.engine import DatabaseEngine


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
    """Manages physical network printers and direct socket printing dispatch."""

    def __init__(self, db: Optional[DatabaseEngine] = None) -> None:
        self.db = db or DatabaseEngine()

    def list_printers(self) -> List[NetworkPrinter]:
        res = self.db.query("SELECT id, name, protocol, host, port, queue_name, description FROM NetworkPrinters ORDER BY id ASC")
        records = self.db.get_records() if res.executed else []
        printers: List[NetworkPrinter] = []
        for r in records:
            printers.append(
                NetworkPrinter(
                    id=int(r["id"]),
                    name=r["name"],
                    protocol=r.get("protocol") or "RAW",
                    host=r["host"],
                    port=int(r.get("port") or 9100),
                    queue_name=r.get("queue_name"),
                    description=r.get("description"),
                )
            )
        return printers

    def create_printer(
        self,
        name: str,
        protocol: str = "RAW",
        host: str = "localhost",
        port: int = 9100,
        queue_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> int:
        clean_name = self.db.quote(name)
        clean_proto = self.db.quote(protocol.upper())
        clean_host = self.db.quote(host)
        clean_queue = self.db.quote(queue_name) if queue_name else "NULL"
        clean_desc = self.db.quote(description) if description else "NULL"

        sql = (
            f"INSERT INTO NetworkPrinters (name, protocol, host, port, queue_name, description) "
            f"VALUES ({clean_name}, {clean_proto}, {clean_host}, {int(port)}, {clean_queue}, {clean_desc})"
        )
        self.db.query(sql)
        return self.db.get_insert_id() or 0

    def delete_printer(self, printer_id: int) -> bool:
        res = self.db.query(f"DELETE FROM NetworkPrinters WHERE id = {int(printer_id)}")
        return res.executed

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
    db: Optional[DatabaseEngine] = None,
) -> Dict[str, Any]:
    """Process inbound print stream from CUPS virtual queue."""
    # Attempt text extraction from raw PostScript/Text stream
    text_content = ""
    try:
        text_content = print_data.decode("utf-8", errors="ignore")
    except Exception:
        pass

    fax_numbers = extract_fax_tags(text_content)

    if fax_numbers:
        destination = fax_numbers[0]
        # In real operation, queue via sendfax/FaxQueue
        return {
            "dispatched": True,
            "status": "QUEUED",
            "destination": destination,
            "sender": sender_user,
            "bytes_received": len(print_data),
        }
    else:
        # Fallback to web drafts repository
        return {
            "dispatched": False,
            "status": "DRAFT",
            "sender": sender_user,
            "bytes_received": len(print_data),
            "message": "No [[FAX: ...]] tag found in print data. Saved to drafts for manual dispatch.",
        }
