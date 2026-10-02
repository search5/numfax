"""Admin > Storage: the connection fields belong to the chosen provider. Local storage needs none, S3 / MinIO / Ceph and Google Cloud Storage
(its S3-compatible interface) need them; the page shows the fields that apply and follows the drop-down without reloading."""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from namifax.services.system_config import SystemConfigService


@pytest.fixture
def client(testapp):
    testapp.post("/login", {"username": "admin", "password": "password", "_submit_check": "1"})
    return testapp


def _page(client):
    return BeautifulSoup(client.get("/admin/storage").text, "html.parser")


def _hidden(node):
    return "hidden" in (node.get("class") or [])


def test_local_storage_shows_no_connection_fields(client, dbsession):
    SystemConfigService(dbsession).set("cloud_storage_type", "LOCAL")
    page = _page(client)
    fields = page.find(id="cloud-fields")
    assert fields is not None and _hidden(fields)
    assert page.find(id="cloud-note-LOCAL") is not None and not _hidden(page.find(id="cloud-note-LOCAL"))
    assert _hidden(page.find(id="cloud-test"))                                    # nothing to test for local files


@pytest.mark.parametrize("kind", ["S3", "GCS"])
def test_a_cloud_provider_shows_the_connection_fields(client, dbsession, kind):
    SystemConfigService(dbsession).set("cloud_storage_type", kind)
    page = _page(client)
    assert not _hidden(page.find(id="cloud-fields")) and not _hidden(page.find(id="cloud-test"))
    assert _hidden(page.find(id="cloud-note-LOCAL"))


def test_each_provider_has_its_own_wording(client):
    page = _page(client)
    for kind in ("S3", "GCS"):
        assert page.find(attrs={"data-for": kind}) is not None
    gcs_hint = " ".join(n.get_text() for n in page.find_all(attrs={"data-for": "GCS"}))
    assert "storage.googleapis.com" in gcs_hint and "HMAC" in gcs_hint


def test_the_dropdown_drives_the_fields(client):
    page = _page(client)
    select = page.find("select", {"name": "storage_type"})
    assert select["data-provider-switch"] == "cloud-fields"
    assert b"data-provider-switch" in client.get("/static/js/storage.js").body
    assert any(s.get("src") == "/static/js/storage.js" for s in page.find_all("script"))


def test_the_fields_still_post_with_the_form(client):
    form = next(f for f in client.get("/admin/storage").forms.values() if "storage_type" in f.fields)
    for name in ("endpoint_url", "region_name", "bucket_name", "access_key", "secret_key", "prefix"):
        assert name in form.fields, name
