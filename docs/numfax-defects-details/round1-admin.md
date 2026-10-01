# Round 1 결함 보고: 엔터프라이즈 기능 + 관리자 화면 (ADM)

환경: NAMIFAX_DB_PATH 를 scratchpad/agent-admin 아래로 지정. webtest.TestApp(namifax.create_app({})) 로 화면 POST 재현.
서비스 계층 결함은 연결된 DatabaseEngine 을 직접 주입하거나 기본 엔진(get_default_engine) 위에서 재현.
(관리자 CRUD 중 users, modems, did, barcodes, covers, categories, dynconf, fax2email 은 MDBOData 가 기본 엔진을 쓰므로 웹 경로에서도 실제로 DB 에 반영된다. smtp, printers, storage, saml 만 K01 영향.)
재현 스크립트: scratchpad/agent-admin/t*.py

## 치명

### ADM-01 (치명) 앱 시작 때마다 seed/migration 이 운영 데이터를 덮어쓰거나 되살림
- 위치: src/namifax/db/schema.py:278, 298-306, 310-320, 332-334, 386, 401-418 (init_database_tables 는 __init__.py create_app 과 get_default_engine 에서 매 기동 호출)
- 증상: 기동할 때마다 다음이 실행된다.
  - Modems 가 2건 미만이면 `INSERT OR REPLACE ... devid 1,2` 로 실제 모뎀(devid=1)을 ttyS0 'Sales Inbound' 로 덮어씀.
  - FaxCategory 가 2건 미만이면 Invoices, Contracts 재삽입(관리자가 삭제한 분류 부활).
  - DIDRoute 가 2건 이상이면 didr_id=1 의 alias 를 'Main Trunk' 로 강제 UPDATE.
  - DistroList dl_id=1 이름을 'Executive Team' 으로 강제 UPDATE.
  - FaxArchive fid=1 을 inbox=1, description='Monthly Financial Report' 로 강제 UPDATE, `company='Acme Corp'` 도 강제(이미 보관함으로 옮긴 실제 1번 팩스가 수신함으로 복귀하고 설명이 바뀜).
- 재현: t20.py. 모뎀 1개(ttyACM0 'Real Line')만 두고 DID 1번 이름을 변경, fid=1 보관 처리 후 init_database_tables 재호출 -> 모뎀이 ttyS0/ttyS1 두 건으로 교체, 카테고리 부활, DID alias 'Main Trunk', fid=1 설명/inbox 복원, DistroList 이름 복원.
- 확인 수준: 재현

## 높음

### ADM-02 (높음) 시스템 로그 화면 SQL 인젝션 (kw, year, month, day)
- 위치: src/namifax/views/admin.py:349-375 (get_all_syslogs, f-string 으로 LIKE 절 조립)
- 증상: kw 에 `x' UNION SELECT username, password FROM UserAccount --` 를 넣으면 사용자 계정의 비밀번호 해시가 로그 목록에 출력된다. year 도 `logdate LIKE '{year}%'` 에 그대로 들어감. 작은따옴표가 포함된 정상 검색어(`it's`)는 SQL 오류가 except 로 삼켜져 빈 결과만 나옴.
- 재현: GET /admin/system_logs?kw=x' UNION SELECT username,password FROM UserAccount -- -> 응답에 5f4dcc3b... 해시 출력 확인.
- 확인 수준: 재현

### ADM-03 (높음) 사용자 관리: 삭제가 항상 조용히 실패 (soft delete 가 NOT NULL 위반)
- 위치: src/namifax/services/user_account.py remove() (soft_del 에 username/email/password=None), schema.py UserAccount (username, password, email NOT NULL), views/admin.py:100-106
- 증상: 삭제 버튼 -> 302 로 복귀하지만 계정이 그대로 남는다. `update_entry` 가 실패(`NOT NULL constraint failed: UserAccount.username`)해도 remove() 는 결과를 무시하고 True 를 반환하고, 뷰도 예외/반환값을 전부 삼킴. userpasswords.clear_hashes 까지 실행됨.
- 재현: t3.py. bob 생성 후 delete=1 POST -> deleted=0, acc_enabled=1 유지. 직접 update_entry 시 sqlite 오류 확인(t4.py).
- 확인 수준: 재현

