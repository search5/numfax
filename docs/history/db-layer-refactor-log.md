# DB 계층 전환 기록 (원문 보존)

`ARCHITECTURE.md`의 13~14장에 있던 전환 과정 기록(DB 엔진 주입 → ORM 전환 → 레거시 엔진 제거)을 그대로 옮겼다.
**현재 상태는 `ARCHITECTURE.md` 17~18장이 기준**이며, 이 문서는 당시의 판단과 근거를 찾아볼 때 쓴다. 본문의
`DatabaseEngine`, `request.db`, `cli_db`, `cli_unit`, `schema.py` 등은 모두 제거되었다.

## 13. DB 엔진 주입 리팩터링 (Spec 48, 방식 A 브리지)

- 목적: 전역 싱글턴 `_DEFAULT_ENGINE` 제거 (결함 F5-12, R4F-13/F5-08). `DatabaseEngine`(SQL.php 의미론)은 유지하고 연결만 주입한다.
- 흐름: `create_app(**settings)` → `resolve_database_url` → `create_sa_engine` → `registry["dbengine"]` → 요청마다 `request.db` (풀 커넥션을 감싼 `DatabaseEngine`, 요청 종료 시 반환).
- URL 우선순위: `sqlalchemy.url` > `DATABASE_URL` > `AFDB_URL` > `NAMIFAX_DB_PATH`/`cwd/namifax.db`.

| 루프 | 범위 | 상태 | 비고 |
| :---: | :--- | :---: | :--- |
| 1 | `db/provider.py`, `DatabaseEngine.from_connection`, `create_app`, `request.db` | `[COMPLETE]` | `tests/unit/test_db_injection.py` 11개, 전체 413 통과 |
| 2 | `views/admin.py` smtp/printers/storage/saml 4개 뷰: `DatabaseEngine()` 폴백 및 `db_engine` 우회 제거, `request.db` 직접 사용 | `[COMPLETE]` | `tests/unit/test_admin_views_request_db.py` 9개, 전체 422 통과 |
| V1 | `views/inbox.py` 5개 뷰 + 공유 헬퍼 `get_all_admin_modems(db)`: `ArchiveIn/AFAddressBook(db=request.db)` | `[COMPLETE]` | `tests/unit/test_inbox_views_request_db.py` 6개, 전체 447 통과 |
| V2 | `views/modals.py` 6개 뷰: `ArchiveIn/AFAddressBook(db=request.db)` 8곳 | `[COMPLETE]` | `tests/unit/test_modals_views_request_db.py` 6개, 전체 453 통과. `FaxQueue()`는 내부에서 `AFUserAccount()`를 만들어 C 단계에서 처리 |
| V3 | `views/ajax.py` 9개 뷰: `ArchiveIn/AFAddressBook/FaxModem/DistributionList(db=request.db)`, `get_all_admin_modems(request.db)` | `[COMPLETE]` | `tests/unit/test_ajax_views_request_db.py` 9개, 공용 `tests/conftest.py::seeded_db` 도입(전역 DB 시드 의존 제거), 전체 462 통과. `FaxQueue()`는 C 단계 |
| V4 | `views/admin.py` 도메인 관리 뷰(users/modems/did/logs/covers/categories/barcodes/dynconf/fax2email): 클래스 19곳 `db=request.db`, 헬퍼 `get_all_admin_users/get_all_syslogs(db)`, 임포트를 `avantfax.services.*`→`namifax.services.*`로 통일 | `[COMPLETE]` | `tests/unit/test_admin_views_domain_request_db.py` 16개, 전체 478 통과 |
| V5 | `views/helpers.py` 팝업·vCard 업로드 뷰 6개: `AFAddressBook/FaxPDFCategory/DistributionList(db=request.db)` | `[COMPLETE]` | `tests/unit/test_helpers_views_request_db.py` 7개, 전체 485 통과 |
| V6 | `views/distrolist.py`: `DistributionList(db=request.db)` 5곳 + `get_all_distrolists(db)` | `[COMPLETE]` | `tests/unit/test_distrolist_views_request_db.py` 7개, 전체 492 통과 |
| V7 | `views/addressbook.py`: `AFAddressBook(db=request.db)` 5곳 + `get_all_companies(db)` | `[COMPLETE]` | `tests/unit/test_addressbook_views_request_db.py` 10개, 전체 502 통과 |
| V8 | `views/auth.py`(login/login_totp), `views/settings.py`: `getattr(request,"db",None)` → `request.db`, `AFUserAccount(db=request.db)` | `[COMPLETE]` | `tests/unit/test_auth_settings_views_request_db.py` 5개, 전체 507 통과. `forgot`/`pwdexpired` 뷰는 DB를 쓰지 않는 스텁(별도 확인 필요) |
| V9 | `views/webauthn.py`(3), `archive.py`, `sendfax.py`, `outbox.py`: `request.db` 주입 | `[COMPLETE]` | `tests/unit/test_misc_views_request_db.py` 6개, 전체 513 통과 |
| V10 | `security.py` `NamiFaxSecurityPolicy.remember()`: `AFUserAccount(db=request.db)` | `[COMPLETE]` | `tests/unit/test_security_policy_request_db.py` 1개, 전체 514 통과 |
| V11 | `services/faxqueue.py`에 `db` 인자 추가(내부 `AFUserAccount(db=self.db)`), `views/ajax·modals·outbox`는 `FaxQueue(db=request.db)` | `[COMPLETE]` | `tests/unit/test_faxqueue_db_injection.py` 4개, 전체 518 통과 |
| V12 | `views/addressbook.py` emailbook `MDBOData(..., db=request.db)` 2곳, `SAMLService.provision_or_get_user`의 `AFUserAccount(db=self.db)` | `[COMPLETE]` | `tests/unit/test_remaining_web_db_injection.py` 3개, 전체 521 통과 |
| V-audit | 웹 계층 AST 전수 점검: `views/*`, `security.py`, 웹 경로 서비스는 모두 주입 완료 | `[COMPLETE]` | 잔여: ① `common/helpers.py` `OcrService()`는 텍스트 추출 전용이라 DB 불필요(유지) ② `cli/*`(C 단계) ③ `db/bridge_cli.py` `FaxQueue`(C/F) ④ `web/*` 폴백 앱(13.2 결정 대기) |
| C0 | `db/provider.py` `cli_db(settings, environ, ensure_schema)` 컨텍스트 매니저: 웹과 동일한 URL 해석, 스키마 보장, 종료/오류 시 커넥션·풀 해제 | `[COMPLETE]` | `tests/unit/test_cli_db.py` 4개 |
| C1 | `cli/faxrcvd.py`: `run_faxrcvd(argv, *, db=None)` — 미주입 시 `cli_db()`로 1회 오픈, 5개 도메인 객체와 `OcrService`에 동일 db 전달, usage 경로는 DB를 열지 않음 | `[COMPLETE]` | `tests/unit/test_cli_faxrcvd_db.py` 3개, 전체 528 통과. 기존 phase3 테스트는 `db=MagicMock()` 주입으로 작업 트리 DB 접근 제거 |
| C2 | `cli/notify.py`: `run_notify(argv, *, db=None)` — usage/qfile 부재 시 DB 미오픈, `AFAddressBook/AFUserAccount/ArchiveOut(db=db)` | `[COMPLETE]` | `tests/unit/test_cli_notify_db.py` 3개 |
| C3 | `cli/cron.py`: `run_cron(..., *, db=None)` — 필요한 작업(-i/-d/-p)이 있을 때만 지연 오픈, 한 번 열어 공유 | `[COMPLETE]` | `tests/unit/test_cli_cron_db.py` 4개 |
| C4 | `cli/dynconf.py`, `phb.py`, `user.py`, `faxcover.py`: 동일 패턴. `faxcover`는 연결 없는 `DatabaseEngine()`과 존재하지 않는 `reduce_single` 인자 때문에 발신자 조회가 항상 조용히 실패하던 결함을 `query()`+`get_records()`로 수정 | `[COMPLETE]` | `tests/unit/test_cli_misc_db.py` 9개, 전체 544 통과 |
| C5 | `main.py` `serve_main`: `get_default_engine()` 제거 → `cli_db()`로 스키마 보장, Pyramid 앱 생성 실패를 stderr에 기록한 뒤 폴백 | `[COMPLETE]` | `tests/unit/test_serve_main_db.py` 2개, 전체 546 통과 |
| C6 (P2) | `namifax.cli`에 `ocr_import`, `create_thumbnails`, `import_users`, `import_blacklist`, `reroute` 이식(`main(args, *, db=None)` + `cli_db()`), `main.py` 디스패치를 `namifax.cli.*`로 전환. `ocr_import`는 항상 `""`을 반환하던 스텁 `ocr_faxcontent` 대신 `common.helpers.ocr_faxcontent`(실제 OCR) 사용 | `[COMPLETE]` | `tests/unit/test_cli_batch_tools_db.py` 17개, 전체 565 통과. `import_archive`는 결함 F4-19의 스텁이라 이식하지 않음 |
| F (P5) | `Repository`의 `get_default_engine()` 폴백을 `resolve_db`(미주입 시 첫 사용에서 `RuntimeError`)로 교체하고 `get_default_engine`/`set_default_engine`/`_DEFAULT_ENGINE` 삭제. 테스트의 "전역 엔진 미생성" 스캐폴딩은 구조적 보장으로 대체 | `[COMPLETE]` | `tests/unit/test_global_engine_removed.py` 11개, 전체 566 통과(고정/랜덤). 잔여 `DatabaseEngine()`는 의도된 2곳: `common/helpers.py` `OcrService()`(텍스트 추출 전용), `db/bridge_cli.py`(PHP FFI 프로토콜의 `connect` 요청으로 연결을 지정) |

