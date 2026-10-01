# 3라운드 G: src/avantfax 와 src/namifax 이중 트리 규명

점검 환경: scratchpad/agent-r3-g/repo (저장소 복제본), wheel 은 같은 복제본에서 `uv build --wheel` 로 생성, 재현 스크립트는 scratchpad/agent-r3-g/run/t_*.py. 모든 실행은 NAMIFAX_DB_PATH 를 agent-r3-g/run 하위로 지정.

## 0. 배포 대상 트리 확정

배포 대상은 src/namifax 이다.
- pyproject.toml: name="namifax", build-backend=uv_build (모듈명 = 프로젝트명 namifax 규약). 생성한 wheel 에는 namifax/ 만 있고 avantfax/ 는 0개 파일. (.py 89개 = src/namifax 의 .py 89개)
- entry_points: console_scripts 10개 전부 namifax.main:*, paste.app_factory main = namifax:main. development.ini / production.ini 의 `use = egg:namifax`.
- src/avantfax 는 어떤 배포 경로에도 들어가지 않는 개발 전용 트리다. 그런데 src/namifax 가 이를 런타임에 import 한다(표 2). 개발 venv 는 editable .pth 로 src 전체를 sys.path 에 올려 이 결함을 가린다.

## 1. 두 트리 차이 분류표

파일 집계(.py 만 대상, __pycache__/static/locale 제외 기준의 비교. 전체 파일 수는 avantfax 80, namifax 261).

