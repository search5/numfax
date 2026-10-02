# Contract Specification: Module 01 - SQL

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/SQL.php` (클래스 `SQL`, `avantfaxSQL`)
- **타깃 모듈**: `src/avantfax/db/engine.py` (클래스 `DatabaseEngine`, `SQLSession`)
- **타깃 기술 스택**: Python 3.11+, SQLAlchemy 2.0+ (Core & Connection Pooling)

---

## 2. Interface Contract (인터페이스 명세)

### 2.1 Connection Management
- `connect(db_user, db_pass, db_name, db_host, db_engine='mysql', **kwargs) -> bool`
  - **선행 조건 (Pre-condition)**: 유효한 호스트, 사용자명, 패스워드, DB명이 주어져야 함. (테스트 시 SQLite in-memory DSN `sqlite:///:memory:`도 투명하게 지원해야 함)
  - **후행 조건 (Post-condition)**: 연결 풀이 초기화되고 UTF-8 인코딩이 보장된 커넥션 팩토리가 생성됨.
  - **예외 처리 (Error Handling)**: 연결 실패 시 에러 문자열을 기록하고 불리언 또는 적절한 예외 반환.

### 2.2 Query Execution
- `query(sql: str, params: dict | tuple = None, fetch_all: bool = False) -> QueryResult`
  - **선행 조건**: 유효한 SQL 문장.
  - **후행 조건**:
    - SELECT문: 결과 행 개수(`row_count`), 컬럼 매핑(`dict` 형태 레코드 리스트) 제공.
    - DML문(INSERT/UPDATE/DELETE): 영향받은 행 개수(`affected_rows`), INSERT인 경우 신규 생성된 ID(`last_insert_id`) 반환.
  - **불변식 (Invariant)**: 모든 결과 딕셔너리의 키는 대소문자를 유지하며, None 값과 특수문자는 UTF-8로 안전하게 디코딩됨.

### 2.3 Record Fetching & Iteration
- `get_records() -> list[dict]`
  - 현재 쿼리의 전체 결과 셋을 딕셔너리 리스트로 반환.
- `get_result() -> dict | None`
  - 결과 셋에서 다음 단일 레코드를 순차 반환하며, 끝에 도달하면 `None` 반환.

### 2.4 SQL Utilities
- `quote(value: Any) -> str`
  - SQL 인젝션 방지를 위한 리터럴 이스케이프 및 쿼팅 지원.
- `get_last_query() -> str`
  - 직전에 실행된 SQL 구문 반환.
- `gen_xml(records=None, title=True, root_tag='response', row_tag='row') -> str`
  - 레거시 호환 XML 직렬화 지원 (AvantFAX 웹 AJAX 응답 포맷 대응).

---

## 3. Idiomatic Transformation Rules (모던 파이썬 재설계 규칙)
1. **No Raw Pointer / Global State**: PEAR MDB2의 전역 싱글톤(`MDB2::singleton`) 및 참조 할당(`=&`) 제거.
2. **Context Manager Pattern**: `with engine.connect() as conn:` 또는 `with engine.transaction():` 지원으로 안전한 자동 리소스 해제(RAII) 보장.
3. **Multi-Dialect Compatibility**: MySQL뿐만 아니라 단위 테스트 및 경량 로컬 개발을 위한 SQLite 지원.