### 13.1 루프 3에서 발견된 기존 결함 (미해결, 별도 처리 필요)
- `[NEEDS_CLARIFICATION]` `services/ocr.py`(`FaxOCR`), `services/webauthn.py`(`UserWebAuthnCredentials`)의 `CREATE TABLE`이 MySQL 전용 DDL(`AUTO_INCREMENT`, `INDEX`, `ENGINE=InnoDB`)이고 `db/schema.py`에도 없다. SQLite에서는 `try/except: pass`로 가려진 채 테이블이 생성되지 않는다. 운영 DB가 MySQL/SQLite 중 무엇인지 확정 후 `schema.py`로 이관 필요.
- 이전에는 위 서비스들이 연결 없는 `DatabaseEngine()`을 썼기 때문에 DB 쓰기가 전부 조용히 실패했다. 주입으로 이 경로가 실제 DB를 보게 되므로 위 DDL 이슈가 표면화된다.

### 13.2 `src/namifax/web/*` (JSON/WSGI 폴백 앱) 조사 결과
- **포팅 누락이 아님**: 모듈 32~37(`WebAuth/Inbox/Outbox/Archive/SendFax/Admin`, specs 32~37)의 `[COMPLETE]` 산출물로, 레거시 PHP 페이지 컨트롤러를 JSON/WSGI 핸들러로 옮긴 1세대 웹 계층이다. 이후 12절의 Pyramid + Jinja2 뷰가 같은 레거시 페이지를 대체해 실제 UI가 되었다.
- **참조는 살아 있음**: `main.py:33`(임포트), `serve_main`의 `except Exception: app = create_app()`, `namifax/__init__.py`의 `except ImportError` 폴백, `security.py`의 `web.session.SessionManager`(활성 사용).
- **테스트 공백**: 테스트는 `avantfax.web.*`(src/avantfax 사본)만 대상이며 `namifax.web.views.*`에는 테스트가 없다. 두 트리는 쿠키명 등 치환 흔적만 다른 사본이다.
- **주의**: `serve_main`이 Pyramid 앱 생성 실패를 로그 없이 삼키고 JSON 앱으로 대체한다. 루프 1 이후 DB 초기화 오류가 예외로 전파되므로, 장애가 조용히 JSON 앱으로 바뀔 수 있다.
- `[NEEDS_CLARIFICATION]` 폴백 앱을 유지할지(→ `AvantFaxApp(db=...)` 주입 필요) 제거할지(→ Dead Code 프로토콜로 '제거된 로직' 기록, `SessionManager`는 이전) 결정 필요. 결정 전까지 V 루프에서 제외.

### 13.3 `src/avantfax/*` 복사본 패키지 (발견: 테스트가 복사본을 검증함)
- `src/avantfax`(56개 .py)는 `src/namifax`의 이름 치환 복사본이며 이후 서로 갈라졌다(`cli/faxrcvd`, `notify`, `cron`, `db/engine` 등은 약 50~64줄 차이, `services/did` 등은 치환만 다름).
- **테스트 91개 파일 중 48개가 `avantfax.*`를 임포트한다.** 배포 패키지(`pyproject` name=`namifax`)가 아니라 복사본을 검증하는 테스트가 많다. 예: `test_cli_faxrcvd.py`, `test_cli_cron.py`, `test_cli_faxcover.py`, `test_cli_dynconf.py`는 `avantfax.cli.*` 대상이다. Spec 48 루프의 `namifax` 변경은 신규 `*_db.py` 테스트로만 검증된다.
- `namifax` 명령 `ocr-import`, `create-thumbnails`, `import-users`, `import-blacklist`, `reroute`는 `namifax.cli`에 대응 모듈이 없어 `avantfax.cli.*`를 직접 호출한다(`main.py:174-190`). 이 모듈들은 `FaxPDFArchive()`, `AFUserAccount()`, `FaxModem()`을 `db` 없이 만든다.
- `avantfax.db.engine.get_default_engine`은 `namifax`의 것을 위임 호출하는 shim이라, `namifax`의 전역 엔진을 지우면 `avantfax.*`가 전부 깨진다.
- `[NEEDS_CLARIFICATION]` `avantfax` 복사본을 제거(테스트를 `namifax`로 이전, 누락된 5개 CLI를 `namifax.cli`로 이식)할지, 유지할지 결정 필요.

### 13.4 P2 관찰 사항
- `DynConf`와 `DynamicConfig` 두 테이블이 스키마에 공존하며 초기화 시 한 번 단방향 동기화된다(`schema.py:270-275`). 서비스(`DynamicConfig` 서비스, `import_blacklist`)는 `DynConf`만 쓰므로 `DynamicConfig` 테이블에 직접 넣은 행은 서비스에 보이지 않는다. 정리 대상.
- `namifax.main`이 모듈 이름이자 `namifax/__init__.py`의 `main = create_app` 함수 이름이다. `from namifax import main`의 결과는 임포트 순서에 따라 달라진다(paste 진입점 `main = "namifax:main"` 때문). 테스트는 `importlib.import_module("namifax.main")`을 사용한다.

### 13.5 P3 (테스트를 배포 패키지로 전환) 결과와 관찰
- `avantfax` 대상 테스트 41개 파일의 임포트·패치 경로를 `namifax`로 전환했다(웹 핸들러 테스트 6개 파일은 P4에서 `web/*`와 함께 삭제하므로 제외). 전환 후 실패는 3건뿐이었고 모두 `namifax`가 의도적으로 개선된 쪽이었다: 메일러 발신자명 `NamiFAX`, `FaxQueue.killjob/faxalter`의 셸 문자열 → `subprocess.run` 인자 리스트(+`FAXUSER` 환경변수), `faxcover`의 DB 주입. 테스트를 배포 코드 동작에 맞췄다.
- `tests/conftest.py`에 autouse `isolated_database` 픽스처 추가: 테스트마다 `DATABASE_URL`/`NAMIFAX_DB_PATH`를 tmp 파일로 지정하고 전역 엔진을 초기화한다. 전환된 CLI 테스트가 작업 트리의 `namifax.db`를 변경하던 문제(R4F-13/F5-09)를 근본적으로 막는다.
- 격리로 드러난 숨은 의존: (1) `create_thumbnails` "빈 아카이브" 테스트는 연결 없는 엔진 덕에 우연히 통과했다 → 빈 DB를 명시 주입. (2) 새 DB에서는 시드 순서 때문에 데모 팩스(`fid=1`)가 `Acme Corp`에 연결되지 않았다(주소록 시드가 팩스 시드보다 뒤). 기존 전역 DB는 두 번째 초기화에서야 채워졌다 → `seed_database_if_empty` 끝에서 멱등 재연결(`tests/unit/test_schema_seed_first_run.py`).
- `[관찰]` `AddressBook`의 기본키는 `ab_id`인데 코드와 시드는 `abook_id` 컬럼을 참조하고 시드 행에서 `NULL`이다. 인박스의 `companyid` 연결이 시드에서는 항상 비어 있다. 정리 대상.
- `[관찰]` `seed_database_if_empty`는 작업 디렉터리 상대 경로(`faxes/2026/09/29/...`)에 샘플 PDF/TIFF를 쓴다. 초기화할 때마다 cwd에 파일이 생긴다.

### 13.6 제거된 로직 (P4, Dead Code Removal Protocol)
- **`src/avantfax/` 전체(56개 .py)**: `src/namifax/`의 이름 치환 복사본. 모든 모듈이 `namifax`에 존재하며 테스트는 P3에서 `namifax` 대상으로 전환했다. 복사본에만 있던 CLI 5개는 P2에서 `namifax.cli`로 이식했다.
  - `avantfax/cli/import_archive.py`: 결함 F4-19의 스텁("Imported N faxes"만 출력)이며 진입점에도 없었다. 이식하지 않고 제거한다. 레거시 `tools/import_archive.php`의 실제 구현은 후속 작업으로 남는다.
- **`src/namifax/web/` 전체(`app.py`, `session.py`, `views/{admin,archive,auth,inbox,outbox,sendfax}.py`)**: 모듈 32~37(`WebAuth/Inbox/Outbox/Archive/SendFax/Admin`)이 만든 1세대 JSON/WSGI 폴백 앱. 12절의 Pyramid + Jinja2 뷰가 같은 레거시 페이지를 대체했다. `SessionManager`는 P1에서 `namifax/sessions.py`로 이동했다.
  - `namifax.create_app`의 `except ImportError` 폴백과 `serve_main`의 JSON 앱 폴백도 제거했다. Pyramid 앱 생성에 실패하면 `serve_main`은 오류를 stderr에 출력하고 종료 코드 1로 끝난다(조용한 대체 서비스 없음).
  - 함께 삭제한 테스트: `test_web_{admin,app,archive,auth,inbox,outbox,sendfax}.py` 7개 파일(제거된 핸들러 대상).
- 위 모듈 매트릭스(1~21절)의 `src/avantfax/...` 경로 표기는 실제 위치인 `src/namifax/...`로 정정했다.

### 13.7 Spec 48 최종 상태
- 프로세스 전역 DB 엔진(`_DEFAULT_ENGINE`)은 존재하지 않는다. DB 접근 경로는 두 가지뿐이다: 웹은 `create_app`이 설정(`sqlalchemy.url` > `DATABASE_URL` > `AFDB_URL` > `NAMIFAX_DB_PATH`)에서 만든 엔진 하나를 `registry["dbengine"]`에 보관하고 요청마다 `request.db`로 제공한다. CLI는 같은 URL 해석을 쓰는 `provider.cli_db()` 컨텍스트로 명령 단위 연결을 연다.
- 도메인 객체/서비스는 `db`를 주입받으며, 주입하지 않으면 연결 없는 엔진으로 조용히 실패하는 대신 첫 사용에서 `RuntimeError`를 낸다.
- 테스트는 `tests/conftest.py`의 autouse `isolated_database`로 테스트마다 별도 DB를 쓰고, 공용 `seeded_db` 픽스처로 시드된 격리 DB를 명시 주입한다.
- 다음 트랙(B): `request.dbsession`(SQLAlchemy ORM) 전환. 선행 조건은 `pyramid_tm`/`zope.sqlalchemy` 의존성 추가와 ORM 모델 정의이며, 모듈 단위 파일럿(예: `SystemSettings`/`SysLog`)으로 시작한다. 한 요청에서 `request.db`와 `request.dbsession`을 동시에 쓰지 않도록 모듈 단위로 전환한다.

---

## 14. B 트랙 준비 (B0): Pyramid starter 구조 도입

