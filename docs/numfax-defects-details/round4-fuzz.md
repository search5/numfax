# 4라운드 기계적 입력 퍼징 결과 (R4Z)

## 개요
- 호출 수: 약 53,500회 (메인 퍼징 52,585 + 파일 파트 형식 위반 스윕 880 + 확인용 프로브 약 40). 실제 waitress 서버 확인 호출 포함.
- 라우트 72개 (ast 로 수집, 뷰 79개), 라우트-파라미터 쌍 220개, 고유 파라미터 키 129개(수집분). 추가로 id/page/fid/_LOCALE_/lang 을 전 라우트에 주입.
- 사용자: anon, 일반 사용자(DB 직접 생성 fuzzuser), admin. GET 과 POST 각각.
- 입력: 빈 문자열, 공백, 0, -1, 99999999999999999999, '²', '٣', 한글+이모지, 10만자, NUL 포함, 같은 키 중복, `key[]` 리스트 모양, 마커(`ZQ7<zq7>`), 경로 구분자('../x', 업로드/저장소 라우트 한정), 잘못된 JSON/Content-Type/멀티파트 본문 19종, 업로드(빈 파일, 0바이트, 30MB, 경로/유니코드/NUL/300자 파일명), 모든 텍스트 파라미터를 파일 파트로 보내기.
- 샌드박스: DB, TMPDIR, 아카이브, 커버, HOME, cwd 모두 scratchpad/agent-r4-fuzz/ 하위. 라우트×사용자 단계마다 사전 DB 스냅샷으로 복원. 최대 디스크 사용 1GB 미만, 최대 RSS 242MB.
- 스크립트: scratchpad/agent-r4-fuzz/ (collect.py, fuzz.py, filepart.py, probe.py, probe2.py, routes.json, results.json, run.log)

### 응답 분포 (메인 퍼징 52,585회; 예외는 WSGI 밖으로 전파된 파이썬 예외 = 운영에서는 500)
| 사용자 | 200 | 302 | 400 | 401 | 403 | 404 | 예외(500) |
|---|---|---|---|---|---|---|---|
| anon (GET+POST) | 4,032 | 746 | 197 | 11,985 | 0 | 198 | 365 |
| user | 8,131 | 1,927 | 197 | 0 | 5,925 | 198 | 1,153 |
| admin | 13,657 | 2,277 | 197 | 0 | 0 | 198 | 1,202 |
| 합계 | 25,820 | 4,950 | 591 | 11,985 | 5,925 | 594 | 2,720 |

예외 2,720건의 대부분은 이미 알려진 결함(K02 request.session 부재 → /login/totp 1,182건 근처, K03 load_by_username 부재 → WebAuthn 계열 약 2,000건)이다. 그 외 신규 원인은 아래 R4Z 항목과 "영향 라우트 추가" 절에 정리한다.

### 항목별 점검 결과
- 응답 5초 초과: 0건. 10만자 입력은 모두 1초 미만이었고 SQLite LIKE 가 오류로 실패해 빈 결과로 끝남(R4Z-04).
- 멈춤/메모리 급증: 없음 (RSS 최대 242MB, 30MB 업로드 후에도 회복).
- DB 깨짐: 216개 단계 모두 integrity_check ok, 잠금 없음. 부분 저장은 R4Z-03 한 건.
- 응답 본문 스택 트레이스 노출: 0건 (예외는 모두 전파되어 500 으로 끝나므로 본문 노출은 없음).
- 이스케이프 없는 반영: /ajax/deletefaxes fids (SEC-04 기존, text/html). /faxes/rotate/{fid}, /rotate 는 JSON(application/json)에 fid 가 그대로 들어가지만 JSON 타입이라 실행 불가여서 결함으로 올리지 않음(USR-05 계열).
- 고아 파일: sendfax 업로드 임시 파일이 요청마다 남음(F2-10 기존). 그 외 라우트에서 고아 파일 없음. 파일명 '../../x.pdf', '/abs/x.pdf' 는 basename 처리로 탈출하지 않음. 파일명 '..\\..\\x.pdf' 는 리눅스에서 그대로 파일명이 되어 탈출 없음.

## 신규 결함

