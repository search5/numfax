# 5라운드 점검 보고서: tests/, 소형 서비스·CLI, PHP 브리지, 저장소 문서 (담당: files)

작성 시각: 2026-10-01 (KST). 저장소 소스는 수정하지 않았고, 서브에이전트도 쓰지 않았습니다.

## 요약

- 새 결함 15건: 중간 3건 (R5F-01, R5F-02, R5F-03), 낮음 12건 (R5F-04 ~ R5F-15). 높음/치명 없음.
- 가장 중요한 3건: R5F-01 (WebAuthn 이 QueryResult 를 리스트로 취급해 저장된 패스키가 목록/인증에서 항상 안 보임), R5F-02 (`pserve` 기동에서는 스케줄러가 시작되지 않음, 문서는 반대로 서술), R5F-03 (`phb` 가 실제 스키마에서 모든 회사의 팩스번호를 비워 PBOOK 이 번호 없는 항목만 가짐).
- tests/ 69개 파일 7,149줄을 전부 줄 단위로 읽었고, 2절에 결함-테스트 은폐 대응표(약 55행)를 만들었습니다. 새로 드러난 은폐 패턴: 테스트가 `db.query()` 반환을 리스트로 모의 (WebAuthn, OCR), 존재하지 않는 계약을 모의 (`export_phonebook` 이 5 를 반환), 같은 코드를 3개 모듈 이름으로 임포트.
- PHP 브리지는 이미 있는 메서드끼리의 action/키/응답 키 대응은 130행 모두 맞지만, 레거시 공개 메서드를 크게 덜 구현합니다 (AFAddressBookBridge 45개 중 16개, R5F-10).
- 문서: ARCHITECTURE.md 의 상태 표는 46행 중 24행이 `FFI_BRIDGED` 인데 머리말은 100% 완료이고, 테스트 수(296/374/362)가 서로 다르며 존재하지 않는 파일/경로(`components/`, `/search`, `views/upload.py`, `/api/hooks/faxrcvd`, `/admin/maintenance`)를 사실처럼 적었습니다 (R5F-13, R5F-14, R5F-15).

## 0. 실행 환경과 기준선

- 모든 실행은 `scratchpad/agent-r5-files/` 아래에서만 했습니다. 저장소는 `agent-r5-files/repo/` 로 복제했고(`.venv` 포함), DB 는 `NAMIFAX_DB_PATH=agent-r5-files/*.db`, `HOME=agent-r5-files/home` 으로 지정했습니다. 복제본 `git status` 는 끝까지 깨끗했습니다.
- 기준선: `pytest tests` = 362 passed (2.4초). `pytest golden_master` = 88 passed (웹 68 + CLI 20). 즉 ARCHITECTURE.md 의 "68/68, 20/20" 은 사실이지만 "pytest 296/296", "374/374" 는 사실이 아닙니다(R5F-14).
- 공격 페이로드는 실행하지 않았습니다. 프린터 SSRF(R5F-09)는 코드 읽기만 했습니다.
- known5.md 의 452건과 같은 결함은 쓰지 않았습니다. 같은 원인의 다른 증상/다른 경로는 "변형"이라고 밝히고 올렸습니다.

## 1. 읽은 파일과 줄 수

읽은 정도: 전문 = 처음부터 끝까지 읽음 / 부분 = 표시한 범위만 읽음 / 기계 = 스크립트로 대조.

### 1-1. 담당 (1) tests/ (69개 파일, 7,149줄, 테스트 362개): 전부 줄 단위로 읽음

빈 줄은 출력에서 뺐고, 일부 묶음(test_auth_pam, test_barcode, test_categories, test_cli_*, test_cloud_storage 등)은 `import`/`sys.path` 줄을 출력에서 뺐습니다. 그 줄들은 별도 스크립트(모듈 이름별 import 통계, R5F-11)로 확인했습니다.

| 파일 | 줄 | 파일 | 줄 | 파일 | 줄 |
|---|---|---|---|---|---|
| test_helpers_media.py | 88 | test_i18n.py | 127 | unit/test_addressbook.py | 176 |
| unit/test_archive_base.py | 239 | unit/test_archive_in.py | 143 | unit/test_archive_out.py | 106 |
| unit/test_auth_pam.py | 50 | unit/test_auth_password.py | 73 | unit/test_barcode.py | 157 |
| unit/test_categories.py | 113 | unit/test_cli_batch_tools.py | 99 | unit/test_cli_cron.py | 61 |
| unit/test_cli_dynconf.py | 78 | unit/test_cli_faxcover.py | 54 | unit/test_cli_faxrcvd.py | 101 |
| unit/test_cli_notify.py | 104 | unit/test_cli_phb.py | 95 | unit/test_cli_print_in.py | 28 |
| unit/test_cli_tools.py | 62 | unit/test_cloud_storage.py | 150 | unit/test_covers.py | 156 |
| unit/test_cover_studio.py | 91 | unit/test_db_base.py | 72 | unit/test_did.py | 154 |
| unit/test_distro.py | 128 | unit/test_dynconf.py | 113 | unit/test_engine.py | 109 |
| unit/test_faxqueue.py | 88 | unit/test_helpers.py | 112 | unit/test_mailer.py | 96 |
| unit/test_main_namifax.py | 62 | unit/test_main.py | 41 | unit/test_models.py | 155 |
| unit/test_modem.py | 163 | unit/test_network_printer.py | 105 | unit/test_ocr.py | 68 |
| unit/test_pyramid_additional_views.py | 112 | unit/test_pyramid_admin_crud.py | 430 | unit/test_pyramid_admin_smtp.py | 92 |
| unit/test_pyramid_authorization.py | 86 | unit/test_pyramid_modals_action.py | 120 | unit/test_pyramid_saml.py | 65 |
| unit/test_pyramid_totp_auth.py | 75 | unit/test_pyramid_webauthn.py | 86 | unit/test_query.py | 109 |
| unit/test_repository.py | 121 | unit/test_saml.py | 100 | unit/test_scheduler.py | 46 |
| unit/test_security_policy.py | 85 | unit/test_smtp_settings.py | 110 | unit/test_storage_lifecycle.py | 152 |
| unit/test_totp.py | 69 | unit/test_upload.py | 104 | unit/test_user_account.py | 222 |
| unit/test_user_passwords.py | 74 | unit/test_validators.py | 93 | unit/test_vcard_upload.py | 117 |
| unit/test_web_admin.py | 58 | unit/test_web_ajax.py | 100 | unit/test_web_app.py | 61 |
| unit/test_web_archive.py | 64 | unit/test_web_auth.py | 74 | unit/test_web_helpers.py | 76 |
| unit/test_web_inbox.py | 93 | unit/test_web_outbox.py | 60 | unit/test_web_sendfax.py | 74 |
| unit/test_webauthn.py | 77 | web/test_web_addressbook.py | 77 | web/test_web_inbox_views.py | 50 |
| web/__init__.py | 0 | | | **합계 69개 파일** | **7,149** |

추가로 AST 로 확인: 같은 모듈 안에서 이름이 겹쳐 덮어써진 테스트 함수 0건, 클래스 안 중복 메서드 0건.

### 1-2. 담당 (2) 소형 서비스·CLI (src/namifax)

| 파일 | 줄 | 정도 | 새 결함 |
|---|---|---|---|
| services/categories.py | 126 | 전문 + 실행 | 새 결함 없음 (공백 이름 허용은 ADM-25 계열 입력 검증, 실행으로 확인만 함) |
| services/printer.py | 147 | 전문 | R5F-09 |
| services/scheduler.py | 156 | 전문 | R5F-05, R5F-02 와 연결 |
| services/__init__.py | 34 | 전문 | 새 결함 없음 |
| services/archive_out.py | 52 | 전문 | 새 결함 없음 (R3C-05 와 같은 접두어 절단, 이미 보고됨) |
| services/user_passwords.py | 60 | 전문 | 새 결함 없음 |
| services/totp.py | 101 | 전문 + 실행 | R5F-08 |
| services/dynconf.py | 138 | 전문 + 실행 | R5F-04 |
| services/distro.py | 177 | 전문 | 새 결함 없음 (구분자 ":" 는 레거시 DL_SEPARATOR 와 같음, 읽기에서 ";" 도 허용) |
| services/faxqueue.py | 193 | 전문 | 새 결함 없음 (faxalter 의 resubmit 후 killjob 은 레거시 FaxQueue.php 와 동일) |
| services/ocr.py | 160 | 전문 + 실행 | 새 결함 없음 (ADM-15 로 이미 보고됨, 재현만 다시 함) |
| services/webauthn.py | 258 | 부분 (112-140, 201-258) + 실행 | R5F-01 |
| services/cover_studio.py | 122 | 부분 (76-95) | 새 결함 없음 |
| services/smtp_settings.py | 180 | 부분 (36-60) | 새 결함 없음 (HTML 서명 누락은 ADM-18) |
| services/storage_lifecycle.py | 127 | 부분 (74-90) | 새 결함 없음 (ADM-12) |
| cli/__init__.py | 1 | 전문 | 새 결함 없음 |
| cli/dynconf.py | 59 | 전문 | 새 결함 없음 |
| cli/i18n.py | 54 | 전문 | 새 결함 없음 (R3E-07~09) |
| cli/phb.py | 85 | 전문 + 실행 | R5F-03, R5F-05 |
| cli/print_in.py | 53 | 전문 | 새 결함 없음 (ADM-14, R3D-26) |
| cli/user.py | 82 | 전문 | 새 결함 없음 (COR-17, F3-23, R3E-18) |
| cli/cron.py | 121 | 전문 | 새 결함 없음 (R3E-12; 음수 일수는 레거시와 동일하게 동작) |
| common/upload.py | 155 | 부분 (sanitize, load_file, movefile) + 실행 | R5F-06 |
| i18n.py | 110 | 전문 + 실행 | R5F-07 |
| routes.py | 100 | 전문 | 문서 대조용 (4장) |
| __init__.py (create_app) | 58 | 전문 | R5F-02 |
| views/admin.py 프린터 구간 | 965-1036 | 부분 | R5F-09 |
| views/admin.py 동적설정 구간 | 650-700 | 부분 | R5F-04 에서 UI 경로 확인 |
| db/bridge_cli.py | 912 | 부분 (1-330 전문, 나머지는 분기/키 정규식 대조) | R5F-10 |

읽지 못한 것: cli/faxrcvd.py, notify.py, faxcover.py(185), populate_*.py 는 이번 라운드에서 다시 읽지 않았습니다(1~4라운드 보고서가 줄 단위로 다룸). services/covers.py, mailer.py, saml.py, archive_in.py 는 이번에 줄 단위로 읽지 않았고 테스트 쪽 사용과 시그니처 실행 확인만 했습니다.

### 1-3. 담당 (3) PHP 브리지

| 파일 | 줄 | 정도 |
|---|---|---|
| services/CoversBridge.php | 185 | 전문 |
| services/AFAddressBookBridge.php | 183 | 메서드 목록 + 레거시 AFAddressBook.php 공개 메서드 대조 |
| 나머지 *Bridge.php 22개 (3,177줄) | | 기계 (공개 메서드, action/method, 전송 키, 응답 키를 정규식으로 추출해 bridge_cli.py 분기와 대조, 레거시 클래스 공개 메서드와 대조) |
| db/bridge_cli.py | 912 | 위 1-2 표 참조. 16개 action 을 `handle_request()` 로 직접 호출해 반환 형식 확인 |

### 1-4. 담당 (4) 문서