### ADM-04 (높음) 사용자 관리: any_modem 이 항상 1, 모뎀/DID/분류 권한이 저장되지 않음
- 위치: views/admin.py:116 (`bool(request.params.get("any_modem", True))`), 폼 admin_users.jinja2:143-169 (didrouting[], modemdevs[], faxcats[])
- 증상: (a) 체크박스를 해제하면 파라미터가 없으므로 기본값 True 가 적용되어 any_modem 을 끌 수 없음. (b) 폼의 didrouting[], modemdevs[], faxcats[] 는 뷰가 읽지 않아 어떤 제한도 저장되지 않음(모두 `checked` 로 고정 렌더링). 결과적으로 사용자별 접근 제한 기능이 동작하지 않음. inbox/archive 뷰는 get_modemdevs()/get_faxcats() 를 소비하므로 값이 NULL 이면 제한 없음/빈 목록 동작이 섞임.
- 재현: t3.py. save 시 modemdevs[]=ttyS0 전송 + any_modem 미전송 -> DB any_modem=1, modemdevs=NULL.
- 확인 수준: 재현

### ADM-05 (높음) 사용자 관리: 빈 비밀번호로 신규 사용자 생성 시 비밀번호가 'password' 로 고정, 수정 시 실패 무시
- 위치: views/admin.py:139 (`"password": password or "password"`), 폼 admin_users.jinja2:103 (placeholder "Required for new user" 이지만 required 속성 없음)
- 증상: 비밀번호 미입력 생성 시 md5('password') 계정이 생성되고 wasreset=0 이라 강제 변경도 없음(레거시는 무작위 비밀번호를 메일 발송, service.create() 에는 그 경로가 있으나 뷰가 우회). 또한 수정 시 change_password 가 길이 부족/재사용 등으로 False 를 반환해도 뷰가 무시(예: 비밀번호 'a' 입력 -> 302, 변경 안 됨, 오류 표시 없음). username/email 중복(set_username/set_email 실패)도 조용히 무시되고 redirect.
- 재현: t3.py. password="" 생성 -> password=5f4dcc3b...(md5 'password'), wasreset=0. 'a' 입력 후 해시 불변, 중복 이메일 수정 후 이메일 불변, 모두 성공처럼 302.
- 확인 수준: 재현

### ADM-06 (높음) 관리자 자기 강등/마지막 관리자 잠금 방지 없음, 권한 변경이 기존 세션에 반영되지 않음
- 위치: views/admin.py:108-130 (uid 수정), 89-107 (uid != "1" 만 삭제 보호)
- 증상: 폼에서 is_admin/superuser 체크박스가 빠진 POST(또는 사용자가 해제) 하나로 uid=1 admin 이 is_admin=0, superuser=0, can_del=0 이 됨. 마지막 관리자를 막는 검사 없음. 동시에 security.identity 는 세션에 캐시된 is_admin 을 써서 강등 직후에도 /admin 이 200 을 반환(세션 종료 후에야 잠김). 삭제 대상 제한도 uid=1 뿐이라 자기 자신(다른 관리자)을 삭제 가능.
- 재현: t15.py. 폼 없이 uid=1 save POST -> DB is_admin=0/superuser=0, 이후 같은 세션의 /admin 은 200.
- 확인 수준: 재현

### ADM-07 (높음) 바코드 라우팅 수정/삭제 불가 (PK 이름 불일치: barcode_id vs bcr_id)
- 위치: src/namifax/models/entities.py BarcodeRoute(table_id_name="barcode_id"), db/schema.py BarcodeRoute(bcr_id), services/barcode.py (get_routes 는 `SELECT barcode_id`), templates/admin_barcodes.jinja2:50 (`b.barcode_id`)
- 증상: DB 컬럼은 bcr_id 인데 서비스/뷰/템플릿은 barcode_id 사용. 목록의 Edit 링크가 `?barcode_id=` (빈 값) 이 되고, 수정/삭제는 "Failed to delete barcode rule"/"Error" 로 실패, get_routes() 는 행이 있어도 None 반환. faxrcvd 의 BarcodeRouting.load_route 는 barcode_id=None 으로 로드.
- 재현: t6.py. 삭제 POST -> 오류 문구, 행 잔존. 수정 POST 동일.
- 확인 수준: 재현

