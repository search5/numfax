# 4라운드 점검 결과: 미정독 파일, 테스트 코드 자체, 골든 마스터 (round4-files)

작업 방식: 원본 저장소는 수정하지 않았고, `scratchpad/agent-r4-files/repo` 로 복제해서 그 안에서만 실행했습니다(HOME, TMPDIR, NAMIFAX_DB_PATH 도 agent-r4-files 하위). 공격 페이로드는 실행하지 않았습니다. 서브에이전트는 쓰지 않았습니다. known4.md 의 418건과 같은 결함은 적지 않았고, 변형은 "(변형)" 으로 표시했습니다.

신규 결함: 총 20건 (높음 1, 중간 10, 낮음 9)

---

## 1. 읽은 파일과 줄 수

읽은 정도: 전문 = 처음부터 끝까지 읽음, 부분 = 일부만 읽고 나머지는 AST/grep 으로 훑음, 기계 = 스크립트로만 검사.

### 1-1. 담당 (1) 미정독 파일

| 파일 | 줄 수 | 정도 | 새 결함 |
|---|---|---|---|
| src/namifax/db/bridge_cli.py | 912 | 전문 (1~912). 사용한 서비스 메서드 존재 여부는 AST 로 대조 | R4F-02 |
| db/MDBODataBridge.php | 77 | 전문 | R4F-01 |
| db/MDBObjectBridge.php | 63 | 전문 | R4F-01 |
| db/MDBOBridge.php | 136 | 전문 | R4F-01 |
| db/SQLBridge.php | 133 | 전문 | 새 결함 없음 (R3F-19 로 이미 보고됨) |
| models/EntitiesBridge.php | 99 | 전문 | 새 결함 없음 (COR-29, ADM-20 범위) |
| auth/PAMAuthBridge.php | 38 | 전문 | 새 결함 없음 |
| auth/PWAuthBridge.php | 52 | 전문 | 새 결함 없음 |
| common/FileUploadBridge.php | 122 | 전문 | R4F-03 |
| common/FormRulesBridge.php | 93 | 전문 | R4F-02 (빈 배열) |
| services/AFUserAccountBridge.php | 330 | 전문 | R4F-04 |
| services/AFUserPasswordsBridge.php | 58 | 전문 | 새 결함 없음 |
| services/ArchiveInBridge.php | 97 | 전문 | 새 결함 없음 |
| services/ArchiveOutBridge.php | 47 | 전문 | 새 결함 없음 |
| services/FaxPDFArchiveBridge.php | 358 | 전문 | R4F-05 |
| services/FaxQueueBridge.php | 76 | 전문 | 새 결함 없음 |
| services/MailerBridge.php | 73 | 전문 | 새 결함 없음 (COR-04 범위) |
| services/DynamicConfigBridge.php | 147 | 전문 | 새 결함 없음 |
| services/AFAddressBookBridge.php | 183 | 전문 | 새 결함 없음 |
| services/DistributionListBridge.php | 214 | 전문 | 새 결함 없음 |
| services/FaxModemBridge.php | 218 | 전문(주요부) | 새 결함 없음 |
| services/CoversBridge.php | 185 | 전반부 | 새 결함 없음 |
| services/DIDRoutingBridge.php, BarcodeRoutingBridge.php, FaxPDFCategoryBridge.php | 207, 207, 149 | 기계 (action/method/field 이름이 bridge_cli 와 맞는지 정규식 대조: 불일치 0) | 새 결함 없음 |
| src/avantfax/cli/create_thumbnails.py | 63 | 전문 | R4F-06 |
| src/avantfax/cli/ocr_import.py | 64 | 전문 | R4F-06 |
| src/avantfax/cli/import_blacklist.py | 52 | 전문 | 새 결함 없음 (원인은 COR-08) |
| src/avantfax/cli/import_archive.py | 47 | 전문 | 새 결함 없음 (F4-19) |
| src/avantfax/cli/import_users.py | 75 | 전문 | 새 결함 없음 (R3E-11) |
| src/avantfax/cli/reroute.py | 44 | 전문 | 새 결함 없음 |
| src/namifax/web/app.py | 146 | 전문 | R4F-07 |
| src/namifax/web/session.py | 76 | 전문 | 새 결함 없음 (R3A-16) |
| src/namifax/web/views/auth.py, inbox.py, outbox.py, archive.py, sendfax.py, admin.py | 60, 134, 71, 164, 89, 140 | 전문 | 새 결함 없음 (R3F-04~07, K16 범위) |
| src/avantfax/web 전체 | diff 로 namifax/web 과 import 경로만 다름을 확인 | 기계 | 새 결함 없음 |
| src/namifax/__init__.py, models/__init__.py, models/meta.py, cli/__init__.py, services/__init__.py, common/__init__.py, auth/__init__.py, db/__init__.py, web/__init__.py, views/__init__.py | 58, 60, 19, 1, 34, 42, 23, 19, 1, 0 | 전문 | 새 결함 없음 (F5-02, F5-03, F5-12 로 이미 보고됨) |
| src/namifax/models/entities.py | 238 | 전문 | 새 결함 없음 (COR-29, COR-09) |
| src/namifax/cli/phb.py | 85 | 전문. 레거시 phb.php 와 대조, 출력 형식은 충실함 | 새 결함 없음 |
| src/namifax/cli/user.py | 82 | 전문 | 새 결함 없음 (COR-17, F3-23, R3E-18) |
| src/namifax/services/archive_in.py, archive_out.py, user_passwords.py | 132, 52, 60 | 전문 | 새 결함 없음 (R3C-24, COR-14, COR-18) |
| src/namifax/cli/i18n.py, populate_all_locales.py, populate_missing_translations.py | 54, 122, 91 | 전문 | R4F-11 |
| src/namifax/cli/populate_ko.py | 709 | 앞 40줄과 뒤 60줄을 읽고, 587개 항목 사전 전체를 AST 로 분석 | 새 결함 없음 (UI-13, UI-17 범위) |
| locale 24개 .po/.mo | 454 msgid x 24 | 기계 (placeholder, 태그, 백슬래시, fuzzy 검사, .mo 실제 gettext 로드) | R4F-10 |
| templates/layout.jinja2, 404, mytemplate | 159, 8, 8 | 전문 | R4F-09 (layout 이 아니라 inbox/login/archive 쪽) |
| templates/admin_layout.jinja2 | 370 | 앞 60줄과 링크/탭 로직 | 새 결함 없음 |
| templates 전체 | | 기계 (sr-only, safe, innerHTML, JS 안의 `_()` 가 번역에서 따옴표를 깨는지 검사: 현재 카탈로그에서는 깨짐 0) | R4F-08, R4F-09 |