Pyramid cookiecutter starter(2.1-branch, jinja2 + sqlalchemy)를 임시 디렉터리에 생성해 비교한 뒤, 우리에게 없던 인프라를 도입했다. 생성물은 확인 후 삭제했다.

| 단계 | 내용 | 상태 | 검증 |
| :---: | :--- | :---: | :--- |
| B0-1 | 의존성 추가: `pyramid_tm`, `pyramid_retry`, `transaction`, `zope.sqlalchemy`, `alembic` | `[COMPLETE]` | 전체 통과 유지 |
| B0-2 | `models.includeme`를 starter 구조로 완성: `tm.manager_hook`을 `pyramid_tm` include **전에** 설정(기존에는 후에 설정해 무시됨), `pyramid_retry` include, `get_tm_session`, `app.dbsession` 테스트 훅, `ImportError` 폴백 제거 | `[COMPLETE]` | `tests/unit/test_models_includeme.py` 8개 |
| B0-3 | `src/namifax/alembic/{env.py,script.py.mako,versions/}` + ini의 `[alembic] script_location = namifax:alembic`. `env.py`는 앱과 같은 `resolve_database_url`로 DB를 정하고 `Base.metadata`를 대상으로 함 | `[COMPLETE]` | `tests/unit/test_alembic_wiring.py` 6개, 실제 `alembic -c development.ini current/heads` 확인 |
| B0-4 | starter 스타일 픽스처 `dbengine`, `app`, `tm`(doomed), `dbsession`, `testapp`, `app_request`, `dummy_request`, `dummy_config` (테스트별 격리 DB에 바인딩) | `[COMPLETE]` | `tests/unit/test_orm_fixtures.py` 6개 |
| B0-5 | `request.db`가 `pyramid_tm` tween 아래(`environ["tm.active"]`)에서는 `request.dbsession`의 커넥션·트랜잭션을 공유(`DatabaseEngine.from_connection(..., managed=True, on_change=mark_changed)`). tween 밖(스크립트, `prepare`)에서는 기존처럼 독립 커넥션 + 쓰기마다 commit | `[COMPLETE]` | `tests/unit/test_request_db_shared_session.py` 11개(실제 tween, 롤백, E2E 로그인+SMTP 저장), 전체 597 통과 |
| B0-6 | 파일럿 `SystemConfig`: ORM 모델 + `SystemConfigService` + storage/saml 뷰를 `request.dbsession`으로 전환 + Alembic 베이스라인 `0001` | `[COMPLETE]` | `tests/unit/test_system_config.py` 15개, `test_system_config_migration.py` 5개(PostgreSQL 1개는 선택 실행), 전체 624 통과 → 14.3 |

### 14.1 B0에서 확정된 계약
- **zope.sqlalchemy는 변경이 감지된 세션만 커밋한다.** ORM flush는 자동으로 변경을 표시하지만 `session.execute(text(...))` 같은 raw SQL은 `zope.sqlalchemy.mark_changed(session)`를 호출하지 않으면 요청 끝에 **롤백**된다. 그래서 `request.db`(raw 커서)의 모든 성공한 쓰기는 `on_change`로 `mark_changed`를 호출한다.
- managed `DatabaseEngine`은 commit/rollback/close를 하지 않는다. `transaction()` 컨텍스트도 커밋하지 않고 소유자(tm)에게 맡긴다.
- 요청이 예외로 끝나면 `request.db`로 쓴 변경도 함께 롤백된다(이전에는 쓰기마다 즉시 commit이라 부분 반영이 가능했음).
- explicit 매니저는 호출자가 `begin()`해야 한다(tween이 요청마다 수행). tween 없이 `prepare()`로 만든 요청에서 `request.dbsession`을 쓰려면 먼저 `request.tm.begin()`이 필요하다.
- `namifax.main`은 모듈 이름이자 패키지의 `main = create_app` 함수 이름이다(13.4 참조).

### 14.2 다중 DB 지원 조사 결과 (운영 DB: SQLite, MySQL, MariaDB, PostgreSQL)
측정은 로컬 PostgreSQL 컨테이너에 임시 DB를 만들어 수행하고 삭제했다.
- **현재 SQLite 외 DB에서는 시작 자체가 불가능하다.** `init_database_tables`의 DDL 20개가 PostgreSQL에서 전부 실패한다(`AUTOINCREMENT`). 이전에는 이 실패 반환값을 `create_app`/`cli_db`가 무시해 테이블이 없는 채로 정상 기동한 것처럼 보였다 → **fail-fast로 수정**(`RuntimeError: Database initialisation failed`).
- SQLite 전용 구문 분포(`src/namifax`): `INSERT OR REPLACE/IGNORE` 23곳(`db/schema.py` 21, `views/admin.py` 2), `AUTOINCREMENT` 20곳, `sqlite_master`/`PRAGMA` 5곳, `ALTER TABLE ... ADD COLUMN`을 예외 무시로 감싼 마이그레이션 7곳. 반대로 MySQL 전용 DDL(`AUTO_INCREMENT`, `ENGINE=InnoDB`)이 `services/ocr.py`, `services/webauthn.py`에 있고 `NOW()`도 쓴다.
- **문자열 이스케이프 결함(보안)**: 74곳이 f-string SQL에 `DatabaseEngine.quote()`를 쓰는데 작은따옴표만 이중화했다. MySQL/MariaDB는 기본 설정에서 역슬래시가 이스케이프 문자라 `\'`로 리터럴을 조기 종료시킬 수 있다 → **`quote()`를 방언별로 처리**(mysql/mariadb는 역슬래시 먼저 이스케이프). 파라미터 바인딩을 쓰는 쿼리는 3곳뿐이다.
- 결론: DB 이식성은 모델(SQLAlchemy 타입, 바인딩 파라미터, `merge`/upsert, `func.now()`)과 Alembic 마이그레이션으로만 확보할 수 있다. 따라서 B 트랙은 선택이 아니라 다중 DB 지원의 **전제 조건**이다. 모델이 없는 테이블이 남아 있는 동안 비 SQLite DB는 지원되지 않는다.
- 파일럿 후보: `SystemConfig`(key/value). `views/admin.py`의 storage/saml 뷰가 `INSERT OR REPLACE`(SQLite 전용)로 쓰고 있어, ORM `merge`로 바꾸면 이식성 결함 1건이 실제로 해소된다.
- 모델 작성 규칙: 방언 중립 타입만 사용(`String(n)`, `Integer`, `Text`, `DateTime`), `mysql_length` 등 방언 옵션은 `with_variant`/조건부로만, 예약어 컬럼(`key` 등)은 SQLAlchemy 인용에 맡김, Alembic 마이그레이션은 `op.create_table`/`batch_alter_table`로 방언 중립 작성.

### 14.3 파일럿 `SystemConfig` 결과와 B 트랙 전환 절차
**변경**
- `models/systemconfig.py`: `SystemConfig`(`key` String(255) PK, `value` Text). 테이블명은 레거시 철자 그대로 유지한다(MySQL/MariaDB 리눅스는 테이블명 대소문자를 구분하므로 남아 있는 raw SQL이 계속 통해야 한다).
- `services/system_config.py`: `SystemConfigService(session).get/set`. 쓰기는 `Session.merge`(이식 가능한 upsert)이고 값은 바인딩 파라미터라 `quote()`가 필요 없다.
- `views/admin.py` storage/saml 뷰: `INSERT OR REPLACE`, 뷰 안의 `CREATE TABLE IF NOT EXISTS`, 문자열 조립 SQL 제거 → `request.dbsession` 사용. 이식성 결함 2곳 해소.
- `alembic/versions/20261001_0001_system_config.py`: 테이블이 없을 때만 생성(레거시 SQLite 초기화가 이미 만든 DB와 공존), 다운그레이드는 삭제.
- 의존성: 선택 extras `postgresql`(psycopg), `mysql`(pymysql), dev 그룹에 psycopg. pytest 마커 `postgres`.

**검증 매트릭스**
| DB | 방법 | 결과 |
| :--- | :--- | :--- |
| SQLite | 자동 테스트(모델, 서비스, 뷰, E2E 로그인+저장, 마이그레이션 신규/레거시/다운그레이드) | 통과 |
| PostgreSQL | `NAMIFAX_TEST_PG_URL=postgresql+psycopg://user:pw@host:port/postgres pytest -m postgres` (테스트가 임시 DB를 만들고 삭제) — Alembic 베이스라인, ORM upsert, 역슬래시 원문 보존 | 통과 |
| MySQL / MariaDB | `CreateTable` DDL 컴파일(예약어 `key` 백틱 인용, `VARCHAR(255)`) + 모든 `String`에 길이가 있는지 전체 메타데이터 검사 | 통과(서버 실행은 미검증) |

**모듈을 ORM으로 전환하는 절차 (이 파일럿에서 확정)**
1. 모델 작성: 방언 중립 타입, `String`에는 항상 길이, 테이블명은 레거시 철자 유지.
2. 서비스는 `Session`을 주입받아 `select`/`merge`/`add`만 사용(문자열 SQL, `quote()`, `INSERT OR REPLACE` 금지).
3. 뷰는 `request.dbsession` 사용. 한 요청에서 `request.db`와 섞여도 같은 트랜잭션이다(B0-5).
4. Alembic 리비전: `inspect(op.get_bind()).has_table(...)`로 멱등하게 작성(레거시 SQLite 스키마와 공존).
5. 테스트: SQLite 자동 + PostgreSQL 선택 + 방언 DDL 컴파일.
6. 뷰 테스트는 `dbsession`/`tm` 픽스처를 쓰거나, 요청 헬퍼에서 `request.tm.begin()`을 호출한다(tween이 하는 일).

**남은 한계**: `create_app` 시작 시 레거시 `init_database_tables`(SQLite DDL)가 실행되므로, 모든 테이블이 모델과 마이그레이션으로 옮겨지기 전에는 비 SQLite DB로 앱이 기동되지 않는다. 모델화된 모듈은 PostgreSQL에서도 서비스·마이그레이션 수준으로 동작한다.

### 14.4 ORM 모델화 진행표 (테이블 단위)
상태: `[LEGACY]` raw SQL(`DatabaseEngine`) / `[ORM]` 모델 + `Session` 서비스 + Alembic 리비전 + 서버 DB 검증 완료.
검증 서버: SQLite(자동), PostgreSQL 16·MySQL 8.4·MariaDB 11.8(`pytest -m serverdb`, 환경변수는 `tests/conftest.py` 참조).

