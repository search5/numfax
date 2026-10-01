from unittest.mock import MagicMock, patch
import pytest
from pyramid.httpexceptions import HTTPFound
from pyramid.testing import DummyRequest

from namifax.views.saml import (
    saml_metadata_view,
    saml_login_view,
    saml_acs_view,
    saml_sls_view,
)

def test_saml_metadata_view():
    req = DummyRequest()
    req.db = MagicMock()
    with patch("namifax.views.saml.SAMLService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.generate_sp_metadata.return_value = "<md:EntityDescriptor/>"
        mock_svc_cls.return_value = mock_svc

        res = saml_metadata_view(req)
        assert res.status_code == 200
        assert res.content_type == "application/xml"
        assert "<md:EntityDescriptor/>" in res.text

def test_saml_login_view():
    req = DummyRequest()
    req.db = MagicMock()
    with patch("namifax.views.saml.SAMLService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.create_authn_request.return_value = {
            "redirect_url": "https://idp.example.com/sso?SAMLRequest=xyz"
        }
        mock_svc_cls.return_value = mock_svc

        res = saml_login_view(req)
        assert isinstance(res, HTTPFound)
        assert res.headers["Location"] == "https://idp.example.com/sso?SAMLRequest=xyz"

def test_saml_acs_view_success():
    req = DummyRequest(post={"SAMLResponse": "fake_b64_response", "RelayState": "/inbox"})
    req.db = MagicMock()
    req.session = {}
    with patch("namifax.views.saml.SAMLService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.process_saml_response.return_value = {
            "success": True,
            "name_id": "alice@corp.com",
            "attributes": {"displayName": "Alice Admin"},
        }
        mock_user = MagicMock()
        mock_user.get_username.return_value = "alice"
        mock_user.get_uid.return_value = 5
        mock_svc.provision_or_get_user.return_value = mock_user
        mock_svc_cls.return_value = mock_svc

        res = saml_acs_view(req)
        assert isinstance(res, HTTPFound)
        assert res.headers["Location"] == "/inbox"
        assert req.session.get("username") == "alice"
        assert req.session.get("uid") == 5

def test_saml_sls_view():
    req = DummyRequest()
    req.db = MagicMock()
    req.session = {"username": "alice", "uid": 5}
    res = saml_sls_view(req)
    assert isinstance(res, HTTPFound)
    assert req.session.get("username") is None