| 파일 | 줄 | 정도 |
|---|---|---|
| README.md | 0 | 0바이트 (F5-22 로 이미 보고됨) |
| AGENTS.md / SYSTEM_PROMPT.md | 95 / (심볼릭 링크) | 전문 (SYSTEM_PROMPT.md 는 AGENTS.md 로의 심볼릭 링크임을 확인) |
| ARCHITECTURE.md | 793 | 1-100, 216-793 전문. 98-215 (DAG 절)은 읽지 못함 |
| NEW_FEATURES_PLAN.md | 305 | 부분: 상태 표기(완료) 줄 전부와 253-294 로드맵 절, 머리말. 4절 본문은 grep 으로 해당 기능 존재 여부만 확인 |
| prompts/01-04 | 28/32/35/19 | 전문 |
| docs/hylafax_avantfax_integration_architecture.md | 528 | 부분: 3.2, 4.1, 7.1-7.2, 8.3 패턴 B |
| specs/ 47개 + specs/web 25개 | 약 2,500 | 01, 02, 03, 06, 07, 12, 14 전문. 나머지는 식별자(백틱 이름) 추출 스크립트로 구현 존재 여부 대조(72개 파일 전부), 의심 항목만 본문 확인 |

## 2. 결함-테스트 은폐 대응표

"은폐 방식" 약어: [스키마] 테스트가 직접 만든 CREATE TABLE 을 써서 실제 schema.py 와 다름 / [목] MagicMock 이 존재하지 않는 메서드나 다른 반환 형태를 받아 줌 / [시드] 테스트가 가짜·시드 데이터를 정답으로 기대 / [경로] 결함이 있는 경로를 아예 호출하지 않음 / [입력] 정상 입력만 사용 / [약] 약한 assert.

| 결함 ID | 결함 | 은폐하는 테스트 (파일:줄) | 은폐 방식 |
|---|---|---|---|
| K01 | 관리자 4화면이 request.db 없이 연결 없는 엔진 사용 | test_pyramid_admin_smtp.py:25,35,58,82 (`req.db = self.db` 를 수동 주입), test_pyramid_totp_auth.py:42,53,66 | [경로] 실제 앱에는 없는 request.db 를 테스트가 만들어 줌 |
| K02 | 세션 팩토리 미등록 | test_pyramid_admin_smtp.py:22-24, test_pyramid_saml.py:40,62, test_pyramid_webauthn.py:14,20,59, test_web_ajax.py:22, test_web_helpers.py:20 | [목] `DummyRequest.session`/직접 대입한 dict 가 항상 존재 |
| K03 | AFUserAccount 에 load_by_username, get_name, create_user, load_user, verify_password 없음 | test_pyramid_webauthn.py:21-26,60-64, test_saml.py:86-100, test_pyramid_totp_auth.py:31-38 | [목] 없는 메서드에 return_value 를 걸고 assert_called |
| K04 | SAML 서명·Audience·시간 검증 없음 | test_saml.py:8-28 (서명 없는 응답 샘플), :77-84 (success True 를 정답으로), test_pyramid_saml.py:38-58 (서비스 전체 목) | [시드] 위조 가능한 응답을 정상으로 기대 |
| K05, K06, K07 | SAML 설정 미사용 / 클라우드 스토리지 미연결 / CoverStudio 호출자 없음 | test_pyramid_saml.py:25-36, test_cloud_storage.py 전체, test_cover_studio.py 전체 | [경로] 각 서비스를 단독으로만 호출, 연결 지점 테스트 없음 |
| K08 | TOTP 활성화 UI 없음 | test_totp.py:37-55 (서비스를 직접 호출해 enable), test_pyramid_totp_auth.py:62-71 (verify_user_login 을 patch) | [경로] 화면 경로 없이 서비스 직접 호출 |
| K09, R3D-11, R3D-12 | WebAuthn DDL/연결/등록 검증 | test_webauthn.py:28-31,42-61,65-77, test_pyramid_webauthn.py:66-86 | [목] 서비스 DB 를 MagicMock 으로 교체, 반환을 리스트로 지정 |
| (R5F-01) | WebAuthn 이 QueryResult 를 리스트로 취급 | test_webauthn.py:29,42 (`db.query.return_value = [ {...} ]`) | [목] 실제 `DatabaseEngine.query()` 는 QueryResult 를 반환 |
| K10 | admin/password 하드코딩 로그인 | web/test_web_addressbook.py:14, web/test_web_inbox_views.py:20 (`admin`/`password` 로 로그인) | [시드] 우회 경로를 로그인 수단으로 사용 |
| K11 | 수신함 링크 404 | web/test_web_inbox_views.py:33-42 (아이콘 파일명만 확인) | [약] 링크를 따라가지 않음 |
| K12 | faxrcvd OCR 호출에서 faxname 미정의 | test_cli_faxrcvd.py:41-97 | [경로] OCR 비활성 경로만 실행, 나머지는 전부 patch |
| K13 | helpers 의 MailerService.set_cc/set_bcc 없음 | test_helpers.py 전체 (메일 보내는 helper 호출 없음) | [경로] |
| K16 | 존재하지 않는 서비스 메서드 호출 | test_web_archive.py:29-30,57, test_web_inbox.py:86, test_web_admin.py:48, test_pyramid_modals_action.py:91,98,115,119 | [목] |
| COR-04 | 모든 메일이 실제로는 발송되지 않음 | test_mailer.py:72-92 (`smtplib.SMTP` patch), test_pyramid_modals_action.py:82-98 (`Mailer` 전체 patch) | [목] 전송 계층을 대체, spool 반환 True 를 검증 안 함 |
| COR-05 | loadbyfaxnum 이 튜플 반환 | test_cli_faxrcvd.py:74, test_web_outbox.py:34 (`return_value = True`), test_addressbook.py:129-131 은 튜플을 올바르게 풀지만 호출부는 그렇지 않음 | [목] 호출부가 쓰는 계약(bool)을 모의 |
| COR-06, COR-07, COR-29 | AddressBook(ab_id)/AddressBookFAX 스키마 불일치 | test_addressbook.py:17-55, test_cli_phb.py:17-51, test_helpers.py:28-62, test_models.py:87-102 (PK 이름을 abook_id 등으로 기대) | [스키마] 테스트가 자기 편한 컬럼으로 테이블을 직접 만듦 (R5F-03 이 이 때문에 숨음) |
| COR-08, ADM-08 | DynConf 테이블이 스키마에 없음 | test_dynconf.py:16-25, test_cli_dynconf.py:18-26, test_models.py:73-79 | [스키마] |
| COR-14 | 보관일시 '/' 구분 | test_archive_base.py:64-71, test_archive_in.py:103-110 (`YYYY-MM-DD HH:MM:SS` 만 사용) | [입력] 실제 생산자(faxrcvd)의 형식을 쓰지 않음 |
| COR-11, R3F-17, SEC-01 | SQL 이스케이프/주입 | test_query.py:34-40 (`quote("NOW()")` 가 그대로 통과하는 것을 정답으로 고정), test_engine.py:78-82 (작은따옴표만) | [입력] [시드] |
| COR-15, F1-03 | 실패를 성공으로 위장, 더미 faxinfo | test_helpers_media.py:33-39 (팩스 태그 없는 일반 TIFF 에서 `Received`, `Sender` 키 존재를 기대) | [시드] 꾸며낸 값을 정답으로 고정 |
| COR-18, COR-19, COR-20 | 비밀번호 이력/삭제 NOT NULL 불일치 | test_user_account.py:17-63 (username 이 NULL 허용인 자체 스키마), :182-198 (삭제 후 username None 기대), test_user_passwords.py:16-24 | [스키마] |
| ADM-07 | 바코드 PK 이름 불일치 | test_barcode.py:18-25 (barcode_id), test_models.py:97 | [스키마] |
| ADM-11, ADM-12, COR-32 | 수명주기 음수 일수, 만료 삭제가 실제 팩스에 안 닿음 | test_storage_lifecycle.py:111-137 (`lastmod` 컬럼에 직접 INSERT), :139-148 (summary 키 존재만) | [입력] [약] 운영 코드가 쓰는 archstamp/lastmoddate 는 쓰지 않음 |
| ADM-13, R3D-19, R3D-20 | Jinja 샌드박스 없음, 비 latin-1 PS | test_cover_studio.py:24-50,61-79 (영문 HTML 만, .ps/.pdf 렌더 없음) | [입력] |
| ADM-14, COR-26 | print-in 이 큐에 넣지 않음 | test_network_printer.py:81-101 (`extract_fax_tags` 를 patch, `dispatched True` 정답), test_cli_print_in.py:8-19 | [목] [시드] |
| ADM-15, COR-27 | OCR 인덱싱이 아무것도 저장하지 않음 | test_ocr.py:42-49 (`db` 를 MagicMock, `query.assert_called()` 만), :51-68 (query 가 리스트를 반환한다고 가정) | [목] [약] |
| ADM-18 | SMTP HTML 서명 삭제 | test_smtp_settings.py:25-48 (`email_sig_html` 를 저장하지만 읽어서 비교하지 않음), test_pyramid_admin_smtp.py:43-63 | [약] 저장 필드 일부를 검증하지 않음 |
| ADM-22 | 존재하지 않는 대상에도 성공 | web/test_web_addressbook.py:53-59,70-76, test_pyramid_admin_crud.py:266-281,322-337 (id 999 삭제가 성공이면 통과) | [시드] 없는 id 삭제의 성공을 정답으로 |
| F1-11, F4-16, UI-26 | 가짜 기본값 'Acme Corp' | web/test_web_inbox_views.py:29, test_pyramid_additional_views.py:106-112, test_pyramid_admin_crud.py:213-219,284-297,398-420 (`Main Trunk`, `admin`, `Executive Team`) | [시드] |
| F2-01~F2-03, F4-07 | 발송 실패/신원 미전달/가짜 성공 | test_web_sendfax.py:58-70 (존재하지 않는 `/tmp/doc.pdf`, sendfax 바이너리 없음에도 `job_ids` 1건 성공) | [시드] |
| F2-04, F4-14 | outbox 취소가 실제로 아무것도 안 함 | test_web_outbox.py:43-56 (`killjob` 목) | [목] |
| F3-03 | can_del 미검사 | test_pyramid_modals_action.py:23-33, test_pyramid_additional_views.py:93-103 (identity 가 항상 superuser) | [경로] 권한 분기를 건드리지 않음 |
| F3-11, UI-06, R3A-12 | 세션 무효화, 원시 JSON 401, `/` 공개 | test_pyramid_authorization.py:35-52,68-82, test_web_app.py:50-53 | [시드] 결함을 정답으로 |
| USR-04, SEC-03 | 모뎀/카테고리 접근 제한 | test_web_inbox.py:57-79, test_web_archive.py:19-24 (`user_has_rights` 가 항상 True 인 목 사용자) | [목] |
| R3B-03 | /assign 모달 reassign 인자 | test_pyramid_modals_action.py:66 (`reassign.assert_called_with(5)`) | [시드] 시그니처와 다른 호출을 정답으로 |
| R3B-04, R3H-01 | fid 없이도 1번 팩스 삭제 | test_pyramid_modals_action.py:23-33,36-47 (항상 fid 를 줌) | [입력] |
| R3C-02 | 카테고리 비교가 문자열 대 정수 | test_archive_base.py:106-112 (`faxcat=[7]` 정수), test_user_account.py:217-218 (`get_faxcats() == ["1","2"]` 문자열 고정) | [시드] 두 테스트가 서로 모순된 계약을 각각 고정하고 둘을 잇는 테스트 없음 |
| R3C-07 | None 조건이 `= NULL` | test_dynconf.py:48-56 (전역 규칙은 한 번만 만들고 중복 생성은 시험 안 함) | [입력] (R5F-04 가 이 때문에 숨음) |
| R3D-01 | S3 delete_fax 접두어에 슬래시 없음 | test_cloud_storage.py:101-126 (`list_objects_v2` 를 목으로 돌려주고 Prefix 인자는 확인 안 함) | [목] [약] |
| R3D-02 | 14바이트 가짜 PDF 를 유효로 판단 | test_storage_lifecycle.py:45-46,101-102 (유효한 24바이트 PDF 만) | [입력] |
| R3D-08, R3D-09 | TOTP fail-open, 재사용/시도 제한 없음 | test_totp.py:27-65 (DB 오류, 재사용, 연속 실패 시나리오 없음) | [입력] |
| R3D-14 | SAML XML 이스케이프 | test_saml.py:43-75 (URL 에 `&` 가 없음) | [입력] |
| R3D-30 | FileUpload 가 클라이언트 size 를 신뢰 | test_upload.py:40-54,56-70 (정직한 size 값) | [입력] |
| R3D-32 | FormRules 경계값 | test_validators.py:29-79 (리스트/nan/공백 입력 없음) | [입력] |
| R3A-04, R3E-01 | `namifax phb` 서브커맨드 실패 | test_main_namifax.py:29-58 (dynconf, scheduler, 단축 진입점 2개만 시험, phb/faxcover/notify/faxrcvd 서브커맨드 없음) | [경로] |
| (createuser) | F3-23, R3E-18 | 어떤 테스트도 `createuser`/`run_createuser` 를 호출하지 않음 (grep 0건) | [경로] |
| COR-13, F5-09, R4F-13 | 전역 기본 DB 사용/오염 | test_cli_tools.py:26-33, test_web_ajax.py:85-89 | [경로] |
| COR-23, F5-19, R3D-39 | 스케줄러 보관 정책 미적용 | test_scheduler.py:28-31 (`run_cron(["cron","-t","1"])` 호출 자체를 정답으로 고정) | [시드] |
| (R5F-05) | 스케줄러가 항목 수 대신 종료코드를 로그 | test_scheduler.py:33-36 (`export_phonebook` 이 5 를 반환한다고 모의) | [목] 존재하지 않는 계약을 모의 |
| (R5F-06) | FileUpload `..` 이름 | test_upload.py:31-38 (sanitize 입력은 `../../danger file (1).PDF` 하나) | [입력] |
| (R5F-07) | Accept-Language 미사용 | test_i18n.py:52-74 (`custom_locale_negotiator` 우선순위만 시험, Accept-Language 와 `ko-KR` 형태 없음), :77-121 (4개 문자열) | [입력] [약] |
| (R5F-11) | 모듈 이름 3중 | 41개 파일이 `avantfax.*`, 2개가 `src.namifax.*`, 19개가 `namifax.*`, 7개 혼합 | [경로] |

