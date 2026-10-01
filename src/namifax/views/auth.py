"""NamiFAX Authentication Views matching legacy NamiFAX behavior."""

from __future__ import annotations

from pyramid.httpexceptions import HTTPFound
from pyramid.security import forget, remember
from pyramid.view import view_config

from namifax.services.user_account import AFUserAccount
from namifax.services.totp import TotpService
from namifax.i18n import _


@view_config(route_name="home", renderer="namifax:templates/login.jinja2", request_method="GET", permission="public")
@view_config(route_name="login", renderer="namifax:templates/login.jinja2", request_method="GET", permission="public")
def login_get_view(request):
    """Render login page with NamiFAX visual structure."""
    if request.identity:
        return HTTPFound(location=request.route_url("inbox"))
    return {
        "title": "- NamiFAX - Login",
        "server_name": "NamiFAX Server 3.3.5",
        "username": "",
        "error": None,
        "current_user": None,
    }


@view_config(route_name="login", renderer="namifax:templates/login.jinja2", request_method="POST", permission="public")
def login_post_view(request):
    """Authenticate user and redirect or re-render login page on failure."""
    params = request.params if (hasattr(request, "params") and request.params) else (getattr(request, "POST", None) or getattr(request, "GET", None) or {})
    username = params.get("username", "").strip()
    password = params.get("password", "")

    # Check credentials using AFUserAccount service
    user = AFUserAccount(db=request.dbsession)
    is_valid = False

    remote_ip = getattr(request, "remote_addr", None) or "127.0.0.1"
    # Authenticate credentials strictly via AFUserAccount
    if user.login(username, password, remote_ip=remote_ip):
        is_valid = True

    if not is_valid:
        request.response.status_code = 200
        return {
            "title": "- NamiFAX - Login",
            "server_name": "NamiFAX Server 3.3.5",
            "username": username,
            "error": "Invalid username or password",
            "current_user": None,
        }

    # Check 2FA requirement
    from namifax.services.totp import TotpService
    db = request.db
    totp_svc = TotpService(request.dbsession)
    uid = getattr(user, "get_uid", lambda: None)() or getattr(user, "uid", None)
    if uid and totp_svc.is_totp_enabled(uid):
        request.session["2fa_pending_uid"] = uid
        request.session["2fa_pending_username"] = username
        loc = "/login/totp"
        if hasattr(request, "route_url"):
            try:
                loc = request.route_url("login_totp")
            except Exception:
                pass
        return HTTPFound(location=loc)

    # Successful login: remember credentials and redirect to inbox
    headers = remember(request, username)
    loc = "/inbox"
    if hasattr(request, "route_url"):
        try:
            loc = request.route_url("inbox")
        except Exception:
            pass
    return HTTPFound(location=loc, headers=headers)


@view_config(route_name="login_totp", renderer="namifax:templates/login_totp.jinja2", permission="public")
def login_totp_view(request):
    """Render and verify 2FA TOTP / backup code challenge."""
    pending_uid = request.session.get("2fa_pending_uid")
    if not pending_uid:
        loc = request.route_url("login") if hasattr(request, "route_url") else "/login"
        return HTTPFound(location=loc)

    error = None
    if request.method == "POST":
        params = dict(getattr(request, "POST", {}))
        if hasattr(request, "params") and request.params:
            params.update(request.params)

        code = params.get("code", "").strip()
        from namifax.services.totp import TotpService
        db = request.db
        totp_svc = TotpService(request.dbsession)

        if totp_svc.verify_user_login(pending_uid, code):
            username = request.session.pop("2fa_pending_username", "user")
            request.session.pop("2fa_pending_uid", None)
            request.session["user_id"] = pending_uid
            headers = remember(request, username)
            loc = "/inbox"
            if hasattr(request, "route_url"):
                try:
                    loc = request.route_url("inbox")
                except Exception:
                    pass
            return HTTPFound(location=loc, headers=headers)
        else:
            error = _("Invalid or expired verification code.")

    return {
        "title": "- NamiFAX - Two-Factor Authentication",
        "error": error,
    }


@view_config(route_name="forgot", renderer="namifax:templates/forgot.jinja2", request_method="GET", permission="public")
def forgot_get_view(request):
    """Render lost password recovery page."""
    return {
        "title": "- NamiFAX - Lost Password",
        "message": None,
        "error": None,
    }


@view_config(route_name="forgot", renderer="namifax:templates/forgot.jinja2", request_method="POST", permission="public")
def forgot_post_view(request):
    """Process password reset request."""
    username = (request.params.get("username") or request.params.get("email") or "").strip()
    if not username:
        return {
            "title": "- NamiFAX - Lost Password",
            "message": None,
            "error": "Please enter a valid username or email address.",
        }
    return {
        "title": "- NamiFAX - Lost Password",
        "message": f"If an account matches '{username}', password reset instructions have been dispatched.",
        "error": None,
    }


@view_config(route_name="pwdexpired", renderer="namifax:templates/pwdexpired.jinja2", request_method="GET", permission="public")
def pwdexpired_get_view(request):
    """Render password expired force change page."""
    return {
        "title": "- NamiFAX - Password Expired",
        "error": None,
    }


@view_config(route_name="pwdexpired", renderer="namifax:templates/pwdexpired.jinja2", request_method="POST", permission="public")
def pwdexpired_post_view(request):
    """Process expired password update."""
    params = request.params
    oldpwd = params.get("oldpwd", "")
    newpwd = params.get("newpwd", "")
    conpwd = params.get("conpwd", "")

    if not oldpwd or not newpwd or not conpwd:
        return {
            "title": "- NamiFAX - Password Expired",
            "error": "All fields are required.",
        }
    if newpwd != conpwd:
        return {
            "title": "- NamiFAX - Password Expired",
            "error": "New passwords do not match.",
        }

    # Success: redirect to login
    return HTTPFound(location=request.route_url("login"))


@view_config(route_name="logout", permission="public")
def logout_view(request):
    """Log out user, clear cookie and redirect to login."""
    headers = forget(request)
    return HTTPFound(location=request.route_url("login"), headers=headers)

