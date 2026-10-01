# 3라운드 A (파일 단위 정독) 결과

## 읽은 파일과 줄 수 (src/namifax 기준, 전부 처음부터 끝까지 정독)
- views/admin.py 1227줄
- views/settings.py 85줄
- views/auth.py 180줄
- views/forbidden.py 39줄
- views/notfound.py 7줄
- views/default.py 10줄
- security.py 180줄
- routes.py 100줄
- __init__.py 58줄
- main.py 203줄
- i18n.py 110줄
- 보조로 읽음: web/session.py, services/user_account.py, services/covers.py, services/did.py, services/addressbook.py 일부, services/printer.py 일부, db/engine.py 일부, 레거시 admin/fax2email.php, fax2email_edit.php, conf_modems_edit.php, system_logs.php
- 실행 환경: NAMIFAX_DB_PATH=.../scratchpad/agent-r3-a/r3a.db (CLI 는 cli.db). 저장소 소스는 수정하지 않음.

## 확인했으나 새 결함이 아니라고 판단한 것 (known3.md 와 중복)
- 관리자 4종 화면의 request.db 부재(K01), 세션 팩토리 부재(K02), 시드 덮어쓰기(COR-02), 사용자 삭제 실패(ADM-03), 바코드 PK(ADM-07), DynConf(ADM-08), sysfunc 가짜 동작(ADM-10), 폼 검증 오류 은폐(USR-03, F3-25, ADM-22), 설정 화면 미저장(UI-01), 로그인 하드코딩(K10), 비밀번호 만료 미강제(SEC-05), pwdexpired/forgot 스텁(F4-02/03), 로그인 next 유실(F3-22), JSON 401(UI-06), 서버 인자 무시(F5-23), 프린터 int 500(ADM-25).
- 시스템 로그 날짜 필터의 부분 조합 무시는 레거시도 같은 의미이므로 결함으로 보지 않음.

---

## R3A-01 [중간] 유니코드 숫자("²")가 isdigit() 검사를 통과해 int() 에서 500
- 위치: views/admin.py:259, 267, 426, 430, 518, 522, 585, 593, 659, 663, 745, 749, 762 (did_id/cover_id/catid/barcode_id/dynconf_id/c_id 와 faxcatid 파싱). 모뎀은 193행.
- 증상: `str(x).isdigit() and int(x)` 패턴인데 "²", "³" 같은 위 첨자 숫자는 isdigit() 가 True 이고 int() 는 ValueError. 관리자 CRUD 6개 화면이 GET 쿼리스트링 하나로 500 이 난다. POST 의 faxcatid 도 모뎀, DID, fax2email 에서 500.
- 재현: 로그인 후 `GET /admin/routing/did?didr_id=²`, `/admin/covers?cover_id=²`, `/admin/categories?catid=²`, `/admin/barcodes?barcode_id=²`, `/admin/dynconf?dynconf_id=²`, `/admin/fax2email?c_id=²` 모두 ValueError 로 예외. `POST /admin/modems {device:x9, alias:y9, faxcatid:²}`, `POST /admin/routing/did {faxcatid:², ...}`, `POST /admin/fax2email {c_id:1, save:1, faxcatid:²}` 도 ValueError.
- 확인 수준: 재현

## R3A-02 [낮음] 사용자 관리 화면의 DID 권한 체크박스에서 라우트 번호가 비어 표시됨
- 위치: views/admin.py:158-161, 177 (did.list_all() 원본 행을 그대로 전달), templates/admin_users.jinja2:144 (`{{ route.route }}`)
- 증상: DID 화면(310-312행)은 `routecode` 를 `route` 로 별칭을 붙이지만 사용자 화면은 이 보정이 없다. 키는 `routecode` 인데 템플릿은 `route.route` 를 써서 "- Main Trunk", "- Accounting Direct" 처럼 번호 없이 표시된다.
- 재현: `GET /admin/users` 응답에서 `didrouting[]` 체크박스 옆 문구가 `<span> - Main Trunk</span>`.
- 확인 수준: 재현