| 그룹 | 테이블 | 상태 | 리비전 | 비고 |
| :--- | :--- | :---: | :---: | :--- |
| 1 | `SystemConfig` | `[ORM]` | 0001 | 파일럿. storage/saml 뷰 |
| 1 | `SystemSettings` | `[ORM]` | 0002 | SMTP 단일 행(id=1). `SmtpSettingsService(Session)`, `MailerService.from_settings(session)`. 참고: `common/helpers.send_mail`은 DB의 SMTP 설정을 쓰지 않고 `MailerService`를 직접 만든다(저장한 설정이 실제 발송에 반영되지 않음) |
| 1 | `NetworkPrinters` | `[ORM]` | 0003 | `NetworkPrinterService(Session)`, 자동 증가 PK는 방언별 DDL로 생성. `delete_printer`는 삭제된 행이 있었는지를 반환(이전에는 항상 True). `process_inbound_print_job`의 미사용 `db` 인자는 유지 |
| 1 | `SysLog` | `[ORM]` | 0004 | `SysLogService(Session).search`. `logdate`는 ISO 텍스트 `String(32)`로 유지(날짜 접두어 `LIKE`가 PostgreSQL의 timestamp에서는 불가). 키워드는 모든 DB에서 대소문자 무시 부분 일치이고 `%`/`_`는 리터럴(이전에는 와일드카드). 조회 오류를 삼키지 않음(이전에는 `except Exception`으로 빈 목록). 관찰: `avantfaxlog()`가 이 테이블에 쓰지 않던 포팅 회귀는 14.7에서 수정 |
| 2 | `FaxCategory` | `[ORM]` | 0005 | `FaxPDFCategory`는 `Session`과 레거시 `DatabaseEngine` 모두 받음. 웹 뷰(admin, archive, helpers)는 `request.dbsession` |
| 2 | `CoverPages` | `[ORM]` | 0006 | `Covers`는 `Session`/`DatabaseEngine` 모두. 웹 뷰(admin, sendfax)는 `request.dbsession` |
| 2 | `DynConf` | `[ORM]` | 0007 | `DynamicConfig` 서비스. 웹 뷰는 `request.dbsession`, CLI(`dynconf`, `import_blacklist`)는 `cli_session(ensure_schema=True)`. 쌍둥이 테이블 `DynamicConfig`는 SQL 사용처가 없어 생성/동기화/시드를 제거(기존 DB의 잔여 테이블은 건드리지 않음) |
| 2 | `Modems` | `[ORM]` | 0008 | `FaxModem`(`faxstat` 상태 파싱은 DB와 무관). 웹 뷰·`get_all_admin_modems`는 `request.dbsession`, `reroute`는 `cli_session`, `faxrcvd`는 `cli_unit` |
| 2 | `DIDRoute` | `[ORM]` | 0009 | `DIDRouting` |
| 2 | `BarcodeRoute` | `[ORM]` | 0010 | `BarcodeRouting`. 포트가 만든 중복 컬럼 `bcr_id`는 모델과 서비스에서 제거(구조 백필이 기존 SQLite DB의 NULL `barcode_id`를 `bcr_id`로 채움) |
| 3 | `DistroList` | `[ORM]` | 0011 | `DistributionList`. `lastmod_date`(레거시 `TIMESTAMP` 자동 갱신)를 ORM이 삽입·수정 시 채움 |
| 3 | `UserPasswords` | `[ORM]` | 0012 | 레거시 컬럼(`upid`, `pwdhash`)으로 정정. 비밀번호 이력이 처음으로 동작(14.12) |
| 3 | `AddressBook`, `AddressBookFAX`, `AddressBookEmail` | `[ORM]` | 0013~0015 | 레거시 기본키(`abook_id`, `abookfax_id`, `abookemail_id`). 포트의 중복 컬럼 제거. 웹 뷰·`faxrcvd`·`notify`·`phb` 전환 |
| 3 | `UserAccount` | `[ORM]` | 0016 | 3d-1. 플래그 8개는 `LegacyBoolean`(14.13). 웹 뷰·`security`·`createuser`·`import_users`·`notify`가 Session 사용. `FaxQueue`/`saml`/`bridge_cli`는 레거시 엔진 경유(동작은 동일) |
| 3 | `UserTOTP` | `[ORM]` | 0017 | 3d-2. `TotpService`는 세션·레거시 엔진 양쪽 지원. 뷰는 Session |
| 3 | `UserWebAuthnCredentials` | `[ORM]` | 0018 | 3d-2. 서비스는 Session 전용. SQLite DDL 추가(기존엔 MySQL 전용) |
| 3 | `FaxOCR` | `[ORM]` | 0019 | 3d-2. 서비스는 Session 전용, `ocr_text`는 MySQL/MariaDB에서 `LONGTEXT`. `faxrcvd`가 세션으로 색인 |
| 4 | `FaxArchive` 외 | `[LEGACY]` | - | |

**공통 규칙 (이번 라운드에서 재확인)**
- 서버 DB 테스트에서 raw SQL을 쓰면 PostgreSQL에서 혼합 대소문자 테이블명이 실패한다. 서버 테스트는 모델 기반 쿼리(`select(func.count()).select_from(Model)`)를 쓴다.
- `tests/conftest.py`: `alembic_cfg`(개인 사본 Alembic 설정), `server_db_url`(서버별 임시 DB), `dbsession`/`tm`/`app_request` 픽스처.
- `tests/unit/test_migrations_match_models.py`가 마이그레이션 결과와 모델의 불일치를 모든 서버에서 잡는다. 모델을 추가할 때는 리비전을 함께 추가해야 통과한다.
- 모듈을 ORM으로 옮기면 `DatabaseEngine`을 임포트하던 감사 테스트(`test_security_audit_phase1::test_audit_18`)의 대상 목록에서 그 모듈을 뺀다.

### 14.5 그룹 1 완료 요약
- 모델 4개(`SystemConfig`, `SystemSettings`, `NetworkPrinters`, `SysLog`), Alembic 리비전 `0001`~`0004`, 서비스 `SystemConfigService`, `SmtpSettingsService`, `NetworkPrinterService`, `SysLogService`가 모두 `Session`을 주입받는다.
- 뷰 `admin_storage/saml/smtp/printers/system_logs`는 `request.dbsession`을 쓴다. 이 뷰들에서 `request.db`와 문자열 조립 SQL, SQLite 전용 구문이 사라졌다.
- 검증: SQLite(자동) + PostgreSQL 16 + MySQL 8.4 + MariaDB 11.8(`pytest -m serverdb`). 마이그레이션-모델 드리프트 검사가 모든 서버에서 통과한다.
- 반복해서 확인된 패턴: (1) 서버 DB 테스트는 모델 기반 쿼리만 쓴다(혼합 대소문자 테이블명과 PostgreSQL). (2) 레거시 SQLite 스키마와 공존하도록 모든 리비전은 `has_table`로 멱등하다. (3) 서비스는 세션 없이 생성하면 첫 사용에서 `RuntimeError`.

### 14.6 기능 결함 수정: SMTP 설정이 실제 발송에 반영되지 않던 문제 (P1)
레거시 원본과 스펙으로 확인한 뒤 TDD로 수정했다.

| 결함 | 근거 | 수정 |
| :--- | :--- | :--- |
| 관리자가 저장한 SMTP 게이트웨이를 아무 발송 경로도 쓰지 않음 | 스펙 39 §3.2: `MailerService`는 DB의 최신 설정을 동적으로 로드하고 읽지 못하면 폴백해야 함 | `MailerService.get_active_mailer(session)`(기존 `from_settings`는 별칭), `helpers.send_mail(..., session=None)`이 이를 사용. 보내는 사람(`from_addr`)은 메시지별로 유지하고, 없으면 게이트웨이의 `from_email` |
| **포팅 후 CLI의 모든 메일 알림이 실제로는 발송되지 않았음** | `send_mail`이 항상 `MailerService(admin_email=...)`(서버 없음)를 만들었고, 서버가 없으면 `sendmail()`은 메모리에만 쌓고 `True`를 반환 | 설정이 없으면 기본 설정(`localhost:25`)으로 실제 발송. DB를 읽지 못하면 로컬 MTA(`MailerService.local_mta()`)로 폴백(조용히 유실되지 않도록) |
| 웹 "팩스 이메일 전송" 모달이 `AttributeError` | `modal_email_view`가 존재하지 않는 `mailer.send_mail(...)`을 호출. 기존 테스트는 `Mailer`를 가짜로 대체해 가려 놓음 | 레거시 `email.php`처럼 `send_mail` 헬퍼를 호출(`file`, `embedd`, `session=request.dbsession`) |

- 요청이 없는 CLI(`faxrcvd`, `notify`)는 호출처를 바꾸지 않고도 설정을 읽는다: `send_mail`이 `provider.cli_session()`(신규, 요청 없는 ORM 세션 컨텍스트)으로 읽기 전용 세션을 잠시 연다.
- 검증: 실제 소켓 SMTP 서버(테스트 내 가짜 서버)가 DB에 저장한 호스트·포트로 메시지를 받는 E2E 테스트(`test_active_mailer.py`).
- `[관찰]` `MailerService()`의 서버 없음 모드는 발송하지 않고 `True`를 반환한다. 호출자가 성공으로 오인할 수 있어 별도 정리를 권장한다(스풀 전용 모드는 `spool_mode=True`로 명시하는 편이 안전).
- `[관찰]` 레거시 `create_tables.sql`의 `SysLog`는 PK `syslogid`, 포트의 SQLite 스키마와 모델은 `log_id`다. 레거시 MySQL DB를 그대로 이어받는 시나리오가 필요한지 `[NEEDS_CLARIFICATION]`. (`AddressBook`의 `ab_id`/`abook_id`와 같은 종류의 이름 불일치)