정직한 한계: DID/Barcode/Category PHP 브리지, FaxModem/Covers 의 후반부, admin_layout 의 SVG/링크 나열부, populate_ko 의 중간 사전은 줄 단위로 읽지 않았습니다. 나머지 services/cli 소형 파일 중 categories.py, cover_studio.py, printer.py, scheduler.py, storage_lifecycle.py, totp.py, dynconf.py, cli/cron.py, cli/dynconf.py, cli/print_in.py 는 이번 라운드에서 다시 읽지 않았습니다(1~3라운드 보고 범위로 판단).

### 1-2. 담당 (2) 테스트 코드

tests/ 69개 파일, 7,149줄, 테스트 362개. 전부를 AST 와 정규식으로 검사했고(assert 없음, try/skip, 약한 assert, 존재하지 않는 메서드를 mock 하는지), 아래 파일은 줄 단위로 읽었습니다.

test_pyramid_admin_crud.py (앞 140/430줄), test_web_ajax.py (전문), test_pyramid_modals_action.py (전문), test_web_inbox.py (전문), test_i18n.py (전문), test_helpers_media.py (앞 80줄), test_cli_tools.py (전문), test_web_app.py (전문), test_pyramid_saml.py (앞 80줄), test_pyramid_authorization.py (앞 90줄), test_cli_cron.py (부분), test_cli_faxrcvd.py (부분), tests/web/test_web_inbox_views.py (앞 70줄).

그 밖의 파일(test_addressbook, test_archive_*, test_barcode, test_did, test_distro, test_mailer, test_modem 등)은 줄 단위로 읽지 않았고 기계 검사 결과만 반영했습니다.

### 1-3. 담당 (3) golden_master

web_runner.py (244), runner.py (312), generate_web_golden.py (1321 중 앞 140줄과 구조), extract_form_structure.py (80), extract_live_forms.py (96), apply_strict_form_contracts.py (134), test_e2e.py, test_web_e2e.py, Dockerfile.legacy 전문. web 68개 meta.json/contract.json 과 data 20개 전수를 스크립트로 집계했습니다.

---

## 2. 골든 마스터 시나리오 표

실측: `pytest golden_master` = 88 passed, 0 failed, 0 xfailed, 0 skipped (복제본, 5초).

### 2-1. implemented=false 또는 xfail 시나리오

| 구분 | implemented=false | xfail | 비고 |
|---|---|---|---|
| web W01~W68 (68개) | 0건 | 0건 | 68개 meta.json 모두 `"implemented": true`. xfail 분기(test_web_e2e.py)는 도달하지 않는 코드 |
| CLI 01~20 (20개) | 0건 | 0건 | 20개 모두 true 또는 키 없음(기본 True). xfail 분기는 도달하지 않는 코드 |

즉 "미구현이라서 xfail 로 빠진 시나리오"는 없습니다. 대신 통과는 하지만 검증이 비어 있거나 약한 시나리오가 아래 표입니다.

### 2-2. 통과하지만 실제로는 일부 항목을 검증하지 않는 시나리오

