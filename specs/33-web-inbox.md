# Specification: Module 33 - WebInbox

## 1. Overview
- **Module Name**: `WebInbox`
- **Legacy Source**: `legacy/avantfax/inbox.php`, `legacy/avantfax/viewfax.php`
- **Target Implementation**: `src/avantfax/web/views/inbox.py`
- **Primary Role**: 수신 팩스 인박스 목록 조회(페이징, 권한 필터링), 단일 팩스 상세 및 이미지 뷰어 데이터 제공, 수신 팩스 삭제/아카이브 이동 처리.

---

## 2. Interface Specification
- **InboxHandler**:
  - `list_inbox(user_account, page=0, limit=10) -> Dict[str, Any]`:
    - 사용자의 모뎀/DID/카테고리 권한에 맞는 수신 팩스 목록 및 페이징 정보 반환
    - 반환 항목: `items`, `total_count`, `num_pages`, `current_page`
  - `get_fax_detail(fax_id, user_account) -> Optional[Dict[str, Any]]`:
    - 특정 `fid`의 팩스 상세 메타데이터 및 이미지/PDF 파일 정보 반환 (권한 검증 포함)
  - `delete_fax(fax_id, user_account) -> bool`:
    - 수신함에서 해당 팩스 삭제 처리
  - `archive_fax(fax_id, user_account) -> bool`:
    - 수신함에서 일반 아카이브로 이동 처리

---

## 3. Verification & Testing Strategy
- **Unit Tests (`tests/unit/test_web_inbox.py`)**:
  - 권한별 팩스 목록 필터링 및 페이징 검증
  - 정상 및 비정상 `fid` 상세 조회 및 접근 권한 검증
  - 삭제 및 아카이브 이동 동작 검증