### R4Z-01 [높음] 텍스트 파라미터에 멀티파트 파일 파트를 보내면 40개 라우트가 500
- 영향 라우트 40개: login, forgot, pwdexpired, saml_acs, api_webauthn_auth_options (인증 전 5개 포함), inbox, viewfax, sendfax, outbox, archive, addressbook, addressbook_edit, distrolist, distrolist_edit, emailbook_edit, settings, modal_assign, modal_email, modal_note, modal_refax, ajax_book, ajax_emailbook, ajax_archivebook, ajax_archivefax, ajax_faxalter, ajax_deletefaxes, setcompany, popup_distrolist_helper, admin_users, admin_modems, admin_routing_did, admin_did, admin_barcodes, admin_covers, admin_categories, admin_dynconf, admin_fax2email, admin_syslog, admin_system_logs, admin_saml.
- 원인 위치: `request.params.get(...)` 값이 문자열이라고 가정하는 모든 곳. 대표 위치: views/auth.py:33, auth.py:129, auth.py:160, services/user_account.py:24 (password 가 bytes 로 오면 md5_hash 의 encode 에서 AttributeError), views/archive.py:18-19, addressbook.py:45,67,146-151, modals.py:25-27,78-81,128,180-182, helpers.py:20, ajax.py:69,109,210,228,288,321, settings.py:43,65, admin.py:188-197,259-269,394,426-432,518-524,588-591,659-665,744-751,1193-1197, sendfax.py:86,112, outbox.py:20, inbox.py:22,152, saml.py:40-41, webauthn.py:88. 공통 헬퍼 없이 `.strip()`/`.isdigit()`/`bool()` 을 FieldStorage 에 직접 호출함. 템플릿에서도 `form_data` 로 되돌려 보내다 settings.jinja2:60-97, archive.jinja2:53,61, viewfax.jinja2:17 에서 TypeError.
- 재현 입력: `multipart/form-data` 로 해당 필드 이름에 파일 파트(`filename="a.txt"`) 하나. 예: `POST /login` 에 `username` 을 파일 파트로, `POST /archive` 에 `search` 를 파일 파트로.
- 확인 수준: webtest 로 재현(예외 전파 = 운영 500). 인증 전 /login, /forgot, /pwdexpired 에서도 재현되어 비인증 500 유발 가능. 영향: 로그 오염과 오류 페이지 노출 정도(낮은 영향이지만 범위가 넓음).

### R4Z-02 [중간] fax_download 가 fid/format 을 Content-Disposition 헤더에 검증 없이 넣어 CR/LF, 비 latin-1 문자에서 500, NUL 은 통과
- 영향 라우트: 1개 (/faxes/download/{fid}). F1-15 는 format 값만 지적했으므로 여기서는 경로 파라미터 fid 와 실제 서버에서의 동작을 추가로 보고한다.
- 원인 위치: views/inbox.py:125 (`f'inline; filename="fax_{fid}.{fmt}"'`), fid 는 inbox.py:104 부근 matchdict.
- 재현 입력: `GET /faxes/download/1%0d%0aX-Injected:%20y` → 실제 waitress 에서 500 (웹 계층 자체는 개행을 걸러내지 않아 헤더 목록에 `X-Injected` 가 들어가고, 개행을 거부하는 서버에서만 막힘). `GET /faxes/download/한글😀` 및 `?format=€` → waitress 500 (UnicodeEncodeError latin-1). `/faxes/download/a%00b` → 200 이고 헤더에 NUL 포함.
- 확인 수준: 실제 waitress 서버에 raw HTTP 로 확인(500 3건, NUL 통과 1건).

### R4Z-03 [중간] /admin/fax2email 생성이 회사 행만 남기고 팩스 행 저장은 실패하는데 성공 화면 (부분 저장)
- 영향 라우트: 1개.
- 원인 위치: views/admin.py:740 부근 admin_fax2email_view 의 create 분기. AddressBook 행(company 만, email 은 NULL)을 INSERT 한 뒤 AddressBookFAX INSERT 가 `table AddressBookFAX has no column named faxfrom` 로 실패해도 롤백이나 오류 표시가 없음. COR-06 은 컬럼 부재 자체를, 이 항목은 그 결과로 남는 부분 저장(회사 행만 존재, 입력한 email 소실)을 다룬다.
- 재현 입력: admin 로그인 후 `POST /admin/fax2email` `create=1&company=ProbeCo&email=a@b.co` → 200, AddressBook 에 (3, 'ProbeCo', 나머지 NULL) 만 추가되고 AddressBookFAX 변동 없음. 퍼징에서는 create 요청마다 빈 회사가 쌓임(2→6).
- 확인 수준: DB 직접 조회로 확인.

