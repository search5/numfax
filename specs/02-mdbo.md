# Contract Specification: Module 02 - MDBO

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/MDBO.php` (클래스 `MDBO`)
- **타깃 모듈**: `src/avantfax/db/query.py` (클래스 `QueryBuilder`, `MDBO`)
- **의존 관계**: `DatabaseEngine` (`src/avantfax/db/engine.py`)

---

## 2. Interface Contract (인터페이스 명세)

### 2.1 SQL Logic Operators
- `SQL_AND = " AND "`
- `SQL_OR = " OR "`

### 2.2 SQL Special Functions (Quoting Bypass)
- SQL 함수인 `CURRENT_TIMESTAMP()`, `LOCALTIMESTAMP()`, `LOCALTIME()`, `CURDATE()`, `NOW()`는 따옴표 없이 리터럴로 처리되어야 함.

### 2.3 Query Construction & Execution
- `insert(table: str, data: dict, id_col: str = None) -> int | bool`
  - **선행 조건**: 유효한 테이블 이름과 1개 이상의 컬럼-값 매핑.
  - **후행 조건**: `INSERT INTO table (c1, c2) VALUES (v1, v2)` 실행 및 생성된 PK 반환.
- `update(table: str, data: dict, where: dict) -> bool`
  - **선행 조건**: 테이블명, 변경할 컬럼-값 매핑, 그리고 1개 이상의 WHERE 조건.
  - **후행 조건**: `UPDATE table SET c1=v1 WHERE w1=wv1` 실행 성공 여부 반환.
- `get(table: str, id_col: str, id_val: Any) -> dict | None`
  - **선행 조건**: 테이블명, 기본 키 컬럼명 및 PK 값.
  - **후행 조건**: 일치하는 단일 행(dict) 반환, 없으면 `None`.
- `find(table: str, conditions: dict, logic: str = SQL_AND, limit: int = None, offset: int = None, reduce_single: bool = True) -> list[dict] | dict | None`
  - **선행 조건**: 검색 조건 사전.
  - **후행 조건**:
    - 검색 조건에 맞는 행 검색.
    - `reduce_single=True`이고 결과가 정확히 1개이면 단일 dict 반환, 복수 개이면 list[dict], 0개이면 빈 리스트/None 반환.
- `delete(table: str, id_col: str, id_val: Any) -> bool`
  - **선행 조건**: 테이블명 및 삭제 대상 PK.
  - **후행 조건**: 레코드 삭제 후 성공 여부 반환.

---

## 3. Idiomatic Transformation Rules
1. **PHP Reflection 대체**: 객체 프로퍼티 리플렉션 대신 Python dataclass / dict / SQLAlchemy 엔티티 속성을 유연하게 처리.
2. **SQL Injection 방어**: 문자열 결합 시 `quote()` 함수를 일관되게 적용하거나 파라미터화된 쿼리 생성.
3. **Flexible Return Type**: 레거시의 `reduce_array` 옵션 완벽 호환 및 모던 파이썬 표준 `list[dict]` 지원.