## R3A-03 [중간] 저장소/SMTP 화면의 숫자 입력 오류가 500 이 되거나 내부 예외 문구를 그대로 노출
- 위치: views/admin.py:1077-1078 (storage save_lifecycle 의 `int(...)`), 937 (smtp test 의 `int(params.get("smtp_port"))`), 931-932 (`error = str(exc)`)
- 증상: 보관 일수에 "abc" 를 넣으면 ValueError 로 500. SMTP 테스트 포트에 "abc" 도 500. SMTP 저장에서는 같은 오류가 잡히지만 화면에 `invalid literal for int() with base 10: 'abc'` 같은 파이썬 예외 문구가 그대로 나온다. ADM-11(음수 일수), ADM-18(SMTP 검증 부족), ADM-25(프린터 500)와 다른 화면/경로.
- 재현: `POST /admin/storage {action:save_lifecycle, purge_tiff_after_days:abc}` -> ValueError. `POST /admin/smtp {action:test, smtp_port:abc}` -> ValueError. `POST /admin/smtp {action:save, smtp_port:abc, smtp_host:h}` -> 200 이고 본문에 예외 문구.
- 확인 수준: 재현

## R3A-04 [중간] `namifax phb` 서브커맨드가 어떤 경우에도 실패함
- 위치: main.py:26(import `main as run_phb`), main.py:~183 (`elif cmd == "phb": return run_phb()`), cli/phb.py:79-80
- 증상: USAGE 에 있는 `namifax phb` 는 인자를 넘기지 않고 `run_phb()`(= phb.main, sys.argv 를 그대로 파싱)를 호출한다. sys.argv 에는 "phb" 가 들어 있어 argparse 가 `unrecognized arguments: phb` 로 종료 코드 2. `-o` 를 줘도 마찬가지. `namifax-phb` 콘솔 스크립트만 동작한다.
- 재현: `namifax phb` -> `namifax: error: unrecognized arguments: phb`, rc=2. `namifax phb -o out` 도 동일. `namifax-phb -o out` 은 파일 생성.
- 확인 수준: 재현

## R3A-05 [낮음] 일부 서브커맨드가 `--help` 를 해석하지 않아 실제 작업을 실행하거나 파일명으로 처리
- 위치: main.py:166-180 (ocr-import, create-thumbnails, import-users, import-blacklist 분기), USAGE 의 "Run 'namifax <command> --help'" 안내
- 증상: `namifax create-thumbnails --help` 는 도움말 없이 "No faxes found / Done" 으로 썸네일 일괄 생성 배치를 실제로 실행한다(데이터가 있으면 전량 처리). `import-users --help`, `import-blacklist --help` 는 "File not found: --help". `ocr-import --help` 는 OCR 미활성 문구만 출력. `dynconf --help` 는 무출력 종료코드 0. F5-23(serve/scheduler) 과 별개의 서브커맨드.
- 재현: NAMIFAX_DB_PATH 를 지정한 상태에서 각 명령을 `--help` 로 실행하여 출력 확인.
- 확인 수준: 재현

## R3A-06 [중간] fax2email 의 "삭제"가 회사 행만 지우고 팩스번호와 아카이브 참조를 고아로 남김 (레거시는 예약 회사로 재배정)
- 위치: views/admin.py:751-756 (`ab.delete_cid(cid)` 만 호출), 레거시 admin/fax2email_edit.php:66-78 (RESERVED_FAX_NUM 회사로 `farchive->reassign` + `addressbook->reassign`)
- 증상: 회사 1곳을 삭제하면 AddressBook 행만 사라지고 AddressBookFAX(팩스번호, 이메일, 프린터 규칙)와 FaxArchive.companyid 는 그대로 남는다. 삭제된 회사의 팩스번호가 계속 수신 매칭에 걸려 존재하지 않는 회사로 귀속된다. 레거시 주석은 "팩스의 흔적을 잃지 않기 위해 예약 번호로 재배정"이라고 명시. RESERVED_FAX_NUM 은 파이썬 트리 어디에도 없다. 같은 패턴이 views/addressbook.py:72 에도 있음.
- 재현: `POST /admin/fax2email {c_id:2, delete:1}` 후 AddressBook 에서 회사 2 만 사라지고 AddressBookFAX 의 (abookfax_id=2, abook_id=2, faxnumber=9876543) 행이 남음. (COR-07 은 신규 행의 NULL abook_id 문제라 시드 행에서는 삭제 자체는 동작함.)
- 확인 수준: 재현