| 분류 | 건수 | 내용 |
|---|---|---|
| 동일(바이트 단위) | 31 | auth/pam, auth/password, common/upload, common/validators 등 |
| 한쪽에만: avantfax | 6 | cli/{create_thumbnails, import_archive, import_blacklist, import_users, ocr_import, reroute}.py |
| 한쪽에만: namifax (.py) | 39 | views/* 18, services 10(cloud_storage, cover_studio, ocr, printer, saml, scheduler, smtp_settings, storage_lifecycle, totp, webauthn), cli 6, db/schema, i18n, models/meta, routes, security |
| 한쪽에만: namifax (비 .py) | templates 42, static 57, locale 49 | 웹 UI 자산은 전부 namifax 에만 존재 |
| 내용 다름, 무의미(import 경로/이름만) | 32 | auth/__init__, cli/{dynconf,faxcover,notify,phb}, common/__init__, db/{__init__,base,bridge_cli,query,repository}, models/entities, services 15종(addressbook, archive_*, barcode, categories, covers, did, distro, dynconf, modem, user_account, user_passwords, __init__), web/app, web/views/{archive,auth,inbox,outbox,sendfax} |
| 내용 다름, 의미 있음 | 11 | 아래 표 |

참고: "74개 파일에서 다르다"는 보고는 .pyc, 템플릿, 로케일 등을 포함한 수치로 보이며, .py 기준 동작 차이는 11개 파일이다.

의미 있는 차이 11건:

| 파일 | avantfax | namifax | 방향 |
|---|---|---|---|
| __init__.py | 패키지 docstring 만 | Pyramid create_app/main (+ImportError 폴백) | namifax 전용 |
| cli/__init__.py | 11개 서브모듈을 eager import | 비어 있음 | 구조 차이 |
| models/__init__.py | 엔티티 re-export | SQLAlchemy 세션 팩토리/includeme | 구조 차이 |
| db/engine.py | get_default_engine 이 namifax.db.engine 으로 위임, set_default_engine 없음 | 싱글턴 _DEFAULT_ENGINE 실체, set_default_engine 있음 | 의존 방향 역전 (R3G-05) |
| common/helpers.py | convert2pdf/tiff2pdf/pdf_preview/static_preview/faxinfo 가 스텁 (14바이트 가짜 PDF, 0바이트 썸네일, 가짜 faxinfo) | Pillow/tiff2pdf/faxinfo 실제 구현 | namifax 만 수정됨 (R3G-06) |
| cli/cron.py | getopt "i:t:d:" | "-p" 추가(TIFF 정리) | namifax 만 기능 추가 (R3G-08) |
| cli/faxrcvd.py | OCR 호출 없음 | OCR 호출 블록 추가 (faxname 미정의, K12) | namifax 만 추가 |
| main.py | serve 가 단일 스레드 wsgiref, 서브명령 7개 | ThreadingMixIn, scheduler/createuser/i18n 추가, avantfax.cli 5개를 cross-import | (R3G-06) |
| services/faxqueue.py | create_job 있음(항상 1001 반환 스텁) | create_job 없음 | avantfax 만 존재 (R3G-05) |
| services/mailer.py | send_mail 있음 (from_settings 없음) | from_settings 있음 (send_mail 없음) | 서로 반대로 갈라짐 (R3G-05) |
| web/views/admin.py | get_modems()/get_routes() 가 None 이면 TypeError | `or []` 방어 추가 | namifax 만 수정. avantfax 쪽은 같은 입력에서 크래시 |

한쪽에만 반영된 버그 수정(다른 쪽 미반영): web/views/admin.py 의 `or []` 방어, helpers 의 미디어 처리 실구현, mailer.from_settings, cron -p 가 namifax 에만 있다. 반대로 avantfax 에만 있는 faxqueue.create_job / mailer.send_mail 은 namifax.views.modals 가 avantfax 를 직접 import 해서 쓰므로 "수정이 닿지 않는" 형태로 남아 있다.

## 2. import 관계표

avantfax -> namifax (역방향 의존): 정확히 1곳.

| 위치 | 대상 | 비고 |
|---|---|---|
| avantfax/db/engine.py:249 (지연 import) | namifax.db.engine.get_default_engine | avantfax 의 "기본 엔진"이 namifax 싱글턴. avantfax 단독으로는 동작 불가 |

namifax -> avantfax (정방향, wheel 에는 avantfax 없음):

| 위치 | import 대상 |
|---|---|
| main.py:173,177,181,185,189 | avantfax.cli.{ocr_import, create_thumbnails, import_users, import_blacklist, reroute} |
| services/{storage_lifecycle, smtp_settings, cover_studio, saml, printer, totp, webauthn, ocr}.py (최상단) | avantfax.db.engine.DatabaseEngine |
| views/admin.py:8-12 (최상단) | avantfax.services.{barcode, categories, covers, did, dynconf} |
| views/admin.py:714, 737-738, 898, 981, 1054, 1173 (지연) | avantfax.services.{modem, addressbook, categories}, avantfax.db.engine.DatabaseEngine |
| views/modals.py:7-10 (최상단) | avantfax.services.{addressbook, archive_in, faxqueue, mailer} |

wheel 에서 import 실패하는 namifax 모듈 19개(실측, avantfax 를 sys.path 에서 제거): cli.print_in, services.{cover_studio, ocr, printer, saml, smtp_settings, storage_lifecycle, totp, webauthn}, views.{admin, ajax, archive, auth, inbox, modals, outbox, saml, sendfax, webauthn}. views 중 ajax/archive/auth/inbox/outbox/sendfax 는 직접 avantfax 를 import 하지 않아도 totp/ocr 등을 통해 연쇄적으로 실패한다.

순환: 최상단 import 순환은 없다(avantfax -> namifax 는 함수 내부 지연 import). 다만 논리적 순환(avantfax.db.engine <-> namifax.db.engine)이 있다.

이중 정의/싱글턴 검증 (t_dup.py 실측):
- avantfax.db.engine.DatabaseEngine is namifax.db.engine.DatabaseEngine -> False (별개 클래스).
- avantfax.db.engine.get_default_engine() is namifax.db.engine.get_default_engine() -> True (싱글턴은 한 벌, namifax 쪽 것).
- 그 싱글턴에 대해 isinstance(engine, avantfax.db.engine.DatabaseEngine) -> False, isinstance(engine, namifax...DatabaseEngine) -> True. 즉 avantfax 시그니처(`-> DatabaseEngine`)가 거짓이다.
- avantfax 에는 set_default_engine / _DEFAULT_ENGINE 이 없다. avantfax 서비스에 기본 엔진을 주입할 방법이 없다.
- db.base, db.query, db.repository, models.entities(14개 클래스), services.user_account, mailer, faxqueue, addressbook, common.validators, common.upload, auth.password 의 클래스 전부가 두 트리에서 별개 객체(공유 0). 같은 요청 처리 중 namifax.views.modals 는 avantfax.AFAddressBook, views.inbox 는 namifax.AFAddressBook 을 쓴다.
- namifax 코드에서 이 클래스들에 대한 isinstance 검사는 없어서 현재 isinstance 불일치로 오동작하는 곳은 없다(잠재 위험).
- 세 번째 루트: 테스트가 `src.namifax.*` 로 import 해서 11개 모듈이 `src.namifax.X` 와 `namifax.X` 로 두 번 로드된다(src.namifax 패키지 __init__ 도 2회 실행). `src.namifax.db.schema.init_database_tables is namifax.db.schema.init_database_tables` -> False.

## 3. 테스트 대상 표

tests/ 파일 69개 (conftest 없음). 기준: 최상단 import 와 patch 문자열.

| 대상 트리 | 파일 수 | 파일 |
|---|---|---|
| avantfax 만 | 38 | test_addressbook, archive_base/in/out, auth_pam, auth_password, barcode, categories, cli_batch_tools, cli_cron, cli_dynconf, cli_faxcover, cli_faxrcvd, cli_notify, cli_phb, cli_tools, covers, db_base, did, distro, dynconf, engine, faxqueue, helpers, mailer, main, models, modem, query, repository, user_account, user_passwords, validators, upload, web_admin, web_app, web_archive, web_auth, web_inbox, web_outbox, web_sendfax |
| namifax 만 (import 이름 기준) | 17 | test_helpers_media, test_i18n, main_namifax, ocr, pyramid_additional_views, pyramid_authorization, pyramid_modals_action, pyramid_saml, pyramid_webauthn, saml, scheduler, security_policy, vcard_upload, web_ajax, web_helpers, webauthn, tests/web/test_web_{addressbook,inbox_views} |
| `src.namifax` 경로 | 10 | cli_print_in, cloud_storage, cover_studio, network_printer, storage_lifecycle, pyramid_admin_smtp, totp, smtp_settings (+avantfax 엔진 혼용: cover_studio, network_printer, storage_lifecycle, totp, smtp_settings, pyramid_admin_smtp) |
| 혼합 | 3 | pyramid_admin_crud(avantfax patch), pyramid_admin_smtp, pyramid_totp_auth |

(표의 파일 수는 분류가 겹치는 행이 있어 합이 69 와 다를 수 있다. 전체 362개 테스트는 현재 전부 통과.)

namifax 트리에서 직접 테스트가 전혀 없는 모듈 53개(테스트가 import 또는 patch 하지 않음):
auth.pam, auth.password, cli.{cron, dynconf, faxcover, faxrcvd, notify, phb, user, populate_all_locales, populate_ko, populate_missing_translations}, common.{upload, validators}, db.{base, bridge_cli, engine, query, repository}, models.{entities, meta}, routes, services.{addressbook, archive_base, archive_in, archive_out, barcode, categories, covers, did, distro, dynconf, faxqueue, modem, user_account, user_passwords}, views.{archive, default, forbidden, notfound, outbox, sendfax, settings}, web.app, web.views.{admin, archive, auth, inbox, outbox, sendfax}.
(이들은 avantfax 복제본이 테스트되거나 간접 실행만 된다. avantfax 쪽 직접 미테스트는 cli.import_archive, db.bridge_cli 2개.)
coverage(--cov=src, 파일별 전체 실행률): namifax 의 cli.faxrcvd 15%, cli.notify 11%, services.faxqueue 13%, views.settings 11%, views.sendfax 20%, views.outbox 23%, web.app 16%.

## 4. 폴백 웹 앱 (namifax.web.app / avantfax.web.app)

- avantfax.web.app 은 폴백이 아니라 avantfax.main serve 의 "정상" 앱이다(avantfax 트리에는 Pyramid 앱이 없다). namifax.web.app.AvantFaxApp 은 byte 단위로 이름만 다른 복제.
- 폴백 진입 조건: namifax.create_app 의 try 블록 안에서 ImportError 가 나면 그대로 `namifax.web.app.create_app()` 을 반환. 실측으로 확인한 트리거: (a) wheel 설치(avantfax 없음, 19개 모듈 실패), (b) pyotp, webauthn, defusedxml, pyramid_jinja2 중 하나라도 없음 (boto3, pytesseract, PIL, babel, apscheduler 는 지연 import 라 폴백 안 됨). `namifax serve` 는 추가로 모든 Exception 을 잡아 폴백.
- 정상 앱과의 차이 (실측): 정상 앱은 pyramid.router.Router 로 /login 은 HTML, /inbox 는 401 JSON, /static 은 CSS, 없는 경로는 404. 폴백은 /api/* 를 제외한 모든 경로(/, /login, /inbox, /admin, /static/css/main.css, /nope, 그리고 POST /login)가 `200 text/plain "AvantFAX Modern Web System Ready"`. /api/health 는 200 `{"status":"ok"}`. HTML UI, i18n, CSRF 이전에 정책, 보안 정책 모두 없음. JSON API 경로는 /api/auth/login, /api/inbox/list 등 정상 앱에 없는 별개 계약.

## 결함

### R3G-01 [높음, 재현] wheel/ini 로 배포하면 사이트 전체가 "Ready" 텍스트 스텁이 되고 모든 URL 이 200
- 위치: namifax/__init__.py create_app 의 except ImportError, views/admin.py:8 외 avantfax import 19개 모듈
- 증상: wheel 을 풀어 avantfax 가 없는 환경에서 create_app({}) 를 호출하면 반환형이 pyramid Router 가 아니라 namifax.web.app.AvantFaxApp. GET /, /login, /inbox, /admin, /static/css/main.css, /nope 와 POST /login 이 전부 200 text/plain "AvantFAX Modern Web System Ready". 헬스체크(200)로 장애를 감지할 수 없고 로그도 없다.
- 재현: `uv build --wheel`; wheel 을 풀고 sys.path 에서 src 제거 후 t_app.py 실행(agent-r3-g/run/t_app.py). 원인은 venusian scan 이 views/admin.py 의 `from avantfax...` 에서 ModuleNotFoundError 를 던지는 것(t_why.py).
- 비고: COR-25/ADM-28(wheel 에 avantfax 없음)과 F5-02(폴백 스텁)의 결합이지만, 종단 증상(모든 경로 200 텍스트, 로그인 불가)을 측정한 결과를 별도로 기록.

### R3G-02 [높음, 재현] 폴백 JSON 로그인이 올바른 비밀번호에서도 AttributeError 로 죽고, 시드 계정은 로그인 자체가 불가
- 위치: namifax/web/views/auth.py:39-44 (avantfax 쪽 동일)
- 증상: AuthHandler.login 이 성공 후 `user.username` 을 읽는데 AFUserAccount 에 username 속성이 없음(dbdata 에 있음) -> 500(AttributeError). 또 `getattr(user, "is_admin", False)` / `"superuser"` 도 속성이 없어 성공했더라도 항상 False, 즉 세션이 관리자여도 비관리자로 생성됨. 시드 admin/operator 는 비밀번호가 평문 'password' 로 들어가 있고 login 은 md5 비교라서 401(폴백에는 K10 의 하드코딩 우회도 없다). 폴백 앱은 사실상 누구도 로그인할 수 없다.
- 재현: createuser 로 md5 계정 생성 후 POST /api/auth/login -> `AttributeError: 'AFUserAccount' object has no attribute 'username'` (run/t_fb3.py). 시드 계정은 t_fb.py 에서 401.
- 근거: 테스트(test_web_auth)는 AFUserAccount 를 Mock 으로 대체해 이를 못 잡음.

### R3G-03 [중간, 재현] paste 진입점 `namifax:main` 이 서브모듈 namifax.main 과 이름 충돌
- 위치: namifax/__init__.py 의 `main = create_app` 과 namifax/main.py
- 증상: 프로세스에서 `namifax.main` 모듈이 한 번이라도 import 되면(namifax CLI, 테스트, 워커가 CLI 모듈을 import) 패키지 속성 `namifax.main` 이 함수에서 모듈로 덮어써져 `egg:namifax` 로드가 `TypeError: 'module' object is not callable` 로 실패.
- 재현: t_paste.py — import 전에는 development.ini 로드가 Router 반환, `import namifax.main` 후 같은 로드가 TypeError.
- 근거: 테스트는 전부 create_app 을 직접 호출하고 egg:namifax 경로를 로드하는 테스트가 없다.

### R3G-04 [중간, 재현] 개발 환경이 avantfax 의존을 가리고, wheel 설치 검증과 이중 모듈 루트가 테스트에 섞임
- 위치: .venv/.../namifax.pth (src 전체를 sys.path 에 추가), pyproject [tool.pytest] pythonpath=[".","src"]
- 증상: editable 설치가 src/avantfax 를 항상 import 가능하게 만들어 R3G-01 을 개발자와 테스트가 절대 보지 못한다. 또한 pythonpath 에 "." 와 "src" 가 동시에 있어 테스트 10개가 `src.namifax.*` 로 import 하고, 그 결과 11개 모듈이 두 번 로드되며 클래스와 함수가 별개 객체가 된다(실측 double-loaded 11). 이 때문에 단위 테스트가 검증하는 모듈 객체와 앱이 쓰는 모듈 객체가 다를 수 있다.
- 재현: t_whl.py (wheel 기준 실패 19개), pytest 종료 후 sys.modules 검사.

### R3G-05 [중간, 재현] namifax 뷰가 avantfax 스텁 구현에 묶여 있어 namifax 쪽 수정이 닿지 않고, 엔진 클래스가 이종
- 위치: views/modals.py:7-10, services/faxqueue.py(create_job 없음), services/mailer.py(send_mail 없음 / from_settings 만), avantfax/db/engine.py:247-250
- 증상: modal_refax 는 avantfax.FaxQueue.create_job(항상 1001) 을, modal_email 은 avantfax.Mailer.send_mail 을 호출한다. namifax 의 FaxQueue 에는 create_job 이 없고 Mailer 에는 send_mail 이 없으며, 반대로 SMTP 설정을 읽는 Mailer.from_settings 는 namifax 쪽에만 있어 모달 메일이 관리자 SMTP 설정에 닿을 수 없다. namifax 서비스만 고치면 모달은 영향을 받지 않고, avantfax 를 지우면 모달 임포트가 깨진다. 또 avantfax.db.engine.get_default_engine 이 namifax 클래스의 인스턴스를 avantfax.DatabaseEngine 타입으로 반환하므로 isinstance/타입이 모순(섹션 2), avantfax 에는 주입용 set_default_engine 도 없어 avantfax 서비스 테스트는 항상 cwd 의 namifax.db 싱글턴 또는 수동 주입에 의존한다.
- 비고: F4-01/F2-08(1001 스텁), ADM-17(SMTP 미사용)의 구조적 원인 차원 변형.

### R3G-06 [중간, 재현] namifax CLI 서브명령 5개가 미디어 스텁이 남아 있는 avantfax 코드를 실행 (namifax 의 개선이 우회됨)
- 위치: namifax/main.py:172-194, avantfax/common/helpers.py, avantfax/cli/create_thumbnails.py:11
- 증상: `namifax create-thumbnails` 는 avantfax.common.helpers.pdf_preview 를 호출한다. 이 버전은 0바이트 thumb.png 만 만들고 preview0.png 를 만들지 않아 같은 팩스가 매번 "Creating images" 로 재처리된다. 같은 입력으로 비교하면 avantfax.tiff2pdf 는 14바이트 가짜 PDF 를 만들고 입력 파일이 없어도 True, namifax.tiff2pdf 는 182,623바이트 PDF 생성/입력 없으면 False. avantfax.faxinfo 는 3쪽 TIFF 에 Pages=1, namifax 는 Pages=3. static_preview 는 avantfax 가 thumb 만, namifax 가 preview0~2 까지 생성. import-users/import-blacklist/reroute 도 avantfax 서비스(avantfax.db.repository 경유)를 쓰므로 동일 엔진이지만 다른 클래스 계층을 탄다. wheel 에서는 5개 전부 ModuleNotFoundError.
- 재현: run/t_diff.py, t_diff2.py (동일 입력, 두 트리 호출 결과).
- 근거: 단위 테스트(test_helpers, test_cli_batch_tools)가 스텁 쪽(avantfax)을 검증해 통과한다.

### R3G-07 [중간, 추론(코드 확인)] `namifax ocr-import` 는 OCR 을 하지 않는 스텁이고 OcrService 와 연결되지 않음
- 위치: avantfax/cli/ocr_import.py:14-22
- 증상: ocr_faxcontent() 가 항상 "" 를 반환하고 namifax.services.ocr.OcrService 를 호출하지 않는다. ENABLE_OCR_SUPPORT 는 모듈 import 시점에 환경변수를 읽어 고정되고, 꺼져 있으면 "local_config.php 에서 활성화하라"(존재하지 않는 PHP 파일)라고 출력하고 종료코드 0. 켜도 set_faxcontent 는 빈 문자열이라 호출되지 않아 일괄 OCR 이 영구히 아무것도 저장하지 않는다.
- 비고: COR-27/ADM-15(OcrService 경로)와 별개의 CLI 경로 원인.

### R3G-08 [낮음, 재현] cron 의 namifax 전용 `-p` 옵션이 도움말에 없고 -t 없이 동작하지 않으며 오류를 삼키고, -i/-d 는 잘못된 값에서 트레이스백
- 위치: namifax/cli/cron.py:55-111 (USAGE 는 -p 없음)
- 증상: `cron -p 30` 은 -t 가 없으면 usage 만 출력하고 0 종료(정리 안 함). `-t 1 -p abc` 는 조용히 무시, `-t 1 -i abc` 는 ValueError 트레이스백(양 트리 동일). avantfax 트리는 -p 자체가 없다. -p 경로는 테스트가 전혀 없다.
- 재현: run/t_cron.py.

### R3G-09 [중간, 재현] 선택 기능용 라이브러리 하나가 없어도 전체 UI 가 폴백 스텁으로 교체됨
- 위치: services/totp.py(pyotp), services/webauthn.py(webauthn), services/saml.py(defusedxml) 의 최상단 import, namifax/__init__.py
- 증상: pyotp, webauthn, defusedxml, pyramid_jinja2 중 하나만 import 불가여도 create_app 이 폴백 앱(R3G-01 동작)을 반환한다. 2FA/패스키/SAML 은 전부 선택 기능인데 없으면 로그인 화면 전체가 사라진다. boto3, pytesseract, PIL, babel, apscheduler 는 지연 import 라 영향 없어 일관성도 없다.
- 재현: run/t_block.py <모듈명> (meta_path 로 import 차단, 공격 페이로드 아님).
- 비고: F5-02 의 일반 원인 외에 구체 트리거를 식별한 변형.

### R3G-10 [낮음, 재현/추론] 테스트가 avantfax 복제본을 검증해 namifax 전용 분기와 53개 모듈이 미검증
- 위치: tests/unit/test_cli_faxrcvd.py:52, test_cli_notify.py:62 등
- 증상: faxrcvd/notify/cron 테스트는 avantfax.cli.* 를 patch 해서 실행하므로 namifax.cli.faxrcvd 에만 있는 OCR 블록(faxname 미정의, K12)과 cron -p 는 한 번도 실행되지 않는다. 섹션 3 의 53개 모듈은 테스트가 직접 import 하지 않는다(views.outbox, views.sendfax, views.settings, views.archive, cli.user, web.app 포함). F5-05 의 구체 모듈 목록과 "그린인데 배포본이 다르다"는 사례 보강.

## 요약
- 배포 트리: src/namifax (avantfax 는 wheel 미포함, 단 namifax 가 런타임 import).
- 총 10건: 높음 2, 중간 6, 낮음 2 (치명 0).
- 동작 차이 파일은 .py 기준 11개, 한쪽에만 반영된 수정은 helpers/cron/mailer/admin view 에서 확인.