| 시나리오 | 계약에 있으나 러너가 검사하지 않는 항목 | 이유 |
|---|---|---|
| W51_rotate_fax, W52_setcompany, W55_ajax_deletefaxes, W56_ajax_archivebook | meta.params (4건) | 러너는 `meta["route"]` 만 쓰고 params 를 요청에 싣지 않음. W52 는 POST 인데 바디도 `_submit_check` 뿐 |
| W51~W56 (6건) | meta 스키마가 다름 (`id`, `expected_status` 없이 `scenario_id`+`params`) | 후속 스크립트가 다른 형식으로 추가. 러너는 contract.status_code 만 보고 meta.expected_status 는 읽지 않음 |
| 계약에 `title` 이 있는 50건 | title 전체 | 러너에 title 비교 코드 없음 |
| W05 | table_headers, required_actions | 검사 코드 없음 |
| W08, W19, W20, W22 | table_headers | 검사 코드 없음 |
| W07_pdf_download | binary_stream | 검사 코드 없음. 본문이 PDF 인지(F1-15, F4-12 의 합성 PDF) 확인 안 함 |
| W03_login_success | set_cookie | 검사 코드 없음 |
| W42_api_distrolist_faxes | content_type 만 있음 | 본문 검사 없음 |
| W43_api_archive_fax | 계약이 status_code 하나뿐 | 사실상 "200 이면 통과" |
| contract.forms 가 있는 43건 | 폼이 2개 이상일 때 두 번째 이후 | `matched_form = forms[0]` 로 항상 첫 폼만 검사 (web_runner.py:117) |
| W04_inbox_empty | 라우트 `/inbox?empty=1` | 레거시에 없는 테스트용 파라미터를 앱이 해석함 (R4F-08) |
| W01, W04 | required_text 중 ':: AvantFAX LOGIN ::', 'MODEM', 'IDLE' | 눈에 보이는 문구가 아니라 숨은 `sr-only` 문구로 통과 (R4F-09) |
| 전체 web 68건 | response.html 68개 | 러너가 읽지 않음. extract_form_structure.py 가 만든 inspected_forms.json 도 어디서도 쓰이지 않음 |
| CLI 20건 | stderr.txt | runner.py:266 에서 읽기만 하고 비교하지 않음 |

### 2-3. 골든 데이터가 어떻게 만들어졌는가

| 대상 | 생성 방법 | 근거 |
|---|---|---|
| CLI data/01~20 | 실제 레거시 PHP 5.6 를 docker 컨테이너에서 실행해 기록한 것으로 보임 (`runner.py --record`). 출력 문구가 레거시 소스의 usage 와 일치 | runner.py run_legacy, Dockerfile.legacy. 단 컨테이너에 DB 서버가 없고 `display_errors=0` (R4F-18) |
| web contract.json 의 status, required_text, required_links 등 | 사람이 generate_web_golden.py 에 직접 써넣은 값 (레거시 실행 결과가 아님) | generate_web_golden.py 의 SCENARIOS 와 html_content. required_text 171개 중 37개(22%)가 레거시 소스 전체(php, tpl, js, css, 언어 파일)에 없음 (R4F-20) |
| web response.html | 같은 생성기에 문자열로 들어 있는 손작성 HTML (Tailwind 클래스, 레거시 Smarty 마크업이 아님) | generate_web_golden.py:34~ |
| web contract.json 의 form_structure (45건) | 신규 앱을 실행해 뽑은 출력을 정답으로 되써넣음 | extract_live_forms.py (create_app 으로 GET 후 추출) -> apply_strict_form_contracts.py |
| dynamic_states (14건) | 사람이 쓴 사전 DYNAMIC_STATE_DEFS | apply_strict_form_contracts.py. 러너는 선택자가 DOM 에 존재하는지만 확인, JS 동작은 검증하지 않음 |

### 2-4. 비교가 놓치는 항목 (요약)

1. 응답 본문의 실제 값(수신함 행, 사용자 목록 등)은 어느 시나리오에서도 비교하지 않음. 문구는 부분 문자열(대소문자 무시, 원본 HTML 포함)로만 확인.
2. required_text 는 `AvantFAX` -> `NamiFAX`, `avantfax.com` -> `namifax.local` 로 치환한 값도 허용(web_runner.py:198, 207). 레거시 브랜드와 다른 화면이 통과.
3. 모든 인증 시나리오가 하드코딩 admin/password 로 로그인한 관리자 한 명으로만 실행(K10 우회에 의존). 일반 사용자, 비활성 계정, 권한 없는 계정 시나리오가 0건.
4. POST 시나리오는 W02, W03, W10, W11 네 개뿐이고 입력값이 러너에 시나리오 ID 별 if 문으로 박혀 있음(web_runner.py 의 s_id 분기). 저장 후 상태 변화는 검증하지 않음.
5. CLI 20건은 전부 인자 없음/누락 usage 와 존재하지 않는 파일 (F5-07).

---

## 3. 테스트 품질 요약

실측 (복제본, 기본 `pytest tests`): 362 passed, 2.3초.

| 항목 | 결과 |
|---|---|
| (a) assert 없음 | 0건. 대신 약한/항상 참인 assert 가 다수 (R4F-15) |
| (b) 경계값, 오류 경로 | `pytest.raises`/`assertRaises` 가 362개 중 4곳뿐. SQL 인젝션, 경로 탈출, 음수/0 페이지, 비ASCII 입력 테스트 0건 (R4F-17) |
| (c) 예외 삼키기, skip | `skip`/`xfail`/`importorskip` 0건. try 가 있는 테스트 5개는 모두 정리용 finally. 실패를 숨기는 skip 은 없음. 실패 은폐는 테스트가 아니라 mock 이 담당 (R4F-12) |
| (d) 전역 상태 순서 의존 | 무작위 순서 9회 중 1회 실패(seed2), 역순 통과, 파일 단위 69개 모두 통과. 원인 쌍 규명 (R4F-13) |
| (e) 결함을 정답으로 고정 | 다수 (R4F-16) |
| mock 의존도 | MagicMock/patch 사용 파일 39개 / 69개. 존재하지 않는 메서드를 mock 해서 통과하는 사례 11종 (R4F-12) |
| 작업 트리 오염 | 테스트가 CWD 에 `faxes/` 를 만들고(F5-09) .mo 를 다시 씀 (R4F-14) |
| 어느 트리를 검증하는가 | `avantfax.*` import 가 많음 (F5-05, R3G-10) |

