# Module Specification: 12. FaxPDFCategory

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/FaxPDFCategory.php`
- **신규 타깃 모듈**: `src/avantfax/services/categories.py`
- **역할**: 수신/송신 팩스 분류를 위한 카테고리(`FaxCategory` 테이블) 등록, 수정, 삭제, 목록 조회 관리 서비스.
- **주요 의존성**:
  - `src/avantfax/models/entities.py` (`FaxCategory`)
  - `src/avantfax/db/repository.py` (`MDBOData` / `Repository`)
  - `src/avantfax/db/engine.py` (`DatabaseEngine`)

---

## 2. Legacy API Analysis & Behavior

### 속성(Attributes)
- `error` (str | None): 최근 발생한 에러 메시지
- `faxcategory`: `FaxCategory` 엔티티를 관리하는 `MDBOData` 인스턴스

### 메서드(Methods)
1. `__init__(db: Optional[DatabaseEngine] = None, repo: Optional[MDBOData] = None, lang: Optional[dict[str, str]] = None)`
   - `FaxCategory`를 관리하는 레포지토리를 초기화하거나 주입받음.
2. `create(name: str) -> bool`
   - 카테고리명 중복 검사: 이미 존재할 경우 실패 (`FAXCAT_ALREADY_EXISTS`)
   - 새 레코드 삽입: 성공 시 `True` 반환, 실패 시 `False` 및 `FAXCAT_NOT_CREATED` 에러 설정
3. `set_name(name: str, catid: int) -> bool`
   - `name` 또는 `catid`가 누락된 경우 실패 ("No name or catid to set")
   - 해당 `catid`의 카테고리명을 업데이트
4. `get_list() -> Optional[tuple[int, str]]` / `get_list_step()`
   - `SELECT * FROM FaxCategory ORDER BY name` 쿼리 결과를 순차적으로 1개씩 순회
   - 레거시 PHP의 `get_list(&$catid, &$name)` 순회 패턴 에뮬레이션
5. `get_categories() -> list[dict[str, Any]] | None`
   - 모든 카테고리를 이름 오름차순(`ORDER BY name`)으로 정렬하여 반환
6. `get_name(catid: int) -> Optional[str]`
   - `catid`가 누락된 경우 에러 ("No catid sent") 및 `None` 반환
   - `catid`로 카테고리를 조회하여 카테고리명 문자열 반환 (없으면 `None`)
7. `delete_category(catid: int) -> bool`
   - `catid`가 누락된 경우 에러 ("No catid sent") 및 `False` 반환
   - 레코드 삭제 수행 및 성공 여부 반환
8. `get_error() -> Optional[str]`
   - 최근 에러 메시지 반환

---

## 3. Error Messages / Localization Constants
- `FAXCAT_ALREADY_EXISTS`: "Category '%s' already exists"
- `FAXCAT_NOT_CREATED`: "Category '%s' could not be created"
- 기타 에러 문자열:
  - "No name or catid to set"
  - "No catid sent"

---

## 4. Modern Python Design (Idiomatic)
- `CategoryService` 및 `FaxPDFCategory` 클래스명 별칭 제공
- `list_all()` 모던 헬퍼 메서드 제공
- CLI/IPC 브리지: `bridge_cli.py`의 `categories` 액션을 통해 레거시 PHP `FaxPDFCategoryBridge.php`와 통신 가능