### ADM-08 (높음) 동적 설정(블랙리스트) 전체 기능 불능: 서비스가 없는 테이블 DynConf 사용
- 위치: src/namifax/models/entities.py DynConf(table_name="DynConf"), services/dynconf.py (`FROM DynConf`), db/schema.py (테이블명은 DynamicConfig), cli/dynconf.py
- 증상: 생성은 "no such table: DynConf" 로 실패("Rule could not be created"), 목록 조회는 [] 이라 가짜 행(01012345678/ttyS0)이 표시됨. DynamicConfig 테이블에 직접 넣은 규칙도 lookup() 이 False 라 `RejectCall: true` 가 출력되지 않아 차단이 동작하지 않음(fail-open). 또한 schema 의 `device TEXT NOT NULL` 이 UI 의 "전체 모뎀(빈 device)" 규칙과 충돌(추론). UI 의 "pattern" 안내와 달리 lookup 은 정확 일치만.
- 재현: t6.py, t17.py (DynamicConfig 에 INSERT 후 lookup False, create False, 오류 'no such table: DynConf').
- 확인 수준: 재현

### ADM-09 (높음) Fax2Email 관리 화면이 규칙을 저장하지 못함
- 위치: views/admin.py:760-790, services/addressbook.py create_faxnumid()/save_settings(), db/schema.py AddressBookFAX (email, printer, faxcatid 컬럼 없음)
- 증상: (a) 신규 생성은 `ab.create_faxnumid(company)` 에 회사명을 팩스번호로 넘겨 clean_faxnum 이 빈 문자열이 되어 'fax number missing' 으로 실패하는데 뷰가 무시함. (b) AddressBookFAX 에 email/printer/faxcatid 컬럼이 없어 기존 회사 수정(save)도 UPDATE 실패, 그러나 화면은 오류 표시 없음. (c) AddressBook 신규 행은 abook_id 가 NULL(PK 는 ab_id)이라 다음 재기동 때 migration 이 채우기 전까지 loadbycid/create_faxnumid 사용 불가. (d) 회사 삭제(delete_cid)가 AddressBookFAX 행과 FaxArchive.companyid 를 정리하지 않음(고아 행). 성공 메시지도 템플릿에 message 출력부가 없어 보이지 않음.
- 재현: t8.py, t9.py. NewCo 생성 -> AddressBook 행만 생성(abook_id NULL), AddressBookFAX 불변. Acme 수정 -> 이메일 미저장, 폼 재조회 시 email 빈 값. Acme 삭제 후 AddressBookFAX 행이 남음.
- 확인 수준: 재현

### ADM-10 (높음) 시스템 기능(sysfunc) 화면: 4개 버튼 모두 무동작, 메시지는 가짜
- 위치: templates/admin_sysfunc.jinja2:80-128 (버튼 name=reboot/shutdown/download_ar/download_db), views/admin.py:862-876 (`action` 파라미터만 검사, "Backup archive successfully created"/"reboot signal sent" 문구를 실제 동작 없이 설정)
- 증상: 폼 버튼 이름과 뷰가 읽는 파라미터(action) 불일치로 어떤 버튼도 동작하지 않음. 뷰의 action=backup/reboot 경로는 실제 백업이나 재부팅을 하지 않고 성공 문구만 설정하며, 템플릿에 message 출력이 없어 그 문구도 표시되지 않음. 다운로드(아카이브, DB)는 구현 자체가 없음.
- 재현: t16.py. 4개 버튼 POST -> 동일한 페이지(200) 반환, 효과 없음. action=reboot/backup -> 본문에 문구 없음.
- 확인 수준: 재현

