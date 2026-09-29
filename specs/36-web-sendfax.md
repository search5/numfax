# Specification: Module 36 - WebSendFax

## 1. Overview
- **Module Name**: `WebSendFax`
- **Legacy Source**: `legacy/avantfax/sendfax.php`, `legacy/avantfax/upload_*.php`
- **Target Implementation**: `src/avantfax/web/views/sendfax.py`
- **Primary Role**: 웹 인터페이스를 통한 팩스 발송, 첨부 파일 검증, 표지 템플릿 결합, 다중 수신처 분기 및 HylaFAX 전송 작업 생성.

---

## 2. Interface Specification
- **SendFaxHandler**:
  - `get_sendfax_options(user_account) -> Dict[str, Any]`:
    - 사용자가 접근 가능한 모뎀 목록(`modems`) 및 팩스 표지 목록(`covers`) 반환
  - `send_fax(user_account, form_data, file_paths) -> Dict[str, Any]`:
    - 수신자 번호 목록(`destinations`) 검증 및 정제
    - 첨부 파일 MIME 타입 및 유효성 검사
    - 표지 옵션 적용 및 HylaFAX 큐에 작업 제출
    - 반환 항목: `success: bool`, `job_ids: List[str]`, `error: Optional[str]`

---

## 3. Verification & Testing Strategy
- **Unit Tests (`tests/unit/test_web_sendfax.py`)**:
  - 수신처 번호 누락 시 유효성 에러 검증
  - 정상 번호 및 첨부 파일 전달 시 성공적인 팩스 작업 큐 등록 검증
  - 사용 가능한 모뎀 및 표지 목록 조회 검증
