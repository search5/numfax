"""TDD Unit Tests for Phase 3 Business Logic & View Layer Refactoring.

Covers:
- AUDIT-10: settings_view real AFUserAccount DB binding, profile update, and password change
- AUDIT-15: helpers.py ocr_faxcontent and bardecode implementation
- AUDIT-16: faxrcvd.py OCR indexing without NameError
- AUDIT-17: outbox_view and faxqueue.py killjob success/failure branching
- AUDIT-07: sendfax.py safe command execution and simulation mode
- AUDIT-11: admin_system_func_view real archive backup generation
- AUDIT-13: printer.py process_inbound_print_job file persistence and queueing
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch
from pyramid import testing
import pytest
from PIL import Image

from namifax.db.engine import DatabaseEngine
from namifax.db.schema import init_database_tables
from namifax.services.user_account import AFUserAccount
from namifax.views.settings import settings_view
from namifax.common.helpers import ocr_faxcontent, bardecode
from namifax.views.outbox import outbox_view
from namifax.services.faxqueue import FaxQueue
from namifax.views.sendfax import dispatch_sendfax, sendfax_view
from namifax.views.admin import admin_system_func_view
from namifax.services.printer import process_inbound_print_job


@pytest.fixture
def memory_db():
    engine = DatabaseEngine()
    engine.connect_sqlite(":memory:")
    init_database_tables(engine)
    return engine


class MockRequest(testing.DummyRequest):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mock_identity = None

    @property
    def identity(self):
        return self._mock_identity

    @identity.setter
    def identity(self, val):
        self._mock_identity = val


@pytest.fixture
def dummy_request(memory_db):
    request = MockRequest()
    request.db = memory_db
    request.identity = {
        "uid": 1,
        "username": "admin",
        "name": "Initial Admin",
        "email": "admin@example.com",
        "is_admin": True,
        "superuser": True,
    }
    return request


# ---------------------------------------------------------------------------
# AUDIT-10: settings_view DB Binding & Profile / Password Updates
# ---------------------------------------------------------------------------
def test_settings_view_load_profile_from_db(dummy_request, memory_db):
    """Verify settings_view loads profile data from real AFUserAccount in DB."""
    user = AFUserAccount(db=memory_db)
    ok = user.create({
        "username": "profileuser",
        "password": "oldpassword123",
        "name": "DB Administrator",
        "email": "dbadmin@example.com",
        "from_company": "Nami Corp",
        "from_location": "Seoul",
        "from_voicenumber": "02-111-2222",
        "from_faxnumber": "02-111-3333",
        "user_tsi": "NAMI-SEOUL",
        "email_sig": "-- Nami Sig",
        "language": "ko",
    })
    assert ok is True
    user_id = user.get_uid()
    dummy_request.identity = {"uid": user_id, "username": "profileuser", "name": "DB Administrator", "is_admin": True}

    res = settings_view(dummy_request)
    profile = res["user_profile"]
    assert profile["name"] == "DB Administrator"
    assert profile["email"] == "dbadmin@example.com"
    assert profile["from_company"] == "Nami Corp"
    assert profile["from_location"] == "Seoul"
    assert profile["from_voicenumber"] == "02-111-2222"
    assert profile["from_faxnumber"] == "02-111-3333"
    assert profile["user_tsi"] == "NAMI-SEOUL"
    assert profile["email_sig"] == "-- Nami Sig"


def test_settings_view_post_updates_profile_in_db(dummy_request, memory_db):
    """Verify POST updates user.dbdata and calls user_update() to persist in DB."""
    user = AFUserAccount(db=memory_db)
    ok = user.create({
        "username": "updateuser",
        "password": "oldpassword123",
        "name": "Old Name",
        "email": "old@example.com",
    })
    assert ok is True
    uid = user.get_uid()
    dummy_request.identity = {"uid": uid, "username": "updateuser", "is_admin": True}

    dummy_request.method = "POST"
    dummy_request.params = {
        "name": "Updated Name",
        "email": "updated@example.com",
        "from_company": "Acme Global",
        "from_location": "Busan",
        "from_voicenumber": "051-123-4567",
        "from_faxnumber": "051-123-9999",
        "user_tsi": "ACME-BUSAN",
        "email_sig": "-- Updated Sig",
        "language": "es",
        "_submit_check": "1",
    }

    res = settings_view(dummy_request)
    assert res["message"] == "Settings updated successfully."
    assert res["error"] is None

    # Verify directly from DB
    reloaded = AFUserAccount(db=memory_db)
    assert reloaded.load(uid) is True
    assert reloaded.dbdata.get("name") == "Updated Name"
    assert reloaded.dbdata.get("email") == "updated@example.com"
    assert reloaded.dbdata.get("from_company") == "Acme Global"
    assert reloaded.dbdata.get("from_location") == "Busan"
    assert reloaded.dbdata.get("language") == "es"


def test_settings_view_password_change(dummy_request, memory_db):
    """Verify password change sets new password in DB and validates old password."""
    user = AFUserAccount(db=memory_db)
    ok = user.create({
        "username": "pwduser",
        "password": "oldpassword123",
        "name": "Admin",
        "email": "pwduser@example.com",
    })
    assert ok is True
    uid = user.get_uid()
    dummy_request.identity = {"uid": uid, "username": "pwduser", "is_admin": True}

    # 1. Password mismatch
    dummy_request.method = "POST"
    dummy_request.params = {
        "old_password": "oldpassword123",
        "new_password": "newpassword123",
        "confirm_password": "mismatchpassword",
    }
    res = settings_view(dummy_request)
    assert res["error"] == "New passwords do not match."

    # 2. Wrong old password
    dummy_request.params = {
        "old_password": "wrongpassword",
        "new_password": "newpassword123",
        "confirm_password": "newpassword123",
    }
    res = settings_view(dummy_request)
    assert res["error"] is not None and "old password" in res["error"].lower()

    # 3. Successful change
    dummy_request.params = {
        "old_password": "oldpassword123",
        "new_password": "newpassword123",
        "confirm_password": "newpassword123",
    }
    res = settings_view(dummy_request)
    assert res["message"] == "Settings updated successfully."
    assert res["error"] is None

    # Check login with new password
    auth_check = AFUserAccount(db=memory_db)
    assert auth_check.login("pwduser", "newpassword123") is True
    assert auth_check.login("pwduser", "oldpassword123") is False


# ---------------------------------------------------------------------------
# AUDIT-15: helpers.py ocr_faxcontent & bardecode
# ---------------------------------------------------------------------------
def test_ocr_faxcontent_existing_file(tmp_path):
    """Verify ocr_faxcontent extracts text using OcrService when file exists."""
    img_path = str(tmp_path / "test_ocr.tif")
    # Create simple 1x1 image
    img = Image.new("RGB", (100, 100), color="white")
    img.save(img_path)

    with patch("namifax.services.ocr.OcrService.extract_text_from_tiff") as mock_extract:
        mock_extract.return_value = {"success": True, "text": "Extracted Invoice Text", "pages": 1}
        result = ocr_faxcontent(img_path)
        assert result == "Extracted Invoice Text"

    # Non-existent file returns None
    assert ocr_faxcontent(str(tmp_path / "non_existent.tif")) is None


def test_bardecode_helper(tmp_path):
    """Verify bardecode returns None for non-existent file and attempts decode on existing file."""
    assert bardecode(str(tmp_path / "non_existent.tif")) is None

    img_path = str(tmp_path / "test_bar.tif")
    img = Image.new("RGB", (100, 100), color="white")
    img.save(img_path)

    with patch("shutil.which", return_value="/usr/bin/bardecode"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="BARCODE-9999\n")
        assert bardecode(img_path) == "BARCODE-9999"


# ---------------------------------------------------------------------------
# AUDIT-16: faxrcvd.py OCR Indexing without NameError
# ---------------------------------------------------------------------------
def test_faxrcvd_ocr_index_logic(tmp_path):
    """Verify faxrcvd indexing executes without NameError on faxname."""
    from namifax.cli.faxrcvd import run_faxrcvd

    tiff_path = str(tmp_path / "fax00123.tif")
    with open(tiff_path, "wb") as f:
        f.write(b"mock tiff content")

    with patch("namifax.cli.faxrcvd.FaxModem") as mock_modem, \
         patch("namifax.cli.faxrcvd.faxinfo") as mock_finfo, \
         patch("namifax.cli.faxrcvd.ArchiveIn") as mock_in, \
         patch("namifax.cli.faxrcvd.AFAddressBook"), \
         patch("namifax.cli.faxrcvd.DIDRouting"), \
         patch("namifax.cli.faxrcvd.tiff2pdf"), \
         patch("namifax.cli.faxrcvd.static_preview"), \
         patch("namifax.cli.faxrcvd.send_mail"), \
         patch("namifax.services.ocr.OcrService.index_fax") as mock_index_fax:

        mock_finfo.return_value = {"Sender": "123456", "Pages": "1", "Received": "2026:10:01 10:00:00"}
        inbox_inst = MagicMock()
        inbox_inst.create.return_value = True
        inbox_inst.get_fid.return_value = 99
        mock_in.return_value = inbox_inst

        # Run faxrcvd CLI function
        code = run_faxrcvd(["faxrcvd.py", tiff_path, "ttyS0", "comm01", "none"], db=MagicMock())
        assert code == 0

        # Verify index_fax was called with fax_file='fax.tif', tiff_path containing fax.tif, and fax_id=99
        mock_index_fax.assert_called_once()
        k_args = mock_index_fax.call_args.kwargs
        assert k_args["fax_file"] == "fax.tif"
        assert k_args["fax_id"] == 99


# ---------------------------------------------------------------------------
# AUDIT-17: outbox_view and FaxQueue killjob Branching
# ---------------------------------------------------------------------------
def test_outbox_view_killjob_success(dummy_request):
    """Verify outbox_view sets success flash message when fq.killjob succeeds."""
    dummy_request.params = {"kill": "105"}
    with patch("namifax.views.outbox.FaxQueue") as mock_fq_cls:
        fq_inst = MagicMock()
        fq_inst.killjob.return_value = True
        mock_fq_cls.return_value = fq_inst

        res = outbox_view(dummy_request)
        assert res["flash_message"] == "Job #105 successfully killed"


def test_outbox_view_killjob_failure(dummy_request):
    """Verify outbox_view sets failure flash message when fq.killjob fails."""
    dummy_request.params = {"kill": "106"}
    with patch("namifax.views.outbox.FaxQueue") as mock_fq_cls:
        fq_inst = MagicMock()
        fq_inst.killjob.return_value = False
        mock_fq_cls.return_value = fq_inst

        res = outbox_view(dummy_request)
        assert res["flash_message"] == "Failed to kill job #106"


def test_faxqueue_killjob_flexible_args():
    """Verify FaxQueue.killjob accepts (jid) or (user, jid)."""
    fq = FaxQueue(auto_process=False)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        # Calling with 1 arg: jid
        assert fq.killjob(101) is True
        # Calling with 2 args: user, jid
        assert fq.killjob("admin", 101) is True

        # Failure returns False
        mock_run.return_value = MagicMock(returncode=1)
        assert fq.killjob(102) is False


# ---------------------------------------------------------------------------
# AUDIT-07: sendfax.py Command Execution & Simulation Mode
# ---------------------------------------------------------------------------
def test_dispatch_sendfax_simulation_mode(monkeypatch):
    """Verify dispatch_sendfax uses simulation when sendfax binary is absent."""
    monkeypatch.setenv("NAMIFAX_QUEUE_SIMULATION", "1")
    with patch("shutil.which", return_value=None):
        res = dispatch_sendfax(destinations="02-123-4567", files=[])
        assert res["success"] is True
        assert res["simulated"] is True
        assert "jobid" in res


def test_dispatch_sendfax_binary_not_found_without_simulation(monkeypatch):
    """Verify dispatch_sendfax returns clear error when binary absent in production mode."""
    monkeypatch.setenv("NAMIFAX_QUEUE_SIMULATION", "0")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    with patch("shutil.which", return_value=None), \
         patch("os.path.exists", return_value=True):
        res = dispatch_sendfax(destinations="02-123-4567", files=[])
        assert res["success"] is False
        assert "not found" in res["error"].lower()


def test_dispatch_sendfax_with_binary():
    """Verify dispatch_sendfax executes subprocess safely when binary exists."""
    with patch("shutil.which", return_value="/usr/bin/sendfax"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="jobid 554", stderr="")
        res = dispatch_sendfax(
            destinations="02-123-4567",
            files=["/tmp/doc.pdf"],
            to_person="John Doe",
            to_company="Acme",
        )
        assert res["success"] is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "/usr/bin/sendfax" in args
        assert "-d" in args


# ---------------------------------------------------------------------------
# AUDIT-11: admin_system_func_view Backup Generation
# ---------------------------------------------------------------------------
def test_admin_system_func_backup_creates_archive(dummy_request, tmp_path, monkeypatch):
    """Verify action=='backup' creates real tar.gz backup file on disk."""
    backup_dir = str(tmp_path / "backup")
    monkeypatch.setenv("NAMIFAX_BACKUP_DIR", backup_dir)
    dummy_request.method = "POST"
    dummy_request.params = {"action": "backup", "_submit_check": "1"}

    res = admin_system_func_view(dummy_request)
    assert res["message"] is not None
    assert "Backup archive successfully created" in res["message"]
    # Check that backup file actually exists on disk
    files = os.listdir(backup_dir)
    assert len(files) >= 1
    assert any(f.endswith(".tar.gz") for f in files)


# ---------------------------------------------------------------------------
# AUDIT-13: printer.py Process Inbound Print Job File Persistence
# ---------------------------------------------------------------------------
def test_printer_inbound_persists_print_file(tmp_path, monkeypatch):
    """Verify process_inbound_print_job writes print data to temporary/draft file."""
    monkeypatch.setenv("NAMIFAX_TMPDIR", str(tmp_path))
    data = b"%!PS-Adobe-3.0 Sample Print Data [[FAX: 02-999-8888]]"
    res = process_inbound_print_job(data, sender_user="testuser")

    assert res["dispatched"] is True
    assert res["destination"] == "02-999-8888"
    assert "file_path" in res
    assert os.path.exists(res["file_path"])
    with open(res["file_path"], "rb") as f:
        assert f.read() == data

    # Test without fax tag (Draft)
    data_draft = b"%!PS-Adobe-3.0 Draft Print Data Without Tag"
    res_draft = process_inbound_print_job(data_draft, sender_user="testuser")
    assert res_draft["dispatched"] is False
    assert res_draft["status"] == "DRAFT"
    assert "file_path" in res_draft
    assert os.path.exists(res_draft["file_path"])