순서 실측 표:

| 방식 | 결과 |
|---|---|
| 기본 순서 | 362 passed |
| 역순 | 통과 |
| 무작위 seed 1,3,4,5,6,7,8,9,10 | 통과 |
| 무작위 seed 2 | `test_cli_tools.py::test_create_thumbnails_empty_archive` 실패 |
| 파일 단위 (69개) | 전부 통과 |

---

## 4. 결함 목록

### R4F-01 | 중간 | PHP 브리지가 공개 속성 `debug` 를 DB 컬럼으로 보내 insert, update, find 가 항상 실패
- 위치: src/namifax/db/MDBObjectBridge.php:15 (`public $debug = false;`), src/namifax/db/MDBOBridge.php:35, 57, 92 (`get_object_vars($dbobject)`). 같은 구조가 MDBODataBridge.php 에도 있음.
- 증상: `get_object_vars` 는 공개 속성만 돌려주는데 `debug` 가 공개라 데이터에 `debug => false` 가 섞여 `Modems` 같은 테이블에 없는 컬럼이 INSERT/UPDATE/WHERE 에 들어갑니다. PHP 쪽에서 MDBObject 계열(엔티티 브리지)로 하는 쓰기와 조회가 모두 실패합니다. 또한 MDBODataBridge::query() 는 항상 null 을 반환하고 get_error() 도 항상 null 이라 오류를 알 방법이 없으며, findext 의 include_index 인자는 MDBOBridge::find 에서 버려집니다.
- 재현: `bridge_cli.handle_request` 에 PHP 가 만드는 요청과 같은 JSON 을 넣음. insert(`debug:false` 포함) -> `{'insert_id': False, 'error': 'table Modems has no column named debug'}`, find(conditions `{"debug": false}`) -> `no such column: debug`, update -> `no such column: debug`. `debug` 키를 빼면 insert_id 3 으로 정상.
- 확인 수준: 재현 (Python 쪽 호출로 PHP 요청을 모사. php 는 설치되어 있지 않아 PHP 자체 실행은 안 함)

### R4F-02 | 낮음 | bridge_cli 인자 모드는 예외를 처리하지 않고, PHP 의 빈 배열이 JSON `[]` 가 되어 `.items()` 에서 죽음
- 위치: src/namifax/db/bridge_cli.py:888-893 (인자 모드에 try/except 없음), :113 (`fr.process_form(req.get("data", {}))`), common/FormRulesBridge.php processForm
- 증상: PHP `json_encode(array())` 는 `{}` 가 아니라 `[]` 입니다. 빈 `$_POST` 로 `processForm` 을 부르면 `post_data.items()` 에서 AttributeError 가 나고, 인자 모드(PHP 가 쓰는 방식)는 트레이스백만 stderr 로 나가 `shell_exec` 출력이 비어 PHP 는 false 만 받습니다. 스트림 모드는 같은 오류를 `{"error": str(e)}` 로 내보내 두 모드의 계약이 다릅니다. `find` 의 빈 `conditions` 도 `[]` 로 들어옵니다.
- 재현: `handle_request({"action":"validate_form","rules":[{"varname":"a","required":True}],"data":[]})` -> `AttributeError: 'list' object has no attribute 'items'`.
- 확인 수준: 재현

### R4F-03 | 낮음 | FileUploadBridge: 무작위 파일명이 호출마다 다시 만들어져 PHP 가 아는 이름과 저장된 이름이 다르고, set_name 은 전달되지 않음
- 위치: src/namifax/common/FileUploadBridge.php:54 (set_name), :63 (set_randname), :107 (movefile), src/namifax/db/bridge_cli.py:149-169
- 증상: load_file 과 movefile 이 각각 새 python 프로세스를 띄우고 매번 `set_randname` 을 다시 부릅니다. `get_name()` 은 첫 호출의 이름을, 실제 저장은 둘째 호출의 이름을 씁니다. `set_name($filename)` 으로 정한 이름은 `upload_process` 요청에 실리지 않아 저장에 반영되지 않습니다.
- 재현: 같은 file_info 로 `upload_process`(randname=True) 를 두 번 호출 -> 이름 `144556b55a.txt` 와 `07521b4c8a.txt`. dest_dir 에는 두 번째 이름의 파일만 생김.
- 확인 수준: 재현

