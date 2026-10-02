# Spec 47: OCR Text Extraction & Full-Text Search Engine

## 1. 목적 및 배경
수신된 팩스(TIFF/PDF) 문서 이미지로부터 광학 문자 인식(Tesseract OCR)을 통해 본문 텍스트를 자동 추출하고 데이터베이스에 인덱싱함으로써, 수신함 및 아카이브에서 팩스 내용에 대한 전문 검색(Full-Text Search)을 가능하게 한다.

---

## 2. 데이터베이스 모델 명세 (`FaxOCR`)

### 테이블 정의 (`FaxOCR`)
- `id`: INTEGER PRIMARY KEY AUTO_INCREMENT
- `fax_id`: INTEGER NULL (아카이브 인바운드 팩스 ID)
- `fax_file`: VARCHAR(255) NOT NULL (팩스 파일명 또는 상대 경로)
- `ocr_text`: LONGTEXT NOT NULL (추출된 전문 텍스트)
- `page_count`: INTEGER DEFAULT 1 (인식된 총 페이지 수)
- `confidence`: FLOAT DEFAULT 0.0 (평균 인식 신뢰도 점수)
- `created_at`: DATETIME DEFAULT CURRENT_TIMESTAMP
- `INDEX idx_fax_ocr_file (fax_file)`
- `INDEX idx_fax_ocr_faxid (fax_id)`
- `FULLTEXT idx_fax_ocr_text (ocr_text)` (MySQL/MariaDB 지원 시)

---

## 3. 서비스 계층 명세 (`OcrService`)

### 모듈 위치
- `src/namifax/services/ocr.py`

### 주요 메서드
1. **`extract_text_from_image(image: Image.Image | str) -> str`**:
   - 단일 이미지 객체 또는 파일 경로로부터 OCR 텍스트를 추출.
   - 예외 발생 시 빈 문자열 반환 (Fail-Safe).
2. **`extract_text_from_tiff(tiff_path: str) -> dict[str, Any]`**:
   - 다중 프레임 TIFF 파일을 순회하며 모든 페이지의 텍스트 추출 및 합산.
   - `{"text": full_text, "pages": n_pages, "success": True}` 반환.
3. **`index_fax(fax_file: str, tiff_path: str, fax_id: int | None = None) -> bool`**:
   - TIFF에서 텍스트를 추출하고 `FaxOCR` 테이블에 저장/갱신.
4. **`search_faxes(keyword: str, limit: int = 50) -> list[dict[str, Any]]`**:
   - 키워드가 포함된 팩스 목록 및 발췌문(snippet) 반환.
5. **`get_ocr_text(fax_file: str) -> str | None`**:
   - 특정 팩스 파일에 대해 인덱싱된 OCR 텍스트 반환.

---

## 4. 검증 기준 (Acceptance Criteria)

1. 단위 테스트:
   - 단일 및 다중 페이지 이미지에서 OCR 텍스트 추출 검증.
   - DB 인덱싱 및 키워드 전문 검색 쿼리 검증.
   - OCR 엔진 부재 또는 비정상 파일 시 예외를 전파하지 않고 안전하게 처리되는지(Fail-Safe) 검증.
2. 기존 시스템 무회귀:
   - 기존 `faxrcvd` 및 아카이브 뷰의 동작에 어떠한 사이드 이펙트도 주지 않음.
