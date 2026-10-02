---
title: 알려진 미구현·한계와 이미 내린 결정
type: topic
updated: 2026-10-02
sources: [src/namifax/main.py, src/namifax/__init__.py, src/namifax/views/auth.py, src/namifax/views/ajax.py, src/namifax/views/inbox.py, src/namifax/views/admin_users.py, src/namifax/views/sendfax.py, src/namifax/views/modals.py, src/namifax/services/faxqueue.py, src/namifax/services/syslog.py, src/namifax/services/mailer.py, src/namifax/services/user_account.py, src/namifax/services/hylafax_info.py, src/namifax/services/sysfunc.py, src/namifax/services/cloud_storage.py, src/namifax/services/scheduler.py, src/namifax/db/bootstrap.py, src/namifax/db/seed.py, src/namifax/db/provider.py, src/namifax/cli/faxrcvd.py, src/namifax/origin_guard.py, src/namifax/routes.py, src/namifax/templates/inbox.jinja2, pyproject.toml, tests/, tools/migration_rehearsal/, "[[porting-gaps]]", "[[defects-report-summary]]", "[[defects-rounds-4-5]]", "[[legacy-divergence-audit]]", "[[new-features-plan]]", "[[future-gcs-storage]]", "[[agents-md-legacy-instructions]]"]
verified: true
---

과거 조사 문서([[porting-gaps]], [[defects-report-summary]], [[legacy-divergence-audit]], [[new-features-plan]])가 보고한 항목 중 중요한 것을 **지금 코드로 다시 열어** 분류한 표와, 의도적으로 제거·보류한 것의 결정 이유. 나머지 라운드 문서는 [[defects-rounds-1-2]], [[defects-rounds-3]], [[defects-rounds-4-5]].
관련: [[overview]] [[architecture-and-modules]] [[authentication-and-security]] [[operations-and-deployment]] [[migration-from-avantfax]] [[scheduler-and-storage]] [[testing]].

판정 기준: **해결됨** = 지금 코드에서 보고된 문제가 없음을 직접 확인. **남음** = 지금 코드에 문제나 한계가 있음. **확인 못함** = 이 세션에서 코드로 판정하지 못함(시험 파일이 있다는 사실만으로 "해결됨"으로 올리지 않음). 시험은 실행하지 않았다.
과거 결함 보고서는 당시 시점(HEAD `e3e50c8`, 2026-10-01 무렵)의 것이며 이후 대부분 고쳐졌다는 것이 문서들의 공통 주장이다 [문서]. 아래는 그 주장을 항목별로 재확인한 결과다. 표의 항목 번호와 설명은 요약 페이지에서 옮겼고 원문은 `git show 01f2f64:docs/...` 에 있다.

## 1. 치명·높음 등급 항목 재확인

