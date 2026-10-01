"""Unit tests for NamiFAX modal POST actions with real domain service integration."""

from unittest.mock import MagicMock, patch
from pyramid import testing
import pytest

from namifax.views.modals import (
    modal_delete_view,
    modal_note_view,
    modal_assign_view,
    modal_email_view,
    modal_refax_view,
)


@pytest.fixture
def dummy_request():
    request = testing.DummyRequest()
    request.__dict__["identity"] = {"username": "admin", "uid": 1, "is_admin": True, "superuser": True}
    request.db = MagicMock()
    request.dbsession = MagicMock()
    return request


def test_modal_delete_post(dummy_request, as_superuser):
    """Verify fax deletion via modal POST."""
    dummy_request.method = "POST"
    dummy_request.params = {"fid": "42", "_submit_check": "1"}
    with patch("namifax.views.modals.ArchiveIn") as mock_cls:
        inst = MagicMock()
        inst.delete_fax.return_value = True
        mock_cls.return_value = inst
        res = modal_delete_view(dummy_request)
        inst.load_fax.assert_called_with(42)
        inst.delete_fax.assert_called_once_with()
        assert res.get("title") == "- NamiFAX - Delete Fax" or res.get("status") == "deleted"


def test_modal_note_post(dummy_request):
    """Verify updating note/description on fax via modal POST."""
    dummy_request.method = "POST"
    dummy_request.params = {"fid": "42", "description": "Important review note", "_submit_check": "1"}
    with patch("namifax.views.modals.ArchiveIn") as mock_cls:
        inst = MagicMock()
        inst.load_fax.return_value = True
        inst.set_note.return_value = True
        mock_cls.return_value = inst
        res = modal_note_view(dummy_request)
        inst.set_note.assert_called()
        assert res.get("title") == "- NamiFAX - Add Note"


def test_modal_assign_post(dummy_request):
    """Verify assigning company to fax via modal POST."""
    dummy_request.method = "POST"
    dummy_request.params = {"fid": "42", "abook_id": "10", "myselect": "5", "_submit_check": "1"}
    with patch("namifax.views.modals.AFAddressBook") as mock_ab_cls, \
         patch("namifax.views.modals.ArchiveIn") as mock_arc_cls:
        inst_ab = MagicMock()
        inst_ab.loadbycid.return_value = True
        inst_ab.get_companyid.return_value = 10
        inst_ab.reassign.return_value = True
        mock_ab_cls.return_value = inst_ab

        inst_arc = MagicMock()
        mock_arc_cls.return_value = inst_arc

        res = modal_assign_view(dummy_request)
        inst_ab.reassign.assert_called_with(5)
        inst_arc.reassign.assert_called_with(10, 5)
        assert res.get("title") == "- NamiFAX - Assign Company"


def test_modal_email_post(dummy_request):
    """Verify sending fax via email via modal POST."""
    dummy_request.method = "POST"
    dummy_request.params = {
        "fid": "42",
        "emails": "client@example.com",
        "subject": "Transmitted Invoice",
        "msg": "Here is the document.",
        "_submit_check": "1",
    }
    with patch("namifax.views.modals.ArchiveIn") as mock_arc_cls, \
         patch("namifax.views.modals.send_mail", return_value=True) as mock_send_mail, \
         patch("namifax.views.modals.AFAddressBook") as mock_ab_cls:
        inst_arc = MagicMock()
        inst_arc.load_fax.return_value = True
        inst_arc.get_pdfpath.return_value = "/tmp/fax42.pdf"
        inst_arc.get_thumbnail.return_value = "/tmp/thumb42.png"
        mock_arc_cls.return_value = inst_arc

        inst_ab = MagicMock()
        mock_ab_cls.return_value = inst_ab

        res = modal_email_view(dummy_request)
        mock_send_mail.assert_called_once()
        inst_ab.create_contacts.assert_called_with("client@example.com")
        assert res.get("title") == "- NamiFAX - Send Fax via Email"


def test_modal_refax_post(dummy_request):
    """Verify resending fax via FaxQueue modal POST."""
    dummy_request.method = "POST"
    dummy_request.params = {
        "fid": "42",
        "destinations": "123-456-7890",
        "regarding": "Resending contract",
        "comments": "Please confirm receipt.",
        "_submit_check": "1",
    }
    with patch("namifax.views.modals.FaxQueue") as mock_fq_cls:
        inst_fq = MagicMock()
        inst_fq.create_job.return_value = 999
        mock_fq_cls.return_value = inst_fq

        res = modal_refax_view(dummy_request)
        inst_fq.create_job.assert_called()
        assert res.get("title") == "- NamiFAX - Reply to Fax"
