# Specification: Module 35 - WebArchive

## 1. Overview
- **Module Name**: `WebArchive`
- **Legacy Source**: `legacy/avantfax/archive.php`, `legacy/avantfax/search.php`
- **Target Implementation**: `src/avantfax/web/views/archive.py`
- **Primary Role**: 팩스 영구 아카이브 검색, 다차원 필터링(키워드, 날짜 범위, 카테고리, 송/수신 구분), 페이징 목록 제공 및 팩스 영구 삭제.

---

## 2. Interface Specification
- **ArchiveHandler**:
  - `search_archive(user_account, filters, page=0, limit=10) -> Dict[str, Any]`:
    - 검색 필터: `kw`, `sentrecvd`, `start_date`, `end_date`, `category_id`, `company_id`
    - 사용자 권한에 따른 접근 제한 필터 자동 적용
    - 반환 항목: `items`, `total_count`, `num_pages`, `current_page`
  - `get_archive_fax(fax_id, user_account) -> Optional[Dict[str, Any]]`:
    - 아카이브 팩스 단일 조회 및 권한 검사
  - `delete_archive_fax(fax_id, user_account) -> bool`:
    - 아카이브 팩스 영구 삭제

---

## 3. Verification & Testing Strategy
- **Unit Tests (`tests/unit/test_web_archive.py`)**:
  - 키워드 및 날짜 필터 검색 결과 검증
  - 슈퍼유저 vs 일반 사용자 권한 분기 검증
  - 아카이브 팩스 상세 및 삭제 동작 검증
