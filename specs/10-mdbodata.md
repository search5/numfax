# Contract Specification: Module 10 - MDBOData

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/MDBOData.php` (클래스 `MDBOData`)
- **타깃 모듈**: `src/avantfax/db/repository.py` (클래스 `Repository`, `MDBOData`)
- **의존 관계**: 02번 `MDBO` (`query.py`), 08번 `MDBObject` (`base.py`), 09번 `classes_entities` (`entities.py`)

---

## 2. Interface Contract (인터페이스 명세)

### 2.1 Repository Constructor
- `__init__(model_class: type[T] | str, db: DatabaseEngine = None)`
  - 엔티티 클래스(예: `UserAccount`, `Modems`) 또는 클래스명 문자열을 받아 레포지토리 초기화.

### 2.2 CRUD Operations
- `load(id_val: int | str) -> bool`
  - 기본 키로 레코드를 조회하여 내부 `data` 인스턴스에 로드. 성공 시 `True`, 실패 시 `False`.
- `new_entry(info: dict[str, Any]) -> bool`
  - `info` 딕셔너리로 새 엔티티를 생성 및 DB에 저장하고, 생성된 PK를 `data`에 반영.
- `update_entry(info: dict[str, Any] = None) -> bool`
  - `info`가 주어지면 `data` 속성을 갱신한 후 DB에 반영.
- `delete_entry(info: dict[str, Any] = None) -> bool`
  - 현재 `data` 인스턴스를 DB에서 삭제.

### 2.3 Query & Search
- `find(conditions: dict[str, Any], query_logic: str = SQL_AND, limit: int = None, offset: int = None, reduce_single: bool = True) -> list[dict] | dict | None`
  - 주어진 조건으로 레코드를 검색.
- `findext(conditions: dict[str, Any]) -> list[dict] | dict | None`
  - 인덱스/PK를 포함한 조건 검색.
- `query(sql: str, reduce_single: bool = True) -> list[dict] | dict | None`
  - 임의의 SQL 쿼리를 실행하여 결과 반환.

### 2.4 State Inspection
- `get_id() -> int | None`
  - 현재 로드된 레코드의 PK 반환.
- `get_info() -> dict[str, Any]`
  - 현재 로드된 레코드의 전체 필드 딕셔너리 반환.

---

## 3. Idiomatic Transformation Rules
1. **Generic Repository Type**: `Repository[T]` 제네릭을 지원하여 정적 타입 체킹 지원.
2. **Entity Resolution**: 문자열 클래스명(`'UserAccount'`) 전달 시 `avantfax.models.entities`에서 자동으로 클래스를 매핑.
3. **Legacy Compatibility**: `$distrolist->data->...` 레거시 체이닝을 `repo.data` 프로퍼티로 완벽하게 보존.
