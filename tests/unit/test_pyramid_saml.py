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
    req.dbsession = MagicMock()
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
    req.dbsession = MagicMock()
    with patch("namifax.views.saml.SAMLService") as mock_svc_cls:
        mock_svc = MagicMock()
        mock_svc.create_authn_request.return_value = {
            "redirect_url": "https://idp.example.com/sso?SAMLRequest=xyz"
        }
        mock_svc_cls.return_value = mock_svc

        res = saml_login_view(req)
        assert isinstance(res, HTTPFound)
        assert res.headers["Location"] == "https://idp.example.com/sso?SAMLRequest=xyz"

def test_saml_acs_without_a_response_goes_back_to_login():
    req = DummyRequest(post={})
    res = saml_acs_view(req)
    assert isinstance(res, HTTPFound) and "missing_saml_response" in res.headers["Location"]


# The successful and the refused sign-ins run against a real application and database in
# test_sso_and_2fa_login.py (the mocked version here could not tell that nobody was actually logged in).


def test_saml_sls_view():
    req = DummyRequest()
    req.db = MagicMock()
    req.dbsession = MagicMock()
    req.session = {"username": "alice", "uid": 5}
    res = saml_sls_view(req)
    assert isinstance(res, HTTPFound)
    assert req.session.get("username") is None
