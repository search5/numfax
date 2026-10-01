from __future__ import annotations

import os
from typing import Any
from PIL import Image
import pytesseract

from namifax.db.engine import DatabaseEngine, resolve_db

class OcrService:
    """Enterprise Fax OCR Text Extraction & Full-Text Search service."""

    def __init__(self, lang: str = "eng", db: DatabaseEngine | None = None) -> None:
        self.lang = lang
        self.db = resolve_db(db, "OcrService")
        if db is not None:
            self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        create_sql = """
        CREATE TABLE IF NOT EXISTS FaxOCR (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fax_id INT NULL,
            fax_file VARCHAR(255) NOT NULL,
            ocr_text LONGTEXT NOT NULL,
            page_count INT DEFAULT 1,
            confidence FLOAT DEFAULT 0.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_fax_ocr_file (fax_file),
            INDEX idx_fax_ocr_faxid (fax_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        try:
            self.db.query(create_sql)
        except Exception:
            pass

    def extract_text_from_image(self, image: Image.Image | str) -> str:
        """Extract text from a single image or file path using Tesseract."""
        try:
            if isinstance(image, str):
                if not os.path.exists(image):
                    return ""
                with Image.open(image) as img:
                    return pytesseract.image_to_string(img, lang=self.lang).strip()
            else:
                return pytesseract.image_to_string(image, lang=self.lang).strip()
        except Exception:
            return ""

    def extract_text_from_tiff(self, tiff_path: str) -> dict[str, Any]:
        """Extract combined text across all pages of a multi-page TIFF."""
        if not os.path.exists(tiff_path):
            return {"success": False, "error": f"File not found: {tiff_path}", "text": "", "pages": 0}

        try:
            extracted_pages = []
            with Image.open(tiff_path) as img:
                n_frames = getattr(img, "n_frames", 1)
                for frame_idx in range(n_frames):
                    img.seek(frame_idx)
                    page_text = self.extract_text_from_image(img.copy())
                    if page_text:
                        extracted_pages.append(page_text)

            combined_text = "\n\n--- Page Break ---\n\n".join(extracted_pages)
            return {
                "success": True,
                "text": combined_text,
                "pages": n_frames,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "pages": 0,
            }

    def index_fax(self, fax_file: str, tiff_path: str, fax_id: int | None = None) -> bool:
        """Extract text from fax TIFF and index in FaxOCR table."""
        res = self.extract_text_from_tiff(tiff_path)
        if not res.get("success"):
            return False

        text = res.get("text", "")
        pages = res.get("pages", 1)

        q_file = self.db.quote(fax_file)
        q_text = self.db.quote(text)
        fid_val = f"{int(fax_id)}" if fax_id is not None else "NULL"

        # Check existing row
        existing = self.db.query(f"SELECT id FROM FaxOCR WHERE fax_file = {q_file} LIMIT 1")
        if existing:
            update_sql = f"""
            UPDATE FaxOCR SET ocr_text = {q_text}, page_count = {int(pages)}, fax_id = {fid_val}
            WHERE fax_file = {q_file}
            """
            self.db.query(update_sql)
        else:
            insert_sql = f"""
            INSERT INTO FaxOCR (fax_id, fax_file, ocr_text, page_count)
            VALUES ({fid_val}, {q_file}, {q_text}, {int(pages)})
            """
            self.db.query(insert_sql)

        return True

    def get_ocr_text(self, fax_file: str) -> str | None:
        """Retrieve stored OCR text for a fax file."""
        try:
            q_file = self.db.quote(fax_file)
            rows = self.db.query(f"SELECT ocr_text FROM FaxOCR WHERE fax_file = {q_file} LIMIT 1")
            if rows:
                return rows[0].get("ocr_text")
            return None
        except Exception:
            return None

    def search_faxes(self, keyword: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search indexed faxes by text keyword."""
        keyword = keyword.strip()
        if not keyword:
            return []

        try:
            q_kw = self.db.quote(f"%{keyword}%")
            sql = f"""
            SELECT id, fax_id, fax_file, ocr_text, page_count, created_at
            FROM FaxOCR
            WHERE ocr_text LIKE {q_kw}
            ORDER BY id DESC
            LIMIT {int(limit)}
            """
            rows = self.db.query(sql)
            if not rows:
                return []

            results = []
            for r in rows:
                full_text = r.get("ocr_text", "")
                idx = full_text.lower().find(keyword.lower())
                if idx >= 0:
                    start = max(0, idx - 40)
                    end = min(len(full_text), idx + len(keyword) + 40)
                    snippet = f"...{full_text[start:end]}..."
                else:
                    snippet = full_text[:80] + ("..." if len(full_text) > 80 else "")

                results.append({
                    "id": r.get("id"),
                    "fax_id": r.get("fax_id"),
                    "fax_file": r.get("fax_file"),
                    "snippet": snippet,
                    "page_count": r.get("page_count", 1),
                    "created_at": str(r.get("created_at")),
                })
            return results
        except Exception:
            return []