### ADM-11 (높음) 스토리지 수명주기: 음수 일수 저장 시 모든 TIFF 즉시 삭제
- 위치: views/admin.py:1077-1083 (검증 없음, min 속성은 HTML 뿐), services/storage_lifecycle.py purge_local_tiffs (`cutoff = now - days_old*86400`), cli/cron.py `-p` 인자도 동일
- 증상: purge_tiff_after_days=-5 가 저장되고(서버측 검증 없음), 이 값 또는 `cron -p -5` 로 실행하면 cutoff 가 미래가 되어 PDF 가 있는 모든 fax.tif 가 나이에 관계없이 삭제됨. 숫자가 아닌 입력은 int() ValueError 로 500.
- 재현: t14.py (음수 저장 확인, 저장된 값 -5), 서비스 로직은 코드 확인. 삭제 동작 자체는 추론.
- 확인 수준: 재현(저장 검증 부재), 추론(삭제)

### ADM-12 (높음) 스토리지 수명주기 서비스의 만료 삭제가 실제 팩스에 적용되지 않거나 잘못 동작
- 위치: services/storage_lifecycle.py purge_expired_faxes(), cloud_storage.py delete_fax()
- 증상:
  1. 만료 기준 컬럼이 `lastmod` 인데 실제 수신 팩스는 `archstamp` 만 채움(ArchiveIn.create). lastmod 가 NULL 이라 영원히 만료되지 않음.
  2. 로컬 디렉터리를 `fax{fid}` 이름으로 찾으나 faxrcvd 는 ARCHIVE/YYYY/MM/DD/번호/HylaFAX-ID 구조라 일치하지 않음. DB 행만 삭제되고 파일은 디스크에 고아로 남음.
  3. policy.remote_sync_delete, delete_remote_tiff_only 는 어디서도 참조되지 않음(False 여도 provider.delete_fax 호출).
  4. 원격 삭제가 예외를 내도 삼키고 DB 행을 그대로 삭제하여 원격 객체가 영구 고아가 됨.
  5. S3 delete_fax 는 `fax{fid}/` 가 비면 `fax{fid}` (슬래시 없음) 접두사로 재검색하여 fax1 삭제 시 fax10, fax100, fax12 객체를 지움.
  6. list_objects_v2 페이지네이션(1000개 제한) 무시, 일부만 삭제하고 True 반환.
  7. 환경변수 불일치: 서비스는 NAMIFAX_ARCHIVE_DIR, faxrcvd 는 AVANTFAX_ARCHIVE, 커버는 AVANTFAX_COVERS_DIR.
- 재현: t10.py (1, 2, 3, 4, 5, 6 모두 출력으로 확인).
- 확인 수준: 재현 (7 은 코드 확인)