### 1.1 보안·권한(치명 위주)
| 항목 | 당시 보고 | 현재 상태 | 근거 경로 |
|---|---|---|---|
| AUDIT-01 관리자 `admin`/`password` 인증 우회 | 치명: DB 확인 없이 로그인 | **해결됨**: 로그인 코드는 `user.login`/`login_alternate_auth` 로 DB 계정을 확인하고, 하드코딩 비밀번호 비교를 찾지 못함(`password` 문자열 grep 결과 관련 없는 폼 필드뿐) | `src/namifax/views/auth.py`, `src/namifax/services/user_account.py` |
| AUDIT-02 / USR-06 `faxalter`·`killjob` 셸 명령 주입 | 치명: `shell=True` + 문자열 결합 | **해결됨**(주 경로): `killjob`/`faxalter` 는 인자 목록으로 `subprocess.run`(셸 없음), 사용자 이름은 환경 변수 `FAXUSER` 로 전달. 숫자 검증도 있음(`/ajax/faxalter` 의 `jid`, `killtime`, `numtries`). **남음(경미)**: `FaxQueue.shell_exec` 는 `shell=True` 로 `faxstat -s`/`-d` 같은 생성자 인자 문자열을 실행한다. 사용자 입력이 들어가는 호출은 찾지 못했다(코드의 `shell_exec` 호출 2곳 모두 고정 명령) | `src/namifax/services/faxqueue.py`, `src/namifax/views/ajax.py` |
| AUDIT-03 / SEC-01 시스템 로그·주소록 검색 SQL 인젝션 | 치명/높음: f-string 으로 SQL 결합 | **해결됨**: 로그 검색은 SQLAlchemy 식(`contains(..., autoescape=True)`). `src` 전체에서 사용자 값이 들어간 `f"SELECT ..."` 를 찾지 못함(`db/sqlite_upgrade.py` 의 f-string 은 내부 상수 테이블 이름) | `src/namifax/services/syslog.py`, `src/namifax/db/sqlite_upgrade.py` |
| ADM-01 / COR-02 앱 시작마다 seed·migration 이 운영 데이터 덮어씀 | 치명 | **해결됨**: `ensure_schema` 는 Alembic `upgrade head` 만 하고, 기본 레코드는 DB 가 "새것"일 때만, 데모 데이터는 `NAMIFAX_DEMO_DATA` 옵트인 + 새 SQLite 에서만 | `src/namifax/db/bootstrap.py`, `src/namifax/db/seed.py` |
| USR-04 / R5U-01 사용자별 모뎀·카테고리 제한 비동작, 권한 필터 fail-open | 치명/높음 | **해결됨(구조만 확인)**: 권한 규칙이 `FaxAccess`(모뎀·DID·카테고리·`can_del`)로 모여 있고 요청마다 DB 에서 읽는다. 사용자가 모뎀·카테고리가 없을 때의 경계 동작은 코드로 따라가지 않았다 → 그 부분은 **확인 못함** | `src/namifax/services/fax_access.py`, `tests/unit/test_fax_access_control.py`(실행 안 함) |
| R4U-01 관리자(uid=1) 삭제 보호 우회 | 치명 | **해결됨(규칙 교체)**: uid=1 고정 보호가 아니라 "자기 자신과 마지막 슈퍼유저는 삭제 불가"로 바뀜 | `src/namifax/views/admin_users.py` |
| B1 `/ajax/deletefaxes` 반사형 XSS | 높음 | **확인 못함**: 뷰는 `batch_delete.jinja2` 로 렌더링하고 그 템플릿에서 `\|safe` 를 찾지 못했으나, 이스케이프 설정과 `fids` 처리를 끝까지 추적하지 않음 | `src/namifax/views/ajax.py`, `src/namifax/templates/batch_delete.jinja2` |
| B2 관리자가 만든 사용자의 빈 비밀번호 → 평문 `password` | 높음 | **해결됨**: 비밀번호가 비면 `genpasswd()` 로 임의 비밀번호를 만들어 해시 저장하고 `wasreset=1`, 메일로 알림(저장은 해시뿐). CLI `createuser` 는 기본 비밀번호 없음 | `src/namifax/services/user_account.py`, `src/namifax/cli/user.py` |
| B3 변경 요청에 CSRF 방어 없음 | 높음 | **해결됨(일부는 확인 못함)**: `Origin`/`Referer` 검사 tween 이 모든 POST/PUT/PATCH/DELETE 에 적용(SAML 콜백 제외). 일부 뷰는 `check_csrf_token` 도 씀. **모든 폼**이 토큰을 쓰는지는 세지 않음 | `src/namifax/origin_guard.py`, `src/namifax/views/auth.py`, `modals.py`, `inbox.py` |
| B4 `/ajax/modemstatus` 권한 검사 없음 | 높음 | **해결됨**: 사용자 계정의 모뎀만 알려 주고 슈퍼유저는 설정된 모뎀 전체 | `src/namifax/views/ajax.py` |
| B5 로그인 성공·실패 감사 로그 없음 | 높음 | **해결됨**: 성공·실패·비활성 계정 시도를 시스템 로그에 기록(실패 시 비밀번호는 뒤 3자만 남김) | `src/namifax/services/user_account.py` |
| R4Z-02 `Content-Disposition` 에 `fid`/`format` 검증 없이 삽입 | 중간 | **남음(확인 못함 포함)**: `ENABLE_DL_TIFF` 가 켜져 있으면 `format` 이 `pdf` 가 아닌 임의 값도 헤더에 들어간다. 개행 차단은 프레임워크(WebOb) 동작에 기대며 시험하지 않음 | `src/namifax/views/inbox.py`(다운로드 뷰) |

