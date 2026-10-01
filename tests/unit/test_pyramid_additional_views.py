"""Unit tests for additional legacy views: rotate, setcompany, emailbook, and ajax delete/archivebook."""

from unittest.mock import MagicMock, patch
from pyramid import testing
import pytest

from namifax.views.inbox import fax_rotate_view, setcompany_view
from namifax.views.addressbook import emailbook_list_view, emailbook_edit_view
from namifax.views.ajax import ajax_deletefaxes_view, ajax_archivebook_view


@pytest.fixture
def dummy_request(seeded_db, dbsession):
    request = testing.DummyRequest()
    request.db = seeded_db
    request.dbsession = dbsession
    request.__dict__["identity"] = {"username": "admin", "uid": 1, "is_admin": True, "superuser": True}
    request.route_url = MagicMock(side_effect=lambda name, *args, **kwargs: f"/{name}")
    return request


def test_rotate_view(dummy_request):
    """Verify fax rotate triggers ArchiveIn.rotate_fax."""
    dummy_request.db = MagicMock()
    dummy_request.params = {"fid": "42"}
    with patch("namifax.views.inbox.ArchiveIn") as mock_arc_cls:
        inst = MagicMock()
        inst.load_fax.return_value = True
        inst.rotate_fax.return_value = True
        mock_arc_cls.return_value = inst

        res = fax_rotate_view(dummy_request)
        inst.rotate_fax.assert_called()
        assert res.get("status") == "ok"
        assert res.get("fid") == "42"


def test_setcompany_view(dummy_request):
    """Verify setcompany assigns faxnumid and increments counter."""
    dummy_request.db = MagicMock()
    dummy_request.method = "POST"
    dummy_request.params = {"fid": "42", "faxnumid": "10"}
    with patch("namifax.views.inbox.ArchiveIn") as mock_arc_cls, \
         patch("namifax.views.inbox.AFAddressBook") as mock_ab_cls:
        inst_arc = MagicMock()
        inst_arc.load_fax.return_value = True
        mock_arc_cls.return_value = inst_arc

        inst_ab = MagicMock()
        inst_ab.loadbyfaxnumid.return_value = True
        mock_ab_cls.return_value = inst_ab

        res = setcompany_view(dummy_request)
        inst_arc.set_faxnumid.assert_called_with(10)
        inst_ab.inc_faxfrom.assert_called()
        assert res.status_code == 302


def test_ajax_deletefaxes_post(dummy_request):
    """Verify batch fax delete via AJAX."""
    dummy_request.method = "POST"
    dummy_request.params = {"fids": "10,20,30"}
    with patch("namifax.views.ajax.ArchiveIn") as mock_arc_cls:
        inst_arc = MagicMock()
        mock_arc_cls.return_value = inst_arc

        res = ajax_deletefaxes_view(dummy_request)
        assert res.status_code == 200
        assert inst_arc.delete_fax.call_count == 3


def test_ajax_archivebook_xml(dummy_request):
    """Verify archivebook auto-suggest XML output."""
    dummy_request.params = {"q": "Acme"}
    res = ajax_archivebook_view(dummy_request)
    assert res.status_code == 200
    assert "response" in res.text
    assert "Acme Corp" in res.text