## R3A-07 [중간] fax2email "create" 가 주소록에 고아 회사를 만들고 성공 메시지를 표시 (회사명을 팩스번호로 사용)
- 위치: views/admin.py:778-790 (create), 773 (`ab.create_faxnumid(company)`), services/addressbook.py:176 (clean_faxnum)
- 증상: 레거시 fax2email 에는 신규 생성이 없다. 새 화면은 회사 이름을 "팩스번호"로 넘겨 create_faxnumid 를 호출한다. 이름은 숫자 정제 후 비어 "fax number missing" 으로 실패하지만 그 결과를 확인하지 않고 항상 "Fax to Email settings saved" 를 표시한다. 그 사이 `ab.create(company)` 로 만든 회사 행은 롤백되지 않아 실제 주소록에 팩스번호 없는 회사가 남는다. 저장 실패 자체(ADM-09)와 별개로 공유 주소록 오염이라는 부작용.
- 재현: `POST /admin/fax2email {company:FooCo, email:f@x.com, printer:lp, create:1}` 후 AddressBook 에 FooCo 행이 생기고 AddressBookFAX 에는 행이 없음.
- 확인 수준: 재현

## R3A-08 [낮음] fax2email 목록이 실제 회사의 빈 값을 가짜 이메일/프린터로 채움
- 위치: views/admin.py:804-811 (`email_val or "faxes@example.com"`, `printer_val or "OfficePrinter"`)
- 증상: 규칙이 없는 실제 회사(시드 회사 포함)가 전부 "faxes@example.com / OfficePrinter" 로 표시되어 관리자가 규칙이 설정된 것으로 오인. ADM-21(빈 테이블의 가짜 행)과 달리 실제 행의 빈 칸을 덮는다.
- 재현: `GET /admin/fax2email` 본문에 `faxes@example.com`, `OfficePrinter` 가 회사 수만큼 출현(3회 확인).
- 확인 수준: 재현

## R3A-09 [중간] 사용자 삭제의 admin 보호 검사("uid != 1")가 "01" 로 우회되고, 삭제 실패에도 비밀번호 이력이 지워짐
- 위치: views/admin.py:97-106 (`str(uid) != "1"` 후 `int(uid)`), services/user_account.py:367-389 (update_entry 결과와 무관하게 clear_hashes 실행 후 True)
- 증상: `uid=01`, `uid=+1`, 전각 숫자 등은 문자열 비교를 통과하고 `int()` 로 1 이 되어 `remove(1)` 이 실행된다. 현재는 소프트 삭제가 NOT NULL 로 실패(ADM-03)해 계정은 남지만 `clear_hashes(1)` 은 실행되어 관리자 비밀번호 이력이 삭제된다. ADM-03 이 고쳐지면 기본 관리자 계정이 삭제된다. 일반 사용자도 삭제 실패 후 이력만 지워진다.
- 재현: UserPasswords 에 uid 1, 2 행을 넣고 `POST /admin/users {uid:1, delete:1}` -> 이력 유지. `POST /admin/users {uid:01, delete:1}` -> uid 1 이력 삭제(계정 행은 그대로).
- 확인 수준: 재현

## R3A-10 [낮음] 모뎀 수정에서 팩스 분류(faxcatid)를 해제할 수 없음
- 위치: views/admin.py:214-215, 220-221 (`if faxcatid_val is not None`)
- 증상: 빈 값("분류 없음")을 제출해도 set_faxcatid 를 호출하지 않아 한번 지정한 분류가 영구히 남는다. 레거시 conf_modems_edit.php 는 항상 `set_faxcatid` 를 호출하며 0 => '' 선택지를 제공. DID 화면(287행)은 None 을 그대로 넘겨 해제 가능해 일관성도 깨짐. ADM-23(폼에 필드 없음)과 별개로 필드를 추가해도 해제 불가.
- 재현: `POST /admin/modems {devid:2, device:ttyS1, alias:S, faxcatid:1}` -> faxcatid=1. 이어서 `faxcatid:""` 제출 -> 여전히 1.
- 확인 수준: 재현

## R3A-11 [중간] 설정 화면의 2FA 상태 조회가 존재하지 않는 키 identity["uid"] 를 사용
- 위치: views/settings.py:70-73, security.py:84-91 (identity 는 user_id 키만 제공)
- 증상: identity 딕셔너리에는 `uid` 가 없고 `user_id` 만 있어 `identity.get("uid")` 는 항상 None. TotpService 연결 문제(F3-01)를 고쳐도 2FA 사용자의 "해제" 폼이 나타나지 않는다. 같은 이유로 settings.py:16-17, 32 의 name/email/language, modals.py 의 `identity.get("uid", 1)` 도 항상 기본값. F3-14 의 다른 원인 변형.
- 재현: UserTOTP 에 uid=1, is_enabled=1 행을 넣고 `TotpService(get_default_engine()).is_totp_enabled(1)` 은 True 인데 `GET /settings` 에는 `value="disable"` 폼이 없음. (request.db 부재 원인과 겹치므로 원인 분리는 코드 근거.)
- 확인 수준: 재현(부분) + 코드 추론

