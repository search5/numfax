# Spec 48: DB 엔진 단일 주입 (Engine Provisioning & `request.db` Bridge)

## 1. 목적 / 배경
- 결함 F5-12(설정 주입 수단 없음), R4F-13/F5-08(테스트 간 전역 DB 공유)의 근본 원인은
  `namifax.db.engine._DEFAULT_ENGINE` 프로세스 전역 싱글턴과, 어디서도 설정되지 않는 `request.db`이다.
- 방식 A(브리지): 앱 기동 시 SQLAlchemy `Engine` 1개를 설정에서 만들어 `registry`에 보관하고,
  요청마다 그 풀의 커넥션을 감싼 `DatabaseEngine`을 `request.db`로 제공한다.
  `DatabaseEngine`(레거시 SQL.php 의미론)은 유지한다. (ORM 전환은 범위 밖)

## 2. 계약

### 2.1 `resolve_database_url(settings, environ) -> str` (`namifax.db.provider`)
우선순위(높은 것이 승):
1. `settings["sqlalchemy.url"]`
2. `environ["DATABASE_URL"]`
3. `environ["AFDB_URL"]`
4. `sqlite:///<NAMIFAX_DB_PATH>` (환경변수 없으면 `<cwd>/namifax.db`) — 기존 `get_default_engine()`과 동일 기본값
- 순수 함수. 전역 상태를 읽거나 쓰지 않는다.

### 2.2 `create_sa_engine(url) -> sqlalchemy.Engine`
- `sqlite://`(메모리)는 `StaticPool` + `check_same_thread=False`로 모든 커넥션이 같은 DB를 보게 한다.
- 파일 sqlite는 `check_same_thread=False`.

### 2.3 `DatabaseEngine.from_connection(dbapi_conn) -> DatabaseEngine`
- 이미 열린 DBAPI 커넥션을 감싼다. `row_factory` 설정 여부와 무관하게 `query()` 결과는 `dict`.
- `disconnect()`는 감싼 커넥션을 `close()` (풀 커넥션이면 풀로 반환).

### 2.4 `create_app(global_config=None, **settings)`
- `resolve_database_url`로 엔진을 만들어 `registry["dbengine"]`(및 `settings["dbengine"]`)에 보관한다.
- 테이블 초기화(`init_database_tables`)는 **그 엔진의 커넥션**에 대해 수행한다.
- `get_default_engine()`을 호출하지 않는다.
- 같은 프로세스에서 서로 다른 URL의 앱 2개를 만들어도 데이터는 격리된다.

### 2.5 `request.db`
- reified. 요청 시작 시 엔진 풀에서 커넥션 1개를 빌려 `DatabaseEngine.from_connection`으로 제공한다.
- 요청 종료(finished callback) 시 `disconnect()` 호출 → 풀 반환.

## 3. 범위 밖 (후속 루프)
- 뷰/서비스/CLI 호출처의 `get_default_engine()`·`DatabaseEngine()` 직접 생성 제거
- `bridge_cli._GLOBAL_ENGINE`, 테스트 롤백 픽스처 전환
- `get_default_engine()`은 이번 루프에서 **삭제하지 않는다** (호출처 교체 후 shim화)