### 14.7 기능 결함 수정: `avantfaxlog()`가 `SysLog` 테이블에 기록하지 않던 문제 (P2)
- 레거시 원본(`includes/functions.php`): `avantfaxlog()`는 `MDBOData('SysLog')->new_entry(['logtext' => $text])`로 테이블에 기록했다. 포팅본은 OS syslog에만 써서 관리자 "System Logs" 화면에는 시드 2행만 보였다(포팅 회귀).
- 수정: `SysLogService.add(logtext, logdate=None)`(날짜는 `YYYY-MM-DD HH:MM:SS` 로컬 시각)과 `avantfaxlog(text, echo=False, session=None)`. OS syslog 기록은 유지하고 DB 기록을 복원했다. 웹은 요청 세션을 넘기고, 훅 프로세스(`faxrcvd`, `notify`, `cron` 등 호출처 19곳)는 호출처를 바꾸지 않고 `cli_session()`으로 짧은 세션을 열어 기록한다.
- 로깅은 호출자를 실패시키지 않는다: DB가 없거나 INSERT가 실패해도 예외를 삼킨다.
- 검증: 세션/CLI/DB 불가/INSERT 실패 케이스, `faxrcvd` 훅이 남긴 줄이 관리자 로그가 읽는 테이블에 저장되는지, 서버 3종에서 `add`와 검색 왕복.
- `[관찰]` 호출 한 번마다 엔진·연결을 새로 만든다(훅당 최대 19회). 현재 규모에서는 무시할 수준이지만, 필요해지면 프로세스 단위로 엔진을 재사용하도록 최적화할 수 있다.

### 14.8 `OrmRepository`: 서비스를 다시 쓰지 않고 이식하는 저장소 계층
**문제**: 2~4그룹의 서비스는 모두 레거시 `MDBOData`를 통해 raw SQL로 DB에 접근한다. 서비스를 하나씩 다시 쓰면 양이 많고 레거시 API 계약(PHP 클래스를 옮긴 상태 보존형 객체)을 깨뜨릴 위험이 크다.

**해결**: `Repository("Modems", db=<Session>)`이 `OrmRepository`를 돌려준다(`Repository.__new__` 디스패치). `DatabaseEngine`을 주면 기존 구현 그대로다. 서비스가 쓰는 메서드(`find`, `new_entry`, `update_entry`, `delete_entry`, `load`, `get_id`, `get_info`, `.data.set_id`)를 같은 시그니처로 제공하고, 값은 바인딩 파라미터이며 테이블·타입·인용은 방언에 맞게 SQLAlchemy가 처리한다. 고정 SQL(`query("SELECT ... ORDER BY ...")`)은 양쪽 구현이 모두 가진 `select(columns, order_by, descending)`로 대체한다.

**레거시 동작 보존(서비스 코드가 의존하는 의미)**
- `find`는 등호 비교만 지원한다. `None`과의 비교는 아무것도 일치시키지 않는다(SQL `= NULL`).
- 값은 느슨하게 타입 변환한다: `"5"`가 정수 컬럼과 일치한다(PostgreSQL은 자동 변환하지 않으므로 컬럼 타입별 변환이 필요).
- 갱신/삭제는 대상 행이 없어도 성공(`True`). `update_entry(info)`는 payload의 기본키가 대상 행을 고르고 기본키 자체는 다시 쓰지 않는다(서비스가 로드한 전체 행을 넘기는 패턴).
- 알 수 없는 키는 무시. `reduce_single`은 일치가 정확히 1건일 때 dict를 돌려준다. 정렬이 없던 `find`는 기본키 순으로 고정(PostgreSQL 결과 순서 안정).

**의도적으로 다른 점**: 고유 제약 위반 같은 DB 오류가 `False`가 아니라 예외로 올라온다. 세이브포인트를 쓰지 않는 이유: pysqlite(SQLite)는 최외곽 `RELEASE SAVEPOINT`에서 트랜잭션을 조기 커밋해 `pyramid_tm`의 원자성을 깨뜨린다. 서비스는 대부분 생성 전에 `find`로 중복을 확인한다. 원시 `query()`는 ORM 저장소에서 `NotImplementedError`로 막아 변환 누락이 즉시 드러나게 했다.

**서비스 생성자**: `db` 인자에 `Session`(이식 가능) 또는 `DatabaseEngine`(FFI 브리지 `bridge_cli`가 계속 사용)을 받는다. 모든 호출처가 세션으로 넘어가면 레거시 경로를 제거한다.

**검증**: `tests/unit/test_orm_repository.py`(SQLite 20개 + 서버 3종). 서비스는 `Session`과 `DatabaseEngine` 양쪽으로 매개변수화한 테스트가 같은 결과를 요구한다(`test_fax_category.py`).

### 14.9 결함 수정: 서버가 시작될 때마다 기존 데이터를 훼손하던 시드/마이그레이션 (P3 진행 중 발견)
`DynamicConfig` 쌍둥이 테이블을 정리하다가 `db/schema.py`가 **애플리케이션 시작 때마다** 데모 값을 다시 적용한다는 것을 발견했다. 운영 데이터가 있는 DB에서 일어나던 일:

| 위치 | 시작할 때마다 |
| :--- | :--- |
| `UserAccount` else | `admin`의 비밀번호가 `password` 또는 `createuser` 기본값(`admin1234!`의 MD5)이면 `password`로 되돌림 |
| `Modems`·`FaxCategory`·`CoverPages` | 행이 2·3개 미만이면 `INSERT OR REPLACE`로 실제 모뎀/카테고리/커버를 덮어씀 |
| `DIDRoute`·`AddressBook`·`DistroList` else | 1번 행의 별칭·회사명·목록 이름을 데모 값으로 덮어씀 |
| `BarcodeRoute` else | 행의 기본키를 1로 바꾸려 함 |
| `DynConf` else | 1번 규칙을 데모 값으로 덮어씀 |
| `FaxArchive` | 받은 팩스가 없으면 `INSERT OR REPLACE`로 **실제 팩스 #1을 데모 행으로 교체**, else는 #1을 받은편지함으로 되돌리고 Acme에 연결 |
| 마이그레이션 | NULL인 모든 `faxnumid`를 1(Acme 번호)로, NULL인 `modemdev`를 `ttyS0`로, #1의 회사를 Acme로 채움 |

**수정**(`tests/unit/test_schema_seed_safety.py`, 데모 행을 관리자 데이터처럼 바꾼 뒤 재시작해도 모든 테이블이 동일해야 함):
- 데모 데이터는 **사용자가 한 명도 없는 새 DB에만** 넣는다. 레거시 설치 SQL이 기본 관리자와 커버 페이지를 넣은 것처럼, 커버 페이지·카테고리 기본값은 **테이블이 비어 있을 때만** 넣는다.
- 모든 `INSERT OR REPLACE`는 `INSERT OR IGNORE`, 모든 `else:` 복구 UPDATE와 데모 마이그레이션 UPDATE는 제거.
- 구조용 백필(`abook_id`, `barcode_id`, `archstamp` 등 NULL 채우기)은 `_backfill_alias_columns`로 모아 마이그레이션 직후와 시드 직후에 실행해, 새 DB가 첫 시작에서 완전하게 만들어진다(이전에는 두 번째 시작에서야 채워졌음).
- `[관찰]` 새 SQLite DB는 여전히 `admin`/`password` 기본 관리자를 만든다(레거시 설치와 같은 동작이지만 레거시는 `wasreset=TRUE`로 첫 로그인에서 변경을 강제했다). 운영 배포에서는 기본 계정을 만들지 않거나 변경을 강제하는 장치가 필요하다 `[NEEDS_CLARIFICATION]`.

### 14.10 CLI에서 레거시와 ORM을 한 실행에서 섞기: `cli_unit`
**문제**: `faxrcvd`는 ORM 서비스(모뎀, DID, 바코드)와 레거시 서비스(`ArchiveIn`, `AFAddressBook`)를 한 실행에서 함께 쓴다. 쓰기 연결이 둘이면 SQLite에서 서로를 잠근다(한쪽의 미커밋 쓰기가 다른 쪽을 막음). 실제로 `avantfaxlog()`가 별도 세션을 열어 로그가 조용히 사라지는 것을 테스트가 잡았다.

**해결**
- `provider.cli_unit()`: 레거시 `DatabaseEngine`(managed)과 ORM `Session`이 **한 연결·한 트랜잭션**을 공유한다(웹의 `request.db` + `request.dbsession`과 같은 모델). 양쪽이 서로의 미커밋 쓰기를 보고, 블록이 정상 종료되면 커밋, 예외면 전체 롤백. SQLite는 스키마도 보장한다.
- `provider.active_session()`: 실행 중인 `cli_session()`/`cli_unit()`의 세션(ContextVar). `avantfaxlog()`와 `send_mail()`(SMTP 설정 조회)은 명시된 세션이 없으면 이것을 먼저 쓰고, 없을 때만 짧은 세션을 따로 연다.
- 선택 기준: ORM 서비스만 쓰는 CLI는 `cli_session()`, 레거시만 쓰는 CLI는 `cli_db()`, 둘을 섞으면 `cli_unit()`.

### 14.11 NULL 정렬 규칙
SQLite·MySQL은 오름차순에서 NULL을 먼저, PostgreSQL은 나중에 둔다. `OrmRepository.select`는 NULL 가능 컬럼 정렬 시 `CASE`로 NULL을 오름차순에서 먼저/내림차순에서 나중에 고정한다(서버 3종 테스트). 문자열 정렬 자체(한글과 영문 혼합)는 DB collation이 정하므로 서비스 계약에 포함하지 않는다.