## R3A-12 [낮음] 비-GET 요청이 죽은 default.py 뷰로 가서 하드코딩 통계 홈을 공개 렌더링
- 위치: views/default.py:1-10, views/auth.py:13-14 (home 라우트 GET 전용), templates/home.jinja2
- 증상: route "home" 에 method 조건이 없는 my_view(permission public)가 등록되어 있어 `POST /`(또는 PUT 등)는 로그인 화면이 아니라 "수신함 0, 송신 큐 0, 등록 모뎀 준비됨" 같은 하드코딩된 대시보드를 인증 없이 반환한다.
- 재현: `POST /` -> 200, 본문에 "수신함 (Inbox) 0 정상 수신 팩스 즉시 조회 가능".
- 확인 수준: 재현

## R3A-13 [낮음] /admin 이 Accept 부분 문자열만으로 JSON 을 반환하고 모뎀 상태도 고정 문자열
- 위치: views/admin.py:75-77
- 증상: `"application/json" in Accept` 이거나 Authorization 헤더가 있기만 하면 q 값과 무관하게 JSON(사용자 이메일 포함)을 준다. `Accept: text/html,application/json;q=0.1` 인 브라우저성 요청도 HTML 이 아닌 JSON. JSON 의 모뎀 status 는 항상 "Running and idle".
- 재현: `GET /admin` 을 해당 Accept 로 요청 -> content-type application/json.
- 확인 수준: 재현

## R3A-14 [낮음] 시드가 SysLog 에 조작된 감사 기록을 삽입해 시스템 로그 화면이 가짜 이벤트만 보여줌
- 위치: db/schema.py:388-397 (시스템 로그 화면 views/admin.py:349-386 이 사용)
- 증상: 빈 SysLog 에 고정 날짜 2026-09-29 의 "Fax job #12 dispatched ... SUCCESS", "User 'admin' successfully authenticated from IP 127.0.0.1" 를 넣는다. 실제 이벤트는 기록되지 않으므로(F3-18) 화면에는 이 가짜 2건만 남아 감사 자료로 오인될 수 있다.
- 재현: 신규 DB 로 `GET /admin/system_logs` -> 위 2건 표시, `SELECT * FROM SysLog` 로 확인.
- 확인 수준: 재현

## R3A-15 [낮음] 권한 없는 로그인 사용자가 관리자 URL 에 접근하면 안내 없이 받은편지함으로 리다이렉트
- 위치: views/forbidden.py:26-27
- 증상: HTML 요청이면 403 이유를 전혀 알리지 않고 /inbox 로 보낸다(POST 도 동일하게 302 GET 으로 바뀌어 입력 유실). 사용자는 링크가 고장 난 것으로 인식.
- 재현: 일반 사용자 bob 으로 로그인 후 `GET /admin/users`, `/admin/smtp` (Accept: text/html) -> 302 /inbox.
- 확인 수준: 재현

## R3A-16 [낮음] SessionManager 가 "Thread-safe" 라고 적혀 있으나 락이 없어 경쟁 시 KeyError 가능
- 위치: web/session.py (get_session 의 `token not in` 후 `self._sessions[token]`, `del`), main.py ThreadingWSGIServer
- 증상: 만료 세션을 동시에 두 요청이 조회하거나 로그아웃과 요청이 겹치면 두 번째 스레드가 KeyError 로 500. F5-11(메모리 보관, 정리 안 됨)과 별개의 동시성 결함.
- 재현 방법 또는 근거: 코드 읽기(두 스레드가 같은 만료 토큰을 동시에 조회하는 경로).
- 확인 수준: 추론

---

## 요약
- 총 16건 (치명 0, 높음 0, 중간 7, 낮음 9)
- 중간: R3A-01, 03, 04, 06, 07, 09, 11
- 낮음: R3A-02, 05, 08, 10, 12, 13, 14, 15, 16