### 1.2 가짜 성공·가짜 데이터(치명·높음 위주)
| 항목 | 당시 보고 | 현재 상태 | 근거 경로 |
|---|---|---|---|
| COR-04 `send_mail` 이 실제 발송 없이 성공 반환 | 치명 | **해결됨**: 기본 SMTP 호스트는 `localhost`, DB 를 읽지 못하면 로컬 MTA 로 보냄. 실패하면 `False` 와 `last_error`. (스풀 모드는 호스트가 비어 있고 테스트용으로만 쓰임) | `src/namifax/services/mailer.py`, `src/namifax/common/helpers.py`, `src/namifax/services/smtp_settings.py` |
| COR-03 `notify` CLI 가 모든 사용자에서 `AttributeError` | 치명 | **확인 못함**: 관련 시험(`test_cli_notify*.py`, `test_notify_registers_receiver.py`)이 있으나 실행하지 않았고 코드 경로를 끝까지 따라가지 않음 | `src/namifax/cli/notify.py` |
| COR-01 SQLite 단일 연결을 스레드가 공유 → 세그폴트 | 치명 | **확인 못함**: 전역 엔진 없이 요청별 세션으로 바뀌었고(`provider.py` 주석, 엔진은 `check_same_thread=False`) 구조는 바뀌었으나 동시성 재현은 하지 않음 | `src/namifax/db/provider.py` |
| AUDIT-04/05 합성 PDF·0바이트 가짜 변환 | 높음 | **해결됨**: `%PDF` 헤더를 직접 쓰는 코드는 데모 데이터 생성(`seed.py`)뿐. 업로드 검사는 앞부분 내용으로 형식을 판정(`upload_check.py`) | `src/namifax/db/seed.py`, `src/namifax/services/upload_check.py` |
| AUDIT-06 "Acme Corp" 자동완성 강제 주입 | 높음 | **해결됨**: "Acme" 는 데모 시드와 입력란 예시 문구에만 남음 | `src/namifax/db/seed.py`, `src/namifax/templates/sendfax.jinja2` |
| AUDIT-07 팩스 전송 시뮬레이션(가짜 job_id 로 성공 위장) | 높음 | **남음(조건부)**: HylaFAX 가 없는 장비(`sendfax` 없음, `NAMIFAX_QUEUE_SIMULATION` 켜짐 또는 `/var/spool/hylafax` 없음)에서는 **가짜 작업 번호로 성공을 돌려준다**. 개발 편의 동작이며, 운영에서는 `sendfax` 가 `PATH` 에 있는지 점검해야 함([[operations-and-deployment]] 4절) | `src/namifax/views/sendfax.py` |
| AUDIT-09 수신함 하드코딩(ttyS0·Acme·고정 날짜) | 중간 | **남음(경미)**: `inbox.jinja2` 첫머리에 화면에는 안 보이는 `sr-only` 문구 `Inbox 0 FAXES MODEM IDLE ttyS0` 가 하드코딩되어 있음(과거 Golden Master 계약용 주석이 달림). 실제 값은 아님 | `src/namifax/templates/inbox.jinja2` |
| AUDIT-10 / A10 사용자 설정이 스텁이라 저장 안 됨 | 높음 | **확인 못함**: 설정 뷰·템플릿이 있고 비밀번호 변경·강제 변경 시험 파일이 있으나 저장 경로를 끝까지 추적하지 않음 | `src/namifax/views/settings.py` |
| AUDIT-11 / C7 시스템 기능(백업·재부팅)이 메시지만 반환 | 높음 | **해결됨(코드 존재)**: 재부팅·종료 명령(`NAMIFAX_REBOOT_CMD` 등)과 보관 폴더 tar.gz·DB 덤프를 만드는 함수가 있음. 단 systemd `NoNewPrivileges=true` 와 `sudo` 의 충돌 가능성은 [[operations-and-deployment]] 3.1 에 적음 | `src/namifax/services/sysfunc.py` |
| AUDIT-12 / C4 HylaFAX 버전 `6.0.7` 하드코딩 | 중간 | **해결됨**: `faxstat -i` 에서 읽고 못 읽으면 `None`("지어내지 않음") | `src/namifax/services/hylafax_info.py` |
| AUDIT-16 `faxrcvd` 의 미정의 변수 `faxname` | 중간 | **해결됨**: `faxname` 이 `os.path.basename(faxfile)` 로 정의된 뒤 OCR 인덱싱에 쓰임 | `src/namifax/cli/faxrcvd.py` |
| AUDIT-17 / C 큐 작업 삭제 실패 은폐 | 중간 | **해결됨**: `killjob` 은 `returncode == 0` 일 때만 `True` | `src/namifax/services/faxqueue.py` |
| AUDIT-13 / E1 CUPS 인쇄·수신 자동 인쇄 스텁 | 중간 | **확인 못함**: `services/printing.py`, `printer.py`, `PRINTFAXRCVD` 읽기 코드가 있으나 실제 프린터로는 시험하지 못함 | `src/namifax/services/printer.py`, `printing.py`, `cli/faxrcvd.py` |

