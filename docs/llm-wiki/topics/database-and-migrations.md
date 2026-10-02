---
title: 데이터베이스와 마이그레이션
type: topic
updated: 2026-10-02
verified: true
sources:
  - src/namifax/db/provider.py
  - src/namifax/db/bootstrap.py
  - src/namifax/db/adopt.py
  - src/namifax/db/sqlite_upgrade.py
  - src/namifax/db/seed.py
  - src/namifax/db/missing.py
  - src/namifax/db/repository.py
  - src/namifax/db/orm_repository.py
  - src/namifax/db/textsearch.py
  - src/namifax/models/__init__.py
  - src/namifax/models/meta.py
  - src/namifax/models/types.py
  - src/namifax/models/useraccount.py
  - src/namifax/models/systemconfig.py
  - src/namifax/services/system_config.py
  - src/namifax/alembic/env.py
  - src/namifax/alembic/versions/
  - src/namifax/views/no_database.py
  - tests/conftest.py
  - pyproject.toml
  - "[[db-layer-refactor-log]]"
  - "[[migrating-from-avantfax3]]"
  - "[[architecture-md-part1]]"
---

# 데이터베이스와 마이그레이션

2026-10-02 시점의 `src/`·`tests/` 를 직접 읽고 쓴 것이다. 시험은 이 세션에서 실행하지 않았으므로 아래 시험 이름은 "이 동작을 지키려고 있는 시험"이라는 뜻이며 통과 여부는 확인하지 않았다. 관련 주제: [[architecture-and-modules]], [[authentication-and-security]], [[migration-from-avantfax]], [[operations-and-deployment]], [[testing]], [[known-gaps-and-decisions]].

## 1. 지원 DB와 엔진 생성

- 지원: SQLite(기본), MySQL, MariaDB, PostgreSQL. 서버 드라이버는 선택 설치다: `pyproject.toml` 의 선택 의존성 `postgresql`(`psycopg[binary]`)과 `mysql`(`pymysql`). 개발 그룹에는 둘 다 들어 있다. [코드] `pyproject.toml`
- URL 우선순위: ini 의 `sqlalchemy.url` > 환경변수 `DATABASE_URL` > `AFDB_URL` > `NAMIFAX_DB_PATH`(SQLite 파일) > 현재 디렉터리의 `namifax.db`. [코드] `src/namifax/db/provider.py::resolve_database_url`; 시험 `tests/unit/test_db_injection.py` (`test_url_prefers_settings_over_env`, `test_url_database_url_beats_afdb_url`, `test_url_falls_back_to_namifax_db_path`, `test_url_default_is_cwd_namifax_db`)
- 엔진: `create_sa_engine(url)`. SQLite 는 `check_same_thread=False`, 메모리 DB(`sqlite://`)는 `StaticPool` 로 한 DB 를 공유한다. 서버 DB 는 `pool_pre_ping=True`. [코드] `provider.py`; 시험 `test_db_injection.py::test_memory_engine_shares_one_database_across_connections`
- 엔진은 앱 시작 때 한 번 만들어 `registry["dbengine"]` 에 두고, 전역 싱글턴은 없다. 서로 다른 URL 로 만든 두 앱은 격리된다. [코드] `src/namifax/models/__init__.py::includeme`; 시험 `test_db_injection.py::test_two_apps_with_different_urls_are_isolated`, `tests/unit/test_global_engine_removed.py`
- CLI 는 요청이 없으므로 `cli_session(settings, environ, ensure_schema)` 로 같은 URL 규칙의 세션을 연다. 블록이 정상 종료하면 커밋, 예외면 롤백, 엔진을 반환한다. 열린 세션은 컨텍스트 변수(`active_session()`)로 공유해 `avantfaxlog()`·`send_mail()` 이 같은 연결을 쓰게 한다(SQLite 에서 두 번째 쓰기 연결이 잠기는 것을 피함). [코드] `provider.py`; 시험 `tests/unit/test_cli_session.py`, `tests/unit/test_db_isolation_fixture.py`
- DB 에 연결할 수 없으면(`OperationalError`/`DBAPIError`) 503 과 "no database" 페이지(10초마다 재시도)를 보인다. 세부 오류는 로그에만 남긴다. [코드] `src/namifax/views/no_database.py`; 시험 `tests/unit/test_no_database_page.py`