### 14.12 그룹 3 진행 중 발견·수정한 결함
| 결함 | 근거 | 수정 |
| :--- | :--- | :--- |
| **주소록 검색 SQL 인젝션** (보안) | `search_companies`가 `LIKE '%<입력>%'`를 SQL에 끼워 넣음. `x'OR(1=1)--`가 주소록 전체를 반환, `UNION`으로 다른 테이블(`UserAccount` 해시) 열람 가능. 웹 자동완성(`ajax_book`)이 호출 | 양쪽 저장소의 `search_text`(패턴을 인용, 대소문자 무시, 여러 단어는 순서대로, `%`/`_`는 리터럴, `ESCAPE '!'`). 별도 보안 커밋 `3beddd3` |
| **비밀번호 이력 미작동** | `AFUserPasswords`가 `{uid, pwdhash}`를 쓰는데 포트 테이블은 `pwd_id/password/date`라 `no such column: pwdhash`. 재사용 차단이 한 번도 적용되지 않음 | 레거시 컬럼으로 모델화. 새 SQLite는 레거시 DDL, 기존 SQLite는 `RENAME COLUMN`으로 제자리 변경(행 보존) |
| **새 주소록 회사를 서버 재시작 전까지 ID로 조회 불가** | 서비스는 `abook_id`를 키로 쓰지만 포트 테이블의 키는 `ab_id`였고 `abook_id`는 다음 시작 때 백필됨 | `abook_id`를 실제 기본키로: 새 DB는 레거시 구조, 기존 DB는 `AddressBook`을 ID와 연결을 보존하며 재구성 후 자식 테이블 링크 백필 |

**주소록 스키마 정리**: 포트가 만든 중복 컬럼(`ab_id`, `fax_id`, `email_id`, `default_num`, `default_email`, 주소록 이메일의 `to_person`/`email`)은 새 DB에서 만들지 않고 모델에서도 제외했다. 기존 DB의 잔여 컬럼은 건드리지 않는다. `AddressBook`의 확장 컬럼(`faxnum`, `phonenum`, `address` 등)은 레거시에는 없고 시드만 채우지만 웹 자동완성 라벨이 `faxnum`을 읽으므로 유지했다. 죽은 코드였던 `AddressBookFAX` 뷰 생성 블록(항상 건너뛰어짐)은 제거했다. 추가한 인덱스: `AddressBookFAX.abook_id`, `.faxnumber`, `AddressBookEmail.contact_email`.

**저장소 계층에 추가된 공통 메서드**: `delete_where`, `update_where`, `search_text`(두 구현 모두). 호출자는 조건이 비어 있거나 `None`이면 아무 행도 건드리지 않는 안전한 동작을 기대할 수 있다.

**남은 raw SQL**: `services/archive_base.py:210`의 `FaxArchive` 검색은 `AddressBookFAX`를 `LEFT JOIN`하는 긴 문자열 SQL이다. PostgreSQL에서는 인용되지 않은 혼합 대소문자 테이블명 때문에 실패하므로 그룹 4(`FaxArchive`)에서 함께 변환한다.

### 14.13 UserAccount(3d-1)에서 발견·수정한 결함
| 결함 | 근거 | 수정 |
| :--- | :--- | :--- |
| **불리언이 문자열 `'False'`로 저장됨 → 권한 상승 위험** | 레거시 엔진 `quote()`가 `str(False)`를 인용해 `superuser`, `can_del`, `pwd_reuse`, `any_modem` 등에 텍스트 `'False'`를 저장. ORM `Boolean`은 비어 있지 않은 텍스트를 참으로 읽으므로 `createuser`/`import_users`로 만든 일반 계정이 ORM 경로에서 **슈퍼유저·삭제 권한 보유**로 읽힘 | ① `quote(bool)`은 `1`/`0`. ② 모델은 `LegacyBoolean`: 드라이버 원시 값을 직접 읽고(`'False'`→거짓, 알 수 없는 문자열→거짓) DDL·쓰기는 일반 `Boolean`과 동일. ③ `init_database_tables`가 텍스트로 저장된 기존 행을 0/1로 복구(SQLite, 멱등, 텍스트인 값만) |
| **저장된 비밀번호 해시가 비밀번호로 통용** | `login()`이 MD5 비교에 실패하면 입력값을 *평문 그대로* 컬럼과 비교하는 대체 경로가 있었음. DB에서 해시가 유출되면 그 해시 자체로 로그인 가능(pass-the-hash)하고, 평문 저장 행도 허용 | 대체 경로 삭제. 로그인은 `md5(입력) == 저장값`만 허용 |
| **계정 삭제가 반영되지 않음** | `remove()`가 `username`/`email`/`password`를 NULL로 갱신하는데 세 컬럼 모두 `NOT NULL`이라 갱신 전체가 실패(엄격 모드 MySQL, PostgreSQL, 새 SQLite DDL). 삭제된 계정이 그대로 로그인 가능 | 계정별로 고유한 자리표시값(`deleted.<uid>`, `deleted.<uid>@invalid.invalid`, 빈 비밀번호)으로 갱신. 실제 이름·주소는 재사용 가능, 어떤 해시와도 일치하지 않아 로그인 불가 |
| 중복 검사의 문자열 SQL | `set_username`/`set_email`이 인용한 값을 SQL에 끼워 넣고 `uid != ...` 비교 | `find()` 후 다른 `uid`가 있는지 확인 |

**테스트 정리**: `tests/unit/linked_db.py`는 레거시 엔진과 ORM 세션이 한 연결을 공유하는 쌍을 만든다. 레거시 엔진으로 데이터를 만든 뒤 뷰(이제 세션을 사용)를 검사하는 기존 테스트에 쓴다. `test_user_account.py::test_remove_account`는 결함이 있던 동작(`username IS NULL`)을 기대값으로 고정하고 있었으므로 새 동작으로 고쳤다.

**남은 항목**: 평문 비밀번호가 들어 있던 기존 계정이 있다면 이제 로그인할 수 없다(해시로 바꾸는 `reset_password` 필요). 기본 `admin`/`password` 시드는 기존 NEEDS_CLARIFICATION 그대로.

### 14.14 3d-2에서 발견·수정한 결함 (패스키·OCR이 SQLite에서 동작하지 않았음)
| 결함 | 근거 | 수정 |
| :--- | :--- | :--- |
| **패스키 저장소가 SQLite에서 동작 안 함** | `UserWebAuthnCredentials` DDL이 MySQL 전용(`AUTO_INCREMENT`, `ENGINE=InnoDB`, `NOW()`)이고 예외를 삼켜서 테이블이 생성되지 않음. 또 `db.query()`가 행이 아니라 결과 객체를 돌려주는데 서비스는 행 목록으로 반복해 `list_credentials`와 로그인용 허용 목록이 항상 비어 있었음. `save_credential`은 id를 항상 0으로 반환 | 모델·리비전·SQLite DDL 추가. 서비스는 ORM 전용으로 재작성(실제 id 반환, 타 사용자의 id로는 삭제 불가, 갱신 시각은 앱에서 설정) |
| **OCR 색인이 한 번도 저장되지 않음** | 같은 이유로 테이블이 없고, `existing = db.query(...)`가 항상 참이라 INSERT 없이 UPDATE만 실행. `faxrcvd`는 예외를 로그로만 남김 | ORM 전용으로 재작성: 있으면 갱신, 없으면 추가 |
| OCR 검색의 와일드카드 | 키워드를 `LIKE %kw%`에 그대로 넣어 `%`, `_`가 와일드카드 | `like_pattern` + `ESCAPE '!'` |

**저장소 계층**: `OrmRepository.new_entry`는 자동 증가가 아닌 기본키(`UserTOTP.uid`)를 호출자가 준 값으로 저장한다.
**테스트 정리**: 서비스가 반환 형태를 잘못 가정한 목(mock) 테스트(`db.query`가 리스트를 반환)는 실제 세션 테스트(`test_webauthn_orm`, `test_ocr_orm`, `test_totp_orm`)로 대체했다.
**그룹 3 완료.** 남은 모델링 대상은 그룹 4(`FaxArchive` 등)이며, 이후 비 SQLite DB에서 앱이 기동되도록 레거시 `init_database_tables`를 Alembic으로 대체한다.

### 14.15 그룹 4: FaxArchive (0020)
`FaxArchive`는 레거시 17개 컬럼만 모델화했다(날짜는 ISO 텍스트, `inbox`는 정수). 포트의 SQLite 테이블에 있는 임의 컬럼(`company`, `faxnum`, `cid_name`, `status` 등)은 건드리지 않고 매핑하지도 않는다.

**이중 경로**: `FaxPDFArchive`는 Session을 받으면 `services/archive_orm.py`의 ORM 쿼리를, 레거시 엔진을 받으면 기존 SQL을 쓴다(레거시 경로는 최종 정리 단계에서 제거). 간단한 조회·변경(`load_fax`, `remove_category`, `reassign`, `create_fax` 등)은 두 경로 모두 저장소 메서드(`find`, `update_where`, `new_entry`)를 쓴다.

**검증**: `tests/unit/test_fax_archive_orm.py`는 같은 12행을 레거시 엔진과 Session에 넣고 검색 조건 표(보낸/받은/전체/기타 × 슈퍼유저 여부 × 모뎀·DID·카테고리·제한 모드, 기간, 키워드, 회사, 페이지)를 돌려 **두 경로의 결과(건수와 fid 순서)가 같음**을 확인한다. 같은 표를 PostgreSQL·MySQL·MariaDB에서 돌려 SQLite 레거시 결과와 비교한다.

**이식 가능하도록 바꾼 부분**: `LIMIT a, b`(MySQL/SQLite 전용)→`LIMIT/OFFSET`; 정수 컬럼과 `''` 비교 제거(PostgreSQL 오류), 라우트 목록의 `didr_id = ''`는 아무것도 일치시키지 않음; 인박스의 `ORDER BY modemdev`는 NULL을 항상 먼저; 키워드는 `lower()+LIKE+ESCAPE`(대소문자 무시, `%`/`_`는 리터럴); 날짜 접두 검색은 `startswith(autoescape)`.

**의도적으로 레거시와 달라진 동작**: 비슈퍼유저가 사용자 ID나 라우트 없이 "기타/전체" 검색을 하면 레거시는 `userid = None` 같은 잘못된 SQL을 만들어 결과 0건이었으나, ORM 경로는 해당 조건을 거짓으로 취급해 나머지 조건으로 검색한다(테스트로 정의).

| 결함 | 근거 | 수정 |
| :--- | :--- | :--- |
| **웹 아카이브 검색 결과가 항상 비어 있음** | `archive_view`가 `FaxPDFArchive`에 없는 `get_company()`를 호출하고 그 `AttributeError`를 `except Exception: pass`가 삼킴. 또 검색은 fid만 돌려주는데 각 팩스를 `load_fax`하지 않음 | fid마다 `load_fax`로 읽고, 회사는 `companyid`→`faxnumid` 순서로 주소록에서 찾음(없으면 "Unknown") |
| 인박스 회사명 폴백 | `r.get("company")`는 레거시에 없는 포트 전용 컬럼. ORM 행에는 없음 | 주소록 조회만 사용(시드 행은 `companyid`로 연결되어 영향 없음) |

