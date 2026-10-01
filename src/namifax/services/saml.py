from __future__ import annotations

import base64
import os
import urllib.parse
import uuid
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import defusedxml.ElementTree as ET

from namifax.db.engine import DatabaseEngine, resolve_db
from namifax.services.user_account import AFUserAccount

@dataclass
class SAMLSettings:
    enabled: bool = False
    idp_entity_id: str = ""
    idp_sso_url: str = ""
    idp_x509_cert: str = ""
    sp_entity_id: str = "http://localhost:8000/auth/saml/metadata"
    sp_acs_url: str = "http://localhost:8000/auth/saml/acs"
    sp_sls_url: str = "http://localhost:8000/auth/saml/sls"
    jit_provisioning: bool = True
    default_role: str = "user"

class SAMLService:
    """Enterprise SAML 2.0 Service Provider implementation."""

    def __init__(self, settings: SAMLSettings | None = None, db: DatabaseEngine | None = None) -> None:
        self.settings = settings or SAMLSettings()
        self.db = resolve_db(db, "SAMLService")

    def generate_sp_metadata(self) -> str:
        """Generate SP metadata XML."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
                     entityID="{self.settings.sp_entity_id}">
    <md:SPSSODescriptor AuthnRequestsSigned="false"
                        WantAssertionsSigned="false"
                        protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
        <md:SingleLogoutService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                                Location="{self.settings.sp_sls_url}"/>
        <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>
        <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified</md:NameIDFormat>
        <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                                     Location="{self.settings.sp_acs_url}"
                                     index="1"/>
    </md:SPSSODescriptor>
</md:EntityDescriptor>
""".strip()

    def create_authn_request(self, relay_state: str = "/") -> dict[str, str]:
        """Generate SAML 2.0 AuthnRequest and HTTP-Redirect parameters."""
        req_id = f"_{uuid.uuid4().hex}"
        issue_instant = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        xml_request = f"""<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                    ID="{req_id}"
                    Version="2.0"
                    IssueInstant="{issue_instant}"
                    Destination="{self.settings.idp_sso_url}"
                    AssertionConsumerServiceURL="{self.settings.sp_acs_url}"
                    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self.settings.sp_entity_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
                        AllowCreate="true"/>
</samlp:AuthnRequest>"""

        # Deflate compression for HTTP-Redirect binding (wbits=-15 for raw deflate)
        compressor = zlib.compressobj(wbits=-15)
        deflated = compressor.compress(xml_request.encode("utf-8")) + compressor.flush()
        b64_request = base64.b64encode(deflated).decode("ascii")

        params = {
            "SAMLRequest": b64_request,
            "RelayState": relay_state,
        }
        redirect_url = f"{self.settings.idp_sso_url}?{urllib.parse.urlencode(params)}" if self.settings.idp_sso_url else ""

        return {
            "request_id": req_id,
            "saml_request": b64_request,
            "relay_state": relay_state,
            "redirect_url": redirect_url,
        }

    def process_saml_response(self, saml_response_b64: str) -> dict[str, Any]:
        """Decode and parse SAML Response XML."""
        try:
            xml_bytes = base64.b64decode(saml_response_b64)
            root = ET.fromstring(xml_bytes)
        except Exception as e:
            return {"success": False, "error": f"Invalid SAML XML response: {e}"}

        # Namespaces
        namespaces = {
            "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
            "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
        }

        # Status check
        status_elem = root.find(".//samlp:StatusCode", namespaces)
        if status_elem is not None:
            status_val = status_elem.attrib.get("Value", "")
            if "Success" not in status_val:
                return {"success": False, "error": f"SAML Response status is {status_val}"}

        # Extract NameID
        name_id_elem = root.find(".//saml:Subject/saml:NameID", namespaces)
        name_id = name_id_elem.text.strip() if name_id_elem is not None and name_id_elem.text else ""

        # Extract Attributes
        attributes: dict[str, str] = {}
        for attr in root.findall(".//saml:AttributeStatement/saml:Attribute", namespaces):
            attr_name = attr.attrib.get("Name", "")
            val_elem = attr.find("saml:AttributeValue", namespaces)
            if attr_name and val_elem is not None and val_elem.text:
                attributes[attr_name] = val_elem.text.strip()

        return {
            "success": True,
            "name_id": name_id,
            "attributes": attributes,
        }

    def provision_or_get_user(
        self,
        name_id: str,
        attributes: dict[str, Any] | None = None,
    ) -> AFUserAccount | None:
        """Find user by NameID/email or provision new account if JIT is enabled."""
        attributes = attributes or {}
        username = name_id.split("@")[0] if "@" in name_id else name_id
        email = attributes.get("email") or (name_id if "@" in name_id else f"{username}@local")
        display_name = attributes.get("displayName") or attributes.get("name") or username

        user = AFUserAccount(db=self.db)
        if user.load_by_username(username):
            return user

        if self.settings.jit_provisioning:
            temp_pwd = base64.b64encode(os.urandom(12)).decode("ascii")
            if user.create_user(
                username=username,
                password=temp_pwd,
                name=display_name,
                email=email,
                is_admin=False,
            ):
                return user

        return None