> 모순: [[db-layer-refactor-log]] 는 `request.db`, `cli_db()`, `cli_unit()`, `DatabaseEngine`, `_DEFAULT_ENGINE` 을 전환 경과로 적는다. 현재 `src/` 에는 이 이름이 하나도 없다(grep 확인). 요청은 `request.dbsession`, CLI 는 `cli_session()` 이다. 같은 문서의 "SQLite 외 DB 는 시작 불가"(§14.2)도 과거 상태이며, 지금은 Alembic 으로 네 DB 를 만든다. `src/avantfax/`, `src/namifax/web/` 도 없다(`ls src`: `namifax` 하나).

## 2. 스키마 부트스트랩(`ensure_schema`)과 Alembic

`ensure_schema(engine, settings)` 는 앱 시작과 CLI(`ensure_schema=True`), 훅 호출 때 실행되는 멱등 함수다. [코드] `src/namifax/db/bootstrap.py`, 호출 `src/namifax/__init__.py`

1. `UserAccount` 테이블이 없으면 새 DB(`fresh`)로 본다.
2. 새 DB가 아니고 `alembic_version` 이 현재 head 와 같으면 SQLite 의 옛 테이블 보정만 하고 바로 돌려보낸다(빠른 경로). 시험 `tests/unit/test_schema_fast_path.py` (`test_the_second_start_does_not_run_the_migrations`)
3. 그 밖에는 순서대로: (SQLite만) `upgrade_existing_sqlite` → `adopt_existing_tables` → `upgrade_to_head`(Alembic `upgrade head`, 열린 연결을 `cfg.attributes["connection"]` 로 넘김) → 시드.
4. 시드: 데모 데이터를 켠 SQLite 에서는 `seed_if_empty`, 그 외 새 DB 에서는 기본 레코드(표지 3종)만. 기존 데이터는 바꾸지 않는다.
5. 어떤 단계든 실패하면 `RuntimeError("Database initialisation failed: ...")` 로 즉시 실패한다(조용히 넘어가지 않음). 시험 `tests/unit/test_multi_dialect_safety.py`, `tests/unit/test_bootstrap.py::test_a_failure_to_initialise_is_loud`

- 데모 데이터: `NAMIFAX_DEMO_DATA=1`(또는 ini `demo.data = true`)이고 SQLite 이고 사용자가 0명일 때만 생긴다. 서버 DB 에서 요청해도 경고하고 무시한다. 서버 DB 의 첫 관리자는 `namifax createuser` 로 만든다. 시험 `tests/unit/test_demo_data_optin.py`, `tests/unit/test_schema_seed_safety.py`, `test_bootstrap.py::test_server_database_gets_the_schema_and_default_records_only` [코드]
- Alembic 환경: `src/namifax/alembic/env.py`. ini 없이 호출되면(앱 내부 호출) 열린 연결을 받아 쓰고, CLI(`alembic -c development.ini ...`)에서는 앱과 같은 규칙으로 URL 을 푼다. `target_metadata` 는 `Base.metadata`. 시험 `tests/unit/test_alembic_wiring.py`, `test_bootstrap.py::test_alembic_environment_accepts_an_existing_connection`
- 리비전: 파일 이름 `YYYYMMDD_NNNN_설명.py`, 리비전 ID 는 `0001`~`0026` 의 직선 체인(분기 없음). 현재 head 는 **`0026`**(`20261002_0026_password_hash_width.py`, 비밀번호 해시 열을 `String(255)` 로 확장). 바로 앞은 `0025`(`page_size_no_default`), `0024`(`fax_number_address`), `0023`(`syslog_key_name`), `0022`(`smtp_password_length`), `0021`(`totp_lockout`). [코드] `src/namifax/alembic/versions/*.py` 의 `revision`/`down_revision` 값을 직접 읽어 체인 확인(2026-10-02). head 가 하나뿐임은 시험 `tests/unit/test_system_config_migration.py::test_there_is_exactly_one_head_revision` 이 지킨다.
- 리비전 `0001` 은 `SystemConfig`, `0002` `SystemSettings`, `0003` 네트워크 프린터, `0004` `SysLog`, `0005` 팩스 카테고리, `0006` 표지, `0007` `DynConf`, `0008` `Modems`, `0009` DID 경로, `0010` 바코드 경로, `0011` 배포 목록, `0012` `UserPasswords`, `0013`~`0015` 주소록 3테이블, `0016` `UserAccount`, `0017` `UserTOTP`, `0018` `UserWebAuthnCredentials`, `0019` `FaxOCR`, `0020` `FaxArchive` 다. [코드] 파일 이름으로 확인(각 파일 내용은 `0026` 만 정독).
- 모델과 마이그레이션이 어긋나지 않는지 비교하는 시험: `tests/unit/test_migrations_match_models.py` (SQLite, 서버 DB 두 가지).
- 리비전을 만들 때: `alembic -c development.ini revision --autogenerate -m "..."`, 적용은 `alembic -c development.ini upgrade head`. [코드] `src/namifax/alembic/versions/README.txt`