**남은 레거시 경로**: `cron`/`StorageLifecycleService`(레거시에 없는 `FaxArchive.lastmod` 컬럼을 참조하는 포트 전용 기능 — 별도 확인 필요), `bridge_cli`, `FaxQueue`/`saml`의 `AFUserAccount`.

### 14.16 모든 DB에서 앱 기동 (`namifax.db.bootstrap`)
`create_app`, `cli_session`, `cli_unit`은 `ensure_schema(engine)` 하나로 스키마를 맞춘다.

| DB | 동작 |
| :--- | :--- |
| SQLite | 기존 경로 유지: `init_database_tables`(레거시 DDL, 구버전 포트 DB 마이그레이션, **새 DB에 한해 데모 데이터**) |
| MySQL, MariaDB, PostgreSQL | `alembic upgrade head`(리비전 0001~0020, 이미 있는 테이블은 건너뜀) + 기본 팩스 카테고리 3개·커버 페이지 2개(테이블이 비었을 때만). **데모 계정은 만들지 않는다** |

* **첫 관리자**: 서버 DB는 `namifax createuser`로 만든다(기본 `admin`/`password` 계정이 운영 DB에 생기지 않도록 의도적으로 제외). SQLite 데모 계정 정책은 기존 `[NEEDS_CLARIFICATION]` 그대로.
* `alembic/env.py`는 ini 파일이 없을 때 호출자가 넘긴 연결(`config.attributes["connection"]`)을 쓴다. 명령줄 `alembic` 사용 방식은 변하지 않는다.
* **검증(`tests/unit/test_bootstrap.py`, serverdb)**: 빈 서버 DB에 `ensure_schema` → 모든 모델 테이블과 `alembic_version=0020`, 기본 레코드만 존재, 재호출해도 변화 없음. 이어서 같은 DB로 `create_app` → 사용자 생성 → 로그인 → 주요 페이지 31개가 모두 200(리다이렉트도 실패로 간주). PostgreSQL 16, MySQL 8.4, MariaDB 11에서 통과.
* **주의**: 여러 워커가 빈 DB를 동시에 처음 기동하면 마이그레이션이 경합할 수 있다. 처음에는 한 프로세스로 기동하거나 배포 단계에서 `alembic upgrade head`를 먼저 실행한다.

### 14.17 스토리지 라이프사이클과 cron (신규 기능, 레거시 구조에 맞춰 수정)
**판단**: 계획서 3.9의 신규 기능이며(레거시 `avantfaxcron.php`는 팩스 전체 삭제만 제공) 유지한다. 다만 레거시 DB·시스템 구조와 맞지 않아 **실제로는 동작하지 않았으므로** 수정했다(`docs/numfax-defects.md` COR-32와 같은 원인).

| 결함 | 근거 | 수정 |
| :--- | :--- | :--- |
| 존재하지 않는 컬럼로 만료 판단 | `purge_expired_faxes`가 `FaxArchive.lastmod`를 조회. 레거시에 없는 포트 전용 컬럼이고 아무도 값을 쓰지 않아 NULL 비교로 항상 0건(서버 DB에서는 컬럼 자체가 없어 오류) | 레거시 크론 `-d`와 같은 `archstamp` 기준, ORM(`archive_orm.fids_older_than`) 사용 |
| 팩스 디렉터리를 못 찾음 | `fax<fid>` 이름의 디렉터리를 탐색하지만 `faxrcvd`는 `<archive>/<일자>/<번호>/<HylaFAX id>`에 저장 | 행의 `faxpath`로 직접 접근. 삭제는 `FaxPDFArchive.delete_fax`를 재사용하고, 아카이브 디렉터리 안에서만 잔여 파일을 정리(밖의 경로는 건드리지 않음) |
| `FaxPDFArchive.delete_fax`가 파일을 지우지 못함 | 설치 디렉터리가 비어 있을 때 절대 경로 `/var/spool/...`가 상대 경로 `var/spool/...`가 되어 파일이 한 번도 삭제되지 않음(COR-28) | 설치 디렉터리가 없으면 저장된 경로를 그대로 사용 |
| 저장한 정책이 한 번도 실행되지 않음 | 관리자 화면은 정책을 SystemConfig에 저장하지만 스케줄러의 매일 작업은 임시 폴더 정리(`-t`)만 실행. `run_lifecycle`은 테스트에서만 호출 | `StorageLifecycleService.run_saved_policy()`, `cron -s`, 스케줄러가 매일 `-s` 실행 |
| `remote_sync_delete` 미반영 | 정책 값이 무시되고 항상 원격 삭제 호출 | 정책에 따라 원격 삭제 여부 결정, 원격 실패는 로컬 삭제를 막지 않음 |

**자동 삭제는 관리자가 정책을 저장했을 때만 실행한다.** 화면에 보이는 기본값(보존 365일)만으로는 아무것도 지우지 않는다. 설정이 없는 기존 설치에서 스케줄러 기동만으로 팩스가 삭제되는 일을 막기 위한 것이다.

`cron`은 `cli_session`을 쓰고 `-p`(TIFF 정리)·`-s`(저장된 정책)를 지원한다. 서비스는 Session 기반이라 PostgreSQL·MySQL·MariaDB에서도 동작하고 서버 테스트로 검증했다.

**미해결(확인 필요)**: 클라우드 `secret_key`가 SystemConfig에 평문으로 저장된다.

### 14.18 브리지 제거 (`bridge_cli.py`, `*Bridge.php` 24개)
`src/namifax/db/bridge_cli.py`와 PHP 브리지 24개를 삭제했다. 이 파일들은 호출자가 없었다: `*Bridge.php`는 `bridge_cli.py`를 실행하는 용도뿐이고, 그 PHP 클래스를 쓰는 곳이 레거시 PHP·Python·테스트 어디에도 없다(`docs/numfax-defects.md` COR-30). 게다가 `bridge_cli.py`는 JSON 요청만으로 임의 SQL과 임의 실행 파일(`pwauth`의 `binary_path`)을 실행할 수 있어 보안상 위험했다. Strangler Fig의 전환 단계는 끝났고(웹/CLI가 모두 Python으로 동작), Phase 4의 죽은 코드 정리에 해당한다.

**제거된 로직(Dead Code Removal Protocol)**: PHP→Python JSON 브리지 전체와 전역 엔진 `_GLOBAL_ENGINE`. 상태표의 `[FFI_BRIDGED]`는 "브리지 연결 완료"가 아니라 "이식 완료, 브리지는 제거됨"으로 읽는다. `specs/`의 브리지 항목은 당시 설계 기록으로 남겨 둔다.

### 14.19 2FA·SAML·패스키 로그인과 `FaxQueue` (mock 테스트가 가린 결함)
기존 테스트는 `AFUserAccount`, 서비스, 세션을 mock으로 바꿔서 아래 문제를 보지 못했다. 새 테스트(`test_sso_and_2fa_login.py`)는 실제 앱·DB·WebTest로 로그인까지 확인한다.