### R4F-04 | 중간 | AFUserAccountBridge: 캐시된 dbdata 로 update() 하면 이미 바꾼 비밀번호가 옛 해시로 되돌아감 (R3C-11 의 PHP 쪽 변형)
- 위치: src/namifax/services/AFUserAccountBridge.php:81 (update), change_password (dbdata 의 password 를 갱신하지 않음)
- 증상: PHP 객체는 로그인/로드 시 받은 행 전체(비밀번호 해시 포함)를 `dbdata` 에 들고 있고, `change_password` 는 별도 프로세스로 DB 만 바꾸고 `dbdata['password']` 는 그대로입니다. 이후 `update()` 가 옛 해시를 포함한 전체 행을 보내 비밀번호가 원복됩니다. (레거시는 같은 객체 안에서 상태가 갱신됨.)
- 재현: 사용자 생성 -> load 로 `values` 확보 -> change_password("NewPass2!") -> 확보한 values 로 update -> 새 비밀번호 로그인 False, 옛 비밀번호 로그인 True.
- 확인 수준: 재현 (Python 브리지 호출로 PHP 호출 순서를 모사)

### R4F-05 | 낮음 | FaxPDFArchiveBridge: PHP 가 기대하는 `m_archstamp` 키를 브리지가 보내지 않아 보관일시, 수정일시가 항상 NULL
- 위치: src/namifax/services/FaxPDFArchiveBridge.php:339-344 (load_vals), src/namifax/db/bridge_cli.py:612-633
- 증상: Python `load_vals` 는 `m_archstamp`, `m_lastmoddate` 를 dbdata 에서 pop 하므로 브리지가 보내는 `data` 에는 이 키가 없습니다. 브리지는 최상위 `archstamp`, `lastmoddate` 를 따로 보내지만 PHP 는 읽지 않습니다. 따라서 PHP 의 `get_archstamp()`, `get_lastmoddate()` 는 항상 NULL 입니다.
- 근거: archive_base.py:567-571 (pop 후 dbdata = raw), FaxPDFArchiveBridge.php:340.
- 확인 수준: 코드 확인

### R4F-06 | 낮음 | create_thumbnails, ocr_import 가 레거시의 `$INSTALLDIR` 접두어를 빼먹어 경로가 현재 디렉터리 기준이 됨
- 위치: src/avantfax/cli/create_thumbnails.py:42-46, src/avantfax/cli/ocr_import.py:53 (레거시: tools/create_thumbnails.php:42 `$INSTALLDIR.$fax->get_thumbnail()`, tools/ocr_import.php:44 `$INSTALLDIR.$archive->get_tiffpath()`)
- 증상: `get_thumbnail()`, `get_tiffpath()` 는 DB 의 상대 경로(`faxes/...`)를 그대로 돌려줍니다(archive_base.py:573-576). Python 판은 설치 디렉터리를 붙이지 않아 `os.path.isfile` 이 cron 의 작업 디렉터리 기준으로 평가됩니다. 설치 디렉터리에서 실행하지 않으면 이미 있는 썸네일도 "없음"으로 보고 전부 다시 만들며, 만들 때도 상대 경로에 씁니다. ocr_import 는 TIFF 를 열지 못합니다. (F4-10 의 데이터 이전 경로 문제와는 별개로, 신규 CLI 자체의 누락.)
- 확인 수준: 코드 확인 (레거시 소스와 줄 대조)

### R4F-07 | 중간 | 폴백 웹앱의 쿼리 파라미터 파싱 예외가 처리되지 않아 서버 오류가 됨
- 위치: src/namifax/web/app.py:111-112, 117-118 (`int(query_params.get("page", 0))`, `int(...limit...)`), 같은 파일이 src/avantfax/web/app.py 에도 있음
- 증상: `page=x`, `limit=abc` 는 ValueError, `limit=0` 은 InboxHandler.list_inbox 의 `math.ceil(total / limit)` 에서 ZeroDivisionError 가 납니다. 라우터에 try/except 가 없어 JSON 오류가 아니라 WSGI 서버의 500 이 됩니다. (R3F-04 의 무한 루프와는 다른 입력.)
- 재현: 폴백 앱에 세션을 직접 만들어 호출: `/api/inbox/list?page=x` -> ValueError, `?limit=0` -> ZeroDivisionError, `/api/archive/search?page=-5&limit=abc` -> ValueError. (`/api/auth/logout` 은 GET 으로도 세션을 지움.)
- 확인 수준: 재현

### R4F-08 | 낮음 | 수신함 뷰에 테스트용 `?empty=1` 스위치가 운영 코드로 남아 있음
- 위치: src/namifax/views/inbox.py:22 (`if not request.params.get("empty"):`)
- 증상: 로그인한 사용자가 `/inbox?empty=1` 을 열면 DB 에 팩스가 있어도 빈 수신함이 표시됩니다. 골든 W04 와 tests/web/test_web_inbox_views.py:47 은 이 훅에 기대어 "빈 상태"를 검증하므로, 실제로 비어 있는 DB 에서의 빈 상태는 어디서도 검증되지 않습니다.
- 재현: 시드 팩스 1건이 있는 DB 에서 `/inbox` 는 목록, `/inbox?empty=1` 은 "There are no incoming faxes..." 를 표시.
- 확인 수준: 재현

