"""Unit tests for popup helper views and vCard upload views matching specs/web/25-popup-helpers.md."""

from unittest.mock import MagicMock
from pyramid import testing
import pytest

from namifax.views.helpers import (
    popup_distrolist_helper,
    popup_distro_contacts,
    popup_fax_contacts,
    popup_email_contacts,
    upload_email_contacts,
    upload_fax_contacts,
)


@pytest.fixture
def dummy_request(seeded_db):
    request = testing.DummyRequest()
    request.db = seeded_db
    request.session = {"user_id": 1, "username": "admin", "is_admin": True, "superuser": True}
    return request


def test_popup_distrolist_helper_get(dummy_request):
    """Verify GET renders distribution list helper popup form."""
    dummy_request.GET["dl_id"] = "1"
    res = popup_distrolist_helper(dummy_request)
    assert res.status_code == 200
    assert "Distribution List Helper" in res.text
    assert 'name="regexp"' in res.text
    assert 'name="myselect[]"' in res.text


def test_popup_distro_contacts_get(dummy_request):
    """Verify GET renders distro contacts selector popup."""
    res = popup_distro_contacts(dummy_request)
    assert res.status_code == 200
    assert "Distribution Contacts" in res.text
    assert 'name="regexp"' in res.text
    assert 'name="dl_id"' in res.text


def test_popup_fax_contacts_get(dummy_request):
    """Verify GET renders fax contacts selector popup."""
    res = popup_fax_contacts(dummy_request)
    assert res.status_code == 200
    assert "Fax Contacts" in res.text
    assert 'name="regexp"' in res.text
    assert 'name="myselect"' in res.text


def test_popup_email_contacts_get(dummy_request):
    """Verify GET renders email contacts selector popup."""
    res = popup_email_contacts(dummy_request)
    assert res.status_code == 200
    assert "Email Contacts" in res.text
    assert 'name="regexp"' in res.text
    assert 'name="abookemail_id"' in res.text


def test_upload_email_contacts_get(dummy_request):
    """Verify GET renders vCard email contact upload form."""
    res = upload_email_contacts(dummy_request)
    assert res.status_code == 200
    assert "Upload Email Contacts" in res.text
    assert 'type="file"' in res.text
    assert 'name="upload"' in res.text


def test_upload_fax_contacts_get(dummy_request):
    """Verify GET renders vCard fax contact upload form with categories."""
    res = upload_fax_contacts(dummy_request)
    assert res.status_code == 200
    assert "Upload Fax Contacts" in res.text
    assert 'type="file"' in res.text
    assert 'name="catid"' in res.text