> 모순: [[architecture-md-part1]] 등 과거 문서에 "초기화 DDL 20개가 SQLite 전용" 같은 서술이 있다면 과거 상태다. 현재는 Alembic 이 DDL 을 만들고 `INSERT OR REPLACE`/`AUTOINCREMENT` 는 `src` 에서 코드가 아니라 주석에만 남아 있다(grep 으로 `db/seed.py`, `services/system_config.py` 의 설명문만 해당). `sqlite_master`/`PRAGMA` 는 SQLite 전용 보정 모듈 `db/sqlite_upgrade.py` 에만 있다.

## 3. 모델 구조와 테이블

- 모든 모델은 `namifax.models.meta.Base`(SQLAlchemy 2 `DeclarativeBase`, 이름 규칙 `NAMING_CONVENTION`)를 상속한다. `models/__init__.py` 가 모든 모델을 import 하고 `configure_mappers()` 를 부른다. [코드]
- 테이블은 현재 `models/*.py` 의 `__tablename__` 을 세어 **20개**다(2026-10-02, `grep -c __tablename__`). 그룹별:
  - 원본 AvantFAX 에서 온 14개: `AddressBook`, `AddressBookFAX`, `AddressBookEmail`, `BarcodeRoute`, `CoverPages`, `DIDRoute`, `DistroList`, `DynConf`, `FaxArchive`, `FaxCategory`, `Modems`, `SysLog`, `UserAccount`, `UserPasswords`. (시험 `tests/unit/test_legacy_database_compat.py` 의 `LEGACY_TABLES` 목록과 같다.)
  - 이식본이 추가한 6개: `SystemConfig`(키-값), `SystemSettings`(SMTP, 한 행), `NetworkPrinters`, `FaxOCR`, `UserTOTP`, `UserWebAuthnCredentials`.
- 테이블·열 이름은 레거시 SQL 의 철자 그대로(대소문자 포함)다. MySQL/MariaDB 가 리눅스에서 대소문자를 구분하므로 원시 SQL 이 계속 맞도록 하기 위해서다. [코드] `models/systemconfig.py`, `models/useraccount.py` 주석
- 공통 컬럼 타입 [코드] `src/namifax/models/types.py`:
  - `LegacyBoolean`: 옛 코드가 문자열 `'False'` 로 쓴 값도 거짓으로 읽는다(`Boolean` 은 비어 있지 않은 문자열을 참으로 읽어 권한 상승이 됨). 시험 `tests/unit/test_boolean_flags.py`
  - `IsoText`: 원본의 `TIMESTAMP`/`DATE` 열이든 이식본의 `VARCHAR` 든 앱에서는 ISO 문자열(`YYYY-MM-DD HH:MM:SS`)로 읽고 쓴다. 시험 `test_legacy_database_compat.py::test_dates_come_back_as_iso_text`
  - `LegacyHtmlString`/`LegacyHtmlText`: 원본이 `htmlentities` 로 저장한 문자(`m&uuml;ller`)를 읽을 때 되돌린다. 검색은 입력 그대로와 원본식 인코딩 두 패턴을 모두 쓴다(`db/textsearch.py::like_patterns`). 시험 `tests/unit/test_legacy_html_entities.py`