## 3. PHP 브리지 대응표

대조 방법: (a) 각 `*Bridge.php` 의 공개 메서드에서 `'action' =>`, `'method' =>`, 전송 키, `$resp[...]` 응답 키를 정규식으로 추출, (b) `bridge_cli.py` 의 `elif action == ...` / `elif method == ...` 분기를 잘라 `req.get(...)`/`req[...]` 읽는 키와 반환 딕셔너리 키를 추출, (c) 두 쪽을 한 행씩 대조, (d) 레거시 클래스(legacy/avantfax/includes/*.php)의 공개 메서드와 브리지 공개 메서드를 대조. 이 환경에는 php 가 없어 PHP 쪽은 읽기/정규식만 했고, Python 쪽은 `handle_request()` 를 직접 호출했습니다(3-3 절).

"Python 이 읽지만 PHP 가 안 보내는 키" 열에서 `cid, fid, uid, installdir, user, raw_output, devices, enable_did_routing, faxcats, params` 는 분기 머리말에서 선택적으로 읽는 컨텍스트 키라 비고에 따로 적었습니다. 응답 키 열은 `$resp|$res|$result|$response['키']` 패턴만 대조했습니다.

### 3-1. 메서드 단위 대응 (130행)

| # | PHP 클래스::메서드(인자) | bridge_cli action/method | Python 호출 대상 | 요청 키 (PHP 가 보냄) | Python 이 읽지만 PHP 가 안 보내는 키 | 응답 키 대응 | 비고 |
|---|---|---|---|---|---|---|---|
| 1 | PAMAuthBridge::login($username, $password) | auth_pam/- | backend.login() | password, service, username | - | 일치 |  |
| 2 | PWAuthBridge::login($username, $password) | auth_pwauth/- | req.get() | password, username | binary_path | 일치 | binary_path 미전달 -> Python 기본값 /usr/local/bin/pwauth 고정 |
| 3 | PWAuthBridge::hashPassword($password) | hash_password/- | PasswordManager.hash_password() | password | - | 일치 |  |
| 4 | PWAuthBridge::verifyPassword($plain, $hash) | verify_password/- | PasswordManager.verify_password() | hash, plain | - | 일치 |  |
| 5 | FileUploadBridge::set_name($filename) | upload_sanitize_filename/- | fu.sanitize_filename() | filename | - | 일치 |  |
| 6 | FileUploadBridge::load_file($file) | upload_process/- | req.get() | file_info, mimelimit, randname, randname_len, sizelimit | dest_dir | 일치 | dest_dir 없음 -> 이동 안 함, moved=false |
| 7 | FileUploadBridge::movefile($dir) | upload_process/- | req.get() | dest_dir, file_info, mimelimit, randname, randname_len, sizelimit | - | 일치 | load_file 때의 임시 파일 정보를 다시 보냄(상태 없음). R4F-03 |
| 8 | FormRulesBridge::processForm(array $post) | validate_form/- | req.get() | data, rules | - | 일치 |  |
| 9 | MDBOBridge::insert($dbobject) | insert/- | qb.insert() | data, id_col, table | - | 일치 |  |
| 10 | MDBOBridge::update($dbobject) | update/- | qb.update() | data, table, where | - | 일치 |  |
| 11 | MDBOBridge::get($dbobject) | get/- | qb.get() | id_col, id_val, table | - | 일치 |  |
| 12 | MDBOBridge::find($dbobject, $query_logic = SQL_AND, $limit = null, $offset = null, $include_index = false, $reduce_array = true) | find/- | qb.find() | conditions, limit, logic, offset, reduce_single, table | - | 일치 |  |
| 13 | MDBOBridge::delete($dbobject) | delete/- | qb.delete() | id_col, id_val, table | - | 일치 |  |
| 14 | SQLBridge::connect($db_user, $db_pass, $db_name, $db_host, $db_engine = 'sqlite') | connect/- | req.get() | database, engine, host, password, user | - | 일치 |  |
| 15 | SQLBridge::query($query, &$num = 0, $type = SQL_NONE) | query/- | req.get() | fetch_all, sql | - | 일치 | 선택 컨텍스트 키 params 미전달(분기 머리말에서 읽음) |
| 16 | SQLBridge::quote($string) | quote/- | req.get() | value | - | 일치 |  |
| 17 | SQLBridge::genXML($xmlTitle = true, $mysqlStyle = "response", $metaHeader = "row", $htmlEntities = true) | xml/- | _GLOBAL_ENGINE.gen_xml() | mysql_style, root_tag, row_tag, xml_title | - | 일치 | action xml 은 직전 쿼리 결과 기준인데 PHP 호출마다 새 프로세스 (R3F-19) |
| 18 | AFAddressBookBridge::create($companyname) | abook/create | ab.create() | company | - | 일치 | 선택 컨텍스트 키 cid 미전달(분기 머리말에서 읽음) |
| 19 | AFAddressBookBridge::loadbycid($cid) | abook/loadbycid | ab.loadbycid() | cid | - | 일치 |  |
| 20 | AFAddressBookBridge::get_companies($with_reserved = false) | abook/get_companies | ab.get_companies() | with_reserved | - | 일치 | 선택 컨텍스트 키 cid 미전달(분기 머리말에서 읽음) |
| 21 | AFAddressBookBridge::search_companies($query) | abook/search_companies | ab.search_companies() | query | - | 일치 | 선택 컨텍스트 키 cid 미전달(분기 머리말에서 읽음) |
| 22 | AFAddressBookBridge::delete_cid($cid) | abook/delete_cid | ab.delete_cid() | cid | - | 일치 |  |
| 23 | AFAddressBookBridge::create_faxnumid($faxnumber) | abook/create_faxnumid | ab.create_faxnumid() | cid, faxnumber | - | 일치 |  |
| 24 | AFAddressBookBridge::loadbyfaxnum($faxnumber, &$mult) | abook/loadbyfaxnum | ab.loadbyfaxnum() | faxnumber | - | 일치 | 선택 컨텍스트 키 cid 미전달(분기 머리말에서 읽음) |
| 25 | AFAddressBookBridge::loadbyfaxnumid($abookfax_id) | abook/loadbyfaxnumid | ab.loadbyfaxnumid() | abookfax_id | - | 일치 | 선택 컨텍스트 키 cid 미전달(분기 머리말에서 읽음) |
| 26 | AFAddressBookBridge::create_contact($name, $email) | abook/create_contact | ab.create_contact() | cid, email, name | - | 일치 |  |
| 27 | AFAddressBookBridge::get_contacts() | abook/get_contacts | ab.get_contacts() | - | - | 일치 | 선택 컨텍스트 키 cid 미전달(분기 머리말에서 읽음) |
| 28 | AFAddressBookBridge::remove_contact($abookemail_id) | abook/remove_contact | ab.remove_contact() | abookemail_id | - | 일치 | 선택 컨텍스트 키 cid 미전달(분기 머리말에서 읽음) |
| 29 | AFUserAccountBridge::create(array $details) | user_account/create | user_svc.create() | details | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 30 | AFUserAccountBridge::list_accounts() | user_account/list_accounts | user_svc.list_accounts() | - | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 31 | AFUserAccountBridge::update() | user_account/update | user_svc.load_vals() | data | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 32 | AFUserAccountBridge::change_password($pwd) | user_account/change_password | user_svc.change_password() | pwd | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 33 | AFUserAccountBridge::reset_password($email) | user_account/reset_password | user_svc.reset_password() | email | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 34 | AFUserAccountBridge::set_newpassword($oldpwd, $newpwd) | user_account/set_newpassword | user_svc.set_newpassword() | newpwd, oldpwd | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 35 | AFUserAccountBridge::login($username, $password, $admin = false) | user_account/login | user_svc.login() | admin, password, remote_ip, username | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 36 | AFUserAccountBridge::login_webauth($username, $admin = false) | user_account/login_webauth | user_svc.login_webauth() | admin, remote_ip, username | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 37 | AFUserAccountBridge::load($userid) | user_account/load | user_svc.load() | userid | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 38 | AFUserAccountBridge::load_username($username) | user_account/load_username | user_svc.load_username() | username | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 39 | AFUserAccountBridge::loadbyemail($email) | user_account/loadbyemail | user_svc.loadbyemail() | email | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 40 | AFUserAccountBridge::remove($userid) | user_account/remove | user_svc.remove() | userid | - | 일치 | 선택 컨텍스트 키 uid 미전달(분기 머리말에서 읽음) |
| 41 | AFUserPasswordsBridge::log_password($pwd, $uid) | user_passwords/log_password | up.log_password() | pwd, uid | - | 일치 |  |
| 42 | AFUserPasswordsBridge::password_used($pwd, $uid) | user_passwords/password_used | up.password_used() | pwd, uid | - | 일치 |  |
| 43 | AFUserPasswordsBridge::clear_hashes($uid) | user_passwords/clear_hashes | up.clear_hashes() | uid | - | 일치 |  |
| 44 | ArchiveInBridge::create($path, $faxnid, $faxnumber, $modem, $pages, $date = NULL, $didr_id = NULL) | archive_in/create | archive_in.create() | date, didr_id, faxnid, faxnumber, modem, pages, path | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 45 | ArchiveInBridge::set_archivebox($faxid) | archive_in/set_archivebox | archive_in.set_archivebox() | faxid | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 46 | ArchiveInBridge::rotate_fax() | archive_in/rotate_fax | archive_in.rotate_fax() | fid | - | 일치 | 선택 컨텍스트 키 installdir 미전달(분기 머리말에서 읽음) |
| 47 | ArchiveInBridge::prune_inbox($days) | archive_in/prune_inbox | archive_in.prune_inbox() | days | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 48 | ArchiveOutBridge::create($path, $userid, $cid, $origfaxnum, $pages) | archive_out/create | archive_out.create() | cid, installdir, origfaxnum, pages, path, userid | - | 일치 | 선택 컨텍스트 키 fid 미전달(분기 머리말에서 읽음) |
| 49 | BarcodeRoutingBridge::create($barcode, $alias, $contact = null, $printer = null, $faxcatid = null) | barcode/create | bc.create() | alias, barcode, contact, faxcatid, printer | - | 일치 |  |
| 50 | BarcodeRoutingBridge::delete_route($id) | barcode/delete | bc.delete_route() | barcode_id | - | 일치 |  |
| 51 | BarcodeRoutingBridge::get_routes() | barcode/get_routes | bc.get_routes() | - | - | 일치 |  |
| 52 | BarcodeRoutingBridge::list_routes(&$barcode_id, &$alias, &$barcode) | barcode/list_all | bc.list_all() | - | - | 일치 |  |
| 53 | BarcodeRoutingBridge::load_route($barcode) | barcode/load_route | bc.load_route() | barcode | - | 일치 |  |
| 54 | BarcodeRoutingBridge::loadbyid($barcode_id) | barcode/loadbyid | bc.loadbyid() | barcode_id | - | 일치 |  |
| 55 | BarcodeRoutingBridge::set_alias($alias) | barcode/update | bc.loadbyid() | barcode_id, field, value | - | 일치 |  |
| 56 | BarcodeRoutingBridge::set_barcode($barcode) | barcode/update | bc.loadbyid() | barcode_id, field, value | - | 일치 |  |
| 57 | BarcodeRoutingBridge::set_contact($contact) | barcode/update | bc.loadbyid() | barcode_id, field, value | - | 일치 |  |
| 58 | BarcodeRoutingBridge::set_printer($printer) | barcode/update | bc.loadbyid() | barcode_id, field, value | - | 일치 |  |
| 59 | BarcodeRoutingBridge::set_faxcatid($faxcatid) | barcode/update | bc.loadbyid() | barcode_id, field, value | - | 일치 |  |
| 60 | CoversBridge::create($title, $file) | covers/create | c.create() | file, title | - | 일치 |  |
| 61 | CoversBridge::delete_cover($id) | covers/delete | c.delete_cover() | cover_id | - | 일치 |  |
| 62 | CoversBridge::get_covers() | covers/get_covers | c.get_covers() | - | - | 일치 |  |
| 63 | CoversBridge::list_covers(&$title, &$file) | covers/list_all | c.list_all() | - | - | 일치 |  |
| 64 | CoversBridge::load_cover($file) | covers/load | c.load_cover() | file | - | 일치 |  |
| 65 | CoversBridge::set_title($title) | covers/set_title | c.load_cover() | file, title | - | 일치 |  |
| 66 | CoversBridge::set_file($file) | covers/set_file | c.load_cover() | new_file, old_file | - | 일치 |  |
| 67 | DIDRoutingBridge::create($route, $alias, $contact = null, $printer = null, $faxcatid = null) | did/create | did.create() | alias, contact, faxcatid, printer, route | - | 일치 |  |
| 68 | DIDRoutingBridge::delete_route($id) | did/delete | did.delete_route() | didr_id | - | 일치 |  |
| 69 | DIDRoutingBridge::get_routes() | did/get_routes | did.get_routes() | - | - | 일치 |  |
| 70 | DIDRoutingBridge::list_routes(&$didr_id, &$alias, &$routecode) | did/list_all | did.list_all() | - | - | 일치 |  |
| 71 | DIDRoutingBridge::load_route($routecode) | did/load_route | did.load_route() | route | - | 일치 |  |
| 72 | DIDRoutingBridge::loadbyid($didr_id) | did/loadbyid | did.loadbyid() | didr_id | - | 일치 |  |
| 73 | DIDRoutingBridge::set_alias($alias) | did/update | did.loadbyid() | didr_id, field, value | - | 일치 |  |
| 74 | DIDRoutingBridge::set_routecode($routecode) | did/update | did.loadbyid() | didr_id, field, value | - | 일치 |  |
| 75 | DIDRoutingBridge::set_contact($contact) | did/update | did.loadbyid() | didr_id, field, value | - | 일치 |  |
| 76 | DIDRoutingBridge::set_printer($printer) | did/update | did.loadbyid() | didr_id, field, value | - | 일치 |  |
| 77 | DIDRoutingBridge::set_faxcatid($faxcatid) | did/update | did.loadbyid() | didr_id, field, value | - | 일치 |  |
| 78 | DistributionListBridge::create($listname) | distro/create | dl.create() | listname, user | - | 일치 |  |
| 79 | DistributionListBridge::delete_list($list_id) | distro/delete | dl.delete_list() | list_id | - | 일치 | 선택 컨텍스트 키 user 미전달(분기 머리말에서 읽음) |
| 80 | DistributionListBridge::get_distrolists() | distro/get_distrolists | dl.get_distrolists() | - | - | 일치 | 선택 컨텍스트 키 user 미전달(분기 머리말에서 읽음) |
| 81 | DistributionListBridge::load_list($id) | distro/load | dl.load_list() | list_id | - | 일치 | 선택 컨텍스트 키 user 미전달(분기 머리말에서 읽음) |
| 82 | DistributionListBridge::set_listname($listname) | distro/set_listname | dl.load_list() | list_id, listname, user | - | 일치 |  |
| 83 | DistributionListBridge::list_entries() | distro/list_entries | dl.load_list() | list_id | - | 일치 | 선택 컨텍스트 키 user 미전달(분기 머리말에서 읽음) |
| 84 | DistributionListBridge::add_entries($entries) | distro/add_entries | dl.load_list() | entries, list_id, user | - | 일치 |  |
| 85 | DistributionListBridge::remove_entries($entries) | distro/remove_entries | dl.load_list() | entries, list_id, user | - | 일치 |  |
| 86 | DynamicConfigBridge::lookup($device, $callid) | dynconf/lookup | dc.lookup() | callid, device | - | 일치 |  |
| 87 | DynamicConfigBridge::list_rules() | dynconf/list_rules | dc.list_rules() | - | - | 일치 |  |
| 88 | DynamicConfigBridge::remove($id) | dynconf/remove | dc.remove() | id | - | 일치 |  |
| 89 | DynamicConfigBridge::create($device, $callid) | dynconf/create | dc.create() | callid, device | - | 일치 |  |
| 90 | DynamicConfigBridge::load_rule($id) | dynconf/load | dc.load_rule() | id | - | 일치 |  |
| 91 | DynamicConfigBridge::save_rule($device, $callid) | dynconf/save | dc.load_rule() | callid, device, id | - | 일치 |  |
| 92 | FaxModemBridge::create($device, $alias, $contact = null, $printer = null, $faxcatid = null) | modem/create | fm.create() | alias, contact, device, faxcatid, printer | - | 일치 |  |
| 93 | FaxModemBridge::delete_device($device) | modem/delete | fm.delete_device() | device | - | 일치 |  |
| 94 | FaxModemBridge::get_modems() | modem/get_modems | fm.get_modems() | - | - | 일치 |  |
| 95 | FaxModemBridge::list_modems(&$devid, &$alias, &$device) | modem/list_all | fm.list_all() | - | - | 일치 |  |
| 96 | FaxModemBridge::load_device($device) | modem/load | fm.load_device() | device | - | 일치 |  |
| 97 | FaxModemBridge::loadbyid($devid) | modem/loadbyid | fm.loadbyid() | devid | - | 일치 |  |
| 98 | FaxModemBridge::get_status() | modem/get_status | fm.load_device() | class, device, status | - | 일치 | 요청에 raw_output 없음 -> 실제 faxstat 실행; 응답 status{class,status} 사용; 선택 컨텍스트 키 raw_output 미전달(분기 머리말에서 읽음) |
| 99 | FaxModemBridge::set_alias($alias) | modem/update | fm.loadbyid() | devid, field, value | - | 일치 |  |
| 100 | FaxModemBridge::set_contact($contact) | modem/update | fm.loadbyid() | devid, field, value | - | 일치 |  |
| 101 | FaxModemBridge::set_printer($printer) | modem/update | fm.loadbyid() | devid, field, value | - | 일치 |  |
| 102 | FaxModemBridge::set_faxcatid($faxcatid) | modem/update | fm.loadbyid() | devid, field, value | - | 일치 |  |
| 103 | FaxPDFArchiveBridge::get_num_faxes($devices, $faxcats) | archive_base/get_num_faxes | archive.get_num_faxes() | devices, enable_did_routing, faxcats | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 104 | FaxPDFArchiveBridge::user_has_rights($userid, array $modems, array $routes, array $faxcat) | archive_base/user_has_rights | archive.user_has_rights() | faxcat, modems, routes, userid | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 105 | FaxPDFArchiveBridge::get_fid_prev() | archive_base/get_fid_prev | archive.viewable_devices() | - | - | 일치 | 선택 컨텍스트 키 devices,enable_did_routing,faxcats,fid,installdir 미전달(분기 머리말에서 읽음) |
| 106 | FaxPDFArchiveBridge::get_fid_next() | archive_base/get_fid_next | archive.viewable_devices() | - | - | 일치 | 선택 컨텍스트 키 devices,enable_did_routing,faxcats,fid,installdir 미전달(분기 머리말에서 읽음) |
| 107 | FaxPDFArchiveBridge::search_archive($criteria) | archive_base/search_archive | archive.search_archive() | criteria | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 108 | FaxPDFArchiveBridge::list_inbox($devices, $index = 0, $limit = 25, $faxcats = null) | archive_base/list_inbox | archive.list_inbox() | devices, enable_did_routing, faxcats, index, limit, order_by_modem | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 109 | FaxPDFArchiveBridge::load_fax($faxid) | archive_base/load_fax | archive.load_fax() | faxid | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 110 | FaxPDFArchiveBridge::set_category($catid, $userid = 0) | archive_base/set_category | archive.set_category() | catid, userid | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 111 | FaxPDFArchiveBridge::remove_category($catid) | archive_base/remove_category | archive.remove_category() | catid | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 112 | FaxPDFArchiveBridge::set_note($description, $category, $userid) | archive_base/set_note | archive.set_note() | category, description, userid | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 113 | FaxPDFArchiveBridge::set_faxcontent($faxcontent) | archive_base/set_faxcontent | archive.set_faxcontent() | faxcontent | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 114 | FaxPDFArchiveBridge::delete_fax($fid = NULL) | archive_base/delete_fax | archive.delete_fax() | fid | - | 일치 | 선택 컨텍스트 키 installdir 미전달(분기 머리말에서 읽음) |
| 115 | FaxPDFArchiveBridge::prune_archive($days) | archive_base/prune_archive | archive.prune_archive() | days | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 116 | FaxPDFArchiveBridge::set_faxnumid($id) | archive_base/set_faxnumid | archive.set_faxnumid() | id | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 117 | FaxPDFArchiveBridge::set_companyid($id) | archive_base/set_companyid | archive.set_companyid() | id | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 118 | FaxPDFArchiveBridge::reassign($oldcid, $newcid) | archive_base/reassign | archive.reassign() | newcid, oldcid | - | 일치 | 선택 컨텍스트 키 fid,installdir 미전달(분기 머리말에서 읽음) |
| 119 | FaxPDFCategoryBridge::create($name) | categories/create | cat.create() | name | - | 일치 |  |
| 120 | FaxPDFCategoryBridge::set_name($name, $catid) | categories/set_name | cat.set_name() | catid, name | - | 일치 |  |
| 121 | FaxPDFCategoryBridge::get_list(&$catid, &$name) | categories/get_categories | cat.get_categories() | - | - | 일치 |  |
| 122 | FaxPDFCategoryBridge::get_categories() | categories/get_categories | cat.get_categories() | - | - | 일치 |  |
| 123 | FaxPDFCategoryBridge::get_name($catid) | categories/get_name | cat.get_name() | catid | - | 일치 |  |
| 124 | FaxPDFCategoryBridge::delete_category($catid) | categories/delete | cat.delete_category() | catid | - | 일치 |  |
| 125 | FaxQueueBridge::process_queue() | faxqueue/get_queue | fq.process_queue() | - | - | 일치 | 선택 컨텍스트 키 raw_output 미전달(분기 머리말에서 읽음) |
| 126 | FaxQueueBridge::process_failed_queue() | faxqueue/get_failed_queue | fq.process_failed_queue() | - | - | 일치 | 선택 컨텍스트 키 raw_output 미전달(분기 머리말에서 읽음) |
| 127 | FaxQueueBridge::list_owner($owner) | faxqueue/list_owner | fq.process_queue() | owner | - | 일치 | 선택 컨텍스트 키 raw_output 미전달(분기 머리말에서 읽음) |
| 128 | FaxQueueBridge::killjob($user, $jid) | faxqueue/killjob | fq.killjob() | jid, user | - | 일치 |  |
| 129 | FaxQueueBridge::faxalter($user, $jid, array $operations) | faxqueue/faxalter | fq.faxalter() | jid, operations, user | - | 일치 |  |
| 130 | MailerBridge::sendmail($to) | mailer_send/- | req.get() | attachments, images, spool_mode, subject, text, to | admin_email, email_sig_html, email_sig_text, smtp_password, smtp_port, smtp_server, smtp_user, use_ssl, use_tls | 일치 | smtp_* 미전달 -> smtp_server=None 이면 spool 모드로 성공 반환 (COR-04) |


130행 모두에서 "PHP 가 보내는 action/method 에 대응하는 Python 분기가 없는" 경우는 0건, "PHP 가 읽는 응답 키를 Python 이 안 돌려주는" 경우도 0건이었습니다. 즉 이미 존재하는 메서드끼리의 이름/인자는 맞습니다. 어긋나는 곳은 아래 3-2(레거시 공개 메서드가 브리지에 아예 없음)와 3-3(실행해 보면 달라지는 곳)입니다.

### 3-2. 레거시 공개 메서드 대비 브리지에 없는 메서드

브리지 파일 머리말은 모두 "Implements legacy X interface" 라고 쓰여 있고 `__call` 매직 메서드도 없어서, 레거시 PHP 코드가 없는 메서드를 부르면 PHP Fatal 입니다. (레거시 공개 메서드 수 / 브리지 공개 메서드 수 / 레거시에는 있고 브리지에 없는 것)

| 브리지 | 레거시 | 브리지 | 브리지에 없는 레거시 공개 메서드 |
|---|---|---|---|
| AFAddressBookBridge | 45 | 18 | create_contacts, delete_companyfaxids, delete_faxnumid, get_category, get_contact_email, get_contact_name, get_description, get_email, get_faxfrom, get_faxnums, get_faxto, get_multinfo, get_printer, get_to_address, get_to_city, get_to_location, get_to_person, get_to_voicenumber, get_to_zip, has_fax2email, inc_faxfrom, inc_faxto, load_contact_by_id, make_contact_list, reassign, save_settings, set_company, totalfaxes, update_contact (29개) |
| FormRulesBridge | 18 | 9 | addCSSErrorID, clearErrors, dbQueryReady, frSerialize, frUnSerialize, getRawDate, htmlentity_array, setDateFmt, setVals, unsetRule (정규식이 잡은 `if` 는 제외한 10개) |
| MDBOBridge | 11 | 8 | getError, getRecords, query, quote, set_quoting |
| MDBODataBridge | 14 | 11 | get, quote, quoting (`debug` 는 공개 속성) |
| SQLBridge | 12 | 12 | XMLHeader, fixAmp |
| FileUploadBridge | 11 | 12 | get_tempname |
| AFUserAccountBridge | 29 | 33 | login_alternate_auth (F4-04 와 연결) |
| 그 밖의 17개 브리지 | | | 누락 0건 |

반대로 `bridge_cli.py` 에는 있는데 PHP 호출자가 없는 분기: `abook/save_settings`, `archive_base/create_fax`, `user_account/{get_didrouting, get_faxcats, get_modemdevs, set_didrouting, set_email, set_faxcats, set_modemdevs, set_username}` (10개). 양쪽에서 서로 상대가 없는 고아입니다 (R5F-10).

### 3-3. Python 쪽 직접 호출 결과 (`handle_request()`, 실제 schema.py 로 초기화한 SQLite)

| 호출 | 결과 | 판정 |
|---|---|---|
| abook/create `company="BridgeCo"` | `{"success": true, "abook_id": 3}` | 일치 |
| abook/create_faxnumid `cid=1` | `success false, "No abook_id loaded"` | 시드 회사 Acme 의 `abook_id` 컬럼이 NULL (COR-07) 이라 로드 실패 |
| abook/loadbyfaxnum | 같은 이유로 실패 | COR-06/07 |
| abook/get_companies | 각 행이 `"ab_id": 1, ..., "abook_id": null` 로 PK 이름 둘을 모두 가짐 | COR-07 |
| categories/create, get_categories | 정상 | 일치 |
| user_account/load_username admin | `password` 값이 평문 `"password"` | K10, SEC-06 |
| user_account/get_modemdevs | `[]` | PHP 측 대응 메서드 없음 (3-2) |
| did/create, did/list_all | 정상, 반환 키 `didr_id, routecode` | 일치 |
| modem/get_status (raw_output 주입) | `{"status":{"class":"modem-free","status":"Running and idle"}}` | 일치 |
| faxqueue/get_queue (raw_output="") | `{"queue": []}` | 일치 |
| mailer_send spool_mode=True | `success true` | spool 일 뿐 발송이 아님 (COR-04) |
| xml | 직전 쿼리가 아니라 프로세스 내 마지막 결과(시드 Modems 행)를 XML 로 반환 | PHP 호출마다 새 프로세스라 의미 없음 (R3F-19) |
| nonexistent | `{"error": "Unknown action: nonexistent"}` | 정상 오류 |
| query SELECT 1 | `records [{"x":1}]`, `insert_id` 는 이전 값(3)을 그대로 돌려줌 | 새 결함 아님 (엔진 전역 결과 상태, F5-18) |

### 3-4. 이 절에서 올린 결함

R5F-10 (레거시 인터페이스 누락과 고아 분기). 그 밖의 대응 어긋남은 R4F-01~05, COR-30, R3F-19 로 이미 보고되어 있습니다.

## 4. 문서 주장 대 실제 표

"판정": 불일치 = 문서가 말한 것과 코드/실행 결과가 다름. 괄호는 이미 known5 에 있는 결함 ID(그 결함 때문에 문서 표기가 거짓이 되는 경우)이고, **새** 는 이번 라운드에서 새로 확인한 어긋남입니다.

### 4-1. ARCHITECTURE.md 4절 "포팅 상태 매트릭스" (46행: COMPLETE 22, FFI_BRIDGED 24)

머리말은 "전 모듈 및 화면 현대화 100% 완료"라고 쓰는데, 같은 문서가 정의한 상태값으로는 24행이 아직 `FFI_BRIDGED`(= COMPLETE 아님)이고, prompts/04 는 "모든 모듈 `[COMPLETE]`, FFI 브리지·임시 래퍼 정리"를 최종 통합의 조건으로 적었습니다. 그런데 `*Bridge.php` 23개와 `bridge_cli.py` 는 그대로 남아 있습니다(COR-30).

| # | 모듈 | 문서 상태 | 실제 (근거) | 판정 |
|---|---|---|---|---|
| 01 | SQL | FFI_BRIDGED | 명세 01 의 `query(fetch_all=)`, `with engine.connect()`, `SQLSession` 이 없음 (R5F-12). 단일 연결 스레드 공유(COR-01), MySQL 사용 불가(COR-12) | 불일치 |
| 02 | MDBO | FFI_BRIDGED | `quote("NOW()")` 가 SQL 함수로 통과 (R3F-17), 주소록 SQLi (SEC-01) | 불일치 |
| 03 | FormRules | FFI_BRIDGED | 레거시 메서드 10개가 FormRulesBridge 에 없음 (R5F-10). 경계값 (R3D-32) | 불일치 |
| 04 | PWAuth | FFI_BRIDGED | 로그인에 연결 안 됨 (F4-04), 해시는 무염 MD5 (SEC-06) | 불일치 |
| 05 | PAMAuth | FFI_BRIDGED | 로그인에 연결 안 됨 (F3-17) | 불일치 |
| 06 | FileUpload | FFI_BRIDGED | 업로드 뷰에 미연결 (F2-09), 이름 `..` 경로 탈출 (R5F-06) | 불일치 |
| 07 | Mailer | FFI_BRIDGED | 발송이 spool 로 성공 반환 (COR-04) | 불일치 |
| 08 | MDBObject | FFI_BRIDGED | 명세의 `BaseModel` 없음 (R5F-12) | 부분 일치 |
| 09 | classes_entities | FFI_BRIDGED | 명세의 `from_dict()` 없음 (R5F-12), PK 이름이 실제 스키마와 다름 (COR-29) | 불일치 |
| 10 | MDBOData | FFI_BRIDGED | update_entry 가 PK 없으면 INSERT (R3C-06), find 반환 형태 3종 (R3F-10) | 불일치 |
| 11 | Covers | FFI_BRIDGED | 업로드/중복 검증 (ADM-30) | 부분 일치 |
| 12 | FaxPDFCategory | FFI_BRIDGED | 명세 12 4절의 `list_all()` 없음 (R5F-12), 참조 정리 없음 (R4U-03) | 불일치 |
| 13 | AFUserPasswords | FFI_BRIDGED | 스키마 불일치 (COR-18), 재사용 금지 왕복 버그 (R4U-02) | 불일치 |
| 14 | DynamicConfig | FFI_BRIDGED | 테이블이 스키마에 없음 (COR-08), 빈 device 규칙 중복 허용 (R5F-04) | 불일치 |
| 15 | BarcodeRouting | FFI_BRIDGED | PK 이름 불일치 (ADM-07), bardecode 항상 None (F4-17) | 불일치 |
| 16 | DIDRouting | FFI_BRIDGED | 테이블명 변경 마이그레이션 없음 (R3F-11) | 부분 일치 |
| 17 | DistributionList | FFI_BRIDGED | 회사 ID 를 항목으로 저장 (R3B-02) | 부분 일치 |
| 18 | FaxModem | FFI_BRIDGED | 폼에 삭제/devid 없음 (ADM-23) | 부분 일치 |
| 19 | AFAddressBook | FFI_BRIDGED | loadbyfaxnum 튜플 (COR-05), 스키마 (COR-06/07), 브리지는 공개 메서드 45개 중 16개 (R5F-10) | 불일치 |
| 20 | FaxPDFArchive | FFI_BRIDGED | 보관일시 '/' (COR-14), 파일 삭제 불능 (COR-28) | 불일치 |
| 21 | AFUserAccount | FFI_BRIDGED | 메서드 누락 (K03), 캐시 write-back (R3C-11) | 불일치 |
| 22 | dynconf CLI | COMPLETE | 골든은 사용법 출력뿐 (F5-07), 차단이 실제로는 동작 안 함 (COR-08) | 불일치 |
| 23 | phb CLI | COMPLETE | 단위 테스트는 직접 만든 스키마에서 통과, 실제 스키마에서는 모든 회사의 번호가 비어 있음 (R5F-03), `namifax phb` 실패 (R3A-04) | 불일치 |
| 24 | ArchiveIn | FFI_BRIDGED | 회전 시 다쪽 TIFF 1쪽으로 (F1-07) | 불일치 |
| 25 | ArchiveOut | FFI_BRIDGED | installdir 접두어 절단 (R3C-05) | 부분 일치 |
| 26 | FaxQueue | FFI_BRIDGED | 명령 주입 (COR-10), 소유자 해석 (COR-21) | 불일치 |
| 27 | functions | COMPLETE | 실패를 성공으로 위장 (COR-15), K13 | 불일치 |
| 28 | avantfaxcron | COMPLETE | 스케줄러는 `-t` 만 호출해 보존 정책 미적용 (COR-23, R5F-15) | 불일치 |
| 29 | notify CLI | COMPLETE | 모든 사용자에서 AttributeError (COR-03) | 불일치 |
| 30 | faxrcvd CLI | COMPLETE | K12, COR-20 | 불일치 |
| 31 | faxcover CLI | COMPLETE | 토큰 치환 (COR-16), PS 이스케이프 (R3E-03) | 불일치 |
| 32-37 | Web 6종 | COMPLETE | K02, K10, F1-08, F2-04, F4-07, ADM-xx 다수 | 불일치 |
| (없음) | 38 tools-batch | **행 자체가 없음** | 순번이 37 에서 39 로 건너뜀. 머리말 "37/37 모듈"과 표의 실제 행 수 46 이 안 맞음. specs/38 과 CLI 골든 15~19 는 존재 | **새**, R5F-14 |
| 39 | AdminSmtpGateway | COMPLETE | K01, ADM-17, ADM-18 | 불일치 |
| 40 | StorageLifecycle | COMPLETE | 스케줄러 미연결 (R5F-15), ADM-11, ADM-12 | 불일치 |
| 41 | CloudStorage | COMPLETE | K06, R3D-01 | 불일치 |
| 42 | NetworkPrinter | COMPLETE | 큐 등록 없음 (ADM-14), LPD/IPP 없음 (R3D-25) | 불일치 |
| 43 | TotpAuth | COMPLETE | UI/QR 없음 (K08), 2FA 미강제 (F3-01), 창 0 (R5F-08) | 불일치 |
| 44 | CoverStudio | COMPLETE | 호출자 없음 (K07) | 불일치 |
| 45 | WebAuthnPasskeys | COMPLETE | K03, K09, R3D-11/12, R5F-01 | 불일치 |
| 46 | SAML2SSO | COMPLETE | K03~K05 | 불일치 |
| 47 | OcrTextExtraction | COMPLETE | ADM-15, K12 | 불일치 |

### 4-2. ARCHITECTURE.md 그 밖의 사실 주장

| 위치 | 문서의 주장 | 실제 (확인 방법) | 판정 |
|---|---|---|---|
| 머리말, §7.1, §8.4 | "pytest 296/296" | 362 (`pytest tests`) | **새** |
| §5.2, §6 | "pytest 374/374" | 같은 문서 안에서 296 과 374 가 섞임. 실제 362. 골든 포함 시 450 | **새** |
| §6.1 | 골든 시나리오 14개 | `golden_master/data` 에 20개, 머리말은 20/20 | **새** (문서 내부 모순) |
| §11.2 제목 | "핵심 22대 웹 라우팅 시나리오" | 표에는 W01~W50 이 50개, 실제 `golden_master/web` 68개 | **새** |
| §9.1 대 §11.2 | 같은 W 번호가 다른 화면을 가리킴 (9.1 의 W08 = fax_rotate, 11.2 의 W08 = outbox_queue 등) | 두 표를 대조 | **새** |
| §9.1 W12 | 라우트 `archive_search` `/search`, 템플릿 `search.jinja2` | routes.py 에 `/search` 라우트 없음, templates 에 `search.jinja2` 없음 | **새** |
| §9.1 W27 | JSON API `/api/*` (권한 view/admin) | 실제는 `/ajax/*` 이고 `permission` 미지정 (SEC-02). `/api/*` 는 WebAuthn 6개뿐 | **새** |
| §9.1 W08 | `fax_rotate` 는 POST | 뷰에 `request_method` 제한 없음, GET 이 열림 (R3H-03) | 불일치 (known) |
| §9.2, §12 레이아웃 행 | `templates/components/{bar,admin_bar,pager,modal}.jinja2` | `templates/components/` 디렉터리 자체가 없음 | **새** |
| §12 W49/W50 | 타깃 `views/upload.py` | 해당 파일 없음, 구현은 `views/helpers.py` 의 `upload_email_contacts`, `upload_fax_contacts` | **새** |
| §9.3 뷰 데이터 계약 | 모든 뷰가 `current_user, lang, active_tab, server_name/version(NamiFAX v3.3.5), modem_status` 주입 | `lang`, `modem_status` 를 주는 뷰 0개, `server_name` 은 login 뷰에만, 버전 문자열은 "NamiFAX Server 3.3.5" 하드코딩인데 패키지는 4.0.0 | **새** (UI-35 와 부분 겹침) |
| §8.2 | 진입점 표 9개 | pyproject 에는 `namifax-createuser` 가 더 있음 (표에 없음). 그 CLI 는 테스트 0건 | **새** |
| §8.3 | `job_phonebook_sync` 는 "매시간 정각(00분)" | `IntervalTrigger(minutes=60)` 이라 기동 시각 기준 60분 간격 | **새** |
| §8.3 | `job_cron_maintenance` 가 "보존기한 만료 팩스 아카이빙 수행" | `run_cron(["cron","-t","1"])` 만 호출, `-i`/`-d` 없음 (COR-23 의 문서 측면) | 불일치 |
| §8.3 | `namifax serve` / `pserve development.ini` 시 스케줄러 자동 활성화 | `pserve` 경로(`create_app`)는 스케줄러를 시작하지 않음: `get_scheduler().is_running == False` | **새**, R5F-02 |
| §7.1 | 로케일 협상: 쿠키, `Accept-Language` 헤더, 기본값 순 | `Accept-Language: ko-KR` 로 요청해도 영어 (`custom_locale_negotiator` 에 헤더 처리 없음) | **새**, R5F-07 |
| §7.1 | 한국어 "416개 전체 UI 토큰 100%" | ko .po 는 457개 항목 중 빈 항목 1개 (숫자가 낡음) | **새** (경미) |
| 머리말 | "33종 템플릿" | templates 에 42개 파일 | **새** (경미) |
| §8.3 (절 8) | "인메모리 모의 데이터 0건, Stub 0건" | 하드코딩 가짜 데이터가 views/admin.py:617,636,815,840, modals.py:108,211, ajax.py:95,145-146,343, helpers.py:42,148, inbox.py:49, archive.py:62 에 있음 | 불일치 (F4-16, UI-31, ADM-21 이 개별로 다룸) |
| 머리말 | "Zero External CDN" | login_totp.jinja2 가 cdn.tailwindcss.com 사용 (UI-08) | 불일치 (known) |
| §1.2, §3 | SQLAlchemy+Alembic, MySQL | SQLAlchemy 계층 무효 (F5-12), 실제 DB 는 SQLite (F5-22) | 불일치 (known) |

### 4-3. NEW_FEATURES_PLAN.md 의 `[완료]` 12개 항목

| 항목 | 계획서 표기 | 실제 | 판정 |
|---|---|---|---|
| A1 수신 시 PDF 자동 변환 | 완료 | 변환 자체는 Pillow 폴백으로 동작(test_helpers_media 확인). 실패 시 가짜 PDF (COR-15) | 부분 |
| A2 관리자 SMTP 설정 UI | 완료 | 저장이 DB 에 반영 안 됨 (K01), 발송에 쓰이지 않음 (ADM-17) | 불일치 |
| A3 TIFF 자동 정리, "APScheduler/CLI 연동" | 완료 | 스케줄러 job 은 `-t` 만 호출하므로 TIFF 정리(`-p`)는 스케줄에서 실행되지 않음. 명세 40 의 `run_storage_lifecycle_job` 없음 | **새**, R5F-15 |
| B1 네트워크 프린터 "RAW/IPP/LPD" | 완료 | RAW 만 (R3D-25), 인쇄 연동 호출자 없음 (ADM-16) | 불일치 |
| B2 커버 스튜디오 "업로드, 렌더링 미리보기, 변수 태깅" | 완료 | 서비스 호출자 없음 (K07), 미리보기/이름변경/활성화 없음 | 불일치 |
| B3 S3 호환 스토리지 "Presigned URL 뷰어" | 완료 | 코드 전체에 presign 0건 | **새**, R5F-15 |
| C1 TOTP "QR 코드 발급" | 완료 | QR 없음, `qrcode` 의존성 없음 (K08) | 불일치 |
| C2 WebAuthn | 완료 | R3D-11/12, R5F-01 | 불일치 |
| C3 SAML "Entra ID/Okta/Keycloak/ADFS" | 완료 | 서명 검증 없음 (K04), 속성 매핑 (R3D-17) | 불일치 |
| C4 OCR 전문 검색 | 완료 | 저장 안 됨 (ADM-15), 검색 화면 없음 | 불일치 |

### 4-4. docs/hylafax_avantfax_integration_architecture.md

| 위치 | 문서의 주장 | 실제 | 판정 |
|---|---|---|---|
| 3.2 | `production.ini` 의 `[app:main] namifax.archive_dir = /data/nas_faxes` 로 아카이브 경로 지정 | 코드 어디에서도 `namifax.archive_dir` 설정을 읽지 않음. faxrcvd 는 환경변수 `AVANTFAX_ARCHIVE`(기본 `/var/spool/hylafax/archive`)만 읽음 | **새**, R5F-13 (COR-24 의 문서 측 변형) |
| 4.1 | 표준 스케줄 `-t 2 -i 30 -d 90` | 내장 스케줄러는 `-t 1` 만 (`tmp_clean_days=1`) | **새**, R5F-13 |
| 7.1, 7.2 | 관리자 콘솔 `Admin > Maintenance` (`/admin/maintenance` 또는 `/admin/lifecycle`): 보존 일수 3종, TIFF 정책, 원격 정책, 실행 시각, 작업 이력, `[Run Clean Now]` | 해당 라우트·템플릿·필드(`tmp_retention_days`, `inbox_retention_days`, `archive_retention_days`, `tiff_lifecycle_policy`, `remote_lifecycle_policy`) 전부 코드에 없음. `/admin/storage` 는 스토리지 연결 설정 화면 | **새**, R5F-13 |
| 8.3 패턴 B | HylaFAX 훅이 `POST http://namifax-app:8000/api/hooks/faxrcvd` 로 파일을 올림 | 그 라우트/뷰가 없음 (`grep hooks` 0건). 패턴 B 는 따라 할 수 없는 절차 | **새**, R5F-13 |

### 4-5. specs/ 요구사항 중 코드에 없는 것

identifier 추출 스크립트(72개 파일)와 실행 확인 결과입니다. "known" 은 이미 보고된 결함의 명세 측 증거입니다.

| 명세 | 요구사항 | 코드 | 판정 |
|---|---|---|---|
| 01-sql §2.2 | `query(sql, params, fetch_all=False)` | 실제 시그니처 `query(sql, params=None, fetch_type=1)`; `fetch_all=True` 는 TypeError (실행 확인) | **새** R5F-12 |
| 01-sql §3.2 | `with engine.connect() as conn:` | `connect()` 는 인자 3개 필수에 bool 반환, `with` 불가 (실행 확인) | **새** R5F-12 |
| 01-sql §1 | 클래스 `SQLSession` | 없음 | **새** R5F-12 |
| 05-pamauth | `PAMDriver` | 없음 (주입 인자 `pam_driver` 만) | 이름 차이 |
| 07-mailer §3.2 | `in_memory_spool` 모드 | 인자 이름이 `spool_mode`; 서버 미설정 시에도 spool 로 빠짐 (COR-04) | 이름 차이 + known |
| 08-mdobject | 클래스 `BaseModel` | 없음 | **새** R5F-12 |
| 09-classes_entities §3 | `to_dict()`, `from_dict()` | `from_dict` 없음 (`hasattr` False) | **새** R5F-12 |
| 12-categories §4 | `list_all()` 모던 헬퍼 | `FaxPDFCategory.list_all` 없음 (Barcode, DID, Modem, Covers 에는 있음) | **새** R5F-12 |
| 14-dynconf §2.9 | (device, callid) 쌍 중복 검사 | device 가 None/"" 이면 검사 우회 (실행 확인) | **새** R5F-04 |
| 11-covers, 15-barcode | PHP 식 `list_covers`, `list_routes` | `list_covers_step`, `list_routes_step` 로 이름 변경 (의도된 변환) | 문제 아님 |
| 27-helpers | `annotate_fax` | 없음 | known (F4-18) |
| 31-faxcover §3 | `wordwrap` 후 `comments0..n` 토큰, `html2ps` 변환 | 코드에 없음 | known (COR-16 계열) |
| 39-smtp | 테이블 `system_settings` | 실제 `SystemSettings` (이름 차이) | 문제 아님 |
| 40-storage | `purge_local_tiff_after_pdf`, `run_storage_lifecycle_job` | 없음 | known (R3D-41), R5F-15 |
| 41-cloud | `CloudStorageService`, `storage_endpoint/bucket/prefix/region/access_key/secret_key` 설정 키 | 없음 (K06) | known |
| 42-printer | `parse_fax_tags`, `process_print_job` | 이름이 다름 | known (R3D-41) |
| 44-cover-studio | `COVER_TEMPLATE_TAGS` | `get_supported_tags()` 로 대체 | 이름 차이 |
| web/24 | faxalter 폼 `sendtime/sendtimeHour/sendtimeMin/sendtime_unit/sendnow/killtime_unit` | 코드와 모달에 없음 | known 계열 (F2-07, 다른 5라운드 보고서에서도 다룸) |
| web/11 | 설정 폼 `opass`, `vpass`, `page_size_options` | 없음 | known (F3-02, R3H-15) |
| web/25 | 팝업 파라미터 `list_type`(to/cc/bcc), `emaildest_id` | 없음 | known 계열 (F2-12) |
| web/10 | 배포 목록 폼 `dlname`, 버튼 `savename`, 액션 `refresh`, `remove` | 코드에 없음 | known 계열 (UI-36) |

## 5. 결함 목록 (새 결함 15건)

### R5F-01 | 중간 | WebAuthn 서비스가 QueryResult 를 리스트처럼 반복·인덱싱해, 저장된 패스키가 목록에도 인증에도 쓰이지 않음 (K16 의 실행 결과, ADM-15 와 같은 원인)
- 위치: src/namifax/services/webauthn.py:120-135 (`generate_authentication_options`), 204-224 (`list_credentials`), 240-247 (`get_credential_by_id`)
- 증상: `rows = self.db.query(...)` 의 반환은 `QueryResult` 인데 `for row in rows` / `rows[0]` 로 씁니다. 연결된 엔진과 올바른 테이블이 있어도 행이 저장은 되지만, `list_credentials()` 는 항상 `[]`, `generate_authentication_options()` 의 `allowCredentials` 는 항상 비어 있고(브라우저가 어떤 패스키를 쓸지 모르는 usernameless 요청이 됨), `get_credential_by_id()` 는 항상 `None` 이라 인증 검증 단계가 자격을 찾지 못합니다. 모든 `except Exception` 이 TypeError 를 삼켜서 오류 표시도 없습니다. K09(DDL/연결), R3D-11(등록 디코딩), R3D-12(sign_count)를 모두 고쳐도 패스키 로그인은 성립하지 않습니다.
- 재현: `UserWebAuthnCredentials` 테이블을 SQLite 에 만들고 `save_credential(uid=1, credential_id=<base64url>, ...)` 호출 → `SELECT COUNT(*)` 는 1. 같은 엔진으로 `list_credentials(1)` = `[]`, `generate_authentication_options(user_id=1)["allowCredentials"]` = `[]`, `get_credential_by_id(cid)` = `None` (agent-r5-files/exp 스크립트 실행 결과).
- 은폐 테스트: tests/unit/test_webauthn.py:28-31,42-61 (`db.query.return_value` 를 리스트로 모의), test_pyramid_webauthn.py:66-86.
- 확인 수준: 재현

### R5F-02 | 중간 | `pserve development.ini` / `production.ini` 로 기동하면 스케줄러(자정 정리, 전화부 동기화)가 전혀 시작되지 않음 (문서 §8.3 은 반대로 주장)
- 위치: src/namifax/__init__.py:14-52 (`create_app`), src/namifax/main.py:76-95 (스케줄러는 `namifax serve` 에서만 시작)
- 증상: ini 파일의 `[server:main] use = egg:waitress#main` 경로는 `paste.app_factory = namifax:main` → `create_app()` 만 호출하고 스케줄러를 만들지 않습니다. ARCHITECTURE.md 8.3 은 "`namifax serve` / `pserve development.ini` 기동 시 자동으로 백그라운드 스케줄러가 함께 활성화"라고 적었습니다. 이 방식으로 배포하고 별도 `namifax scheduler` 데몬을 띄우지 않으면 임시 파일 정리와 PBOOK 동기화가 영구히 실행되지 않습니다. (F5-01 은 기동 경로가 waitress 가 아닌 점, COR-23 은 서비스 중복 실행 쪽이고 이 결함은 반대 방향입니다.)
- 재현: `create_app({})` 호출 직후 `namifax.services.scheduler.get_scheduler().is_running` → `False`.
- 확인 수준: 재현

### R5F-03 | 중간 | `phb` 가 실제 스키마에서 모든 회사의 팩스번호를 빈 값으로 내보내 HylaFAX 전화부가 번호 없는 항목만 가짐 (COR-06/07 의 변형)
- 위치: src/namifax/cli/phb.py:28-39 (`entry.get("abook_id")` 로 `loadbycid`)
- 증상: 실제 스키마의 `get_companies()` 행은 PK 가 `ab_id` 이고 `abook_id` 는 NULL 이라 `loadbycid(None)` 이 비어 있는 번호 목록을 돌려줍니다. 시드 DB 에서 출력은 `PBOOK1.1Acme Corp||||||||Initech Corp||||||||` 로, 시드에 번호 `1234567` 이 있는 Acme 도 비어 있습니다. 새로 만든 회사의 번호는 `create_faxnumid` 가 `False` (COR-06) 라 저장조차 안 됩니다. 매시간 이 파일을 덮어쓰므로(R3D-39, F5-19) 기존 HylaFAX 전화부 내용이 지워집니다.
- 재현: `init_database_tables` 후 `generate_phonebook_content(AFAddressBook(db=engine))` → 위 문자열. `export_phonebook(path)` 의 반환값은 0.
- 은폐 테스트: tests/unit/test_cli_phb.py:17-51 (PK 를 `abook_id` 로 직접 만든 스키마).
- 확인 수준: 재현

### R5F-04 | 낮음 | DynamicConfig.create 가 device 가 비어 있는(전체 모뎀 적용) 규칙의 중복을 막지 못함 (명세 14 위반, R3C-07 의 변형)
- 위치: src/namifax/services/dynconf.py:85-103 (`find({"callid":..., "device": None})` 가 `device = NULL` 이 되어 항상 불일치), 호출 경로 src/namifax/views/admin.py:672-689 (빈 device 는 `None` 으로 변환해 create 호출)
- 증상: `create(None, "spam")` 을 연속 3번 하면 모두 `True` 이고 `list_rules()` 가 3건. "Rule already exists" 가 발동하지 않습니다. 관리자 화면에서 device 칸을 비우고 같은 번호로 추가를 반복해도 같은 결과입니다. 중복 행은 목록에 나란히 보이고, 하나를 삭제해도 나머지가 차단을 유지해서 "삭제했는데 계속 차단됨"이 됩니다.
- 재현: 서비스를 DynConf 테이블(수동 생성)에 연결해 `create(None,"spam")`, `create(None,"spam")`, `create("","spam")` → `True True True`, `len(list_rules()) == 3`.
- 은폐 테스트: tests/unit/test_dynconf.py:48-62 (중복은 `ttyS0` 에서만 시험).
- 확인 수준: 재현

### R5F-05 | 낮음 | 스케줄러의 전화부 동기화 로그가 항상 "synchronized 0 entries" (종료 코드를 항목 수로 사용)
- 위치: src/namifax/services/scheduler.py:50-51, src/namifax/cli/phb.py:74-76
- 증상: `count = export_phonebook()` 의 반환은 `run_phb()` 의 종료 코드(0)인데 `"Phonebook synchronized {count} entries."` 로 기록합니다. 운영자는 로그로 동기화 건수를 확인할 수 없고, 회사가 100개여도 0 으로 보입니다(R5F-03 의 빈 번호 증상도 이 로그로는 구분 불가).
- 재현: `export_phonebook(path, addressbook=...)` → `0`.
- 은폐 테스트: tests/unit/test_scheduler.py:33-36 (`export_phonebook` 이 5 를 반환한다고 모의).
- 확인 수준: 재현

### R5F-06 | 낮음 | FileUpload 가 이름 `..` 을 허용해 파일이 대상 디렉터리의 상위에 임시 파일 이름으로 저장됨 (R3D-31 (3) 의 변형)
- 위치: src/namifax/common/upload.py:37-43 (`sanitize_filename`), :145-155 (`movefile`)
- 증상: 업로드 이름이 `..` 이면 `load_file` 이 True 이고 `get_name()` 이 `..` 입니다. `movefile(dest)` 는 `dest/..` 로 복사하므로 파일이 `dest` 가 아니라 `dest` 의 부모 디렉터리에 임시 파일 이름(예: `src.bin`)으로 놓입니다. 빈 이름과 `.` 은 이미 보고된 것처럼 임시 이름으로 `dest` 안에 저장됩니다. `dest` 가 업로드 전용 하위 디렉터리면 한 단계 위로 탈출하는 셈입니다(이름 내용은 통제 못 하므로 영향은 제한적).
- 재현: `FileUpload().load_file({"name": "..", "tmp_name": src, "size": 7, "type": "application/pdf", "error": 0})` 후 `movefile(<d>/up/sub)` → 파일이 `<d>/up/src.bin` 에 생김 (agent-r5-files/exp3.py).
- 확인 수준: 재현

### R5F-07 | 낮음 | 로케일 협상이 Accept-Language 를 쓰지 않고, `ko-KR` 같은 지역 코드는 인식하지 못함 (문서 §7.1 과 다름)
- 위치: src/namifax/i18n.py:58-70 (`normalize_locale`), 73-110 (`custom_locale_negotiator`)
- 증상: ARCHITECTURE.md 7.1 은 "쿠키, Accept-Language 헤더, 기본값 순 감지"라고 하지만 헤더 처리가 없어 한국어/일본어 브라우저로 처음 접속해도 영어 화면입니다. 또 `?lang=ko-KR`, `ja-JP`, `pt`(포르투갈어 단독) 은 `None` 이 되어 영어로 떨어집니다(`ko` 만 인식). R4E-04 (언어가 쿠키에만 저장)와는 별개입니다.
- 재현: `webtest` 로 `/login` 에 `Accept-Language: ko-KR,ko;q=0.9` → 화면에 "로그인" 없음. `/login?lang=ko-KR` → 영어, `/login?lang=ko` → 한국어.
- 확인 수준: 재현

### R5F-08 | 낮음 | TOTP 검증 창이 0 이라 시계 오차나 30초 경계에서 정상 코드가 거부됨
- 위치: src/namifax/services/totp.py:31 (`totp.verify(code.strip())`, `valid_window` 기본 0)
- 증상: 직전/다음 30초 스텝의 코드는 모두 거부됩니다(서버와 휴대폰 시계가 수 초만 어긋나도, 사용자가 코드를 입력하는 사이 스텝이 바뀌어도 실패). 백업 코드로 우회하게 되어 소모됩니다. 시도 횟수 제한이 없는 점(R3D-09)과 달리 너무 엄격한 쪽의 결함입니다.
- 재현: `TotpService.verify_code(secret, totp.at(now-30))` → `False`, `totp.at(now+30)` → `False`, 현재 코드 → `True`.
- 확인 수준: 재현

### R5F-09 | 낮음 | 관리자 프린터 화면의 "테스트" 동작이 임의 host:port 로 서버가 소켓 연결을 맺고, 성공/실패와 예외 문자열을 돌려줌 (SSRF/내부망 포트 스캔 오라클, 관리자 한정)
- 위치: src/namifax/views/admin.py:1011-1019 (`test_host`, `test_port` 를 폼에서 그대로 사용), src/namifax/services/printer.py:70-83 (`send_raw_print` 의 `socket.create_connection` 과 `f"... - {exc}"`)
- 증상: 등록된 프린터가 아니라 폼에 입력한 호스트/포트로 연결하고 `NamiFAX Direct Print Test OK` 바이트를 보냅니다. 응답 메시지가 연결 성공/거부/타임아웃/이름 해석 실패를 구분해 주므로 서버 관점에서 내부망 포트를 스캔할 수 있습니다. 허용 대역(사설망 제한), 포트 제한, 등록된 프린터로만 테스트하는 제약이 없습니다. ADM-25 는 값 검증과 500 오류만 다뤘습니다.
- 재현: 코드 확인 (공격 재현은 하지 않음).
- 확인 수준: 코드 확인

### R5F-10 | 낮음 | PHP 브리지가 레거시 공개 인터페이스를 크게 덜 구현하고, bridge_cli 에는 호출자 없는 분기가 남아 있음
- 위치: src/namifax/services/AFAddressBookBridge.php (45개 중 16개), common/FormRulesBridge.php, db/MDBOBridge.php, db/MDBODataBridge.php, db/SQLBridge.php, common/FileUploadBridge.php, services/AFUserAccountBridge.php, db/bridge_cli.py
- 증상: 3-2 표 참조. `AFAddressBookBridge` 는 `reassign`, `save_settings`, `get_description`, `inc_faxfrom`, `has_fax2email`, `get_faxnums` 등 29개가 없고 `__call` 도 없어, "레거시 인터페이스를 구현한다"는 머리말과 달리 레거시 PHP(`faxrcvd.php`, `notify.php`, `admin/fax2email.php`)가 쓰는 메서드를 부르면 Fatal 입니다. 반대로 bridge_cli 의 `abook/save_settings`, `archive_base/create_fax`, `user_account/{get_,set_}{modemdevs,faxcats,didrouting}`, `set_email`, `set_username` 10개 분기는 PHP 호출자가 없어 도달 불가입니다. COR-30 (브리지가 사용되지 않음)이 영향 범위를 줄이지만, FFI_BRIDGED 상태 표기(ARCHITECTURE 4절 01-21, 24-26)의 근거인 "브리지 연결 완료"는 이 표로 반박됩니다.
- 재현: 레거시 `legacy/avantfax/includes/*.php` 의 공개 메서드 집합에서 각 `*Bridge.php` 의 공개 메서드 집합을 뺀 결과 (agent-r5-files/bridgemap.py 와 인라인 스크립트).
- 확인 수준: 재현 (정규식 추출, php 미설치)

### R5F-11 | 낮음 | 테스트가 같은 소스를 세 가지 모듈 이름(`avantfax.*`, `src.namifax.*`, `namifax.*`)으로 임포트해, 서로 다른 클래스와 전역 싱글턴을 검증함 (R3G-10 의 확장)
- 위치: tests/ 전체. `avantfax` 만 41개 파일, `src.namifax` 만 2개(test_cli_print_in.py, test_cloud_storage.py), `namifax` 만 19개, 혼합 7개(test_cover_studio, test_network_printer, test_pyramid_admin_smtp, test_pyramid_totp_auth, test_smtp_settings, test_storage_lifecycle, test_totp). `pyproject.toml` 의 `pythonpath = [".", "src"]` 때문에 `src.namifax` 와 `namifax` 가 동시에 임포트됩니다.
- 증상: `namifax.db.engine.DatabaseEngine`, `src.namifax.db.engine.DatabaseEngine`, `avantfax.db.engine.DatabaseEngine` 가 서로 다른 클래스 객체이고, `get_default_engine()`/`get_scheduler()` 싱글턴도 모듈 이름마다 따로입니다. 혼합 파일은 avantfax 엔진을 namifax 서비스에 넣어 오리 타이핑으로 통과합니다. 한쪽 트리만 고쳐도 다른 쪽 테스트가 통과하므로, 어느 테스트가 어느 구현을 검증하는지 읽어서는 알 수 없습니다.
- 재현: 세 모듈 이름으로 임포트해 `is` 비교 → 전부 False (`DatabaseEngine`, `get_scheduler()`, `get_default_engine()`).
- 확인 수준: 재현

### R5F-12 | 낮음 | 명세 01~38 의 인터페이스 요구와 구현이 어긋남 (명세 39~47 은 R3D-41 이 다룸)
- 위치: specs/01-sql.md §1,§2.2,§3.2, specs/08-mdobject.md §1, specs/09-classes_entities.md §3, specs/12-categories.md §4
- 증상: (1) `DatabaseEngine.query(..., fetch_all=True)` 는 `TypeError` (실제 인자는 `fetch_type`), (2) `with engine.connect() as conn:` 불가 (`connect()` 는 인자 3개 필수에 bool 반환), (3) `SQLSession` 클래스 없음, (4) `BaseModel` 없음, (5) `from_dict()` 없음 (`to_dict` 만 있음), (6) `FaxPDFCategory.list_all()` 없음 (Barcode/DID/Modem/Covers 는 있음). 명세를 보고 만든 외부 코드나 테스트는 이 호출에서 바로 실패합니다.
- 재현: `inspect.signature`, `hasattr`, 실제 호출 (agent-r5-files/exp 실행).
- 확인 수준: 재현

### R5F-13 | 낮음 | docs/ 운영 문서가 안내하는 설정과 기능이 실제로는 없음
- 위치: docs/hylafax_avantfax_integration_architecture.md §3.2, §4.1, §7.1-7.2, §8.3 패턴 B
- 증상: (1) `production.ini` 의 `namifax.archive_dir` 는 코드가 읽지 않습니다(환경변수 `AVANTFAX_ARCHIVE` 만 사용). 문서대로 설정해도 팩스는 기본 경로에 쌓입니다. (2) 문서의 표준 스케줄 `-t 2 -i 30 -d 90` 과 달리 내장 스케줄러는 `-t 1` 만 호출합니다. (3) §7.2 의 관리자 유지보수 화면(`/admin/maintenance`, `/admin/lifecycle`, 보존 일수 3종, TIFF/원격 정책, 작업 이력, `[Run Clean Now]`)은 라우트·템플릿·필드가 하나도 없습니다. (4) 패턴 B 웹훅이 호출하는 `/api/hooks/faxrcvd` 엔드포인트가 없어, 컨테이너 분리 구성 절차를 따라 하면 수신 팩스가 처리되지 않습니다.
- 재현: `grep` 으로 `namifax.archive_dir`, `hooks`, 필드명 0건, routes.py 확인.
- 확인 수준: 재현 (코드 부재 확인)

### R5F-14 | 낮음 | ARCHITECTURE.md 의 수치와 구조 서술이 서로 모순되거나 실제와 다름
- 위치: ARCHITECTURE.md 머리말, 4절(매트릭스), 5.2, 6, 6.1, 7.1, 8.4, 9.1-9.3, 11.2, 12절
- 증상: 4-2 표 참조. 요약: (a) 테스트 수가 296(머리말, 7.1, 8.4)과 374(5.2, 6)로 서로 다르고 실제는 362. (b) "37/37 모듈 이식 100% 완료"인데 매트릭스는 46행이고 24행이 `FFI_BRIDGED`, 38번 행은 아예 없음. (c) 존재하지 않는 파일/경로를 사실처럼 적음: `templates/components/*.jinja2` 4개, `views/upload.py`, `/search` 라우트와 `search.jinja2`, `/api/*` (실제는 `/ajax/*`). (d) 같은 W 번호가 9.1 과 11.2 에서 다른 화면을 가리키고, "핵심 22대"라고 쓴 표가 50개를 나열하며 실제 골든은 68개. (e) 9.3 뷰 데이터 계약의 `lang`, `modem_status` 를 주입하는 뷰가 없음. (f) 8.3 "매시간 정각"은 실제 60분 간격. (g) 8.2 진입점 표에 `namifax-createuser` 누락. 이 문서는 AGENTS.md 가 "단일 진실 공급원(SSOT)"으로 규정하고 작업자가 최우선 참조하라고 한 문서입니다.
- 재현: `routes.py`, `ls templates`, `ls views`, `pytest --collect-only`, 표 행 집계 스크립트.
- 확인 수준: 재현

### R5F-15 | 낮음 | NEW_FEATURES_PLAN.md 가 `[완료]` 로 표기한 기능 중 구현되지 않은 것: 스케줄러 TIFF 정리 연동, Presigned URL 뷰어
- 위치: NEW_FEATURES_PLAN.md:283 (A3 "APScheduler/CLI 연동"), :288 (B3 "Presigned URL 뷰어"), src/namifax/services/scheduler.py:37-44, src/namifax/cli/cron.py:103-111
- 증상: (1) `job_cron_maintenance` 는 `run_cron(["cron","-t","N"])` 만 호출하므로 `StorageLifecycleService.purge_local_tiffs` (cron 의 `-p` 경로)는 스케줄에서 한 번도 실행되지 않습니다. 명세 40 의 `run_storage_lifecycle_job` 도 없습니다. 원본 TIFF 는 수동으로 `cron -t .. -p ..` 를 돌릴 때만 정리됩니다. (2) 코드 전체에 presign 이 0건이라 Presigned URL 뷰어가 없습니다. (R3D-25 가 이미 보고한 IPP/LPD 부재는 제외.)
- 재현: `grep -rni presign src/namifax` 0건, scheduler.py 의 `run_cron` 인자 확인.
- 확인 수준: 코드 확인

## 6. 파일별 "새 결함 없음" 목록

아래는 이번에 읽었고 이번 라운드에서 새 결함이 없는 파일입니다(이미 보고된 결함의 증거만 확인).

- 소스: services/__init__.py, archive_out.py, user_passwords.py, categories.py, distro.py, faxqueue.py, ocr.py, cover_studio.py(76-95), smtp_settings.py(36-60), storage_lifecycle.py(74-90), cli/__init__.py, cli/dynconf.py, cli/i18n.py, cli/print_in.py, cli/user.py, cli/cron.py, routes.py.
- 테스트 (줄 단위로 읽었으나 새 결함 없음, 은폐 대응표에 기여만 함): test_helpers_media.py, test_i18n.py, test_addressbook.py, test_archive_base.py, test_archive_in.py, test_archive_out.py, test_auth_pam.py, test_auth_password.py, test_barcode.py, test_categories.py, test_cli_batch_tools.py, test_cli_cron.py, test_cli_dynconf.py, test_cli_faxcover.py, test_cli_faxrcvd.py, test_cli_notify.py, test_cli_phb.py, test_cli_tools.py, test_covers.py, test_db_base.py, test_did.py, test_distro.py, test_engine.py, test_faxqueue.py, test_helpers.py, test_mailer.py, test_main.py, test_models.py, test_modem.py, test_query.py, test_repository.py, test_saml.py, test_security_policy.py, test_smtp_settings.py, test_user_account.py, test_user_passwords.py, test_validators.py, test_vcard_upload.py, test_web_*.py, tests/web/*.py.
- 새 결함에 기여한 테스트 파일: test_webauthn.py (R5F-01), test_scheduler.py (R5F-05), test_dynconf.py (R5F-04), test_upload.py (R5F-06), test_cli_phb.py (R5F-03), test_i18n.py (R5F-07), test_totp.py (R5F-08), tests 전체 (R5F-11).
- 테스트 자체의 품질 결함은 R4F-12, R4F-15, R4F-16, R4F-17 로 이미 보고되어 있어, 이번에는 줄 단위로 읽은 구체 위치를 2절 대응표로 정리했습니다. 이번에 추가로 확인한 점: 테스트 함수명/메서드명 중복으로 덮어써진 테스트 0건, 정의만 하고 수집되지 않는 테스트 0건.
