"""Email dispatching service replacing legacy Mailer.php and htmlMimeMail5.php."""

from __future__ import annotations

import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Sequence


class MailerService:
    """Modern Email service compatible with AvantFAX legacy semantics."""

    def __init__(
        self,
        smtp_server: str | None = None,
        smtp_port: int = 25,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        use_ssl: bool = False,
        use_tls: bool = False,
        admin_email: str = "root@localhost",
        email_sig_text: str = "",
        email_sig_html: str = "",
        spool_mode: bool = False,
    ) -> None:
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_ssl = use_ssl
        self.use_tls = use_tls
        self.admin_email = admin_email
        self.email_sig_text = email_sig_text
        self.email_sig_html = email_sig_html
        self.spool_mode = spool_mode

        self.last_error: str | None = None
        self._spooled_messages: list[EmailMessage] = []
        self._current_message: EmailMessage | None = None
        self._current_subject: str = "NamiFAX Notification"
        self._attachments: list[dict[str, Any]] = []
        self._embedded_images: list[dict[str, Any]] = []

    @classmethod
    def from_settings(cls, engine: Any = None) -> MailerService:
        if engine is None:
            return cls()
        try:
            from src.namifax.services.smtp_settings import SmtpSettingsService
            service = SmtpSettingsService(engine)
            cfg = service.get_settings()
            use_ssl = (cfg.smtp_security == "SSL")
            use_tls = (cfg.smtp_security == "STARTTLS")
            return cls(
                smtp_server=cfg.smtp_host,
                smtp_port=cfg.smtp_port,
                smtp_user=cfg.smtp_username if cfg.smtp_auth else None,
                smtp_password=cfg.smtp_password if cfg.smtp_auth else None,
                use_ssl=use_ssl,
                use_tls=use_tls,
                admin_email=cfg.from_email,
                email_sig_text=cfg.email_sig_text,
                email_sig_html=cfg.email_sig_html,
            )
        except Exception:
            return cls()

    def set_message(self, text: str, subject: str | None = None) -> None:
        """Construct multi-part plaintext and HTML message bodies."""
        if subject:
            self._current_subject = subject

        msg = EmailMessage()
        msg["Subject"] = self._current_subject
        msg["From"] = f"NamiFAX <{self.admin_email}>"

        # Plaintext body with signature
        full_text = text
        if self.email_sig_text:
            full_text = f"{text}\n\n\n\n{self.email_sig_text}"
        msg.set_content(full_text)

        # HTML alternative body
        converted = text.replace("\n", "<br />")
        sig_html = f"<br /><br />{self.email_sig_html}" if self.email_sig_html else ""
        html_body = f"<html><body>{converted}{sig_html}</body></html>"
        msg.add_alternative(html_body, subtype="html")

        self._current_message = msg

    def attach_file(self, file_path: str | Path, alt_name: str | None = None) -> bool:
        """Attach file to the current message."""
        path = Path(file_path)
        if not path.exists():
            self.last_error = f"Attachment file not found: {path}"
            return False

        filename = alt_name or path.name
        content_type, _ = mimetypes.guess_type(str(path))
        if not content_type:
            content_type = "application/octet-stream"

        main_type, sub_type = content_type.split("/", 1)
        data = path.read_bytes()

        self._attachments.append({
            "data": data,
            "maintype": main_type,
            "subtype": sub_type,
            "filename": filename,
        })
        return True

    def embed_image(self, image_path: str | Path, cid: str | None = None) -> bool:
        """Embed an inline image into HTML body."""
        path = Path(image_path)
        if not path.exists():
            self.last_error = f"Image file not found: {path}"
            return False

        cid = cid or path.name
        content_type, _ = mimetypes.guess_type(str(path))
        main_type, sub_type = (content_type or "image/jpeg").split("/", 1)

        self._embedded_images.append({
            "data": path.read_bytes(),
            "maintype": main_type,
            "subtype": sub_type,
            "cid": cid,
        })
        return True

    def sendmail(self, to: str | Sequence[str], subject: str | None = None) -> bool:
        """Dispatch email to recipient(s)."""
        self.last_error = None

        if not self._current_message:
            self.set_message("", subject=subject)

        if subject:
            if "Subject" in self._current_message:
                del self._current_message["Subject"]
            self._current_message["Subject"] = subject

        recipients = [to] if isinstance(to, str) else list(to)
        if "To" in self._current_message:
            del self._current_message["To"]
        self._current_message["To"] = ", ".join(recipients)

        # Attach files
        for att in self._attachments:
            self._current_message.add_attachment(
                att["data"],
                maintype=att["maintype"],
                subtype=att["subtype"],
                filename=att["filename"],
            )

        # Spool mode for unit testing and offline development
        if self.spool_mode or not self.smtp_server:
            self._spooled_messages.append(self._current_message)
            return True

        # SMTP dispatch
        try:
            server = (
                smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15)
                if self.use_ssl
                else smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15)
            )

            with server as client:
                if self.use_tls and not self.use_ssl:
                    client.starttls()
                if self.smtp_user and self.smtp_password:
                    client.login(self.smtp_user, self.smtp_password)
                client.send_message(self._current_message)
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def get_spooled_messages(self) -> list[EmailMessage]:
        return list(self._spooled_messages)

    def get_error(self) -> str | None:
        return self.last_error


# Legacy alias
Mailer = MailerService