### 1.3 기능 부족([[porting-gaps]] A~G)
| 항목 | 당시 보고 | 현재 상태 | 근거 경로 |
|---|---|---|---|
| A1 / A9 메일 보내기 첨부·CC/BCC 미동작 | 화면에 있으나 고장 | **해결됨**: 모달이 `cc_emails`/`bcc_emails`, 파일명, 썸네일 첨부를 `send_mail` 에 넘기고 메일러가 CC/BCC·첨부를 지원 | `src/namifax/views/modals.py`, `src/namifax/services/mailer.py` |
| A2 받은 팩스함 25건 고정·쪽 나누기 없음 | 고장 | **해결됨**: `pageindex` 처리가 있음 | `src/namifax/views/inbox.py` |
| A5 검색 기능·OpenSearch 미구현 | 고장 | **해결됨(경로 존재)**: `/search`(`opensearch` 라우트)와 보관함 검색 뷰가 있음. 원본과의 완전한 동일성은 문서 주장(원본 실행 대조)이며 직접 재현하지 않음 | `src/namifax/routes.py`, `src/namifax/views/archive.py` |
| A3 / A4 / A6~A8, A11 받은 팩스함 버튼·팩스 보기·주소록 편집 등 | 고장 | **확인 못함**: 개별 화면을 열어 동작을 보지는 않았다 | `src/namifax/views/` |
| C8 시스템 로그가 100행에서 잘림 | 중간 | **남음**: `MAX_ROWS = 100`. 원본도 같은 한도인지는 확인 못함 | `src/namifax/services/syslog.py` |
| E7 설정 변수 약 70개 미구현 | 중간 | **남음/확인 못함**: 많은 변수가 환경 변수로 구현됐으나([[operations-and-deployment]] 2.2) 원본 147개 전체와 일일이 대조하지 않았다. 문서는 일부를 "필요 없음(Ghostscript·Pillow 로 대체)"으로 분류 | `src/namifax/common/settings.py` |
| E11 2.x 이전 DB `update_contacts` 미지원 | 낮음 | **남음(결정)**: 해당 명령이 없고 2.x 는 지원 대상이 아님 | `src/namifax/main.py`(명령 목록), [[migrating-from-avantfax3]] |
| F 이메일→팩스 게이트웨이 미구현 | 설치·운영 | **해결됨(설명서만)**: 코드가 아니라 Postfix `faxmail` 파이프 설정 설명서(`deploy/postfix/setup-email2fax.md`)다. 실제 메일로 시험하지 않음 | `deploy/postfix/setup-email2fax.md`, [[setup-email2fax]] |
| F HylaFAX 사용자 동기화(`faxadduser`/`faxdeluser`) 없음 | 설치·운영 | **해결됨(코드, 시험 못함)**: `HYLAFAX_USER_SYNC=1` 일 때만 동작하는 서비스가 있고 sudoers 항목이 있음. 실제 HylaFAX 로 시험하지 못함 | `src/namifax/services/hylafax_users.py`, `deploy/sudoers.d/namifax` |

