---
title: 아키텍처와 모듈
type: topic
updated: 2026-10-02
sources: [src/namifax/__init__.py, src/namifax/main.py, src/namifax/routes.py, src/namifax/security.py, src/namifax/sessions.py, src/namifax/origin_guard.py, src/namifax/models/__init__.py, src/namifax/db/provider.py, src/namifax/db/repository.py, src/namifax/db/bootstrap.py, src/namifax/views/inbox.py, pyproject.toml, "[[architecture-md-part1]]", "[[architecture-md-part2]]", "[[db-layer-refactor-log]]"]
verified: true
---

# 아키텍처와 모듈

## 진입점
- `pyproject.toml` 의 스크립트: `namifax`(=`namifax.main:main`, 하위 명령 분기), `namifax-server`(`serve_main`), `namifax-scheduler`, `namifax-createuser`, `namifax-dynconf`, `namifax-faxrcvd`, `namifax-notify`, `namifax-faxcover`, `namifax-cron`, `namifax-phb`. [코드] `pyproject.toml`
- paste 진입점 `paste.app_factory: main = namifax:main` 이고 `namifax.main = create_app` 이므로 ini 로도 띄울 수 있다(`development.ini` 는 waitress, `0.0.0.0:6543`). [코드] `pyproject.toml`, `src/namifax/__init__.py`, `development.ini`
- `namifax <명령>` 명령 목록: serve, scheduler, createuser, import-archive, reset-2fa, encrypt-secrets, dynconf, cron, notify, faxrcvd, faxcover, phb, ocr-import, create-thumbnails, import-users, import-blacklist, reroute, i18n. [코드] `src/namifax/main.py` `main()`
- `serve_main`: 같은 방식으로 URL 을 풀어 `ensure_schema` 실행 → 스케줄러 시작(`NAMIFAX_ENABLE_SCHEDULER`) → `create_app()`. 앱 생성이 실패하면 대체 앱으로 숨기지 않고 stderr 에 쓴 뒤 종료 코드 `1`. [코드] `src/namifax/main.py`, `tests/unit/test_legacy_trees_removed.py`
- `main.py` 의 `faxrcvd_main` 등은 PHP 시절 스크립트 이름(`faxrcvd.php`, `notify.php`, `avantfaxcron.php`)을 `argv[0]` 으로 넣어 호출한다. [코드] `src/namifax/main.py`

## create_app 이 하는 일 ([코드] `src/namifax/__init__.py`)
1. `Configurator(root_factory=RootContext)` 와 `NamiFaxSecurityPolicy` 를 설정한다(`registry.namifax_policy` 에 보관).
2. 서명 쿠키 세션 `namifax_flow`(2FA 단계, 패스키 챌린지용 짧은 흐름 상태). 로그인 자체는 보안 정책의 토큰 쿠키가 한다. 비밀은 `session.secret` 또는 `NAMIFAX_SESSION_SECRET`, 없으면 프로세스마다 무작위값을 쓰고 경고를 남긴다.
3. `secret.key` 설정을 `secretbox` 기본 키로 등록.
4. 번역 디렉터리 `namifax:locale`, 로케일 협상기 `custom_locale_negotiator`.
5. `pyramid_jinja2` 와 `.models` include. `.models` 가 `pyramid_tm`, `pyramid_retry`, 엔진 1개, `request.dbsession`(reify) 을 만든다.
6. `BeforeRender` 구독자가 모든 템플릿에 스위치(`did_routing_enabled`, `barcode_enabled`, `dl_tiff_enabled` 등)와 헤더용 수치(안 읽은 수 `num_inbox`, `user_full_name`, `modem_devices`)를 넣는다.
7. `ensure_schema(engine, settings)` → `.routes` include → 트윈 `namifax.origin_guard.origin_guard_factory` → `config.scan(".views")`.

## 계층과 의존 방향
```
views  ->  services  ->  db(Repository/ORM)  ->  models
  \          \-> common, auth
   \-> templates(Jinja2)         cli -> services/db/common   (웹과 독립된 진입점)
```
의존은 위에서 아래로만 흐른다. [추정] 순환을 막는 규칙이 코드로 강제되는지는 확인하지 못했다(시험은 찾지 못함).

| 패키지 | 책임 | 근거 |
|---|---|---|
| `views/` | Pyramid 뷰(`@view_config`). 폼 처리, 권한 지정, 서비스 호출, 템플릿 렌더링. `admin.py`(약 1100줄)가 관리자 화면 대부분을 가진다 | [코드] `src/namifax/views/*.py` |
| `services/` | 업무 로직(주소록, 보관함 `archive_in/out/base/orm`, 큐, 커버 페이지, DID/바코드 라우팅, 모뎀, 메일, OCR, TOTP, WebAuthn, SAML, 스케줄러, 저장소 수명 주기, 시스템 설정 등). 세션을 인자 `db=` 로 받는다 | [코드] `src/namifax/services/` |
| `models/` | SQLAlchemy 모델(테이블 이름은 원본처럼 `UserAccount`, `FaxArchive` 등 혼합 대소문자), `meta.Base`, `types.py` | [코드] `src/namifax/models/` |
| `db/` | `provider`(URL 해석, 엔진, `cli_session`), `bootstrap`(`ensure_schema`), `repository`/`orm_repository`(PHP `MDBOData` 호환 API), `adopt`/`sqlite_upgrade`(기존 테이블 수용), `seed`, `missing`, `textsearch` | [코드] `src/namifax/db/` |
| `common/` | `settings`(원본 `local_config.php` 이름의 환경변수), `secretbox`(자격증명 암호화), `passwords`(Argon2id + MD5 수용), `helpers`, `upload`, `validators` | [코드] `src/namifax/common/` |
| `auth/` | `password`(해시, 외부 pwauth), `pam`, `alternate`(대체 인증 설정) | [코드] `src/namifax/auth/` |
| `cli/` | HylaFAX 훅과 배치 도구, 사용자 관리, i18n 관리 | [코드] `src/namifax/cli/` |
| 최상위 모듈 | `security.py`(ACL, 보안 정책), `sessions.py`(메모리 로그인 세션), `origin_guard.py`(CSRF 성격 방어 트윈), `i18n.py`, `routes.py` | [코드] |
| `alembic/` | 리비전 `20261001_0001` ~ `20261002_0026` | [코드] `src/namifax/alembic/versions/` |