- 서비스는 `Repository("모델이름", db=session)`(별칭 `MDBOData`)로 `OrmRepository` 를 쓴다. 호출 방식은 원본 PHP 의 `find/new_entry/update_entry/delete_entry` 를 유지하되 값은 바인드 파라미터이고, DB 오류는 `False` 가 아니라 예외다. 숫자 문자열은 정수 열에 맞게 변환한다. 원시 `query` 는 지원하지 않는다. [코드] `db/repository.py`, `db/orm_repository.py`; 시험 `tests/unit/test_orm_repository.py`
- 사용자 입력 SQL 주입 방어: 주소록·팩스 큐·로그 조회 등에 대한 시험 `tests/unit/test_addressbook_search_injection.py`, `test_faxqueue_db_injection.py`, `test_services_db_injection.py`, `test_db_injection.py`. 과거 보고서의 SEC-01(주소록 검색 SQL 주입)·74곳 f-string SQL 지적은 값이 바인드되는 ORM 경로로 바뀌었다. 다만 `db/adopt.py` 와 `db/sqlite_upgrade.py`, `db/bootstrap.py` 에는 상수에서 만든 DDL·보정용 `text()` 가 남아 있다(입력값이 아님). [코드]

## 4. 레거시 AvantFAX DB 이어 쓰기 규칙

목적: 원본 AvantFAX 3.x(MySQL/MariaDB)가 만든 DB 에 이식본을 붙여 쓰고, 원본 PHP 도 같은 DB 를 계속 읽을 수 있게 한다([[migrating-from-avantfax3]]).

- `adopt_existing_tables` 규칙 [코드] `src/namifax/db/adopt.py`: 이미 있는 테이블은 Alembic 이 건드리지 않으므로, 모델이 필요로 하는 것을 덧붙인다 — (1) 없는 컬럼은 NULL 허용(모델이 서버 기본값을 주면 그 값과 함께) 컬럼으로 추가, (2) 모델이 선언한 인덱스 중 같은 열을 덮는 인덱스가 없으면 생성(유니크 인덱스는 제외), (3) 너무 좁은 열은 넓힘(MySQL/MariaDB 에서만 `UserAccount.last_ip` 를 45자로). **삭제·이름 변경·타입 변경과 기존 행 수정은 하지 않는다.** 시험 `tests/unit/test_legacy_database_compat.py` (서버 DB 시험: `test_starting_on_a_legacy_database_keeps_every_legacy_row`, `test_nothing_is_added_to_a_database_that_already_has_its_data`, `test_a_second_start_changes_nothing`, `test_every_column_the_models_need_exists_afterwards`, `test_the_legacy_column_types_are_left_alone`)
- 예외가 아닌 한 컬럼·테이블 이름은 원본 SQL 의 철자를 바꾸지 않는다. 새 기능이 필요한 컬럼은 "추가"만 한다(예: 주소록의 추가 필드, `0024`). 이를 어기면 원본 PHP 가 깨진다. 이 규칙은 코드 주석(`adopt.py` 모듈 docstring, `models/*.py` 주석)에 명시돼 있다. [코드]
- 한 가지 의도된 비호환: 이식본에서 로그인했거나 비밀번호를 바꾼 계정은 Argon2id 해시가 되어 원본이 읽지 못한다. 병행 운영이면 `NAMIFAX_PASSWORD_HASH=md5`. 자세히는 [[authentication-and-security]] 1절, [[migrating-from-avantfax3]] 4.3 [문서].
- 원본 설치의 기본 관리자 계정은 로그인 시 비밀번호 변경을 강제한다. 시험 `test_legacy_database_compat.py::test_the_legacy_administrator_can_log_in_and_must_change_the_password`
- 레거시 DB 위에서 수신·검색·주소록·계정·모뎀·경로·목록 관리가 모두 되는지 확인하는 시험이 같은 파일에 있다(`test_faxes_can_be_received_searched_and_listed`, `test_accounts_modems_routes_and_lists_can_be_managed`, `test_the_web_application_serves_a_legacy_database`, IPv6 주소 기록, 상대 `faxpath` 해석 등).
- 시험 데이터는 원본 설치 SQL(`create_tables.sql` 과 3.2.0/3.3.5 업그레이드 스크립트)을 `tests/` 아래 고정 파일로 두고 3.2.0·3.3.5 × MySQL·MariaDB 4가지로 DB 를 만든다. [코드] `tests/conftest.py::legacy_db`(파라미터 `("mysql","3.3.5")` 등), 상수 `LEGACY_ROOT`. 위치는 `tests/fixtures/legacy_sql/`(`LEGACY_ROOT`).

### SQLite 의 옛 테이블 보정(`sqlite_upgrade`)