### 1.4 배포·검증 체계([[defects-report-summary]] C8·C9)
| 항목 | 당시 보고 | 현재 상태 | 근거 경로 |
|---|---|---|---|
| 기동 시 다른(폴백) 웹 앱으로 대체 | 높음: 배포 시 `avantfax` 미포함, 폴백 앱 | **해결됨**: `serve_main` 은 앱 생성 실패를 stderr 에 내고 종료 코드 1(대체 앱 없음). `avantfax` 복사본과 JSON 폴백 웹 앱이 없음을 확인하는 시험이 있음 | `src/namifax/main.py`, `tests/unit/test_legacy_trees_removed.py` |
| 기동 경로가 개발 서버 | 중간 | **남음**: `namifax serve` 는 `wsgiref` 스레드 서버. 운영 전용 서버는 `pserve` + `waitress` 경로가 따로 있음([[operations-and-deployment]] 1절) | `src/namifax/main.py`, `production.ini` |
| `namifax-server` 가 포트를 열지 않음 | 미분석 | **확인 못함**: `namifax-server` 는 `namifax.main:serve_main` 진입점이고 코드상 포트에 바인딩한다. 당시 현상의 원인은 모르고 서버를 실행해 보지 않았다 | `pyproject.toml`, `src/namifax/main.py` |
| wheel 에 코드 미포함 | 높음 | **확인 못함**: 빌드 백엔드는 `uv_build`. 설치해서 확인하지 않음 | `pyproject.toml` |
| 시험이 mock 위주·골든 마스터 자기 참조 | 중간 | **해결됨(방식 교체)**: 골든 마스터 스위트는 삭제됨(2절). 자기 참조의 해소 여부는 [[testing]] 참고 | `tests/` |
| 번역 문자열 부재 | 높음 | **남음**: 한국어만 새 문구까지 채워짐. 나머지 언어는 영어로 보이는 새 문구가 많음(수치는 문서 주장, 이번에 다시 세지 않음) | `src/namifax/locale/`, [[i18n-and-ui]] |

## 2. 의도적으로 제거·보류한 것과 이유

| 항목 | 결정 | 이유(근거) | 다시 하려면 |
|---|---|---|---|
| GCS(Google Cloud Storage) 지원 | 보류: Admin > Storage 화면과 코드에서 제거(2026-10-02) | [문서] [[future-gcs-storage]]: GCS 전용 코드가 없고 S3 호환(boto3)으로만 연결했으며 **실제 GCS 계정으로 한 번도 시험하지 않았다**. 시험하지 못한 기능을 화면에 두지 않기로 함. 코드에서 `S3CompatibleStorageProvider` 는 엔드포인트가 비면 boto3 기본(AWS)으로 간다(`cloud_storage.py` 에서 `endpoint_url` 이 있을 때만 전달) | S3 호환 방식(엔드포인트 기본값 + 실제 시험) 또는 `google-cloud-storage` 전용 공급자. 제거 직전 상태는 커밋 `53ed28b` 와 [[future-gcs-storage]] |
| 골든 마스터(E2E 시험 자료)·`dev/`(specs, prompts) | 삭제(`01f2f64`) | [코드] 커밋 메시지: "골든 마스터, specs, prompts 를 지우고 지식 노트는 별도 llm-wiki 로 옮긴다". 원본 PHP 가 사라져 새로 뽑을 수 없는 자료이고, 결함 보고서도 "골든 마스터가 자기 참조"를 지적했다 [문서: [[defects-report-summary]]]. 이 이유 추론은 [추정]. 남은 시험은 `tests/` 의 단위·웹 시험이며 `tests/unit/data/fax_archive_search_golden.json` 같은 개별 비교 자료만 있다 | `git show 72a7324`/`01f2f64` 에서 복원 |
| `legacy/` 원본 PHP 트리 | 삭제(`083920e`) | [코드] 커밋 메시지: 이식이 끝났기 때문. 원본 설치 SQL 은 시험 자료로 `tests/fixtures/legacy_sql/` 에 보존 | `git checkout 9408385 -- legacy`. 이전 연습 도구 `tools/migration_rehearsal/` 는 남아 있으나 `legacy/` 없이는 실행 불가([[migration-from-avantfax]] 0.1) |
| `AGENTS.md`·`SYSTEM_PROMPT.md`·`ARCHITECTURE.md`·감사/결함 보고서 | 삭제(`4368da8`), 요약은 wiki 의 [[agents-md-legacy-instructions]], [[architecture-md-part1]], [[architecture-md-part2]] 등에 남김 | [코드] 커밋 메시지(복원 경로 `01f2f64`) | `git show 01f2f64:ARCHITECTURE.md` 등 |
| 한국어 외 번역 | 보류 | [문서] [[porting-gaps]] 제외 사항: 한국어 외 번역 보류. 한국어는 시험으로 빠진 문구 0개를 보장한다고 문서가 말함 | [[i18n-and-ui]] |
| 대화상자 | 별도 창이 아니라 페이지로 구현 | [문서] [[porting-gaps]]: 의도한 차이 | |
| 레거시 CSS·테마 | Tailwind 로 대체, 원본 테마·`custom.css` 미지원 | [문서] [[migrating-from-avantfax3]] 4.4 | |
| SAML 로그인이 앱의 2FA 를 거치지 않음 | 확정된 정책: IdP 가 책임 | [문서] [[operations-checklist]] | |
| 비밀번호 찾기의 계정 존재 노출·무효화 가능성 | 원본 동작을 따름(앞단 속도 제한 권장) | [문서] [[operations-checklist]] | |
| 대기열 작업 수정(`/ajax/faxalter`) 권한 | 원본처럼 로그인만 확인 | [문서] [[operations-checklist]] | |

