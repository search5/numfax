"""AvantFAX Web Authentication view handler."""

from __future__ import annotations

from typing import Any, Dict, Optional

from avantfax.services.user_account import AFUserAccount
from avantfax.web.session import Session, SessionManager


class AuthHandler:
    """Handles web login, session validation, and logout."""

    def __init__(self, session_manager: Optional[SessionManager] = None) -> None:
        self.session_manager = session_manager or SessionManager()

    def login(
        self,
        username: str,
        password: str,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authenticate user against AFUserAccount and establish session."""
        user = AFUserAccount()
        if not user.login(username, password, remote_ip=client_ip or "127.0.0.1"):
            return {
                "success": False,
                "error": user.get_error() or "Login failed",
            }

        if user.is_expired():
            return {
                "success": False,
                "error": "Password expired",
                "pwd_expired": True,
            }

        sess = self.session_manager.create_session(
            user_id=user.get_uid(),
            username=user.username,
            is_admin=getattr(user, "is_admin", False),
            superuser=getattr(user, "superuser", False),
        )

        return {
            "success": True,
            "token": sess.token,
            "username": user.username,
            "user_id": user.get_uid(),
            "is_admin": sess.is_admin,
            "superuser": sess.superuser,
        }

    def check_login(self, token: Optional[str]) -> Optional[Session]:
        """Validate token and return session if active."""
        return self.session_manager.get_session(token)

    def logout(self, token: Optional[str]) -> bool:
        """Terminate active session."""
        return self.session_manager.destroy_session(token)
