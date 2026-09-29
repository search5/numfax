# Module Specification: 20. FaxPDFArchive

## 1. 개요 (Overview)
- **모듈명**: `FaxPDFArchive` (`archive_base.py`)
- **레거시 파일**: `legacy/avantfax/includes/FaxPDFArchive.php`
- **의존성**:
  - `MDBOData` (`src/avantfax/db/repository.py` - 테이블: `FaxArchive`)
  - `DatabaseEngine` (`src/avantfax/db/engine.py`)
  - `clean_faxnum` (팩스 번호 정제 함수)
- **책임**:
  - 수신 및 송신 팩스 메타데이터(`FaxArchive` 테이블) 저장, 조회, 수정, 삭제 관리.
  - 디바이스(모뎀)/DID 라우트 및 카테고리에 기반한 접근 권한 검사 (`user_has_rights`).
  - 인박스 목록 조회 및 페이징 (`list_inbox`, `get_num_faxes`, `get_fid_prev`, `get_fid_next`).
  - 아카이브 검색 쿼리 빌더 및 페이징 (`search_archive`, `next_archive_entry`).
  - 팩스 파일 시스템 정리 (`delete_fax`, `prune_archive`).
  - 하위 클래스(`ArchiveIn`, `ArchiveOut`)의 기반 클래스로 동작.

---

## 2. 데이터 모델 및 상수 (Constants & Schema)
- **기본 파일 상수**:
  - `PDFNAME`: `'fax.pdf'`
  - `THUMBNAIL`: `'thumb.png'`
  - `TIFFNAME`: `'fax.tif'`
  - `PREVIMG`: `'page'`
  - `PREVIMGSFX`: `'.png'`
  - `DEFAULT_ARCHIVE_DATE_FORMAT`: `'%Y-%m-%d %H:%M'`

---

## 3. 인터페이스 명세 (API Contract)

### `FaxPDFArchive(db_engine=None, installdir='')`
- `load_fax(faxid: int) -> bool`
- `get_error() -> Optional[str]`
- `get_num_faxes(devices: list, faxcats: list, enable_did_routing: bool = False) -> int`
- `user_has_rights(userid: int, modems: list, routes: list, faxcat: list) -> bool`
- `get_fid_prev() -> Optional[int]`
- `get_fid_next() -> Optional[int]`
- `search_archive(criteria: dict) -> int` (검색 조건 적용 후 전체 행 수 반환)
- `next_archive_entry() -> Optional[int]` (검색 결과에서 다음 fid 반환, 없으면 None)
- `list_inbox(devices: list, index: int = 0, limit: int = 25, faxcats: list = None, enable_did_routing: bool = False, order_by_modem: bool = False) -> List[dict]`
- `set_category(catid: Optional[int], userid: int = 0) -> bool`
- `remove_category(catid: int) -> bool`
- `set_note(description: str, category: Optional[int], userid: int) -> bool`
- `set_faxcontent(faxcontent: str) -> bool`
- `delete_fax(fid: Optional[int] = None) -> bool`
- `prune_archive(days: int) -> int` (삭제된 건수 반환)
- `set_faxnumid(id: int) -> bool`
- `set_companyid(id: int) -> bool`
- `reassign(oldcid: int, newcid: int) -> bool`
- `create_fax(path: str, faxnid: int, faxnumber: str, pages: int, date: Optional[str] = None, didr_id: Optional[int] = None) -> bool`
- Getters:
  - `get_fid()`, `get_faxcatid()`, `get_userid()`, `get_description()`, `get_lastmoduser()`, `get_faxnumid()`, `get_origfaxnum()`, `get_pages()`, `get_inbox()`, `get_companyid()`, `get_didr_id()`, `get_modemdev()`, `get_tiffpath()`, `get_pdfpath()`, `get_thumbnail()`, `get_faximages()`, `get_archstamp()`, `get_lastmoddate()`

---

## 4. 검증 시나리오 (Test Scenarios)
1. `create_fax` 및 `load_fax`: 팩스 레코드 생성 및 경로/필드 로드 확인.
2. `user_has_rights`: 소유자(userid), 모뎀(modemdev), 카테고리(faxcatid), 라우트(didr_id) 별 권한 확인.
3. `search_archive`: 발신(s)/수신(r)/전체(*) 및 날짜/키워드/회사 조건에 따른 SQL 검색 및 페이징 확인.
4. `delete_fax` 및 `prune_archive`: DB 레코드 및 관련 파일/폴더 삭제 검증.
5. `reassign` & `remove_category`: 회사 재지정 및 카테고리 NULL 처리 확인.
