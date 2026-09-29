# Contract Specification: Module 08 - MDBObject

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/MDBObject.php` (인터페이스 `iMDBObject`, 클래스 `MDBObject`, `afDB`)
- **타깃 모듈**: `src/avantfax/db/base.py` (클래스 `BaseModel`, `MDBObject`)
- **의존 관계**: 01번 `SQL` (`src/avantfax/db/engine.py`)

---

## 2. Interface Contract (인터페이스 명세)

### 2.1 Table Metadata
- `get_table_name() -> str`
  - 엔티티가 매핑되는 데이터베이스 테이블명 반환.
- `get_table_id() -> str`
  - 기본 키(PK) 컬럼명 반환 (예: `uid`, `abook_id`, `fid`).

### 2.2 Primary Key Accessors
- `get_id() -> int | str | None`
  - 현재 인스턴스의 기본 키 값 반환.
- `set_id(id_val: int | str) -> bool`
  - 기본 키 값 설정.

### 2.3 Attribute Population & Serialization
- `set_vars(vals: dict[str, Any]) -> None`
  - 딕셔너리의 키-값 쌍을 인스턴스 속성으로 일괄 설정.
- `to_dict() -> dict[str, Any]`
  - 현재 인스턴스의 모든 컬럼/필드를 딕셔너리로 직렬화.

---

## 3. Idiomatic Transformation Rules
1. **SQLAlchemy DeclarativeBase 통합**: 단순 동적 객체가 아닌 SQLAlchemy 2.0 `DeclarativeBase`와 결합하여 정적 타입 검사 및 ORM 세션 바인딩을 가능하게 함.
2. **동적 속성 안전성**: 존재하지 않는 컬럼 주입 시에도 안전하게 속성 보관 또는 경고 처리.
3. **Pydantic 호환성**: `to_dict()`를 통해 Pydantic 스키마 및 JSON 직렬화와 완벽 호환.
