# Module Specification: 27. Common Helpers (functions.php)

## 1. 개요 (Overview)
- **모듈명**: `helpers` (`src/avantfax/common/helpers.py`)
- **레거시 파일**: `legacy/avantfax/includes/functions.php`
- **의존성**:
  - `DatabaseEngine` (`src/avantfax/db/engine.py`)
  - `AFAddressBook` (`src/avantfax/services/addressbook.py`)
  - `DIDRouting` (`src/avantfax/services/did.py`)
  - `FaxPDFArchive` (`src/avantfax/services/archive_base.py`)
- **책임**:
  - 전역 텍스트, 이메일, 전화번호, 템플릿 치환 유틸리티 제공.
  - 파일 시스템, MIME, 임시 파일 관리.
  - 시스템 로깅(`avantfaxlog`).
  - 주소록 및 전화번호 역방향 조회(`phone_lookup`, `get_company_details`).
  - 팩스 이미지 변환 및 주석(`tiff2pdf`, `pdf_preview`, `annotate_fax`).

---

## 2. 인터페이스 명세 (API Contract)
- **문자열/검증**:
  - `clean_faxnum(fnum: Optional[str]) -> str`
  - `genpasswd(length: int = 8) -> str`
  - `rem_nl(text: str) -> str`
  - `str_len(text: str) -> int`
  - `unaccent(text: str) -> str`
  - `strip_sipinfo(text: str) -> str`
  - `split_emails(emails: str) -> List[str]`
  - `invalid_email(email: str) -> bool`
  - `process_template(template: str, match: str, values: List[str]) -> str`
  - `process_html_template(template: str, match: str, values: List[str]) -> str`
- **파일/MIME**:
  - `mime_by_suffix(filename: str) -> str`
  - `get_filetype(filename: str) -> str`
  - `tmpfilename(suffix: str = "") -> str`
  - `mkdirs(path: str, mode: int = 0o777) -> bool`
  - `fupload_error_code(code: int) -> str`
- **로깅**:
  - `avantfaxlog(text: str, echo: bool = False) -> None`
- **비즈니스 조회**:
  - `phone_lookup(number: str, db=None) -> Optional[dict]`
  - `get_company_details(abookfax_id: Optional[int], orig_faxnum: Optional[str], companyid: Optional[int], db=None) -> dict`
  - `list_languages(languages_dir: str = "") -> List[dict]`

---

## 3. 검증 시나리오 (Test Scenarios)
1. 문자열 유틸리티: `clean_faxnum`, `rem_nl`, `unaccent`, `strip_sipinfo`, `split_emails`, `process_template` 동작 검증.
2. MIME 및 파일 타입: 확장자별 정확한 MIME 반환 검증.
3. `phone_lookup` 및 `get_company_details`: 주소록 및 DID 기반 조회 정확성 검증.