- DB 세션은 요청마다 `request.dbsession` 으로, CLI 는 `cli_session()` 으로 얻는다. 전역 엔진은 없다(엔진은 레지스트리 `dbengine`). [코드] `src/namifax/db/provider.py`, `src/namifax/models/__init__.py`, `tests/unit/test_global_engine_removed.py`
- `db=` 를 빠뜨리면 `db/missing.py` 의 자리표시자가 첫 사용 때 큰 소리로 실패한다. [코드] `src/namifax/db/repository.py` docstring
- DB URL 우선순위: `sqlalchemy.url` 설정 > `DATABASE_URL` > `AFDB_URL` > `NAMIFAX_DB_PATH` 또는 현재 폴더의 `namifax.db`. [코드] `src/namifax/db/provider.py`
- 세부는 [[database-and-migrations]], 인증은 [[authentication-and-security]].

## 보안 정책과 권한
- ACL: `public` 은 모두, `view`·`send_fax` 는 인증된 사용자, `admin` 은 `role:admin` 만(나머지 Deny). [코드] `src/namifax/security.py` `RootContext.__acl__`
- 신원은 `Authorization: Bearer`, 쿠키 `namifax_session`(옛 이름 `avantfax_session` 도 받음), 흐름 세션 순으로 토큰을 찾아 `SessionManager` 에서 조회한다. [코드] `src/namifax/security.py`
- 로그인 세션 저장소는 프로세스 메모리다(`sessions.py`). [코드] 파일 제목 "in-memory login session management" [추정] 다중 워커에서는 세션이 공유되지 않는다. 확인 필요.
- `origin_guard`: `POST/PUT/PATCH/DELETE` 가 `Origin`(없으면 `Referer`)을 말하면 요청 호스트, `X-Forwarded-Host`, `csrf.trusted_origins` 중 하나여야 한다. SAML ACS/SLS 경로는 제외. [코드] `src/namifax/origin_guard.py`

## 라우트와 뷰 구조
- `routes.py` 의 `includeme` 가 `static` 뷰(`cache_max_age=3600`)와 라우트를 모두 선언한다. 뷰는 `config.scan(".views")` 로 `@view_config` 에서 모은다. [코드] `src/namifax/routes.py`
- 묶음별 라우트(이름 → 경로):
  - 공개: `home /`, `login`, `logout`, `forgot`, `pwdexpired`, `login_totp /login/totp`
  - 사용자: `inbox`, `viewfax`, `/faxes/download|image|thumbnail|rotate/...`, `sendfax`, `outbox`, `archive`, `/search`(OpenSearch), `addressbook(/edit)`, `emailbook(/edit)`, `distrolist(/edit)`, `settings`, `/settings/2fa/{setup,enable,disable,recovery}`
  - 관리자(`permission="admin"`): `/admin`, `/admin/users`, `modems`, `routing/did`, `barcodes`, `covers`, `categories`, `dynconf`, `fax2email`, `system_func`, `system_logs`, `smtp`, `printers`, `storage`, `scheduler(/state,/jobs)`, `saml`
  - 모달: `/email`, `/assign`, `/assignx`, `/note`, `/delete`, `/refax`, `/txreport`
  - AJAX: `/ajax/{modemstatus,inbox,book,emailbook,prefillto,dlist,archivefax,faxalter,deletefaxes,archivebook}`, `/audio/{name}`
  - 도우미 팝업 `/helper/*`, vCard 업로드 `/upload/contacts|faxcontacts`
  - WebAuthn `/api/webauthn/...`, SAML `/auth/saml/{metadata,login,acs,sls}`
- 일부 경로는 별칭이 둘이다(`admin_did`/`admin_routing_did`, `admin_sysfunc`/`admin_system_func`, `admin_syslog`/`admin_system_logs`). [코드] `src/namifax/routes.py`
- 뷰 파일: `inbox, outbox, archive, sendfax, addressbook, distrolist, modals, ajax, fax_files, fax_rights, helpers, auth, settings, settings_2fa, webauthn, saml, admin, admin_users, admin_scheduler, default, forbidden, notfound, no_database`. 렌더러는 `renderer="namifax:templates/<이름>.jinja2"` 또는 `json`. [코드] `src/namifax/views/`, `src/namifax/views/inbox.py`
- 팩스 접근 권한 계산은 `views/fax_rights.py` 의 `fax_access(request)` 와 `services/fax_access.py` 가 한다. [코드] `src/namifax/__init__.py` 에서 import
- 화면 규칙은 [[i18n-and-ui]].

## 모순 기록
> 모순: [[architecture-md-part1]] / [[architecture-md-part2]] 의 의존성 그래프와 "이식 상태 `[PENDING]`/`[IN_PROGRESS]`" 표, `[FFI_BRIDGED]` 개념은 현재 코드에 대응물이 없다(이식 완료, 브리지 없음). [코드] 위 구조를 따른다.
> 모순: 요약이 말하는 "JSON 대체 웹 앱" 이나 `avantfax` 복사본은 없다. [코드] `tests/unit/test_legacy_trees_removed.py` 가 `avantfax`, `namifax.web` 모듈 부재를 확인한다.