이식본 초기 버전이 만든 SQLite 파일만 해당한다. `alembic upgrade` 보다 먼저 돌며 새 DB 에서는 아무것도 하지 않는다. 멱등이다. [코드] `src/namifax/db/sqlite_upgrade.py`; 시험 `tests/unit/test_sqlite_upgrade.py`

- 옛 테이블 이름 `DIDRouting`→`DIDRoute`, `FaxPDFCategory`→`FaxCategory`로 이름 변경(원본 철자에 맞춤).
- `UserPasswords` 의 `pwd_id`/`password` → `upid`/`pwdhash` 열 이름 변경.
- `AddressBook` 기본키 `ab_id` → `abook_id` 로 테이블을 재구성(모든 id 보존, 자식 테이블 연결 열 채움).
- 빠진 열 추가, 이식본이 중복으로 만든 id 열의 NULL 값을 원본 열에서 채움, `UserAccount` 플래그의 문자열 `'True'/'False'` 를 0/1 로 정규화(문자열인 값만). 시험 `tests/unit/test_boolean_flags.py`

> 이 이름 변경·재구성은 이식본이 자기 이전 버전의 SQLite 파일을 고치는 것이고, 원본 AvantFAX 의 MySQL DB 에는 적용되지 않는다. 원본 DB 에는 "이름 변경 금지, 추가만" 규칙이 그대로다. [코드] `sqlite_upgrade.py` 는 SQLite 전용(`ensure_schema` 가 `dialect.name == "sqlite"` 일 때만 호출).

## 5. SystemConfig 키 저장 방식

- 테이블 `SystemConfig(key String(255) PK, value Text)`. 접근은 `SystemConfigService(session)` 의 `get(key, default)`, `set(key, value)` 이다. `set` 은 `Session.merge` 로 upsert 하므로 네 DB 에서 같다(`INSERT OR REPLACE` 같은 방언 구문 없음). 값이 `NULL` 이면 기본값을 돌려준다. 따옴표·역슬래시는 그대로 저장한다. [코드] `src/namifax/services/system_config.py`; 시험 `tests/unit/test_system_config.py`, `tests/unit/test_system_config_migration.py`
- 비밀 값은 `set_secret`/`get_secret` 가 `secretbox` 로 암호화(`enc:v1:`)해 저장한다(`cloud_secret_key`). 키가 없으면 `SecretKeyError`. 자세히는 [[authentication-and-security]] 7절.
- 코드가 쓰는 키(2026-10-02, `src` 에서 `get/set/get_secret/set_secret("...")` 호출을 grep): `cloud_storage_type`, `cloud_bucket_name`, `cloud_endpoint_url`, `cloud_region_name`, `cloud_prefix`, `cloud_access_key`, `cloud_secret_key`, `storage_retention_days`, `storage_purge_tiff_days`, `storage_remote_sync_delete`, `sched_engine_state`, `sched_stopped`, 그리고 SAML 의 `saml_*` 15개([[authentication-and-security]] 5절). 동적 키 이름을 쓰는 호출은 이 grep 에 안 잡힐 수 있다. [코드 + 한계]
- `key` 는 MySQL/MariaDB 예약어라 원시 SQL 에서는 따옴표가 필요하다(시험 도우미 `tests/conftest.py::_quote_key_column`). ORM 경로는 알아서 인용한다. [코드]
- SMTP 설정은 `SystemConfig` 가 아니라 별도 단일 행 테이블 `SystemSettings`(id=1)에 둔다. 비밀번호 열은 암호화 토큰이 들어가도록 `String(512)`(마이그레이션 `0022`). [코드] `src/namifax/models/systemsettings.py`
- `AVANTFAX_*`, `ENABLE_*`, `MAX_PASSWD_SIZE` 같은 원본 `local_config.php` 설정은 DB 가 아니라 환경변수에서 읽는다. [코드] `src/namifax/common/settings.py` (`flag`, `text`, `number`)

## 6. 세션 주입(`request.dbsession`)

