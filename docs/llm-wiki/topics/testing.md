---
title: 시험
type: topic
updated: 2026-10-02
sources: [pyproject.toml, tests/conftest.py, tests/sqlsession.py, tests/request_identity.py, tests/unit/test_ko_catalog_complete.py, tests/unit/test_legacy_trees_removed.py, tests/unit/test_fax_archive_orm.py, tests/unit/test_migrations_match_models.py, tests/test_i18n.py, tests/fixtures/, "[[architecture-md-part2]]", "[[agents-md-legacy-instructions]]", "[[db-layer-refactor-log]]"]
verified: true
---

# 시험

## 구성
- 도구: `pytest`, `pytest-cov`, `webtest`(dev 의존성 그룹). 설정은 `pyproject.toml` 의 `[tool.pytest.ini_options]`: `--strict-markers`, `testpaths = ["tests"]`, `pythonpath = [".", "src"]`, `faulthandler_timeout = 20`(20초 넘게 끝나지 않는 시험은 모든 스레드 스택을 stderr 에 덤프하고 계속 진행). [코드] `pyproject.toml`
- 디렉터리: `tests/conftest.py`(공용 픽스처), `tests/sqlsession.py`, `tests/request_identity.py`, `tests/test_i18n.py`, `tests/test_helpers_media.py`, `tests/unit/`(나머지 전부, 파일 수백 개), `tests/unit/linked_db.py`, `tests/unit/data/fax_archive_search_golden.json`, `tests/fixtures/`(`legacy_sendfax_commands.json`, `legacy_sql/create_tables.sql`, `legacy_sql/db-update-334.sql`). [코드] `git ls-files tests`
- 시험 개수: `uv run pytest --collect-only -q` 로 2026-10-02 에 **2314개 수집**됨(수집만 했고 실행하지 않음). 이 수치는 곧 낡는다. [코드] 같은 명령
- 시험 이름이 `*_request_db.py`, `*_db.py`, `*_orm.py` 인 파일은 요청 세션 주입, 서비스 DB 주입, ORM 구현을 각각 확인하는 묶음이다. [코드] `ls tests/unit`
- 영역별 파일 예: CLI 훅(`test_cli_faxrcvd*`, `test_cli_notify*`, `test_cli_cron*`, `test_cli_dynconf`, `test_cli_faxcover`), 보관함(`test_archive_*`), 인증(`test_auth_*`, `test_totp*`, `test_webauthn*`, `test_saml*`, `test_security_*`), 스케줄러(`test_scheduler*`), 저장소(`test_storage_*`, `test_cloud_storage`), 마이그레이션(`test_alembic_wiring`, `test_migrations_match_models`, `test_sqlite_upgrade`, `test_legacy_database_compat`), i18n(`test_ko_*`, `tests/test_i18n.py`). [코드] `git ls-files tests`

## 픽스처와 격리 ([코드] `tests/conftest.py`)
- `isolated_database`(autouse): 시험마다 `tmp_path` 의 SQLite 파일을 만들어 `DATABASE_URL`, `NAMIFAX_DB_PATH` 로 지정하고 `AFDB_URL` 은 지운다. 작업 트리의 `namifax.db` 는 건드리지 않는다.
- `_demo_data`(autouse): `NAMIFAX_DEMO_DATA=1`(샘플 계정과 행 생성). 기본 동작을 시험할 때는 이 변수를 시험 안에서 지운다(`test_demo_data_optin.py`).
- `_secret_key`(autouse): 고정 `NAMIFAX_SECRET_KEY`. 키가 없는 경우를 시험할 때만 지운다.
- 시험 속도를 위해 Argon2 비용을 낮춘다(`NAMIFAX_ARGON2_TIME_COST=1`, `MEMORY_COST=1024`, `PARALLELISM=1`; 운영은 라이브러리 기본값).
- `dbengine`, `app`(= `create_app(dbengine=engine)`), `tm`(실행 취소되는 트랜잭션 관리자), `dbsession`, `testapp`(WebTest, `HTTP_HOST=example.com`), `app_request`, `dummy_request`, `dummy_config`, `admin_call`(관리자 권한으로 뷰 직접 호출). 쓰기는 `tm.doom()` 으로 시험 끝에 사라진다.
- `seeded_db`: 스키마와 시드가 들어간 메모리 `SqlSession`(`tests/sqlsession.py`, 옛 시험이 쓰는 원시 SQL 편의 메서드를 가진 `Session`).
- PostgreSQL 용 보정: 따옴표 없는 혼합 대소문자 테이블 이름을 따옴표로 감싸는 리스너, MySQL 계열에서 예약어 `key` 를 백틱으로 감싸는 리스너, 시퀀스 보정(`sync_sequences`).
- 같은 이유로 원시 SQL 시험은 서버 DB 에서 돌 때 이 보정에 기대고 있다. [코드] 같은 파일