### ADM-13 (높음) Cover Studio 렌더링: 샌드박스 없는 Jinja2 로 임의 코드 실행 + PS 주입 + 토큰 치환 충돌
- 위치: services/cover_studio.py render_template()
- 증상:
  - .html/.jinja2 템플릿을 `jinja2.Template()` (비샌드박스, autoescape 없음)으로 렌더링. 업로드된 템플릿 `{{ cycler.__init__.__globals__.os.popen('id').read() }}` 가 서버에서 명령 실행. 컨텍스트 값은 이스케이프 없이 HTML 에 삽입(`<script>` 그대로 출력).
  - .ps 치환에서 값의 `(`, `)`, `\` 를 이스케이프하지 않아 PostScript 문자열 탈출 가능(`(x) show (evil`).
  - 토큰 목록 순서 때문에 `XXXX-to` 가 `XXXX-to-company`/`XXXX-to-fax-number` 안에서 먼저 치환됨(`XXXX-from` 도 마찬가지). 또 latin-1 인코딩이라 한글 이름(`김철수`)에서 UnicodeEncodeError 로 예외 전파.
  - 잘못된 템플릿은 예외를 삼키고 원본을 그대로 반환.
- 재현: t11.py. popen('id') 결과 반환, 한글 이름 UnicodeEncodeError, 빈 title/파일 허용.
- 확인 수준: 재현 (토큰 충돌은 faxcover 에서 재현, studio 는 동일 루프라 추론)

### ADM-14 (높음) print-to-fax CLI 가 '큐에 등록됨'이라 출력하지만 아무것도 큐에 넣지 않음, 실패 시에도 종료코드 0
- 위치: services/printer.py process_inbound_print_job() (주석 "In real operation, queue via sendfax/FaxQueue"), cli/print_in.py:42-50
- 증상: `[[FAX: 번호]]` 를 찾으면 `{"dispatched": True, "status": "QUEUED"}` 만 반환하고 FaxQueue/sendfax 호출이 없음. 태그가 없으면 "Saved to drafts" 라고 출력하나 저장 코드가 없음(인쇄 데이터 유실). 항상 exit 0 이라 CUPS 는 성공으로 간주. sender_user, db 인자는 사용되지 않음. 파일이 실행 권한 없음(-rw-rw-r--), pyproject 에 entry point 없음.
- 재현: t18.py. `print_in.py 1 bob t 1 "" /nonexistent` 에 `[[FAX: 555]]` 입력 -> "Job successfully enqueued for 555." rc=0, DB 변화 없음.
- 확인 수준: 재현

### ADM-15 (높음) OCR 인덱싱이 실제로는 아무것도 저장하지 않음 (연결된 엔진에서도)
- 위치: services/ocr.py index_fax() (`existing = self.db.query(...)` 는 QueryResult 라 항상 truthy), get_ocr_text(), search_faxes(), _ensure_table_exists() (MySQL 전용 DDL)
- 증상: K16 의 QueryResult 반복 불가와 별개로, 엔진을 연결해도 index_fax 는 항상 UPDATE 분기로 가서 0행 갱신 후 True 반환(INSERT 가 없음). FaxOCR 테이블은 schema.py 에 없고 OCR 서비스의 DDL 은 `AUTO_INCREMENT`, 인라인 `INDEX`, `ENGINE=InnoDB` 라 SQLite 에서 구문 오류. 기본 생성자는 연결 없는 DatabaseEngine() 을 사용. 결과적으로 FaxOCR 에는 행이 생기지 않고 get_ocr_text 는 항상 None, search_faxes 는 항상 []. 호출부 faxrcvd 는 `except Exception: pass` 로 은폐. 검색 UI/뷰도 없음.
- 재현: t18.py (pytesseract 모킹, 테이블 수동 생성 후 index_fax 2회 True, FaxOCR 행 0건).
- 확인 수준: 재현

## 중간

### ADM-16 (중간) 저장된 네트워크 프린터/라우팅의 printer 값이 어디서도 소비되지 않음
- 위치: services/printer.py list_printers(), cli/faxrcvd.py:174-215 (printer, printer_type 계산만 하고 사용 안 함), PRINTFAXRCVD 환경변수 미사용
- 증상: NetworkPrinters 테이블과 protocol/queue_name(LPD, IPP) 은 관리 화면 외에서 읽히지 않음. 모뎀/DID/바코드/Fax2Email 의 `printer` 값은 faxrcvd 에서 결정만 하고 인쇄 호출이 없음. test_print/send_raw_print 는 RAW 만 지원, protocol 을 무시. K06 과 같은 계열의 "저장된 값 미소비" 변형.
- 확인 수준: 재현(grep 으로 호출부 부재 확인)

### ADM-17 (중간) SMTP 게이트웨이 설정이 실제 메일 발송에 쓰이지 않고 send_mail 은 메일을 보내지 않음
- 위치: common/helpers.py send_mail() (`MailerService(admin_email=from_addr)`, smtp_server 없음), services/mailer.py sendmail() (`if self.spool_mode or not self.smtp_server` 면 메모리에 쌓고 True), from_settings() 는 테스트 외 호출자 없음, get_admin_email 은 env ADMIN_EMAIL
- 증상: faxrcvd, notify 가 쓰는 send_mail 은 SMTP 서버 없이 MailerService 를 만들어 메시지를 메모리 스풀에만 넣고 성공(True)을 반환. 즉 수신 알림 메일이 전혀 발송되지 않으며 로그에는 "Fax sent to ... contact" 성공이 남음. 관리자가 저장하는 smtp_host/포트/보안/인증/from_name/서명은 전혀 소비되지 않음. from_name 은 MailerService 에서 "NamiFAX" 고정.
- 재현: t12.py (smtplib.SMTP 모킹, send_mail True, SMTP 미호출; from_settings 기본값 localhost:25).
- 확인 수준: 재현

### ADM-18 (중간) SMTP 설정 저장 시 HTML 서명 삭제, 비밀번호 평문 노출, 검증 부족
- 위치: services/smtp_settings.py save_settings() (email_sig_html 을 data 에서 읽어 덮어씀), templates/admin_smtp.jinja2:146 (`value="{{ config.smtp_password }}"`), views/admin.py:933-939 (test 액션 int() 미보호)
- 증상: (a) 폼에 email_sig_html 필드가 없어 저장할 때마다 DB 의 email_sig_html 이 ''로 지워짐. (b) SMTP 비밀번호가 DB 에 평문 저장되고 페이지 HTML value 속성에 그대로 출력됨(소스 보기로 유출, 추론: 템플릿 소스 확인). (c) 저장 시 포트가 숫자가 아니면 내부 예외 문구("invalid literal for int()...")가 화면 오류로 표시되고, test 액션은 같은 경우 예외가 전파되어 500. (d) host 빈 값, from_email 형식 및 CR/LF 포함 값이 그대로 저장됨(MailerService.set_message 는 이후 ValueError).
- 재현: t12.py (a, c, d 재현), (b) 추론.
- 확인 수준: 재현(a, c, d), 추론(b)

### ADM-19 (중간) 스토리지/SAML 설정 저장이 MySQL 에서 동작하지 않는 SQLite 전용 SQL
- 위치: views/admin.py:1063, 1068, 1182, 1186 (`CREATE TABLE ... (key TEXT PRIMARY KEY, value TEXT)`, `INSERT OR REPLACE INTO SystemConfig`, `WHERE key = ...`); schema.py 전체(AUTOINCREMENT, sqlite_master, PRAGMA, INSERT OR IGNORE)
- 증상: MySQL/MariaDB 에서 `key` 는 예약어이고 TEXT 기본키는 길이 지정이 필요하며 `INSERT OR REPLACE` 는 구문 오류. set_cfg/get_cfg 가 결과를 확인하지 않아 오류가 조용히 사라지고 성공 메시지만 출력. DatabaseEngine.connect 는 pymysql 을 요구하나 pyproject 의존성에 없음(`MySQL driver (pymysql) not installed`). user_passwords.clear_hashes 의 `:uid` 이름 파라미터도 pymysql 스타일과 불일치(추론).
- 재현: 코드 확인(SQLite 로는 정상). pymysql 부재는 pyproject 확인.
- 확인 수준: 추론

### ADM-20 (중간) DB 스키마와 엔티티 불일치로 비밀번호 이력과 시스템 로그 PK 오류
- 위치: models/entities.py UserPasswords(upid, pwdhash) vs schema.py UserPasswords(pwd_id, password NOT NULL), SysLog(syslogid) vs schema SysLog(log_id)
- 증상: log_password 의 INSERT 가 없는 컬럼 때문에 실패(결과 무시) -> UserPasswords 가 항상 비어 있어 "이전에 사용한 비밀번호" 검사(password_used)와 pwd_reuse 정책이 무력. SysLog 도 동일 불일치이며, 애초에 SysLog 는 기동 seed 외에 기록하는 코드가 없어(avantfaxlog 는 syslog 데몬에만 기록) 시스템 로그 화면은 seed 의 가짜 행 2건만 보여줌.
- 재현: t4.py(UserPasswords 비어 있음), grep(SysLog 기록 코드 없음).
- 확인 수준: 재현

### ADM-21 (중간) 관리 화면이 빈 테이블/삭제 후 가짜 데이터를 표시하고 그 행은 수정/삭제 불가
- 위치: views/admin.py:460-463(covers), 560(categories), 616-619(barcodes), ~700(dynconf), 805-820(fax2email: 없는 이메일을 faxes@example.com, printer 를 OfficePrinter 로 조작), dashboard 60(status 고정 "Running and idle"), 87(hylafax 버전 고정 "6.0.7")
- 증상: 테이블이 비면 General/Invoices/Legal, urgent.ps, BC-1001, Cyberdyne 등 하드코딩 행이 나타나고 삭제해도 계속 남음. fax2email 은 규칙이 없는 회사에 실제로 없는 전달 주소/프린터를 표시. 모뎀 상태는 faxstat 을 호출하지 않고 항상 정상 표시.
- 재현: t19.py.
- 확인 수준: 재현

### ADM-22 (중간) DID/카테고리/모뎀/커버 액션이 실패해도 성공 메시지, 존재하지 않는 대상 삭제도 성공
- 위치: views/admin.py:262-300 (DID), 480-560(covers, categories), 195-235(modems)
- 증상:
  - DID 생성 시 잘못된 이메일 또는 중복은 서비스가 False 를 반환하지만 뷰는 반환값을 안 보고 "created successfully" 표시. DID 수정에서 라우트 중복(UNIQUE 위반)도 set_* 실패를 무시하고 "updated successfully"(실제 변경 없음). 수정 경로에는 이메일 검증 자체가 없어 `bad-email` 저장됨.
  - DID, 프린터, 카테고리, 커버 삭제는 존재하지 않는 ID 에도 성공 표시("deleted successfully").
  - 카테고리 삭제 시 사용 중인지 확인하지 않고 DIDRoute/Modems/Barcode 의 faxcatid 를 정리하지 않아 댕글링 참조가 생김. 커버 삭제도 UserAccount.coverpage_id 참조를 정리하지 않음(추론).
  - 카테고리, dynconf, fax2email 템플릿은 message 출력이 없어 성공/실패 문구가 보이지 않는 화면이 있음(layout 은 flash_message 만 출력).
- 재현: t5.py, t6.py.
- 확인 수준: 재현 (커버 참조는 추론)

### ADM-23 (중간) 모뎀 화면: 삭제 버튼, devid, faxcatid 필드가 폼에 없음
- 위치: templates/admin_modems.jinja2:76-100, views/admin.py:195-235
- 증상: 뷰는 delete/devid/faxcatid 를 처리하지만 템플릿 폼에 해당 입력이 없어 UI 로 모뎀을 삭제할 수 없고 분류를 지정할 수 없음(barcodes, dynconf 의 faxcatid 도 마찬가지로 barcode 폼에는 faxcatid 선택이 없음). device 이름은 수정 가능한 필드라 이름 변경 시 새 모뎀이 생성됨. 저장 시 contact/printer 형식 검증 없음(`contact=notanemail` 저장 확인).
- 재현: t8.py (devid 포함 POST 로만 삭제 가능).
- 확인 수준: 재현

### ADM-24 (중간) Local/Cloud 스토리지 제공자의 경로 탈출, 연결 테스트 오판
- 위치: services/cloud_storage.py LocalStorageProvider._full_path/test_connection/생성자, CloudStorageManager.get_provider
- 증상:
  - `_full_path` 가 `../` 를 막지 않아 delete_file("../victim.txt") 가 base_dir 밖 파일을 삭제하고 upload_file 이 base_dir 밖에 씀.
  - test_connection 은 `os.access(W_OK) or os.path.exists` 라 읽기 전용 디렉터리도 success. 연결 테스트가 디렉터리를 생성하고, /var/spool/hylafax/archive 생성 실패 시 조용히 `~/.namifax/archive` 로 대체(이 실행에서 홈 아래에 실제 생성됨).
  - 저장 유형 'FTP' 같은 임의 값이 저장되고 테스트는 "Local storage accessible" 로 성공 보고. GCS 는 endpoint 가 없으면 AWS S3 로 연결(GCS 엔드포인트 기본값 없음), 별도 GCS 클라이언트 없음.
  - S3 provider 의 upload/download/delete 는 예외를 모두 False 로 바꿔 원인 정보가 사라지고 boto3 타임아웃/재시도 설정이 없어 잘못된 endpoint 테스트가 오래 블록될 수 있음(추론).
- 재현: t10.py (경로 탈출, 읽기 전용 성공), t14.py (FTP).
- 확인 수준: 재현 (타임아웃은 추론)

### ADM-25 (중간) 프린터 화면 입력 검증 부재 및 예외 500
- 위치: views/admin.py:990-1013, services/printer.py create_printer()
- 증상: 포트가 숫자가 아니면 int() 예외로 500(add, test, delete 의 printer_id 도 동일), 포트 범위(99999, -1) 미검증, protocol 임의값('GARBAGE') 저장, 이름/호스트 중복과 공백, 세미콜론 포함 호스트 허용. 존재하지 않는 printer_id 삭제도 성공 문구. 관리자 입력 호스트/포트로 임의 소켓 연결(연결 테스트, SSRF 성격이나 관리자 전용).
- 재현: t14.py.
- 확인 수준: 재현

## 낮음

### ADM-26 (낮음) 시스템 로그 화면 기능 한계
- 위치: views/admin.py:349-413
- 증상: years 가 2024-2027 로 하드코딩(2028 이후 선택 불가), LIMIT 100 고정에 페이지네이션 없음, LIKE 와일드카드(%, _) 이스케이프 없음, 잘못된 날짜(2월 31일)나 유니코드 숫자는 오류 없이 빈 결과.
- 확인 수준: 재현 (years), 추론(나머지)

### ADM-27 (낮음) SAML 관리 설정 검증 없음
- 위치: views/admin.py:1185-1200
- 증상: idp_sso_url 에 `javascript:alert(1)` 같은 스킴, 임의 default_role('superuser'), 잘못된 PEM 이 그대로 저장됨. (소비 코드가 없으므로 K05 와 별개로 저장 시 검증이 필요.)
- 재현: t14.py.
- 확인 수준: 재현

### ADM-28 (낮음) 패키징: avantfax 패키지가 wheel 에 포함되지 않지만 namifax.views.admin 이 avantfax 를 import
- 위치: pyproject.toml (uv_build, 모듈 namifax 만), views/admin.py:8-12, 714, 737, 759, 이하 admin.py 의 DatabaseEngine import, services/saml.py, printer.py, smtp_settings.py, storage_lifecycle.py, cover_studio.py, ocr.py 의 `from avantfax.db.engine import DatabaseEngine`
- 증상: `uv build --wheel` 산출물에 namifax/ 324개 파일, avantfax/ 0개. 설치 배포본에서는 admin 뷰 import 가 실패하고 config.scan 이 예외를 일으킬 수 있음(개발 환경은 src 가 경로에 있어 가려짐). 또 avantfax.db.engine.DatabaseEngine 과 namifax.db.engine.DatabaseEngine 이 서로 다른 클래스(`is` 비교 False)라 isinstance 기반 코드에서 어긋남. K14 와 관련.
- 재현: wheel 내용 검사로 확인. 실제 설치 후 ImportError 는 미실행.
- 확인 수준: 재현(산출물 검사), 추론(ImportError)

### ADM-29 (낮음) 설정 화면 안내/태그 불일치
- 위치: views/admin.py:490-510 (supported_tags: TO_COMPANY 등 대문자 HylaFAX 스타일), services/cover_studio.py COVER_TAGS_METADATA(XXXX-to ...), cli/faxcover.py values 키(to-company 등), cover_studio covers_dir(/var/spool/hylafax/covers) vs faxcover INSTALLDIR/images
- 증상: 관리 화면이 안내하는 태그, Cover Studio 태그, faxcover.py 가 실제 치환하는 토큰이 서로 달라 안내대로 만든 템플릿이 치환되지 않음. 저장 위치도 달라 Studio 에 저장한 템플릿은 faxcover 가 찾지 못함. faxcover.process_template 도 `XXXX-to` 가 `XXXX-to-company` 를 먼저 치환해 "Bob-company" 출력(재현: t11.py).
- 확인 수준: 재현 (토큰 충돌), 추론(나머지)

### ADM-30 (낮음) 커버 관리: 파일명 검증 없음, 중복 등록
- 위치: views/admin.py:470-495, services/cover_studio.py save_template()
- 증상: Covers 관리 화면은 file 에 `../../etc/passwd` 같은 값도 그대로 등록(존재/확장자 검증 없음). Cover Studio save_template 은 같은 파일명을 덮어쓰면서 CoverPages 행을 중복 생성(같은 file 에 행 2개, 이전 템플릿 내용 소실), DB 가 연결되지 않아도 success True/cover_id None 반환, 빈 title 도 허용, INSERT 실패 여부를 확인하지 않음(K07 과 별개의 서비스 결함).
- 재현: t5.py, t11.py.
- 확인 수준: 재현
