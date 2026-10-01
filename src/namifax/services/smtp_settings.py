import os
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
from typing import Any, Dict, List, Optional
from namifax.db.engine import DatabaseEngine, resolve_db


@dataclass
class SmtpConfig:
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_security: str = "NONE"  # NONE, STARTTLS, SSL
    smtp_auth: bool = False
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: str = "root@localhost"
    from_name: str = "NamiFAX"
    email_sig_text: str = ""
    email_sig_html: str = ""
    updated_at: Optional[str] = None


@dataclass
class SmtpTestResult:
    success: bool
    message: str
    details: List[str] = field(default_factory=list)


class SmtpSettingsService:
    """Manages enterprise SMTP gateway configuration and connectivity diagnostics."""

    def __init__(self, db: Optional[DatabaseEngine] = None) -> None:
        self.db = resolve_db(db, "SmtpSettingsService")

    def get_settings(self) -> SmtpConfig:
        res = self.db.query(
            "SELECT smtp_host, smtp_port, smtp_security, smtp_auth, "
            "smtp_username, smtp_password, from_email, from_name, "
            "email_sig_text, email_sig_html, updated_at "
            "FROM SystemSettings WHERE id = 1"
        )
        records = self.db.get_records()
        if not records:
            return SmtpConfig()

        row = records[0]
        return SmtpConfig(
            smtp_host=row.get("smtp_host") or "localhost",
            smtp_port=int(row.get("smtp_port") or 25),
            smtp_security=row.get("smtp_security") or "NONE",
            smtp_auth=bool(row.get("smtp_auth")),
            smtp_username=row.get("smtp_username"),
            smtp_password=row.get("smtp_password"),
            from_email=row.get("from_email") or "root@localhost",
            from_name=row.get("from_name") or "NamiFAX",
            email_sig_text=row.get("email_sig_text") or "",
            email_sig_html=row.get("email_sig_html") or "",
            updated_at=row.get("updated_at"),
        )

    def save_settings(self, data: Dict[str, Any]) -> bool:
        port = int(data.get("smtp_port", 25))
        if port < 1 or port > 65535:
            raise ValueError(f"Invalid SMTP port: {port}. Port must be between 1 and 65535.")

        security = str(data.get("smtp_security", "NONE")).upper()
        if security not in ("NONE", "STARTTLS", "SSL"):
            security = "NONE"

        auth_val = data.get("smtp_auth", False)
        auth = False
        if isinstance(auth_val, str):
            auth = auth_val.lower() in ("1", "true", "on", "yes")
        elif isinstance(auth_val, (int, bool)):
            auth = bool(auth_val)

        host = str(data.get("smtp_host", "localhost")).strip()
        username = data.get("smtp_username") or ""
        password = data.get("smtp_password") or ""
        from_email = str(data.get("from_email", "root@localhost")).strip()
        from_name = str(data.get("from_name", "NamiFAX")).strip()
        sig_text = data.get("email_sig_text", "") or ""
        sig_html = data.get("email_sig_html", "") or ""
        now_str = datetime.now().isoformat()

        # Check existing
        self.db.query("SELECT id FROM SystemSettings WHERE id = 1")
        if self.db.get_records():
            sql = (
                f"UPDATE SystemSettings SET "
                f"smtp_host = {self.db.quote(host)}, "
                f"smtp_port = {port}, "
                f"smtp_security = {self.db.quote(security)}, "
                f"smtp_auth = {1 if auth else 0}, "
                f"smtp_username = {self.db.quote(username)}, "
                f"smtp_password = {self.db.quote(password)}, "
                f"from_email = {self.db.quote(from_email)}, "
                f"from_name = {self.db.quote(from_name)}, "
                f"email_sig_text = {self.db.quote(sig_text)}, "
                f"email_sig_html = {self.db.quote(sig_html)}, "
                f"updated_at = {self.db.quote(now_str)} "
                f"WHERE id = 1"
            )
        else:
            sql = (
                f"INSERT INTO SystemSettings (id, smtp_host, smtp_port, smtp_security, smtp_auth, "
                f"smtp_username, smtp_password, from_email, from_name, email_sig_text, email_sig_html, updated_at) "
                f"VALUES (1, {self.db.quote(host)}, {port}, {self.db.quote(security)}, "
                f"{1 if auth else 0}, {self.db.quote(username)}, {self.db.quote(password)}, "
                f"{self.db.quote(from_email)}, {self.db.quote(from_name)}, "
                f"{self.db.quote(sig_text)}, {self.db.quote(sig_html)}, "
                f"{self.db.quote(now_str)})"
            )
        res = self.db.query(sql)
        return res.executed

    def test_connection(self, target_email: str, config: Optional[SmtpConfig] = None) -> SmtpTestResult:
        if config is None:
            config = self.get_settings()

        logs: List[str] = []
        host = config.smtp_host or "localhost"
        port = config.smtp_port or 25
        security = (config.smtp_security or "NONE").upper()

        logs.append(f"Initiating connection to {host}:{port} (Security: {security})...")

        try:
            if security == "SSL":
                ctx = ssl.create_default_context()
                server = smtplib.SMTP_SSL(host, port, context=ctx, timeout=10)
            else:
                server = smtplib.SMTP(host, port, timeout=10)

            with server as s:
                s.ehlo()
                logs.append("EHLO handshake successful.")

                if security == "STARTTLS":
                    logs.append("Starting STARTTLS handshake...")
                    ctx = ssl.create_default_context()
                    s.starttls(context=ctx)
                    s.ehlo()
                    logs.append("STARTTLS handshake verified.")

                if config.smtp_auth:
                    logs.append(f"Authenticating as {config.smtp_username}...")
                    s.login(config.smtp_username or "", config.smtp_password or "")
                    logs.append("Authentication accepted.")

                logs.append(f"Sending diagnostic message from {config.from_email} to {target_email}...")
                msg = EmailMessage()
                msg["Subject"] = "[NamiFAX] SMTP Gateway Diagnostic Test"
                msg["From"] = f"{config.from_name} <{config.from_email}>"
                msg["To"] = target_email
                msg.set_content(
                    "This is an automated diagnostic test message from NamiFAX Admin SMTP Gateway.\n"
                    "If you received this message, your external SMTP configuration is operational."
                )
                s.send_message(msg)
                logs.append("Diagnostic test email delivered successfully.")

            return SmtpTestResult(
                success=True,
                message=f"Successfully connected to {host}:{port} and delivered test email.",
                details=logs,
            )

        except Exception as exc:
            err_msg = str(exc)
            logs.append(f"Error during SMTP operation: {err_msg}")
            return SmtpTestResult(
                success=False,
                message=f"Failed to connect to SMTP server: {err_msg}",
                details=logs,
            )