### R4F-09 | 중간 | 골든 마스터의 required_text 를 통과시키려고 템플릿에 눈에 안 보이는 문구를 심어 둠
- 위치: src/namifax/templates/inbox.jinja2:8 (`<span class="sr-only">- NamiFAX - Inbox 0 FAXES MODEM IDLE ttyS0</span>`), login.jinja2:14 (`:: AvantFAX LOGIN :: AvantFAX 3.3.5`), archive.jinja2:8 (`Archive Search Categories Results`)
- 증상: 이 문구는 계약의 required_text 토큰을 그대로 나열한 것입니다. 스크린리더 사용자에게는 팩스가 있어도 매번 "0 FAXES ... IDLE ttyS0" 라고 읽혀 거짓 정보가 되고(번역도 안 됨), 골든 검사는 화면에 없는 문구로 통과합니다. `.sr-only`/`.hidden` 요소와 주석, script/style 을 제거한 가시 텍스트로 W01, W04 를 다시 검사하면 ':: AvantFAX LOGIN ::' (W01), 'MODEM', 'IDLE' (W04) 이 사라집니다. 즉 W01, W04 의 해당 계약은 실제 화면이 아니라 숨은 문구가 충족하고 있습니다. W04 의 `"0 FAXES" in res.text` 단언도 팩스가 있는 정상 수신함에서 이미 참입니다(숨은 span 때문).
- 재현: 가시 텍스트만 추출하는 스크립트로 W01~W68 required_text 를 대조 (XML 응답의 태그 이름 항목은 제외).
- 확인 수준: 재현

### R4F-10 | 중간 | 이메일북 빈 목록 안내문이 9개 로케일에서 `\"` 를 글자 그대로 표시
- 위치: src/namifax/locale/{de,el,es,fr,it,pt_BR,pt_PT,ro,tr}/LC_MESSAGES/namifax.po 와 .mo (msgid "No email contacts found in the directory. Click \"+ New Contact\" to register one.", 사용처 templates/emailbook.jinja2:72)
- 증상: msgstr 에 백슬래시가 이중으로 들어가 실제 번역 문자열이 `... Klicken Sie auf \"+ Neuer Kontakt\", um ...` 처럼 백슬래시와 따옴표를 그대로 포함합니다.
- 재현: 각 로케일의 .mo 를 gettext 로 로드해 해당 msgid 를 번역하면 `'\\"+ Neuer Kontakt'` 처럼 백슬래시가 남아 있음 (9개 로케일). 원인은 번역 JSON 을 .po 에 주입하는 populate_missing_translations.py 가 키만 이스케이프 변형을 만들고 값은 그대로 쓰는 구조(줄 38-46)로 보임.
- 확인 수준: 재현 (원인은 추정)

### R4F-11 | 낮음 | populate_all_locales.py 의 레거시 가져오기 범위가 좁고, 스크립트 설명과 산출물이 서로 맞지 않음
- 위치: src/namifax/cli/populate_all_locales.py:42-52 (parse_php_lang 정규식), :112-120 (en 처리)
- 증상: 정규식이 `$LANG['KEY'] = "...";` 한 줄 형태만 읽어, 레거시 en.php 에서 33줄(월 이름 배열 MONTHS, FAX_FILETYPES, UPLOAD_CONTACTS 등 배열, 상수 연결, 줄 끝 주석이 있는 줄)을 건너뜁니다. 월, 요일 이름은 가져오지 못합니다. 또 스크립트는 "en 의 msgstr 은 비워 둔다"고 하지만 커밋된 en/namifax.po 는 454개 항목 모두 msgstr 이 msgid 와 같아(번역 455건) 스크립트를 다시 돌리면 산출물이 달라집니다(재현 불가능한 카탈로그).
- 재현: en.php, de.php, ja.php 에서 정규식 불일치 줄 각각 33, 32, 33건. en/namifax.po 의 비어 있지 않은 msgstr 455건.
- 확인 수준: 재현

### R4F-12 | 높음 | 테스트가 클래스에 없는 메서드를 mock 해서, 운영에서 AttributeError 가 나는 경로가 통과함
- 위치:
  - tests/unit/test_pyramid_modals_action.py:91, 98 (`Mailer.send_mail` 없음), :115, 119 (`FaxQueue.create_job` 없음)
  - tests/unit/test_web_inbox.py:86 (`ArchiveIn.archivefax` 없음)
  - tests/unit/test_web_archive.py (`del_fax`, `get_results_count`, `search_results` 없음)
  - tests/unit/test_web_admin.py (`DynamicConfig.get_dynconf` 없음)
  - tests/unit/test_saml.py, test_pyramid_saml.py, test_pyramid_totp_auth.py, test_pyramid_webauthn.py (`AFUserAccount.get_username`, `load_by_username`, `create_user`, `load_user` 없음)
- 증상: `MagicMock` 은 어떤 이름이든 받아 주므로 존재하지 않는 메서드에 `return_value` 를 걸고 `assert_called` 해도 통과합니다. 실제 클래스에서 hasattr 로 확인하면 `Mailer.send_mail` False, `FaxQueue.create_job` False, `ArchiveIn.archivefax` False 입니다. 이 때문에 K03, K13, K16 의 결함이 테스트 362개를 통과합니다. 같은 방식으로 `ab_inst.loadbyfaxnum.return_value = True` (test_cli_faxrcvd.py:74, test_web_outbox.py:34)는 실제가 튜플(COR-05)을 돌려주는 계약과 다릅니다.
- 재현: tests 의 `X.attr.return_value|side_effect|assert_called*` 에서 attr 이름을 뽑아 src/namifax 에 정의된 이름과 대조하는 스크립트: 정의되지 않은 이름 `archivefax, create_job, create_user, del_fax, get_dynconf, get_results_count, search_results, get_username, load_by_username, load_user` (boto3, smtplib, socket 의 정당한 외부 이름은 제외) 와 hasattr 확인.
- 확인 수준: 재현

