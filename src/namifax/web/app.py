"""AvantFAX unified WSGI / HTTP web application router."""

from __future__ import annotations

import json
import urllib.parse
from typing import Any, Callable, Dict, List, Tuple

from namifax.web.session import SessionManager
from namifax.web.views.admin import AdminHandler
from namifax.web.views.archive import ArchiveHandler
from namifax.web.views.auth import AuthHandler
from namifax.web.views.inbox import InboxHandler
from namifax.web.views.outbox import OutboxHandler
from namifax.web.views.sendfax import SendFaxHandler


class AvantFaxApp:
    """Lightweight unified WSGI application router for AvantFAX."""

    def __init__(self) -> None:
        self.session_mgr = SessionManager()
        self.auth = AuthHandler(self.session_mgr)
        self.inbox = InboxHandler()
        self.outbox = OutboxHandler()
        self.archive = ArchiveHandler()
        self.sendfax = SendFaxHandler()
        self.admin = AdminHandler()

    def _get_bearer_token(self, environ: Dict[str, Any]) -> str:
        """Extract session token from Authorization header or cookie."""
        auth_header = environ.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        cookie_header = environ.get("HTTP_COOKIE", "")
        for item in cookie_header.split(";"):
            if "=" in item:
                k, v = item.strip().split("=", 1)
                if k == "avantfax_session":
                    return v
        return ""

    def __call__(
        self,
        environ: Dict[str, Any],
        start_response: Callable[[str, List[Tuple[str, str]]], None],
    ) -> List[bytes]:
        """WSGI request dispatcher."""
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET").upper()

        # Parse query params
        qs = environ.get("QUERY_STRING", "")
        query_params = {k: v[0] for k, v in urllib.parse.parse_qs(qs).items()}

        # Parse JSON body for POST/PUT
        body: Dict[str, Any] = {}
        if method in ("POST", "PUT"):
            try:
                content_length = int(environ.get("CONTENT_LENGTH", 0) or 0)
                if content_length > 0:
                    raw_body = environ["wsgi.input"].read(content_length)
                    body = json.loads(raw_body.decode("utf-8"))
            except Exception:
                body = {}

        token = self._get_bearer_token(environ)
        session = self.auth.check_login(token)

        # Route table
        status = "200 OK"
        headers = [("Content-Type", "application/json")]
        res: Dict[str, Any] = {}

        if path == "/api/health":
            res = {"status": "ok", "system": "AvantFAX Modernized"}

        elif path == "/api/auth/login" and method == "POST":
            res = self.auth.login(
                username=body.get("username", ""),
                password=body.get("password", ""),
                client_ip=environ.get("REMOTE_ADDR"),
            )
            if res.get("success"):
                headers.append(("Set-Cookie", f"avantfax_session={res['token']}; Path=/; HttpOnly"))
            else:
                status = "401 Unauthorized"

        elif path == "/api/auth/logout":
            self.auth.logout(token)
            res = {"success": True}
            headers.append(("Set-Cookie", "avantfax_session=; Path=/; Max-Age=0"))

        elif path == "/api/auth/check":
            if session:
                res = {
                    "authenticated": True,
                    "username": session.username,
                    "is_admin": session.is_admin,
                    "superuser": session.superuser,
                }
            else:
                status = "401 Unauthorized"
                res = {"authenticated": False}

        elif path.startswith("/api/"):
            if not session:
                status = "401 Unauthorized"
                res = {"error": "Authentication required"}
            elif path == "/api/inbox/list":
                page = int(query_params.get("page", 0))
                limit = int(query_params.get("limit", 10))
                res = self.inbox.list_inbox(session, page=page, limit=limit)
            elif path == "/api/outbox/queue":
                res = self.outbox.get_outbox_queue(session)
            elif path == "/api/archive/search":
                page = int(query_params.get("page", 0))
                limit = int(query_params.get("limit", 10))
                res = self.archive.search_archive(session, filters=query_params, page=page, limit=limit)
            elif path == "/api/sendfax/options":
                res = self.sendfax.get_sendfax_options(session)
            elif path == "/api/sendfax/send" and method == "POST":
                res = self.sendfax.send_fax(session, body, file_paths=[])
            elif path == "/api/admin/modems" and session.is_admin:
                res = {"modems": self.admin.list_modems()}
            elif path == "/api/admin/users" and session.is_admin:
                res = {"users": self.admin.list_users()}
            else:
                status = "404 Not Found"
                res = {"error": f"Endpoint not found: {path}"}

        else:
            status = "200 OK"
            headers = [("Content-Type", "text/plain; charset=utf-8")]
            start_response(status, headers)
            return [b"AvantFAX Modern Web System Ready\n"]

        payload = json.dumps(res, default=str).encode("utf-8")
        headers.append(("Content-Length", str(len(payload))))
        start_response(status, headers)
        return [payload]


def create_app() -> AvantFaxApp:
    """Application factory for WSGI / ASGI runners."""
    return AvantFaxApp()