## 3. 신규 기능([[new-features-plan]])의 구현 상태
[문서]는 Phase A·B·C 가 모두 "완료"라고 말한다. 코드와 시험 파일의 존재를 확인했다. 아래 "시험 못함"은 **실제 외부 시스템과** 시험하지 못했다는 뜻이다.

| 기능 | 코드 존재 | 실제 환경 시험 |
|---|---|---|
| TOTP 2단계 인증, 복구 코드, 잠금 | [코드] `services/totp.py`, `tests/unit/test_totp*.py` | 인증 앱과의 실사용은 확인 못함 |
| WebAuthn 패스키 | [코드] `services/webauthn.py`, `tests/unit/test_webauthn*.py`, `test_pyramid_webauthn.py` | 실제 보안 키·기기는 확인 못함 |
| SAML 2.0 SSO | [코드] `services/saml.py`, `views/saml.py`, `tests/unit/test_saml*.py`, `test_pyramid_saml.py` | [문서] Keycloak 26 컨테이너로 확인함. **실제 IdP(Okta, Entra ID 등)는 시험하지 못함** |
| 네트워크 프린터(IPP/LPD/RAW) | [코드] `services/printer.py`, `tests/unit/test_network_printer*.py` | 실제 프린터는 확인 못함 |
| 표지 스튜디오 | [코드] `services/cover_studio.py`, `tests/unit/test_cover_studio.py` | — |
| 클라우드 스토리지(S3 호환)와 수명주기 | [코드] `services/cloud_storage.py`, `storage_lifecycle.py`, `tests/unit/test_cloud_storage.py`, `test_storage_lifecycle*.py` | 실제 S3·GCS 계정은 확인 못함(GCS 는 제거됨) |
| OCR 검색 | [코드] `services/ocr.py`(`pytesseract`), `tests/unit/test_ocr*.py` | 언어 패키지·한국어 인식률은 환경 의존 |
| SMTP 관리자 화면 | [코드] `services/smtp_settings.py`, `mailer.py` | 실제 외부 SMTP 는 확인 못함 |

## 4. 지금도 시험하지 못한 것(요약)
- **실제 HylaFAX**: `JobFmt` 열 순서, `faxrm`/`faxalter` 소유자 권한, 훅 환경 변수 전달, 서비스 이름. 출력함 시험은 가짜 `faxstat` 출력으로만 했다 [문서].
- **실제 IdP**: Keycloak 외 SAML 공급자.
- **실제 클라우드·프린터·메일**: S3/GCS 계정, 네트워크 프린터, Postfix 이메일→팩스.
- **대용량·오래된 DB**: 수년치 `FaxArchive` 의 첫 기동 시간, 3.0~3.2.x 업그레이드 이력이 있는 DB [문서].
- **이 세션의 한계**: 코드를 읽고 grep 으로만 확인했다. 시험도 서버도 실행하지 않았으므로 "해결됨"은 "지금 코드에서 보고된 증상이 보이지 않는다"는 뜻이지 "시험으로 증명했다"가 아니다.