- `models.includeme` 가 `pyramid_tm`(요청 단위 트랜잭션), `pyramid_retry`, `zope.sqlalchemy` 를 붙이고 `request.dbsession`(reify)을 만든다. 요청이 정상 끝나면 커밋, 예외면 롤백한다. `tm.manager_hook` 은 `pyramid_tm` include 전에 설정해야 한다. [코드] `src/namifax/models/__init__.py`; 시험 `tests/unit/test_models_includeme.py` (`test_tm_manager_hook_is_configured_before_pyramid_tm_is_included`, `test_aborted_request_transaction_discards_session_writes`)
- zope.sqlalchemy 는 변경이 감지된 세션만 커밋한다. 원시 SQL 로 쓴 변경은 `mark_changed` 없이 롤백된다. 시험 `test_models_includeme.py::test_raw_sql_without_mark_changed_is_rolled_back` [코드 + 문서 [[db-layer-refactor-log]]]
- 서비스 클래스는 세션을 생성자로 받는다(`Service(db=request.dbsession)`). 세션 없이 만들면 `MissingDatabase` 자리표시자가 되어 첫 사용에서 `RuntimeError`("no database session injected")로 크게 실패한다. 다른 DB 를 조용히 쓰지 않는다. [코드] `src/namifax/db/missing.py::resolve_db`; 시험 `tests/unit/test_global_engine_removed.py::test_repository_without_db_is_a_loud_placeholder`
- 시험 훅: 환경(`environ`)의 `app.dbsession` 이 있으면 요청이 그 세션을 쓰고, 설정 `dbengine` 이 있으면 그 엔진을 쓴다. 시험이 세션·엔진을 공유하기 위한 것이다. [코드] `models/__init__.py::includeme`; 시험 `test_models_includeme.py::test_environ_hook_lets_tests_share_a_session`, `test_dbengine_setting_hook_is_honoured`

## 7. 서버 DB 시험

- 표시: pytest 마커 `serverdb`(`pyproject.toml` 의 `markers`, `--strict-markers`). 서버 주소가 설정돼 있지 않으면 건너뛴다. [코드] `pyproject.toml`, `tests/conftest.py`
- 서버 URL 환경변수: `NAMIFAX_TEST_PG_URL`(PostgreSQL, `postgresql+psycopg://...`), `NAMIFAX_TEST_MYSQL_URL`(`mysql+pymysql://...`), `NAMIFAX_TEST_MARIADB_URL`(`mariadb+pymysql://...`). 값은 여기 적지 않는다. [코드] `tests/conftest.py::SERVER_DB_ENV`
- 도우미: `throwaway_database(kind)` 가 `nami_test_<임의>` 이름의 빈 DB 를 만들고(MySQL 은 `utf8mb4`) 시험 후 삭제한다. `server_db_url` 픽스처는 설정된 서버마다 한 번씩 돌린다. `legacy_db` 픽스처는 원본 AvantFAX 가 만든 MySQL/MariaDB 상태를 재현한다.
- 전체 시험을 서버 DB 로 돌리기: 환경변수 `NAMIFAX_SUITE_DB=postgresql|mysql|mariadb` 를 주면 `isolated_database` autouse 픽스처가 시험마다 임시 서버 DB 를 만들고 앱으로 스키마를 만든 뒤 데모 행을 넣는다(앱은 서버 DB 에 데모 데이터를 만들지 않으므로 시험 쪽에서 `_seed_server_database`). PostgreSQL 에서는 대소문자 혼합 테이블 이름을 따옴표로 감싸고, 시퀀스를 `sync_sequences` 로 맞춘다. [코드] `tests/conftest.py`
- 기본 실행은 시험마다 임시 SQLite 파일을 쓰고 작업 디렉터리의 `namifax.db` 는 건드리지 않는다(`DATABASE_URL`/`NAMIFAX_DB_PATH` 를 임시 경로로 설정). 시험 `tests/unit/test_db_isolation_fixture.py`
- 서버 시험이 있는 파일(`serverdb` 마커 또는 `server_db_url` 사용)은 `grep` 으로 20여 개가 나온다(예: `test_bootstrap.py`, `test_system_config_migration.py`, `test_orm_repository.py`, `test_user_account_orm.py`, `test_totp_orm.py`, `test_webauthn_orm.py`, `test_syslog.py`, `test_legacy_database_compat.py`). 개수는 시점에 따라 달라지므로 적지 않는다.
- 이 세션에서는 서버 DB 시험을 실행하지 않았다. 서버 DB 에서 통과한다는 주장은 코드와 시험 구조로 본 "지원하도록 작성됨"이지 이 세션의 실행 결과가 아니다. [추정: 이전 과거 문서의 "PostgreSQL 16 / MySQL 8.4 검증" 서술은 [[db-layer-refactor-log]] [문서]]
