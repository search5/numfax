# Specification: Web Route 05 - Fax Streaming & Image Rotation

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/pdf.php`, `legacy/avantfax/file.php`, `legacy/avantfax/rotate.php`
- **Target Route**:
  - `fax_download` (`GET /faxes/download/{fid}`): PDF / TIFF 바이너리 파일 다운로드 및 브라우저 스트리밍
  - `fax_rotate` (`POST /faxes/rotate/{fid}`, `GET /faxes/rotate/{fid}`): 팩스 이미지 90도 회전
- **ACL Permission**: `view`
- **Request Parameters**:
  - `fid` (path int): 대상 팩스 ID
  - `format` (query str, optional: 'pdf' | 'tiff', default: 'pdf')
- **Response Behavior**:
  - `fax_download`:
    - Status: HTTP 200 OK
    - Headers:
      - `Content-Type`: `application/pdf` (또는 `image/tiff`)
      - `Content-Disposition`: `inline; filename="fax_{fid}.{fmt}"`
    - Body: 원본 PDF/TIFF 바이너리 바이트 스트림
  - `fax_rotate`:
    - Status: HTTP 200 OK
    - Content-Type: `application/json`
    - Body: `{"status": "ok", "fid": "{fid}", "rotation": 90}`

---

## 2. Golden Master Verification Scenarios
- `W07_pdf_download`: `GET /faxes/download/1` 호출 시 HTTP 200 및 `Content-Type: application/pdf` 검증