### R4F-13 | 중간 | 테스트 간 전역 DB 공유로 순서 의존 (원인 쌍 규명, F5-08 의 구체화)
- 위치: tests/unit/test_web_ajax.py:85 (`test_ajax_archive_fax`), tests/unit/test_cli_tools.py:26 (`test_create_thumbnails_empty_archive`)
- 증상: `test_ajax_archive_fax` 가 기본(전역) 엔진의 시드 팩스를 보관함으로 옮기고, `test_create_thumbnails_empty_archive` 는 같은 전역 DB 가 "비어 있음"을 가정합니다. 무작위 순서 9회 중 seed2 에서 실패, 기본/역순/나머지 seed 에서는 통과해서 CI 에서 간헐 실패로 보입니다.
- 재현: `tests/unit/test_web_ajax.py` 다음에 `tests/unit/test_cli_tools.py::test_create_thumbnails_empty_archive` 를 실행하면 실패 (다른 67개 파일을 앞에 두면 모두 통과해 원인 쌍으로 특정).
- 확인 수준: 재현

### R4F-14 | 낮음 | `test_i18n_cli_compile` 이 작업 트리의 .mo 를 다시 써서 오래된 .mo 를 가려 줌
- 위치: tests/test_i18n.py:124, src/namifax/cli/i18n.py:35-38
- 증상: 테스트가 `run_i18n(["compile"])` 로 `src/namifax/locale/*/LC_MESSAGES/*.mo` 24개(추적 파일)를 실제로 덮어씁니다. .po 만 고치고 .mo 를 컴파일하지 않고 커밋해도 같은 테스트 실행이 .mo 를 갱신해 버려 그 뒤의 번역 단언이 통과합니다. 번역 단언은 4개 문자열만 확인합니다(test_translation_multilingual).
- 재현: 테스트 실행 전후로 ko .mo 의 mtime 이 변경됨 (08:57 -> 09:05).
- 확인 수준: 재현

### R4F-15 | 낮음 | 항상 참이거나 아무것도 증명하지 못하는 assert
- 위치: tests/unit/test_web_ajax.py:82 (`";" in res.text or res.text.isalnum() or len(res.text) > 0`), tests/unit/test_pyramid_modals_action.py:33 (`res.get("title") == "..." or res.get("status") == "deleted"`), tests/unit/test_pyramid_admin_crud.py:50 (`res["message"] is not None or "NewCategory" in str(res)`), tests/unit/test_web_ajax.py:93 (`test_ajax_archive_fax` 는 상태 200 만 확인하는데 뷰는 항상 200, R3B-20), tests/web/test_web_inbox_views.py:49 (`"0 FAXES" in res.text` 는 R4F-09 때문에 항상 참), 그 밖에 `assertIsNotNone`/`is not None` 만으로 끝나는 테스트 약 60곳(test_pyramid_admin_crud.py 에 20곳, test_did, test_modem, test_covers, test_categories, test_barcode 등)
- 증상: `or` 로 이어진 조건은 앞이 거짓이어도 뒤가 참이면 통과하고, `is not None` 은 가짜 기본값(F4-16)이어도 통과합니다.
- 확인 수준: 코드 확인

### R4F-16 | 중간 | 결함을 정답으로 고정한 테스트 (K15, F5-06 의 구체 목록)
- 위치와 고정된 내용:
  - tests/unit/test_pyramid_authorization.py:35-42: 로그인하지 않은 요청에 원시 JSON 401 이 정답 (UI-06). 줄 20-33 은 `/` 를 로그인 없이 200 으로 공개하는 것을 정답으로 고정 (R3A-12).
  - 같은 파일 줄 44-52: DB 에 없는 `user_id=10` 의 임의 Bearer 세션이 `/inbox` 에 200 이면 통과 (F3-11, 비활성/삭제 계정에도 세션 유효). 실제 쿠키/로그인 경로는 쓰지 않고 폴백 SessionManager 의 Bearer 경로만 검증.
  - tests/unit/test_web_app.py: `/` 가 "AvantFAX Modern Web System Ready" 스텁 텍스트인 것을 정답으로 고정 (R3G-01).
  - tests/web/test_web_inbox_views.py:29 와 tests/unit/test_web_ajax.py:46: "Acme Corp" 가짜 기본값(F1-11, F4-16)을 기대값으로 사용. 존재하지 않는 검색어/ID(`q=ZZZ`, `dl_id=999`, `fnid=99999`)에서도 가짜 'Acme Corp', '1234567; 9876543', 'John Doe' 가 나옴을 확인했으나 그 경로를 아예 테스트하지 않음.
  - tests/unit/test_pyramid_modals_action.py:66: `reassign.assert_called_with(5)` 는 실제 시그니처 `reassign(oldcid, newcid)` 와 다르게 인자 1개 호출을 정답으로 고정 (R3B-03).
  - tests/unit/test_cli_phb.py:72: 출력에 줄바꿈이 없는 것은 레거시와 같아 문제 아님(참고).
