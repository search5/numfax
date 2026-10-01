from __future__ import annotations

from pyramid.httpexceptions import HTTPFound
from pyramid.request import Request
from pyramid.security import remember
from pyramid.response import Response
from pyramid.view import view_config

from namifax.services.saml import SAMLService, SAMLSettings
from namifax.services.user_account import AFUserAccount

def _get_saml_service(request: Request) -> SAMLService:
    base_url = request.application_url if hasattr(request, "application_url") else "http://localhost:8000"
    settings = SAMLSettings(
        enabled=True,
        sp_entity_id=f"{base_url}/auth/saml/metadata",
        sp_acs_url=f"{base_url}/auth/saml/acs",
        sp_sls_url=f"{base_url}/auth/saml/sls",
    )
    return SAMLService(settings, db=request.dbsession)

def _safe_relay(target: str) -> str:
    """Only paths on this site; ``RelayState`` comes from the browser and must not become an open redirect."""
    return target if target.startswith("/") and not target.startswith("//") and "\\" not in target else "/inbox"


@view_config(route_name="saml_metadata")
def saml_metadata_view(request: Request) -> Response:
    svc = _get_saml_service(request)
    xml_content = svc.generate_sp_metadata()
    return Response(
        xml_content,
        content_type="application/xml",
        charset="utf-8",
    )

@view_config(route_name="saml_login")
def saml_login_view(request: Request) -> Response:
    svc = _get_saml_service(request)
    relay_state = request.params.get("relay_state", "/inbox")
    req_data = svc.create_authn_request(relay_state=relay_state)
    target_url = req_data.get("redirect_url") or "/login"
    return HTTPFound(location=target_url)

@view_config(route_name="saml_acs", request_method="POST")
def saml_acs_view(request: Request) -> Response:
    saml_response = request.POST.get("SAMLResponse") or request.params.get("SAMLResponse")
    relay_state = request.POST.get("RelayState") or request.params.get("RelayState") or "/inbox"

    if not saml_response:
        return HTTPFound(location="/login?error=missing_saml_response")

    svc = _get_saml_service(request)
    result = svc.process_saml_response(saml_response)
    if not result.get("success"):
        return HTTPFound(location=f"/login?error={result.get('error', 'saml_failed')}")

    user = svc.provision_or_get_user(
        name_id=result.get("name_id", ""),
        attributes=result.get("attributes"),
    )
    if not user:
        return HTTPFound(location="/login?error=user_provision_failed")

    # sign in like the password login does: the same checks (disabled account) and the same token cookie
    username = user.get_username()
    remote_ip = getattr(request, "remote_addr", None) or "127.0.0.1"
    if not AFUserAccount(db=request.dbsession).login_webauth(username, remote_ip=remote_ip):
        return HTTPFound(location="/login?error=account_disabled")

    return HTTPFound(location=_safe_relay(relay_state), headers=remember(request, username))

@view_config(route_name="saml_sls")
def saml_sls_view(request: Request) -> Response:
    if hasattr(request, "session"):
        request.session.clear()
        if hasattr(request.session, "changed"):
            request.session.changed()
    return HTTPFound(location="/login")