## 서버 DB 시험 (`serverdb` 마커)
- 마커 정의: `serverdb: 실제 PostgreSQL/MySQL/MariaDB 서버의 일회용 DB 에서 도는 시험(서버 URL 이 없으면 건너뜀)`. [코드] `pyproject.toml`
- 환경변수(없으면 해당 시험은 skip): `NAMIFAX_TEST_PG_URL`(예 `postgresql+psycopg://user:pw@host:port/postgres`), `NAMIFAX_TEST_MYSQL_URL`(`mysql+pymysql://...`), `NAMIFAX_TEST_MARIADB_URL`(`mariadb+pymysql://...`). 접속 정보 값은 위키에 적지 않는다. [코드] `tests/conftest.py` `SERVER_DB_ENV`
- `throwaway_database(kind)` 가 `nami_test_<8자리>` DB 를 만들고(MySQL 계열은 `utf8mb4`) 끝나면 지운다. 픽스처 `server_db_url` 은 설정된 서버마다 1회씩 돈다. `legacy_db` 픽스처는 원본 AvantFAX 가 만든 DB(`3.3.5`, `3.2.0`)를 MySQL/MariaDB 에 재현한다(`tests/fixtures/legacy_sql`). [코드] `tests/conftest.py`
- **스위트 전체를 서버 DB 로 돌리기**: `NAMIFAX_SUITE_DB=postgresql|mysql|mariadb`(해당 `NAMIFAX_TEST_*_URL` 필요). 그러면 `serverdb` 마커가 없는 시험도 시험마다 일회용 서버 DB 에서 돌고, 데모 행은 `seed_demo_records` 로 직접 넣는다(앱은 SQLite 에서만 데모 데이터를 만든다). [코드] `tests/conftest.py` `isolated_database`, `src/namifax/db/bootstrap.py`
- 실행 예(상태를 바꾸므로 이 조사에서는 실행하지 않았다): `NAMIFAX_TEST_PG_URL=... uv run pytest -m serverdb`. [추정] 명령 형태는 마커와 변수명에서 유추.
- DB 쪽 설계는 [[database-and-migrations]].

## 실행 명령
- 전체: `uv run pytest` / 수집만: `uv run pytest --collect-only -q` / 한 파일: `uv run pytest tests/unit/test_ko_catalog_complete.py` / 키워드: `-k`. [코드] `pyproject.toml` 설정과 표준 pytest 사용법
- 주의: `tests/test_i18n.py::test_i18n_cli_compile` 은 `.mo` 파일을 다시 쓴다. [코드] [[i18n-and-ui]]
- 주의: 개발 서버(8000/8001 포트)와 시험은 독립이다. 시험은 임시 DB 를 쓰고 포트를 열지 않는다(WebTest). [코드] `tests/conftest.py`

