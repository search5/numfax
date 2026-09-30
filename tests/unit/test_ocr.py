from unittest.mock import MagicMock, patch
import os
import pytest
from PIL import Image, ImageDraw

from namifax.services.ocr import OcrService

def test_ocr_service_init():
    svc = OcrService(lang="eng")
    assert svc.lang == "eng"

def test_extract_text_from_image_mock():
    svc = OcrService()
    with patch("pytesseract.image_to_string") as mock_tess:
        mock_tess.return_value = "CONFIDENTIAL FAX TRANSMISSION\nPage 1 of 1"
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        text = svc.extract_text_from_image(img)
        assert "CONFIDENTIAL" in text
        mock_tess.assert_called_once()

def test_extract_text_from_image_fail_safe():
    svc = OcrService()
    with patch("pytesseract.image_to_string", side_effect=RuntimeError("Tesseract failed")):
        img = Image.new("RGB", (50, 50))
        text = svc.extract_text_from_image(img)
        assert text == ""

def test_extract_text_from_tiff(tmp_path):
    svc = OcrService()
    tiff_file = str(tmp_path / "sample.tif")
    img1 = Image.new("RGB", (100, 100), color=(255, 255, 255))
    img2 = Image.new("RGB", (100, 100), color=(200, 200, 200))
    img1.save(tiff_file, save_all=True, append_images=[img2], format="TIFF")

    with patch("pytesseract.image_to_string", side_effect=["First Page Content", "Second Page Invoice"]):
        result = svc.extract_text_from_tiff(tiff_file)
        assert result["success"] is True
        assert result["pages"] == 2
        assert "First Page Content" in result["text"]
        assert "Second Page Invoice" in result["text"]

def test_index_fax():
    svc = OcrService()
    mock_db = MagicMock()
    with patch.object(svc, "db", mock_db):
        with patch.object(svc, "extract_text_from_tiff", return_value={"text": "Invoice #9999", "pages": 1, "success": True}):
            success = svc.index_fax(fax_file="fax_001.tif", tiff_path="/tmp/fax_001.tif", fax_id=42)
            assert success is True
            mock_db.query.assert_called()

def test_search_faxes():
    svc = OcrService()
    mock_db = MagicMock()
    mock_db.query.return_value = [
        {
            "id": 1,
            "fax_id": 42,
            "fax_file": "fax_001.tif",
            "ocr_text": "Company Statement: Invoice #9999 is paid in full.",
            "page_count": 1,
            "created_at": "2026-10-01 00:00:00",
        }
    ]
    with patch.object(svc, "db", mock_db):
        results = svc.search_faxes(keyword="Invoice")
        assert len(results) == 1
        assert results[0]["fax_id"] == 42
        assert "Invoice #9999" in results[0]["snippet"]