### R4Z-04 [낮음] NUL 문자 또는 10만자 입력이 SQL 오류로 조용히 삼켜져 성공/빈 결과 응답
- 영향 라우트 13개: login(username), ajax_book, ajax_archivebook, admin_syslog, admin_system_logs, archive, popup_distrolist_helper, modal_note, admin_covers, admin_categories, admin_dynconf, admin_fax2email, (SQLite 의 `LIKE or GLOB pattern too complex` 는 ajax_book, ajax_archivebook, admin_system_logs, admin_syslog).
- 원인 위치: db/engine.py:109-140 의 `query()` 가 예외를 `_error` 에 넣고 `executed=False` 만 반환, 호출 쪽(예: views/admin.py 의 create 분기, modals.py:128 부근 note 저장)이 결과를 확인하지 않음. 값 검증 없이 `quote()` 로 SQL 문자열에 보간(COR-11 과 동일 계열)되어 `the query contains a null character` 가 발생.
- 재현 입력: `POST /note fid=1&description=a%00b` → 200 (저장 실패를 알리지 않음), `POST /admin/categories create=1&name=a%00b` → 200, `GET /ajax/book?q=<10만자>` → 빈 결과.
- 확인 수준: 실제 waitress 요청과 SQL 로그로 확인. USR-03, COR-22 와 원인이 겹치므로 우선순위는 낮음.

### R4Z-05 [낮음] /admin/covers 의 `file` 필드가 업로드 파트일 때 500 (R4Z-01 의 admin 변형이 아니라 신규 업로드 경로)
- 영향 라우트: 1개. 같은 원인이 R4Z-01 에 포함되므로 별도 번호는 두지 않고 R4Z-01 의 admin.py:426-451 항목으로 합칠 수 있음. (참고용 기재)
- 원인 위치: views/admin.py:443,451. 화면의 `file` 은 파일 입력이 아니라 텍스트 입력인데, 업로드 파트를 보내면 `.strip()` 에서 AttributeError.
- 확인 수준: webtest.

## 기존 결함에 영향 라우트 추가
- R3A-01 (유니코드 숫자 isdigit→int 500): 관리자 화면 외에 추가 라우트 7개 — admin_modems(faxcatid, admin.py:193), admin_routing_did 와 admin_did(didr_id:259, faxcatid:267), admin_barcodes(barcode_id:585), admin_covers(cover_id:426), admin_categories(catid:518), admin_dynconf(dynconf_id:659), admin_fax2email(c_id:745). R3B-09 의 /archive faxid(archive.py:61)는 일반 사용자 계정에서도 재현됨.
- F2-09 (긴 파일명 500): 같은 위치(sendfax.py:107)에서 파일명에 NUL 문자가 있어도 `ValueError: embedded null byte` 로 500. 확인 수준 webtest.
- UI-28 (GET 으로 상태 변경): `GET /distrolist?dl_id=1&delete=1` 이 배포목록을 삭제하고 302 (distrolist.py:46-49). 다른 delete 계열은 GET 쿼리로는 삭제되지 않음(addressbook_edit, emailbook_edit, modems, did, modal_delete 는 GET 불변).
- COR-11 / SEC-01 / ADM-02 (SQL 문자열 보간): 마커가 SQL 문자열에 그대로 들어간 라우트가 추가로 발견됨 — login(username), archive(search, date_from, date_to), modal_note(description), admin_covers/admin_categories/admin_dynconf/admin_fax2email 의 create(title, name, callid 등). ajax_book, ajax_archivebook, admin_system_logs 는 기존. 작은따옴표는 `''` 로 이스케이프되고 있어 SQLite 에서는 구문 변경은 보내지 않았으며, 로그 문자열로만 확인.
- ADM-30: `POST /admin/covers` 의 `file=../x` 가 그대로 DB 에 등록됨(경로 검증 없음).
- K02/K03: 예외의 최다 원인(약 2,700건 중 대부분). 신규 라우트 추가 없음.

## 결과 요약
- 신규 결함 5건 (R4Z-05 는 R4Z-01 에 흡수 가능). 심각도: 높음 1, 중간 2, 낮음 2.
- 기타: 응답 지연, 메모리, DB 손상, 스택 트레이스 노출, 스크립트 실행 가능한 반사는 신규로 발견되지 않음.