- 확인 수준: 코드 확인 + 일부 재현

### R4F-17 | 낮음 | 경계값과 오류 경로 테스트가 거의 없음
- 위치: tests/ 전체
- 증상: `pytest.raises`/`assertRaises` 4곳(362개 테스트 중). SQL 인젝션 문자열, 경로 탈출(`../`), 0 또는 음수 페이지 크기, 비ASCII 숫자/이름, 빈 입력, 중복 키, 동시성 시나리오를 다루는 테스트가 0건입니다. SEC-01, SEC-04, R3B-09, R3C-25 같은 결함이 테스트로 잡히지 않는 이유입니다. 서비스 테스트는 정상 경로 1~2개와 존재하지 않는 id 한 건 정도입니다.
- 근거: grep 으로 `raises` 4건, `injection|traversal|'\.\./'|UNION|<script` 는 test_validators.py 의 XSS 정화 1건뿐.
- 확인 수준: 코드 확인 (기계 집계)

### R4F-18 | 중간 | CLI 골든 마스터가 DB 없는 환경에서 기록되었고 stderr 를 비교하지 않으며 오류 출력을 끔
- 위치: golden_master/Dockerfile.legacy (mysql 드라이버만 설치, DB 서버 없음), golden_master/runner.py:266 (exp_stderr 를 읽고 쓰지 않음), runner.py:25 등 SCENARIOS 의 `-d display_errors=0`, runner.py:249 (`sys.exit(1)` 이 verify 함수 안에 있어 pytest 에서 SystemExit)
- 증상: 레거시 PHP 는 DB 없이 실행되어 DB 를 만지는 시나리오(02, 03, 14, 16)의 출력이 "아무 것도 하지 않음/빈 출력"입니다. 03 의 "SIP 번호 규칙 생성" 은 레거시도 DB 가 없어서 빈 출력이 정답으로 기록되었고, 신규 앱은 DynConf 테이블 결함(COR-08)으로 역시 아무것도 못 해도 통과합니다. `display_errors=0` 은 PHP 경고, 치명 오류를 stdout 에서 지웁니다. 기록된 stderr.txt 20개는 모두 비어 있고 비교도 되지 않습니다. meta.json 의 `target_cmd` 에 기록 시점의 `/usr/local/bin/python3` 절대 경로가 박혀 있습니다. 검증 대상은 `avantfax.cli.*` 이며 `namifax.cli.*` 가 아닙니다.
- 확인 수준: 코드 확인 + 데이터 20건 집계 (모두 exit 0, stderr 0바이트)

### R4F-19 | 중간 | 웹 골든 러너가 계약의 상당 부분을 읽지 않음
- 위치: golden_master/web_runner.py (전체), 특히 :57-59 (`meta["route"]` 만 사용, `meta.params`, `meta.expected_status` 무시), :117 (`forms[0]`), :198, :207 (브랜드 치환), :211-212 (원본 HTML 에서도 부분 문자열 대소문자 무시 일치)
- 증상: 2-2 표 참조. 검사 코드가 없는 계약 키 5종(title 50건, table_headers 5건, required_actions 1건, binary_stream 1건, set_cookie 1건), params 4건, response.html 68개 전부가 사실상 무시됩니다. required_text 는 속성값, script, 주석, 숨은 요소 안의 문자열도 일치로 인정합니다.
- 재현: `pytest golden_master` 88 passed. 계약 키 집계 스크립트로 러너가 처리하는 키(status_code, redirect_location, content_type, forms, form_structure, dynamic_states, required_links, required_text) 외 항목을 확인.
- 확인 수준: 재현

### R4F-20 | 중간 | 웹 골든 계약의 required_text 상당수가 레거시에 없는 문구 (F5-06 의 수치화)
- 위치: golden_master/web/*/contract.json, golden_master/generate_web_golden.py
- 증상: required_text 171개 중 37개(약 22%)가 레거시 소스(php, tpl, js, css, 언어 파일 전체)에서 찾아지지 않습니다. 예: W02 'Invalid username or password' (레거시 언어 파일은 LOGIN_INCORRECT = "Incorrect username or password. Please try again."), W05 'Acme Corp'와 '2026-09-29' (신규 앱 시드/가짜 기본값), W58 'Sales Inbound' (시드 데이터), W04 '0 FAXES', W18 'Server Status', W64 'Configure User' 등. 따라서 "레거시와 동일한 화면" 보증이 아니라 "신규 앱이 지금 내는 문구" 보증이 되어, AGENTS.md 의 "레거시 디자인을 따른다" 제약을 검증하지 못합니다. views/auth.py:51 이 같은 문구를 하드코딩해(F3-22) 계약과 구현이 서로를 정당화합니다.
- 재현: 계약의 required_text 를 소문자로 legacy/avantfax 아래 모든 .php/.tpl/.js/.html/.css 연결 문자열에서 부분 문자열 검색: 171건 중 134건 발견, 37건 미발견 (미발견 목록은 위 예시 외 W06 'Fax Viewer', W09 'Destination Number', W20 'Configure Modems', W36 'Transmission Report' 등).
- 확인 수준: 재현 (검색은 대소문자 무시 부분 문자열이라 번역 파일 안의 변형 표기는 놓칠 수 있음)
