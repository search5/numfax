# 2라운드 운영/배포/검증 체계 점검 결과 (F5-xx)

실험 환경: scratchpad/agent-r2-ops/clone (깨끗한 git clone). `uv sync --frozen`, `uv build`, 엔트리포인트 10종 실행, pserve(production.ini, 포트 18601), `namifax-server`(18602), 전체 pytest, pytest-randomly 시드 반복, 테스트 파일별 개별 실행, 스케줄러 잡 직접 실행.
정상 확인: `uv sync`/`uv lock --check`/`uv build` 성공(sdist+wheel), 엔트리포인트 10종 모두 --help 또는 최소 인자로 기동(단, server/scheduler는 --help 를 해석하지 않고 그대로 구동됨), production.ini 로 waitress 기동 및 /login 200.

---

## F5-01 [높음] 운영 기동 경로(systemd, namifax serve, namifax-server)가 waitress 가 아니라 wsgiref 개발 서버이고 ini 를 전혀 읽지 않음
- 위치: src/namifax/main.py `serve_main`, systemd/namifax.service, production.ini
- 증상: `make_server(..., ThreadingWSGIServer)`(wsgiref) 사용. 응답 헤더 `HTTP/1.0`, `Server: WSGIServer/0.2 CPython`, 리슨 백로그 5, 요청당 스레드 무제한 생성, 타임아웃/헤더 크기/본문 크기 제한 없음. waitress 는 의존성에 선언돼 있으나 systemd 유닛은 `namifax serve` 를 쓰므로 production.ini([server:main], 로깅 설정, reload_templates=false)는 적용되지 않음. 포트도 ini 6543, 유닛 8000 으로 서로 다름. 앱 설정은 `create_app()` 을 settings 없이 호출하므로 ini 의 pyramid.* 값도 무시됨.
- 재현: `namifax-server` 기동 후 `curl -i localhost:18602/` -> `HTTP/1.0 200`, `Server: WSGIServer/0.2`. 같은 앱을 `pserve production.ini` 로 띄우면 `Server: waitress`.
- 확인 수준: 재현