| 결함 | 근거 | 수정 |
| :--- | :--- | :--- |
| **TOTP를 켠 사용자가 로그인하면 500** | 앱에 HTTP 세션 팩토리가 없어 `request.session`이 `AttributeError`. 2단계 인증 로그인이 불가능(잠김). 패스키 챌린지도 `hasattr(request,"session")`가 거짓이라 저장되지 않아 패스키 로그인은 항상 실패 | `create_app`이 서명 쿠키 세션(`namifax_flow`, HttpOnly, SameSite=Lax)을 등록. 비밀키는 `session.secret` 또는 `NAMIFAX_SESSION_SECRET`(없으면 프로세스별 임의 키 + 경고 로그, 운영에서는 고정 키 필요). `session.secure=true`로 Secure 플래그 |
| **SAML·패스키가 `AFUserAccount`에 없는 메서드를 호출** | `load_by_username`, `load_by_id`, `create_user`, `get_name`, `get_username`이 없어 `AttributeError`(SAML 최초 로그인 자동 생성, 패스키 등록·로그인 불가) | 메서드 추가. `name` 프로퍼티는 `FaxQueue`의 표시 이름 조회에도 쓰임 |
| **SAML·패스키 "로그인"이 실제로는 로그인되지 않음** | `request.session["username"]`만 기록하는데 보안 정책은 `remember()`의 토큰 쿠키로 인증 | 두 경로 모두 `remember()` 헤더를 내려줌. 비활성 계정은 `login_webauth`로 거부 |
| **SAML 계정 연결(보안)** | NameID의 `@` 앞부분으로 기존 계정을 찾아 `admin@다른회사`가 로컬 `admin`으로 로그인 가능 | 기존 계정은 IdP가 단언한 **이메일로만** 찾음. 새 계정은 앞부분에서 만든 빈 사용자명(`frank`, `frank1`, …), 관리자 아님, 사용되지 않는 임의 비밀번호 |
| SAML `RelayState` 열린 리다이렉트 | 브라우저가 보낸 값을 그대로 `Location`으로 사용 | 이 사이트의 경로(`/...`, `//`와 `\` 제외)만 허용, 아니면 `/inbox` |
| 패스키 챌린지 재사용 | 검증 후에도 세션에 남음 | 읽을 때 제거(1회용) |
| `FaxQueue`의 사용자 이름 조회 | 레거시 엔진 사용(PostgreSQL에서 혼합 대소문자 테이블명으로 실패), `AFUserAccount`에 `name`이 없어 표시 이름이 항상 폴백 | Session 사용(뷰가 `request.dbsession` 전달), 표시 이름 표시 |

**알려진 한계(미수정)**: SAML 로그인은 2FA 단계를 거치지 않는다(IdP가 인증을 책임진다는 가정). 6자리 TOTP 코드에는 시도 횟수 제한이 없다. SAML 서명 검증과 IdP 설정은 관리자 화면의 별도 기능이다.

### 14.20 보안 보완: 2FA 시도 제한과 비밀값 암호화 저장
**TOTP 시도 제한** (`services/totp.py`, `UserTOTP.failed_attempts/locked_until`, 리비전 0021)
* 6자리 코드는 값이 100만 개뿐이므로 사용자별로 틀린 시도를 **DB에 기록**한다(워커가 여럿이어도 같은 값). 연속 5회 실패하면 15분 잠기고, 잠긴 동안은 올바른 코드·복구 코드도 거부한다. 성공하면 카운터가 초기화되고, 잠금이 풀린 뒤 첫 실패는 1부터 다시 센다. 2FA를 다시 등록하면 잠금도 해제된다.
* **시도를 먼저 센다**: 확인하기 전에 원자적 증가(`failed_attempts = failed_attempts + 1`)로 시도를 확보하므로, 동시에 보낸 추측들이 모두 옛 카운트를 읽고 통과할 수 없다.
* 로그인 화면은 잠겼을 때 "Too many failed attempts. Try again in N minutes."를 보여준다. 기존 SQLite DB는 기동 시 컬럼이 추가되고(등록된 시드 유지), 서버 DB는 Alembic으로 추가된다.

**비밀값 암호화 저장** (`common/secretbox.py`, 리비전 0022)
| 대상 | 저장 위치 | 처리 |
| :--- | :--- | :--- |
| 클라우드 `secret_key` | `SystemConfig.cloud_secret_key` | `set_secret`/`get_secret`, 사용 시점(연결 테스트, 라이프사이클 실행)에 복호화 |
| SMTP 비밀번호 | `SystemSettings.smtp_password`(255→512자) | 저장 시 암호화, 읽을 때 복호화. 복호화 불가면 "없음"으로 취급(관리자가 다시 입력) |
| TOTP 시드 | `UserTOTP.secret_key` | 등록 시 암호화. 복호화 불가면 로그인 거부(fail closed) |

* 형식은 `enc:v1:<Fernet 토큰>`(AES-128-CBC + HMAC). 키는 환경변수 `NAMIFAX_SECRET_KEY` 또는 ini의 `secret.key`(환경변수 우선). Fernet 키 또는 16자 이상의 임의 문자열(HKDF로 유도)을 쓸 수 있고, 쉼표로 여러 개를 주면 **키 교체**가 가능하다(앞의 키로 암호화, 모든 키로 복호화).
* **키가 없으면 평문으로 저장하지 않고** `SecretKeyError`로 거부한다(관리자 화면에는 안내 문구가 표시됨). 기존 평문 값은 키 없이도 읽히고, 다시 저장될 때 암호화된다. `namifax encrypt-secrets`가 한 번에 변환한다(여러 번 실행해도 안전).
* **운영 절차**: ① 키 생성 `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` → ② `NAMIFAX_SECRET_KEY`로 설정 → ③ `namifax encrypt-secrets`. 키를 잃으면 암호화된 값은 복구할 수 없으므로 안전한 곳에 보관한다.

**남은 항목**: TOTP 복구 코드는 일회용 평문 값으로 저장된다(해시 저장으로 바꿀 수 있음). 현재 TOTP 등록(`enable_totp`)을 호출하는 화면·엔드포인트가 없어 사용자가 직접 2FA를 켤 방법이 없다(서비스와 로그인 단계만 존재).

### 14.21 레거시 `DatabaseEngine` 제거 — 최종 상태 (전부 ORM)
13~14.20은 전환 과정의 기록이다. 그 과정에서 쓰이던 아래 구성요소는 **모두 제거**되었다.

| 제거된 것 | 대체 |
| :--- | :--- |
| `db/engine.py` (`DatabaseEngine`, 문자열 SQL, `quote()`), `db/query.py`(`QueryBuilder`), `db/base.py`(`MDBObject`), `models/entities.py` | SQLAlchemy 세션 + 모델. 테이블 접근은 `db/repository.py`의 `Repository`/`MDBOData`(= `OrmRepository`) |
| `request.db`, `cli_db()`, `cli_unit()`/`CliUnit`, `open_db()` | `request.dbsession`, `cli_session()` (한 연결·한 트랜잭션, 정상 종료 시 커밋) |
| `db/schema.py` (SQLite DDL, 마이그레이션, 시드를 한 파일에서 raw SQL로) | ① 테이블 생성: Alembic(모든 DB 동일), ② 이전 버전 SQLite 보정: `db/sqlite_upgrade.py`, ③ 기본·데모 데이터: `db/seed.py`(ORM). 진입점은 `db/bootstrap.ensure_schema()` |
| 서비스의 이중 경로(`isinstance(db, Session)` 분기, 아카이브의 레거시 SQL, TOTP의 raw SQL 증가) | ORM 한 경로 |
| `CoverStudioService`, `faxcover` CLI의 raw SQL | ORM 조회·삽입 |

**남은 `db/` 패키지**: `provider`(URL 해석, 엔진 생성, `cli_session`), `bootstrap`, `sqlite_upgrade`, `seed`, `repository`/`orm_repository`, `missing`(주입을 잊었을 때 첫 사용에서 크게 실패하는 자리표시), `textsearch`.

**시작 순서** (`ensure_schema`): ① SQLite만: 이미 있는 옛 테이블 이름 변경(`DIDRouting`→`DIDRoute`, `FaxPDFCategory`→`FaxCategory`), `UserPasswords` 컬럼 이름, 주소록 키 재구성, 누락 컬럼 추가, 별칭 컬럼 채움, 텍스트 불리언 정리 → ② `alembic upgrade head`(없는 테이블만 생성) → ③ 시드(SQLite는 기본+새 DB에 한해 데모, 서버는 기본만). 실패하면 `RuntimeError("Database initialisation failed: …")`로 즉시 중단한다.
* 이전에는 시작 때 레거시 DDL이 먼저 모든 테이블을 만들어서 `DIDRouting`→`DIDRoute` 이름 변경이 실제로는 한 번도 실행되지 않았다(빈 `DIDRoute`가 이미 생겨 있었음). 순서를 바꿔 이름 변경이 동작한다.

**제거된 로직(Dead Code Removal Protocol)**
* 포트가 임의로 만들던 `FaxArchive.company` 컬럼과 그 시드(`company='Acme Corp'`), 읽기 폴백(`r.get("company")`).
* 호환용 뷰 `DIDRouting`, `FaxPDFCategory`(참조하는 코드가 없었다).
* 새 SQLite 데이터베이스가 만들던 포트 전용 컬럼(`FaxArchive.faxnum/cid_name/...`)과 중복 컬럼. 이제 새 DB는 모델과 Alembic이 정의한 구조만 갖는다(이전 DB의 잔여 컬럼은 건드리지 않음).

**테스트 구조**: `tests/sqlsession.py`의 `SqlSession`은 실제 `Session`에 테스트 설정·검증용 raw SQL 편의(`query`, `get_records`, `get_insert_id`, `quote`)를 더한 **테스트 전용** 클래스다(`seeded_session()`, `empty_session()`, `bare_session()`). 아카이브 검색의 기대 답은 레거시 SQL 구현에서 제거 전에 기록한 골든 데이터(`tests/unit/data/fax_archive_search_golden.json`)이며 ORM과 3개 서버 DB가 같은 답을 내는지 계속 검사한다.

**결과**: 프로덕션 코드에 raw SQL 문자열 조립 경로가 없다(`seed`/`sqlite_upgrade`의 고정 SQL 제외). SQLite, MySQL, MariaDB, PostgreSQL이 같은 코드 경로와 같은 Alembic 리비전으로 동작한다.

### 14.22 2FA 자가 설정과 복구 코드 해시 저장
**화면** (`views/settings_2fa.py`, `templates/settings_2fa.jinja2`, 설정 화면의 2FA 카드)
| 요청 | 동작 |
| :--- | :--- |
| `GET /settings/2fa/setup` | 새 비밀키를 만들고 QR(인라인 SVG, `segno`)·키·otpauth URI를 보여 준다. 확인 전의 비밀키는 흐름 쿠키에 **암호화해서**(`enc:v1`) 보관 |
| `POST /settings/2fa/enable` | 앱이 보여 주는 6자리 코드로 확인하면 켜지고 복구 코드 8개를 **한 번만** 보여 준다. 틀리면 같은 QR로 재시도 |
| `POST /settings/2fa/disable` | 비밀번호 + 유효한 코드(또는 복구 코드)가 필요. 틀린 코드는 잠금 횟수에 합산 |
| `POST /settings/2fa/recovery` | 유효한 코드를 입력하면 복구 코드를 새로 발급(기존 코드는 모두 무효) |
모든 POST는 CSRF 토큰(`request.session.get_csrf_token()`)을 확인한다. 로그인한 사용자만 접근 가능. 암호화 키가 없으면 설정 화면이 `NAMIFAX_SECRET_KEY` 안내를 보여 준다(오류 페이지가 아님).

**복구 코드**: `XXXXX-XXXXX`(10자, 0/O/1/I/L 제외, 약 49비트). DB에는 코드마다 다른 솔트의 **scrypt 해시**만 저장(`scrypt$<salt>$<hash>`). 입력은 대소문자·공백·하이픈을 무시하고, 맞으면 그 항목이 삭제된다(1회용). 6자리 숫자 입력은 복구 코드 형식이 아니므로 해시 비교를 건너뛰어 잘못된 TOTP 시도가 느려지지 않는다. 이전 버전의 평문 8자리 hex 코드도 한 번씩 쓸 수 있고, `namifax encrypt-secrets`가 해시로 바꾼다.

**운영**: 기기와 복구 코드를 모두 잃은 사용자는 `namifax reset-2fa <사용자명>`으로 2FA 등록을 지운다(관리자 작업).

**함께 고친 결함**: 설정 화면의 2FA 상태가 항상 "꺼짐"이었다. 세션 identity에는 `uid`가 없고 `user_id`만 있는데 `identity["uid"]`를 읽었기 때문이다. 이제 불러온 계정의 uid를 쓴다. 또 설정 화면의 "Enable 2FA"는 로그인 코드 입력 페이지(`/login/totp?setup=1`)로, "Disable 2FA"는 같은 페이지로 POST해서 실제로는 아무 동작도 하지 않았다.