## 골든 마스터는 삭제되었다
- 이전 방식의 골든 마스터(레거시 입출력, 웹 HTML/폼 계약 스냅샷)와 `dev/`, `legacy/` 는 저장소에 없다. 삭제 커밋: `dev/` → `01f2f64`, `legacy/` → `9408385`, 경로 이동 이력 `72a7324`. 필요하면 `git show <커밋>:<경로>` 로 읽는다. [코드] `git log`, `git ls-files`
- 영향:
  - 레거시 PHP 를 기준으로 한 차분 비교(원본과 같은 HTML/DOM, 같은 훅 출력)는 더 이상 시험이 자동으로 지켜 주지 않는다. 그 역할은 현재 시험이 기대값을 직접 박아 둔 방식(예: `tests/fixtures/legacy_sendfax_commands.json`)으로 부분적으로만 남아 있다. [코드] 파일 존재 / [추정] 완전한 대체는 아님
  - 원본의 SQL 은 시험 기반 자료로만 남았다: `tests/fixtures/legacy_sql/*.sql`. [코드]
  - "골든" 이라는 이름은 한 군데 남아 있다: `tests/unit/data/fax_archive_search_golden.json` 는 옛 SQL 구현을 지우기 전에 기록한 보관함 검색 응답이며 ORM 쿼리가 같은 답을 내야 한다(서버 DB 시험에서도 같은 행렬이 돈다). 이것은 레거시 PHP 골든 마스터와 다른 것이다. [코드] `tests/unit/test_fax_archive_orm.py`
  - 원본과 새 코드를 나란히 돌리는 이관 리허설 도구는 `tools/migration_rehearsal/` 에 따로 있다(시험 스위트 밖). [코드] `git ls-files tools`
- 삭제 상태를 확인하는 시험: `test_legacy_trees_removed.py`(`avantfax` 패키지, `namifax.web` 부재, 배치 도구가 `namifax.cli` 에 있음, 앱 생성 실패를 숨기지 않음). [코드]
> 모순: [[architecture-md-part2]], [[agents-md-legacy-instructions]] 는 "모듈 하나를 교체할 때마다 골든 마스터 E2E 를 돌린다" 를 규칙으로 말한다. 지금은 골든 마스터가 없으므로 이 절차를 그대로 따를 수 없다. [코드] 위 삭제 근거.

## 시험이 지키는 주요 규칙
| 규칙 | 시험 | 비고 |
|---|---|---|
| 모든 메시지가 한국어로 번역됨 | `test_ko_catalog_complete.py::test_every_message_of_the_template_is_translated_into_korean` | `.pot` 기준, fuzzy 불가 |
| 번역이 자리표시자를 유지함(위키 지시문의 `placeholders_translated`) | 같은 파일 `test_translations_keep_the_placeholders_of_the_original_text` | `%(x)s`, `%d` 등 |
| 컴파일된 `.mo` 가 새 문구를 가짐 | 같은 파일 | `.mo` 재컴파일 필요 |
| 화면이 `?lang=ko` 로 한국어로 나옴 | `test_ko_pages.py` | |
| 로케일 24개, 별칭, 협상 우선순위 | `tests/test_i18n.py` | `len(SUPPORTED_LOCALES) == 24` |
| 마이그레이션과 모델이 일치함 | `test_migrations_match_models.py`, `test_alembic_wiring.py` | 스키마 변경 시 리비전 추가 필요 [추정: 이름 기준] |
| 요청 단위 DB 주입, 전역 엔진 없음 | `test_global_engine_removed.py`, `test_db_injection.py`, `test_*_request_db.py` | |
| 다중 DB 방언 안전 | `test_multi_dialect_safety.py` | |
| 데모 데이터는 명시적으로 켤 때만 | `test_demo_data_optin.py` | 기본 꺼짐 |
| 상태 변경은 POST, 출처 검사 | `test_state_changing_posts.py`, `test_logout_post.py` | `origin_guard` 관련 |
| 구형 트리 제거 유지 | `test_legacy_trees_removed.py`, `test_legacy_redirects.py` | |
| 시험이 DB 를 건드리지 않음 | `test_db_isolation_fixture.py` | |
[코드] 파일 존재는 `git ls-files tests` 로 확인. 표의 "비고" 중 [추정] 표시가 없는 것은 각 파일의 첫 부분 또는 이름으로 판단했다(모든 시험 본문을 읽은 것은 아니다).
- 관련: [[architecture-and-modules]], [[overview]]