## F5-02 [높음] 임포트/앱 생성 오류가 조용히 전혀 다른 JSON 스텁 앱으로 대체됨
- 위치: src/namifax/__init__.py `create_app` 의 `except ImportError`(fallback_create_app), src/namifax/main.py `serve_main` 의 `except Exception: app = create_app()`
- 증상: 의존성 하나가 없거나 설정 오류가 있으면 오류 없이 `AvantFAX Modern Web System Ready` 텍스트와 /api/* JSON 만 주는 별개의 스텁 앱(namifax.web.app)이 200 으로 뜸. 로그도 없음. 헬스체크가 통과하고 UI 는 전부 사라지는 형태의 장애가 됨.
- 재현: `sys.modules['pyramid_jinja2']=None` 후 `namifax.create_app({})` -> `AvantFaxApp` 반환, `GET /login` -> `200 AvantFAX Modern Web System Ready`.
- 확인 수준: 재현

## F5-03 [높음] DB 열기/스키마 초기화 실패를 삼키고 200 + 가짜 데이터로 서비스 계속
- 위치: src/namifax/__init__.py (init_database_tables 를 `except Exception: pass`), db/engine.py `connect_sqlite`(실패 시 False 만 반환), db/schema.py `init_database_tables`(첫 DDL 실패 시 False 반환, 호출부가 무시)
- 증상: NAMIFAX_DB_PATH 가 쓸 수 없는 경로여도 기동 성공. 로그인(admin/password)이 통과하고 /inbox, /addressbook 이 200 으로 가짜 행을 표시. 운영자는 DB 가 없다는 사실을 알 수 없음.
- 재현: `NAMIFAX_DB_PATH=/nonexistent_dir/x.db` 로 create_app 후 로그인, `/inbox` 200(12420B), `/addressbook` 200.
- 확인 수준: 재현

## F5-04 [높음] 팩스 전송 결과 무시 + sendfax 바이너리 부재 시 가짜 성공 + 업로드 임시파일 미삭제
- 위치: src/namifax/views/sendfax.py `dispatch_sendfax`/`sendfax_view`(118-135행), src/namifax/web/views/sendfax.py(80-90행)
- 증상: `dispatch_sendfax` 반환값(`success: False`, 오류 출력)을 버리고 항상 /outbox 로 리다이렉트. 바이너리가 없으면 uuid 로 가짜 jobid 를 만들어 `success: True`. 업로드 파일은 `tempfile.gettempdir()` 에 저장 후 삭제하지 않아 /tmp 가 계속 증가하고 (다른 사용자에게 읽힐 수 있는 경로). 이 환경에는 sendfax 바이너리가 없음(`which sendfax` 빈 결과).
- 확인 수준: 추론(코드 근거)

## F5-05 [높음] 테스트 48개 파일 중 다수가 wheel 에 포함되지 않는 src/avantfax 트리를 검증
- 위치: tests/**, pyproject.toml(pythonpath = [".", "src"])
- 증상: `from avantfax...` 를 임포트하는 테스트 파일 48개, `namifax` 를 임포트하는 파일 20개. avantfax 만 임포트하고 namifax 는 임포트하지 않는 파일이 41개. 배포되는 패키지는 namifax 뿐이므로 362개 통과가 배포물 품질을 보증하지 못함. pythonpath 에 src 가 들어 있어 wheel 에 없는 트리가 계속 임포트되어 패키징 결함(COR-25)이 테스트에서 드러나지 않음. golden_master CLI 타깃(`python -m avantfax.cli.*`)도 같은 문제.
- 재현: grep 집계, wheel 내용 목록에 avantfax 없음.
- 확인 수준: 재현

## F5-06 [높음] Web golden master 가 자기 참조적이며 가짜 데이터를 "정답"으로 고정
- 위치: golden_master/generate_web_golden.py, extract_live_forms.py, apply_strict_form_contracts.py, web_runner.py
- 증상: (a) 계약은 실제 레거시 실행에서 녹화한 것이 아니라 손으로 쓴 마크업에서 생성됨("derived from legacy ... markup"). (b) `form_structure` 는 새 앱을 실행해 추출한 live_form_structures.json 으로 덮어써 앱이 자기 출력과 비교됨. (c) W05 inbox 계약의 required_text 가 "Acme Corp", "2026-09-29" 이고 이는 뷰의 하드코딩 placeholder(views/inbox.py:49-51, archive.py:62-65) 이므로 USR-02/UI-07 류 결함이 오히려 통과 조건. (d) 브랜드 별칭 치환(avantfax->namifax)을 허용. (e) 저장된 response.html 은 web_runner 에서 전혀 비교되지 않음. (f) 검사 항목은 필드 이름 존재, 버튼/입력 개수, 텍스트 포함 여부에 한정되고 값, 동작, 권한, DB 상태는 비교하지 않음.
- 재현: `pytest golden_master` 88 passed 이지만 위 결함들이 전부 존재.
- 확인 수준: 재현

## F5-07 [중간] CLI golden master 20건이 모두 "인자 없음/누락" 사용법 출력뿐
- 위치: golden_master/runner.py SCENARIOS, golden_master/data/*
- 증상: 20개 시나리오가 usage/오류 종료 경로뿐이고 실제 처리(수신, 통지, 차단, 정리, 커버 생성)를 비교하는 건 없음. 그래서 faxrcvd/notify/cover 의 핵심 결함(COR-03, 05, 06, 16 등)이 전혀 잡히지 않음. 타깃도 avantfax 트리.
- 확인 수준: 재현

## F5-08 [중간] 테스트가 실행 순서에 의존 (pytest-randomly 로 재현)
- 위치: tests/unit/test_cli_tools.py::test_create_thumbnails_empty_archive
- 증상: 무작위 순서에서 시드 3, 4, 5, 7, 9, 11 에서 실패: `assert "No faxes found" in '1 faxes in Archive ...'`. 이전 테스트가 전역 싱글턴 DatabaseEngine(`get_default_engine`)에 넣은 아카이브 행이 남아서 생김. 테스트 간 DB 초기화/격리 fixture 없음(conftest.py 없음, set_default_engine 호출 0건).
- 재현: `pytest -p randomly --randomly-seed=3` -> 1 failed, 361 passed. 개별 파일 단위 실행은 전부 통과.
- 확인 수준: 재현

## F5-09 [중간] 테스트가 작업 트리와 CWD 의 DB 를 오염시킴
- 위치: tests/**(전역 engine 사용), src/namifax/db/engine.py(`cwd/namifax.db`)
- 증상: NAMIFAX_DB_PATH 없이 pytest 를 실행하면 저장소 루트에 namifax.db(시드 포함)를 만들고 테스트가 그 영속 상태를 재사용하며, 별도로 저장소 루트에 `faxes/2026/09/29/fax001/thumb.png` 를 생성함(`git status`: `?? faxes/`, .gitignore 에 없음). 개발자의 실제 DB 를 테스트가 읽고 쓸 수 있고, 같은 DB 로 반복 실행하면 결과가 달라질 수 있음.
- 재현: clone 에서 `unset NAMIFAX_DB_PATH; pytest` 후 `git status --short` -> `?? faxes/`, namifax.db 생성.
- 확인 수준: 재현

## F5-10 [낮음] 기본 pytest 가 golden_master 를 실행하지 않고, xfail 분기는 죽은 코드, 수치 문서 불일치, CI 부재
- 위치: pyproject.toml(testpaths = ["tests"]), golden_master/test_*.py, ARCHITECTURE.md 머리말, .github 없음
- 증상: `pytest` 는 tests 만 수집(362). golden_master 88건은 별도로 지정해야 돎. 골든 테스트의 `xfail(... implementation pending)` 분기는 implemented=false 인 시나리오가 0개라 동작하지 않음(미구현 시 조용히 xfail 로 바뀌는 구조 자체가 결함 은닉 경로). ARCHITECTURE.md 는 "296/296 PASS", "Web 68/68", "Mock/Stub 전수 제거" 라고 쓰지만 실제는 362/88 이고 Mock 317건 사용. CI, 린트(ruff/mypy) 설정 없음(캐시 디렉터리만 존재).
- 확인 수준: 재현

## F5-11 [중간] 세션이 프로세스 메모리에만 있고 정리되지 않으며 쿠키 속성이 부족함
- 위치: src/namifax/web/session.py, src/namifax/security.py `remember`
- 증상: "Thread-safe ... TTL eviction" 이라는 docstring 과 달리 락이 없고, 만료 세션은 해당 토큰이 다시 조회될 때만 삭제되므로 안 쓰는 세션이 영구히 메모리에 남음. 재시작하면 전원 로그아웃되고 다중 프로세스/워커 배포 불가. 쿠키는 `HttpOnly; SameSite=Lax` 뿐, `Secure` 와 Max-Age 없음(프록시 뒤 HTTPS 에서 평문 전송 가능). 세션 서명 키/시크릿 설정(session.secret 등) 개념이 없어 운영자가 지정할 방법도 경고도 없음(토큰은 secrets.token_hex 라 위조는 불가).
- 확인 수준: 추론(코드 근거)

## F5-12 [중간] DATABASE_URL, AFDB_URL, sqlalchemy.* 설정과 SQLAlchemy 계층 전체가 아무 효과 없음 (설정 주입 수단이 문서와 실제 모두 없음)
- 위치: src/namifax/models/__init__.py, models/meta.py, pyproject.toml(sqlalchemy, pydantic)
- 증상: `request.dbsession` 사용처 0건. 모델/세션 팩토리는 기본 `sqlite:///:memory:` 엔진만 만들고 실제 데이터는 raw sqlite3 DatabaseEngine 에 저장됨. 따라서 DATABASE_URL 을 줘도 ini 에 sqlalchemy.url 을 줘도 동작이 바뀌지 않음. 실제로 동작하는 설정은 NAMIFAX_DB_PATH 등 몇 개의 환경변수뿐이며 어디에도 문서화돼 있지 않음(README 0바이트, ARCHITECTURE 는 Alembic/MySQL 이라고 서술). pydantic 은 선언만 되고 임포트 0건.
- 확인 수준: 재현(grep)

## F5-13 [중간] requirements.txt 가 pyproject/uv.lock 과 크게 다르고 잘못된 소스를 가리킴
- 위치: requirements.txt
- 증상: `-e git+https://github.com/YetOpen/avantfax.git@c7c5088...#egg=namifax`(업스트림 외부 저장소)를 설치하도록 되어 있어 `pip install -r requirements.txt` 는 이 저장소 코드가 아니라 외부 코드를 받음. boto3, pillow, pyotp, webauthn, babel, defusedxml, pytesseract, cryptography 등 uv.lock 에 있는 런타임 의존성 26개가 빠져 있고, pytest/webtest/beautifulsoup4 같은 개발 패키지가 섞여 있음. 반대로 golden_master 가 임포트하는 bs4 는 pyproject 의 dev 그룹에 없어 `uv sync` 후 `pytest golden_master` 는 bs4 가 없으면 실패함(requirements.txt 에만 있음). (COR-31 의 구체 사례)
- 재현: uv.lock 과 requirements 버전 비교 스크립트, golden_master import 집계.
- 확인 수준: 재현

## F5-14 [중간] createuser CLI 기본값이 위험함 (기본 관리자 + 공개된 기본 비밀번호 + 중복 이메일)
- 위치: src/namifax/cli/user.py 20-25행
- 증상: `--admin` 이 `default=True` 이므로 `-u bob` 만 주면 관리자 + superuser 로 생성됨(일반 사용자는 --user-only 필요). 비밀번호 기본값이 "admin1234!" 로 `--help` 에 그대로 노출되고 wasreset=0/pwdexpire=None 이라 변경을 강제하지 않음. `-p` 는 argv 로 받아 ps 에 노출됨. 이메일 기본값이 고정(admin@namifax.local)이어서 `-e` 없이 두 번째 사용자를 만들면 "Email already in use" 로 실패하는데 종료 코드가 1 이 아니라(첫 경우 0) 스크립트에서 성공으로 오인됨. 시드된 `operator`/`password` 계정도 함께 존재(admin 은 K10).
- 재현: `namifax-createuser -u opsu` -> "Failed to create user: Email already in use", rc 0. `-u opsu -e o@x.test` 생성 결과 is_admin=1, superuser=1. `-u opsu3` 재실행 시 rc=1 로 일관성 없음.
- 확인 수준: 재현

## F5-15 [중간] 스키마 버전 관리/업그레이드 경로와 레거시 DB 이관 수단이 없음
- 위치: src/namifax/db/schema.py `init_database_tables`, `_apply_schema_migrations`
- 증상: ARCHITECTURE.md 는 Alembic 을 명시하나 저장소에 없음. 스키마는 `CREATE TABLE IF NOT EXISTS` 에 임시 `ALTER ... except: pass` 와 뷰 별칭(DIDRouting->DIDRoute)을 덧댄 형태이고 user_version/스키마 버전 테이블이 없어, 배포 후 컬럼이 바뀌면 기존 DB 에 반영되지 않거나 조용히 실패함. 레거시 AvantFAX 의 MySQL 스키마(legacy/create_tables.sql, db-update-*.sql)에서 이 SQLite 스키마로 옮기는 스크립트/문서가 없고, 이관용 import_* CLI 는 wheel 에 없음(COR-25).
- 확인 수준: 추론(코드 근거)

## F5-16 [중간] 외부 바이너리 의존이 문서화되지 않았고 기동 시 사전 점검이 없어 부재 시 조용히 성공한 척 동작
- 위치: helpers.py(tiff2pdf, faxinfo), archive_in.py(convert), modem.py(faxstat), views/sendfax.py(sendfax), ocr.py(pytesseract->tesseract), CUPS(lp/lpr) 호출부
- 증상: tesseract, ghostscript, tiff2pdf(libtiff-tools), ImageMagick convert, HylaFAX 클라이언트(sendfax, faxstat, faxinfo, faxrm, faxalter), CUPS 가 필요하다는 설치 문서가 없음(README 0바이트). 시작 시 shutil.which 점검이나 /health 항목이 없고, 부재 시 동작은 호출부마다 달라서(가짜 성공 F5-04, 빈 결과, 예외 삼키기) 운영자가 원인을 찾기 어려움. 이 검증 환경에는 tesseract, gs 만 있고 tiff2pdf, sendfax, faxstat 이 없음.
- 확인 수준: 추론(코드 근거)

## F5-17 [중간] 로깅이 사실상 없고 130곳의 광범위 except 가 오류를 은폐하며 크래시 흔적도 남지 않음
- 위치: src/namifax 전역(logging 사용은 services/scheduler.py 하나뿐), main.py, ini 의 [logger_namifax]
- 증상: `except Exception` 130곳 중 약 100곳이 pass/무로그. ini 의 `namifax` 로거(DEBUG)는 아무도 로깅하지 않아 무의미. `serve` 는 print 로 안내하며 stdout 이 파이프/journald 일 때 즉시 출력되지 않음(flush 없음). 세그폴트 시 faulthandler 미활성이라 프로세스가 사라져도 로그에 아무 흔적이 없음(pserve 로그에 기동 문구 이후 공백, 테스트에서 재현).
- 재현: 동시 요청 400건을 보낸 뒤 prod.log 에는 기동 줄 외에 아무것도 남지 않고 프로세스 종료.
- 확인 수준: 재현

## F5-18 [중간] DatabaseEngine 전역 결과 상태로 인한 요청 간 데이터 혼선 (COR-01 세그폴트와 별개의 동시성 문제)
- 위치: src/namifax/db/engine.py (`_records`, `_current_iter`, `_error`, `_last_insert_id`, `_affected_rows` 가 싱글턴 인스턴스의 필드)
- 증상: `query()` 후 `get_records()` 로 읽는 두 단계 API 가 전역 싱글턴 위에 있어서, 스레드가 쓰레드 안전한 연결로 고쳐지더라도 요청 A 의 결과를 요청 B 가 읽거나 덮어써 다른 사용자의 행이 섞임. 오류 상태(`_error`)도 공유됨.
- 재현: 2스레드 경합 스크립트는 세그폴트(rc 139)로 종료되어 결과 불일치를 직접 관측하지 못함. 코드상 결함.
- 확인 수준: 추론

## F5-19 [낮음] 스케줄러 운영 결함
- 위치: src/namifax/services/scheduler.py, cli/phb.py
- 증상: (a) phonebook 동기화는 기동 후 60분이 지나야 처음 실행. (b) 기본 출력 경로 /var/spool/hylafax/etc/phonebook 이 없거나 쓸 수 없으면 매시간 트레이스백이 로그에 쌓임(job 직접 실행으로 FileNotFoundError 확인). (c) 전화부 파일을 `open(path, "w")` 로 직접 덮어써 faxq 가 읽는 도중 잘린 파일을 볼 수 있음(임시 파일 + rename 아님). (d) `serve` 내장 스케줄러에서는 logging.basicConfig 를 호출하지 않아 INFO 로그 전부 소실. (e) APScheduler 기본값(coalesce/misfire_grace_time 미지정)이라 서버 재시작/중단으로 자정 잡이 지나가면 그날 정리가 건너뜀. 잡 등록 자체(cron 00:00, interval 60분)는 정상 등록됨을 확인.
- 확인 수준: 재현((a),(b),(d)), 추론((c),(e))

## F5-20 [낮음] systemd 유닛 구성 문제
- 위치: systemd/namifax.service, systemd/namifax-scheduler.service
- 증상: DB 가 SQLite 전용인데 `After=mariadb.service mysql.service` 만 있고 설정/DB 위치 지정이 없음. NAMIFAX_DB_PATH 미지정이라 DB 는 WorkingDirectory(/opt/namifax)/namifax.db 가 되어 uucp 사용자가 /opt/namifax 에 쓰기 권한이 있어야 하는데 이를 보장하는 StateDirectory/ReadWritePaths 없음. PYTHONPATH=/opt/namifax/src 로 설치된 wheel 대신 소스 트리(avantfax 포함 이중 트리)를 그대로 임포트. EnvironmentFile 없이 환경변수를 유닛에 직접 박아 설정 주입 수단이 불명확. HylaFAX 훅(faxrcvd/notify/dynconf)을 HylaFAX 설정에 연결하는 절차 문서/유닛이 없어 훅의 cwd/사용자에 따라 DB 가 갈라짐(COR-13 의 배포 측면). 웹 유닛이 스케줄러를 내장(ENABLE_SCHEDULER=1)하는데 전용 스케줄러 유닛이 따로 있어 동시 설치 시 중복(COR-23 과 동일 계열).
- 확인 수준: 추론

## F5-21 [낮음] 라이선스 표기 누락 (GPLv2 파생물)
- 위치: legacy/COPYING.txt(GPL v2, README 에 GPLv2 명시, @copyright MENTALBARCODE/iFAX Solutions), 저장소 루트, pyproject.toml, package.json
- 증상: 원본 AvantFAX 는 GPL v2 이고 이 프로젝트는 그 이식/파생물(템플릿, 문자열, 아이콘 포함)인데 루트에 LICENSE/COPYING 이 없고 pyproject 에 license 필드 없음, package.json 은 "ISC", src 파일에 저작권/라이선스 헤더 없음, wheel 에도 라이선스가 포함되지 않음. 배포하면 GPL 고지/소스 제공 의무 위반이 될 수 있음.
- 확인 수준: 재현

## F5-22 [낮음] 저장소 위생과 문서 불일치, 죽은 코드
- 위치: 저장소 루트, ARCHITECTURE.md, .gitignore, package.json, src/namifax/web, src/namifax/cli/populate_*.py
- 증상: (a) pyproject 의 `readme = "README.md"` 가 0바이트라 패키지 메타데이터가 비어 있음. (b) .gitignore 에 faxes/, dist/, build/ 누락(테스트와 빌드가 만드는 산출물), 존재하지 않는 `avantfax/includes/local_config.php` 항목이 남아 있음. (c) ARCHITECTURE.md 는 실행 명령을 `avantfax serve/dynconf/...`, 스케줄을 "OS Cron", DB 를 "MySQL Database" 로 설명하고 `src/avantfax` 경로 참조가 44곳인데 실제 명령은 namifax, 스케줄러는 APScheduler, DB 는 SQLite. (d) package.json 이름이 avantfax, repository/bugs/homepage 가 업스트림 YetOpen/avantfax, `npm test` 는 "no test specified" 로 실패. (e) `namifax.web.app` 스텁 앱(146줄)과 session.py 는 F5-02 의 대체 경로로만 쓰이는 사실상 죽은 코드이고 별도 인증/세션 체계를 갖고 있어 혼동과 보안 표면만 늘림. (f) 번역 카탈로그 채움용 일회성 스크립트(populate_ko.py 등, 소스에 subprocess 호출)가 wheel 에 배포됨. (g) 작업용 지침(AGENTS.md, prompts/*, NEW_FEATURES_PLAN.md)이 제품 저장소에 커밋됨.
- 확인 수준: 재현

## F5-23 [낮음] server/scheduler 엔트리포인트가 --help 를 해석하지 않고 그대로 구동됨 (COR-23 의 "인자 무시" 와 별개의 사용성 결함)
- 위치: src/namifax/main.py `serve_main`(argv None 이면 `argv or []`), `scheduler_main`
- 증상: `namifax-server --help`, `namifax-scheduler --help` 가 도움말 없이 서버/데몬을 기동하고 종료하지 않음(timeout 으로만 종료). 포트 인자는 COR-23 대로 무시. `namifax-dynconf --help` 는 출력 없이 종료 코드 0.
- 확인 수준: 재현
