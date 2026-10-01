# Round 1 - CLI / 서비스 / DB 계층 결함 (COR)

범위: src/namifax 의 cli, services, common, db, models, main.py, pyproject, systemd, ini.
모든 재현은 NAMIFAX_DB_PATH 를 scratchpad/agent-core 아래로 지정해 수행했고 저장소 파일은 수정하지 않았다.
known.md(K01~K16)와 중복되는 항목은 제외했으며, 변형/원인 차이가 있는 경우만 "K?? 와의 관계"로 표기했다.
mypy attr-defined, call-arg 항목은 전수 대조했다. K03/K12/K13/K16 에 이미 포함된 것을 제외한 나머지(notify 의 user.email, faxcover reduce_single, bridge_cli 등)는 아래 항목에 반영했다.

---

## COR-01 [치명] 단일 sqlite 연결/커서를 여러 스레드가 공유해 인터프리터가 세그폴트
- 위치: src/namifax/db/engine.py:39-41(_conn/_cursor/_records 인스턴스 공유), :89(check_same_thread=False), :134(fetchall); src/namifax/main.py:14 (ThreadingWSGIServer), src/namifax/services/scheduler.py(APScheduler 스레드); get_default_engine 싱글턴(engine.py:250-265)
- 증상: 웹 요청(스레드 서버, waitress 기본 4스레드), 스케줄러 잡이 같은 DatabaseEngine 의 커서와 _records 를 동시에 사용. 결과가 뒤섞이거나 프로세스가 SIGSEGV 로 죽는다.
- 재현: 4개 스레드가 `db.query("SELECT ...")` 를 100회씩 반복 -> 3회 실행 모두 "Fatal Python error: Segmentation fault" (engine.py line 134 in query), 종료코드 139. 스크립트: scratchpad/agent-core/thr.py
- 확인 수준: 재현

## COR-02 [치명] 기동할 때마다 seed/migration 이 실제 운영 데이터를 덮어씀
- 위치: src/namifax/db/schema.py:259-420 (seed_database_if_empty), :200-247(_apply_schema_migrations); 호출: main.py serve_main, namifax/__init__.py create_app, db/engine.py get_default_engine(CLI 마다 호출)
- 증상: init_database_tables 는 매 프로세스 기동(웹, 모든 CLI 훅 호출마다)마다 실행되고 "테이블이 비었을 때"가 아니라 조건부로 다음을 수행한다.
  - Modems 행이 2개 미만이면 devid 1,2 를 `INSERT OR REPLACE` -> 운영 중 모뎀 설정(alias, contact, printer)을 샘플로 덮어씀
  - `UPDATE FaxArchive ... WHERE fid = 1` 로 description/inbox/companyid 등을 강제 설정 (실제 1번 팩스 변조). company 도 'Acme Corp' 로 갱신
  - DistroList dl_id=1 이름을 'Executive Team' 으로 덮어씀, DIDRoute 1번 alias 를 'Main Trunk' 로, 'Acme Global' 회사명을 변경
  - 운영 DB 에 Acme/Initech 샘플 주소록, 샘플 SysLog, admin/operator (비밀번호 평문 'password') 가 주입됨 (K10 과 별개의 시딩 경로)
- 재현: 사용자/모뎀/팩스1/배포목록을 "REAL" 값으로 바꾼 뒤 init_database_tables 재호출 -> Modems 가 Sales Inbound/Support Outbound 로 복원, FaxArchive fid=1 description 이 'Monthly Financial Report', inbox=1 로 복원, DistroList 가 'Executive Team' 로 복원. 스크립트: scratchpad/agent-core/r1.py
- 확인 수준: 재현

## COR-03 [치명] notify CLI 가 DB 에 있는 모든 사용자에 대해 AttributeError 로 종료 (발송 팩스 미보관, 통지 메일 없음)
- 위치: src/namifax/cli/notify.py:195-205 (`owner = user.username`, `to_email = user.email`, `user.email`), src/namifax/services/user_account.py (AFUserAccount 는 dbdata 딕셔너리만 보유, username/email/name 속성 없음)
- 증상: qfile 의 owner 가 UserAccount 에 존재하거나 faxmail/www-data 이면서 mailaddr 이 사용자 이메일과 일치하면 `user.email` 에서 AttributeError. 예외가 잡히지 않아 종료코드 1. 그 뒤의 ArchiveOut 기록, PDF 생성, 성공 메일이 모두 실행되지 않는다. (알 수 없는 owner 만 동작)
- 재현: bob 사용자를 만든 뒤 `owner:bob` qfile 로 run_notify(['notify.php', qfile, 'done', '10']) -> `AttributeError: 'AFUserAccount' object has no attribute 'email'` (notify.py:205). K03(다른 메서드 부재)과 다른 호출부.
- 확인 수준: 재현

## COR-04 [치명] CLI/서비스에서 나가는 모든 메일이 실제로는 발송되지 않고 성공(True)을 반환
- 위치: src/namifax/common/helpers.py:263-289 (send_mail 이 `MailerService(admin_email=from_addr)` 로 smtp_server 없이 생성), src/namifax/services/mailer.py:~165 (`if self.spool_mode or not self.smtp_server: self._spooled_messages.append(...); return True`), mailer.from_settings 는 어떤 CLI 도 호출하지 않음
- 증상: faxrcvd/notify 가 호출하는 send_mail 은 SMTP 설정을 읽지 않으므로 메시지를 메모리에 쌓고 True 를 반환. 프로세스 종료와 함께 소실. 관리자 화면의 SMTP 설정(K01)과 무관하게 설정 자체를 읽는 경로가 없음. 또한 embed_image 로 등록한 인라인 이미지(`_embedded_images`)는 sendmail 에서 메시지에 붙지 않아 썸네일 임베드가 전부 무시됨. (K13 은 attach_file/set_cc 호출 불일치, 이 항목은 그 이전 단계의 발송 자체 불능)
- 재현: smtplib.SMTP 를 계측한 상태에서 `send_mail("a@b.com","root@x","s","t")` -> True 반환, SMTP 시도 0회.
- 확인 수준: 재현 (embed_image 미첨부는 코드 확인: sendmail 이 _embedded_images 를 참조하지 않음 - 추론)

## COR-05 [높음] AFAddressBook.loadbyfaxnum 이 튜플을 반환해 항상 참 -> faxrcvd/notify 가 회사/팩스번호를 생성하지 않음
- 위치: src/namifax/services/addressbook.py:loadbyfaxnum (반환 `tuple[bool, bool]`), 호출: src/namifax/cli/faxrcvd.py:119 `if addressbook.loadbyfaxnum(company_fax):`, src/namifax/cli/notify.py:158, helpers.py 의 다른 호출부도 동일 패턴 가능
- 증상: (False, False) 도 truthy. 신규 발신번호도 "이미 존재" 분기로 들어가 create/create_faxnumid 를 건너뜀. faxnumid=None, 주소록 자동 등록 없음. 다중 매치(True, True)도 단일 매치로 처리되어 faxnumid=None. notify 는 `getattr(addressbook, "is_multiple", False)` 를 보지만 속성명은 `multiple` 이라 다중 매치 감지 불가.
- 재현: `bool(AFAddressBook().loadbyfaxnum("999999"))` -> True (실제 반환 (False, False)). faxrcvd 를 2회 실행한 뒤 AddressBook 에 신규 회사 없음, FaxArchive.faxnumid=None 2건.
- 확인 수준: 재현

## COR-06 [높음] AddressBookFAX 스키마에 레거시 컬럼이 없어 팩스번호 생성, 카운터, Fax2Email 라우팅이 모두 실패 (에러는 삼켜짐)
- 위치: src/namifax/db/schema.py:88-97 (AddressBookFAX 는 fax_id, abook_id, ab_id, faxnumber, to_person, default_num 만 보유) vs legacy/create_tables.sql:93-106 (email, description, to_location, to_voicenumber, faxcatid, faxfrom, faxto, printer), src/namifax/models/entities.py AddressBookFAX 엔티티
- 증상: create_faxnumid 가 `INSERT ... (abook_id, faxnumber, faxfrom, faxto)` 에서 "table AddressBookFAX has no column named faxfrom" 로 실패 -> "Fax number could not be created". inc_faxfrom/inc_faxto, save_settings(notify 의 to_person/to_location/to_voicenumber), has_fax2email(SELECT email ...) 전부 실패. get_email/get_category/get_printer 는 영구 None 이라 faxrcvd 의 Fax2Email 라우팅(메일/프린터/카테고리)이 동작하지 않는다.
- 재현: `AFAddressBook().create("Co2"); create_faxnumid("5551111")` -> False, db.get_error() = "table AddressBookFAX has no column named faxfrom". `has_fax2email()` -> "no such column: email". 엔티티 대 스키마 비교 스크립트로 8개 컬럼 누락 확인.
- 확인 수준: 재현

## COR-07 [높음] AddressBook.abook_id 가 신규 행에서 NULL (PK 는 ab_id) -> 신규 회사는 조회/삭제 불가, delete_cid 는 True 를 반환하고 아무것도 안 지움
- 위치: src/namifax/db/schema.py (AddressBook 의 PK 는 ab_id, abook_id 는 마이그레이션에서 ALTER 로 추가되고 일회성 UPDATE 로만 채움), src/namifax/services/addressbook.py create/loadbycid/delete_cid, src/namifax/cli/phb.py
- 증상: create() 는 lastrowid(ab_id)를 abook_id 로 돌려주지만 테이블의 abook_id 컬럼은 NULL. 이후 `WHERE abook_id = N` 을 쓰는 loadbycid, create_faxnumid, delete_cid, reassign 이 모두 행을 못 찾음. delete_cid 는 "0행 삭제"인데 True 반환. phb 는 abook_id=None 회사에 대해 loadbycid 실패 후 이전 회사의 번호 목록을 재사용할 수 있음(상태 잔존).
- 재현: create("ZetaCo") -> abook_id 5 반환, loadbycid(5) -> False, delete_cid(5) -> True, AddressBook 에서 행 잔존 및 abook_id 컬럼 NULL.
- 확인 수준: 재현

## COR-08 [높음] DynConf 테이블이 스키마에 없음(DynamicConfig 로 생성) -> 차단(RejectCall) 규칙이 영구 동작하지 않음
- 위치: src/namifax/db/schema.py:54-59 (`CREATE TABLE DynamicConfig`), src/namifax/services/dynconf.py (`MDBOData("DynConf")`), src/namifax/models/entities.py DynConf, legacy/create_tables.sql:169 (DynConf)
- 증상: DynamicConfig().create/lookup/list_rules 전부 "no such table: DynConf". `namifax dynconf` 는 어떤 규칙이 있어도 "RejectCall: true" 를 출력하지 않아 블랙리스트 기능이 사실상 없다. 오류는 삼켜짐.
- 재현: `DynamicConfig().create("ttyS0","5551234")` -> False "no such table: DynConf". DynamicConfig 테이블에 직접 INSERT 후 `run_dynconf(["dynconf","ttyS0","5551234@sip.example"])` -> 출력 없음.
- 확인 수준: 재현

## COR-09 [높음] QueryBuilder.quote 가 Python bool 을 'True'/'False' 문자열로 저장 -> 계정이 비활성/비관리자가 됨
- 위치: src/namifax/db/query.py:quote (engine.quote 는 str() 후 따옴표), src/namifax/db/base.py save()/to_dict (entities 의 bool 기본값 False/True 를 그대로 INSERT), src/namifax/services/user_account.py login 의 `in (1, True, "1")` 검사
- 증상: `create({... "is_admin": True, "acc_enabled": True})` -> DB 에 텍스트 'True' 저장. login 은 "Account is disabled", admin=True 로그인은 "Incorrect username or password". 엔티티 경로(MDBObject.save)는 기본 bool 필드(superuser False 등)를 모두 'False' 문자열로 INSERT. MySQL 에서는 BOOL 컬럼에 'True' 삽입 자체가 오류.
- 재현: carol 계정을 is_admin=True, acc_enabled=True 로 생성 -> `SELECT is_admin, typeof(is_admin)` = 'True', text; login 실패("Account is disabled").
- 확인 수준: 재현

## COR-10 [높음] faxqueue 명령 주입 (shell=True, 사용자 입력을 그대로 보간)
- 위치: src/namifax/services/faxqueue.py:99-103 (shell_exec shell=True), :166-168 killjob(`FAXUSER='{user}'`, jid 미검증), :172-190 faxalter(`-d "{val}"` 등 값 미이스케이프)
- 증상: user 에 작은따옴표, 값에 `$(...)` 를 넣으면 임의 명령이 웹 프로세스 권한(uucp)으로 실행. killjob/faxalter 는 실패해도 항상 True.
- 재현: faxrm_cmd="echo" 로 `killjob("x'; touch FILE; echo '", "1")` -> FILE 생성. `faxalter("u",1,{"destination":"$(touch FILE)"})` -> FILE 생성. (views 가 jid 를 str 로 전달: web/views/outbox.py:71 mypy arg-type)
- 확인 수준: 재현

## COR-11 [높음] SQL 조립/이스케이프 결함 (LIKE 인젝션 재현, MySQL 백슬래시는 추론)
- 위치: src/namifax/services/addressbook.py:search_companies (`LIKE '%{keywords}%'` 미이스케이프), src/namifax/db/engine.py:quote (작은따옴표만 이중화, 백슬래시 미처리), src/namifax/db/query.py:quote (set_quoting(False) 시 `'{var}'` 무이스케이프, SPECIAL_FUNCTIONS 문자열은 그대로 통과), 식별자(테이블/컬럼)는 전혀 인용/검증하지 않음
- 증상: search_companies("zzz%'/**/OR/**/1=1/**/OR/**/company/**/LIKE/**/'%zzz") 가 전체 회사 목록 반환(4건). 일반 입력 `x' OR '1'='1` 는 구문 오류로 조용히 빈 결과. MySQL(백슬래시 이스케이프 활성)에서는 quote("a\\") -> `'a\'` 로 문자열이 닫히지 않아 인젝션 가능(추론). 또 "NOW()" 같은 특수 함수 문자열을 사용자 값으로 넣으면 SQL 함수로 해석됨.
- 재현: 위 search_companies 호출 결과 4건(전체) 반환 확인; `db.quote("a\\' OR 1=1 -- ")` 출력 `'a\'' OR 1=1 -- '`.
- 확인 수준: 재현 (MySQL 백슬래시 경로는 추론)

## COR-12 [높음] MySQL 백엔드가 사실상 사용 불가 (드라이버 미선언, 문법/파라미터 스타일, 스키마 전부 SQLite 전용)
- 위치: pyproject.toml dependencies (pymysql 없음), src/namifax/db/engine.py:55-80 (connect), :250-265 (get_default_engine 은 항상 sqlite), src/namifax/db/schema.py (`sqlite_master`, AUTOINCREMENT, `INSERT OR REPLACE/IGNORE`, `CREATE VIEW IF NOT EXISTS`), 이름 있는 파라미터 `:cid` 사용처 addressbook.delete_companyfaxids/reassign, user_passwords.clear_hashes (pymysql 은 `%(cid)s`), ocr.py/webauthn.py 의 MySQL 전용 DDL(SQLite 에서는 실패), admin 뷰의 `INSERT OR REPLACE`
- 증상: `connect(..., db_engine="mysql")` 는 pymysql 미설치로 False("MySQL driver (pymysql) not installed"). 설사 설치해도 default engine 이 sqlite 만 연결하고, init_database_tables 는 sqlite_master 조회를 해서 MySQL 에서 실패하며, 이름 있는 파라미터 쿼리가 오류. systemd 유닛은 mariadb.service/mysql.service 를 After 로 지정하지만 어디서도 MySQL 설정 경로가 없다(ini/환경변수 없음). 레거시(MySQL 전제) 데이터 이관 경로 없음.
- 재현: `DatabaseEngine().connect("u","p","db")` -> False, get_error() "MySQL driver (pymysql) not installed".
- 확인 수준: 재현 (파라미터 스타일 불일치는 추론)

## COR-13 [높음] DB 경로 기본값이 현재 작업 디렉터리 기준이고 CLI 훅마다 seed 까지 실행 -> 호출 위치마다 별개의 DB 가 생김
- 위치: src/namifax/db/engine.py:256 (`os.path.join(os.getcwd(), "namifax.db")`), systemd/namifax.service 와 namifax-scheduler.service (NAMIFAX_DB_PATH 미설정), development.ini/production.ini (DB 설정 항목 자체 없음)
- 증상: faxrcvd/notify/dynconf/faxcover/cron 은 HylaFAX(faxgetty, 스케줄러, cron)가 임의의 cwd(예: /var/spool/hylafax)에서 호출하므로 각각 새 namifax.db 를 만들고 샘플 데이터까지 시딩(COR-02). 웹(WorkingDirectory=/opt/namifax)과 DB 가 달라 수신팩스가 웹에 보이지 않는다. dynconf 는 호출마다 스키마 DDL 전체 + 마이그레이션 + seed UPDATE 를 실행(콜 필터는 지연에 민감).
- 재현: cwd=임의 디렉터리, NAMIFAX_DB_PATH 미설정으로 `run_dynconf(["dynconf","ttyS0","123"])` -> 그 디렉터리에 118KB 짜리 namifax.db 생성(seed 포함).
- 확인 수준: 재현

## COR-14 [높음] 보관 일시(archstamp)를 '/' 구분자로 저장해 보관 기간 정리(prune)가 동작하지 않고 날짜 파싱 실패
- 위치: src/namifax/cli/faxrcvd.py:99-101,150 (`day = parts[0].replace(":", os.sep)` 를 "{day} {hour}" 로 ArchiveIn.create 에 전달), src/namifax/services/archive_base.py:create_fax(archstamp 그대로 저장), prune_archive/prune_inbox (`archstamp < 'YYYY-MM-DD 00:00:00'` 문자열 비교), _format_row_dates(fromisoformat 실패 후 문자열 자르기)
- 증상: 저장값이 "2026/10/01 08:10:31". '/'(0x2F) > '-'(0x2D) 이므로 같은 해의 컷오프와 비교하면 항상 "더 큼" -> cron -i/-d 가 같은 해의 팩스를 절대 정리하지 못함. 날짜 범위 검색(archstamp > start)도 형식 불일치. (레거시 PHP 는 날짜 포맷을 ArchiveIn 에서 정규화)
- 재현: archstamp='2026/03/01 10:00:00', inbox=1 행을 넣고 `ArchiveIn().prune_inbox(30)` -> 0건 처리, inbox 그대로.
- 확인 수준: 재현

## COR-15 [높음] tiff2pdf/convert2pdf/static_preview/faxinfo 가 실패를 성공으로 위장(가짜 PDF, 빈 썸네일, 가짜 팩스 정보) + 저장소 정리 시 원본 TIFF 삭제
- 위치: src/namifax/common/helpers.py:tiff2pdf(끝부분 `%PDF-1.4\n%EOF` 스텁 작성 후 True), convert2pdf, pdf_preview, static_preview(빈 thumb.png 작성 후 True), faxinfo(:357-372 Pillow 실패 시 Sender "00000000" 더미 반환), src/namifax/services/storage_lifecycle.py:purge_local_tiffs, src/namifax/cli/cron.py -p
- 증상: 손상/비 TIFF 파일도 faxinfo 가 성공 딕셔너리를 돌려줘 faxrcvd 가 "00000000" 발신 팩스로 보관(레거시는 "corrupted" 로 종료). tiff2pdf 실패 시 18바이트 가짜 PDF 가 남고, purge_local_tiffs 는 "PDF 가 0바이트가 아니면" 원본 fax.tif 를 삭제하므로 유일한 원본이 유실된다. 썸네일 0바이트.
- 재현: 깨진 파일에 대해 faxinfo -> {'Sender':'00000000','Pages':1,...}; tiff2pdf -> True, 내용 `b'%PDF-1.4\n%EOF\n'`; static_preview -> True, thumb.png 크기 0. purge 경로는 코드 확인(추론).
- 확인 수준: 재현 (원본 TIFF 삭제 연쇄는 추론)

## COR-16 [높음] faxcover: 토큰 접두어 치환으로 커버 페이지가 깨지고, DB 조회와 HTML 커버가 동작하지 않음
- 위치: src/namifax/cli/faxcover.py:46-58 (process_template: `line.replace(f"{match}{k}")` 를 dict 순서대로 적용), :85-125 (`DatabaseEngine()` 미연결 + `query(..., reduce_single=True)` 는 존재하지 않는 인자로 TypeError, `except Exception: pass` 로 은폐), 레거시 대비 unaccent 누락, HTML 커버(.html, html2ps), NUM_PAGES_FOLLOW 누락
- 증상: "XXXX-from-mail-address" 가 "<from>-mail-address" 로, "XXXX-to-company" 가 "<to>-company" 로, "XXXX-todays-date" 가 "<to>days-date" 로 출력. 사용자 이름/이메일 DB 조회(-f 사용자명 -> 이름, 이메일)는 항상 조용히 실패. 비라틴 문자를 PS 에 그대로 출력(레거시는 unaccent). (K16 의 faxcover mypy 항목의 실제 영향)
- 재현: 템플릿 `From: XXXX-from <XXXX-from-mail-address>` 등으로 `run_faxcover(["faxcover","-f","Bob","-M","bob@x.com","-n","555","-t","Alice","-x","ACME","-C",tpl])` -> `From: Bob <Bob-mail-address>`, `To: Alice / Alice-company / Alice-fax-number`, `Date: Alicedays-date`.
- 확인 수준: 재현

## COR-17 [중간] createuser CLI 의 "기존 사용자 갱신" 분기가 비밀번호를 바꾸지 않고 성공 메시지를 출력
- 위치: src/namifax/cli/user.py:38-53 (`set_newpassword(args.password, args.password)`)
- 증상: set_newpassword(oldpwd, newpwd) 는 old 가 현재 비밀번호와 같아야 통과하므로 새 비밀번호를 old 로 넘기면 "Incorrect old password" 로 실패(반환값 무시). 그 뒤 "[+] updated successfully" 출력. 비밀번호 분실 복구 용도로 쓸 수 없다. (기본 비밀번호 admin1234! 가 -p 없이 CLI 기본값인 점도 위험)
- 재현: createuser -u bob -p firstpass1 후 -p secondpass2 재실행 -> 성공 출력, login("bob","secondpass2") False, login("bob","firstpass1") True.
- 확인 수준: 재현

## COR-18 [중간] 비밀번호 이력(UserPasswords) 스키마 불일치로 이력이 기록되지 않고 재사용 검사가 무력
- 위치: src/namifax/db/schema.py:30-35 (pwd_id, uid, password, date) vs src/namifax/models/entities.py UserPasswords/services/user_passwords.py (upid, pwdhash), src/namifax/auth/password.py PasswordManager.hash_password(솔트 해시라 동일 입력이 같은 해시를 내지 않으면 find 매칭 불가)
- 증상: log_password 는 "no column named pwdhash" 로 실패(반환값 무시), password_used 는 항상 False, clear_hashes 는 무의미. change_password 의 "이미 사용한 비밀번호" 검사와 pwd_reuse 정책이 동작하지 않음. user 생성, 변경은 성공으로 보임. 로그인 저장은 MD5 무솔트(레거시 호환)인데 이력만 다른 해시 체계를 써서 검사 자체가 성립하지 않음(추론).
- 재현: change_password("firstpass1") 를 같은 비밀번호로 반복 -> True, db.get_error() "table UserPasswords has no column named pwdhash", UserPasswords 행 0건.
- 확인 수준: 재현

## COR-19 [중간] AFUserAccount.remove 가 NOT NULL 제약 위반으로 실패하는데 True 반환 (계정 삭제 불능)
- 위치: src/namifax/services/user_account.py:remove (soft delete 로 username/email/password 를 None 으로 UPDATE), src/namifax/db/schema.py:UserAccount (username, password, email NOT NULL)
- 증상: UPDATE 가 제약 위반으로 실패하지만 반환값을 확인하지 않아 True. 계정은 그대로 남고 로그인 가능.
- 재현: remove(uid) -> True, 이후 `SELECT uid,username,deleted` -> 행 그대로(deleted=0).
- 확인 수준: 재현

## COR-20 [중간] faxrcvd 가 레거시 PHP 동작에서 벗어남 (누락/은폐)
- 위치: src/namifax/cli/faxrcvd.py
- 증상:
  1. TIFF 복사 실패(`shutil.copy2` 의 OSError)를 `pass` 로 삼키고 계속 진행 -> 원본 없이 DB 에 보관 (레거시는 로그 후 exit)
  2. 회사명 중복(COMPANY_EXISTS) 시 기존 회사에 새 팩스번호를 붙이는 분기와 다중 매치 경고가 없음 (LANG 에 COMPANY_EXISTS 만 정의하고 미사용)
  3. PRINTFAXRCVD, ENABLE_FAX_ANNOTATION, PRINTERNAME 은 읽기만 하고 사용하지 않아 자동 출력/주석 기능이 죽은 코드. (printer/printer_type 계산만 수행)
  4. ArchiveIn 실패 로그 없음(legacy: FAILED to insert ... 로그), avantfaxlog 를 모두 echo=False 로 호출해 표준 출력 로그 제거, mkdirs 실패를 확인하지 않음
  5. OCR 호출은 K12(faxname 미정의)로 NameError 가 `except Exception: pass` 에 흡수, 더해 `OcrService()` 는 COR-27 때문에 어차피 동작 불가
  6. 설정(ENABLE_DID_ROUTING, AUTOCONFDID, FAXRCVD_INCLUDE_PDF 등)은 환경변수로만 읽고, 레거시 local_config 에 해당하는 저장/화면이 없음. HylaFAX 훅은 환경변수를 상속하지 않으므로 사실상 항상 기본값
- 재현: 1, 4는 코드 대조(추론). 같은 TIFF 로 faxrcvd 2회 실행 -> FaxArchive 중복 행, 회사 미생성(COR-05). PRINTFAXRCVD 미사용은 grep 으로 확인.
- 확인 수준: 재현(일부), 추론(1, 4, 6)

## COR-21 [중간] FaxQueue 의 사용자 표시명/소유자 해석이 존재하지 않는 속성에 의존
- 위치: src/namifax/services/faxqueue.py:get_queue, list_owner (`getattr(user_svc, "name", ...)`, `getattr(user_svc, "username", "")`)
- 증상: AFUserAccount 에는 name/username 속성이 없어(dbdata 딕셔너리) 항상 폴백값이 쓰인다. 표시명 대신 username/메일주소가 나오고, faxmail/www-data 소유 작업은 list_owner 에서 username 비교가 "" 와 이루어져 해당 사용자의 목록에서 영구히 빠진다.
- 재현: owner=faxmail, mailaddr=bob@x.com 작업 -> get_queue 의 user 는 'bob@x.com', list_owner("bob") 결과에 미포함.
- 확인 수준: 재현

## COR-22 [중간] DatabaseEngine 의미론: transaction() 무력, 오류 은폐, SELECT 판별/insert id 오류
- 위치: src/namifax/db/engine.py:query(:115-150), transaction(:225-235)
- 증상:
  1. transaction() 컨텍스트 안에서 query() 는 비-SELECT 마다 즉시 commit 하므로 예외 시 롤백되지 않음 (사용자 생성+비밀번호 이력 등 다단계 작업은 원자적이지 않음)
  2. SELECT 가 아닌 "WITH ... SELECT", "PRAGMA", "SHOW" 는 레코드를 반환하지 않고 executed=True 로 위장
  3. 모든 예외를 QueryResult(executed=False) 로 흡수하고 대다수 호출부는 반환값을 무시(schema 의 ALTER 마이그레이션 `try/except: pass` 는 절대 예외가 나지 않아 무의미). 오류는 _error 단일 필드로 덮어씌워져 유실
  4. get_insert_id 는 UPDATE/0행 갱신 후에도 이전 값(lastrowid) 유지
  5. 연결 수명: `__del__` 에서 disconnect 호출, 싱글턴 엔진은 종료 시까지 유지되며 MySQL 재연결/핑 없음 (autocommit=True 이므로 transaction() 도 무의미)
- 재현: transaction() 안에서 INSERT 후 예외 -> 롤백 안 됨(행 1건 잔존). WITH 쿼리 records=[]. PRAGMA records=[]. 잘못된 INSERT -> executed False 만 반환. UPDATE 0행 후에도 get_insert_id()==이전 값.
- 확인 수준: 재현

## COR-23 [중간] 스케줄러/서비스 기동 결함 (서비스 중복 실행, 보관 정책 미적용, 진입점 인자 무시)
- 위치: src/namifax/services/scheduler.py:41-48(job_cron_maintenance 는 `-t` 만 전달), :50-57(`count = export_phonebook()` 는 0/종료코드를 "entries" 로 로그), 폴백 스레드는 phonebook 만 실행; src/namifax/main.py:63-70(serve_main 이 argv=None 일 때 `parse_known_args(argv or [])` 로 sys.argv 무시), systemd/namifax.service(NAMIFAX_ENABLE_SCHEDULER=1) + systemd/namifax-scheduler.service 동시 사용 시 이중 스케줄; production.ini/development.ini(waitress 6543) vs serve_main(wsgiref, 0.0.0.0:8000) 이원화
- 증상:
  1. 스케줄된 cron 은 `-i/-d/-p` 를 전달하지 않아 인박스/아카이브 보관 정책과 TIFF 정리가 스케줄에서는 전혀 실행되지 않음(임시폴더 정리만). 정책 값을 설정하는 화면/DB 도 없음
  2. namifax.service 는 내부 스케줄러를 켜고, 별도 namifax-scheduler.service 도 같은 잡을 실행 -> 잡 중복(동시 sqlite 접근과 결합해 COR-01)
  3. `namifax-server --port 9911 --host 127.0.0.1` 같은 인자가 무시되고 항상 0.0.0.0:8000 으로 바인드 (진입점 namifax-server 경로)
  4. `pserve development.ini`(waitress) 경로는 스케줄러를 기동하지 않고 같은 싱글턴 DB 를 다중 스레드로 공유. 서버 구현체가 wsgiref 이라 운영용으로 부적합 (waitress 는 의존성만 있고 serve 에서는 미사용)
  5. APScheduler 잡은 영속 저장소가 없어 자정에 프로세스가 내려가 있으면 실행이 영구 누락
- 재현: serve_main 을 sys.argv=["namifax-server","--port","9911","--host","127.0.0.1"] 로 실행하고 make_server 를 계측 -> "BIND 0.0.0.0 8000". 나머지는 코드 확인(추론).
- 확인 수준: 재현(3), 추론(1,2,4,5)

## COR-24 [중간] 설정 키 체계 불일치: 같은 디렉터리를 서로 다른 환경변수로 참조
- 위치: src/namifax/cli/faxrcvd.py:39 (`AVANTFAX_ARCHIVE`), src/namifax/services/storage_lifecycle.py:29 및 cloud_storage.py:47, cover_studio.py:31 (`NAMIFAX_ARCHIVE_DIR` 등), notify.py(`ARCHIVE_SENT`, `AVANTFAX_TMPDIR`), cron.py(`AVANTFAX_TMPDIR`), faxcover.py(`AVANTFAX_INSTALLDIR`)
- 증상: faxrcvd 가 쓰는 보관소와 lifecycle/cloud/커버 서비스가 보는 보관소가 별개 변수라 한쪽만 설정하면 -p 정리나 스토리지 연동이 엉뚱한 경로를 본다. 모든 키가 환경변수뿐이고 systemd 유닛과 ini 어디에도 정의가 없다(레거시 local_config.php 대체 수단 부재). 이름이 AVANTFAX_*/NAMIFAX_* 로 혼재.
- 확인 수준: 추론 (코드 대조)

## COR-25 [중간] 이중 트리/패키징: namifax 가 avantfax 를 import 하지만 휠에는 avantfax 가 없고, CLI 서브커맨드 5개가 avantfax 전용
- 위치: src/namifax/main.py:172-190 (`from avantfax.cli import ocr_import/create_thumbnails/import_users/import_blacklist/reroute`), src/namifax/services/{printer,smtp_settings,storage_lifecycle,webauthn,ocr}.py 와 views/modals.py 의 `from avantfax...` (29곳), pyproject.toml(uv_build 기본 모듈 = namifax)
- 증상: `uv build --wheel` 결과물은 namifax/ 만 포함(avantfax 0개, PHP 브리지 24개 포함). 설치형 배포에서는 위 모듈 import 가 ModuleNotFoundError. systemd 는 PYTHONPATH=/opt/namifax/src 로 가려져 있음. import-users/import-blacklist 는 `--help` 를 파일명으로 취급("Error: File not found: --help"), ocr-import 는 "You must enable ENABLE_OCR_SUPPORT in local_config.php first"(레거시 문구)만 출력. 두 트리의 파일이 45개 이상 내용이 다르고(예: avantfax faxqueue.create_job 이 1001 을 그냥 반환하는 스텁, avantfax mailer.send_mail 존재 여부 상이), 어느 쪽이 실제 사용되는지는 모듈별로 섞여 있음 (namifax 가 주, 위 5개 CLI 와 일부 서비스만 avantfax). K14 는 문서 측면, 이 항목은 런타임/패키징 영향.
- 재현: 휠 namelist 집계 {'namifax': 324, dist-info 5} (avantfax 없음), 24개 .php 포함. `namifax import-users --help`, `namifax ocr-import --help` 출력 확인. avantfax 의존 모듈의 설치형 ImportError 는 코드 확인(추론).
- 확인 수준: 재현(휠 구성, CLI 동작), 추론(설치형 ImportError)

## COR-26 [중간] print_in(CUPS 인쇄-팩스) 경로가 실제로 큐에 넣지 않고 "enqueued" 를 출력하며 진입점에도 미등록
- 위치: src/namifax/cli/print_in.py, src/namifax/services/printer.py:process_inbound_print_job (주석 "In real operation, queue via sendfax/FaxQueue" 후 dict 반환), pyproject.toml [project.scripts] 및 main.py 서브커맨드에 print-in 없음
- 증상: [[FAX: 번호]] 태그를 인식해도 sendfax/FaxQueue 호출이 없어 전송되지 않는다. "Job successfully enqueued for N" 를 출력하고 종료코드 0 -> CUPS 는 성공으로 간주, 팩스는 소실. 태그가 없으면 "Saved to drafts" 라고 출력하지만 드래프트 저장소가 존재하지 않는다. 실행 가능한 진입점(스크립트/서브커맨드)도 없음.
- 확인 수준: 추론 (코드 확인: 큐 호출 부재, 진입점 미등록 grep)

## COR-27 [중간] OCR 서비스: 미연결 엔진 + MySQL 전용 DDL -> 인덱싱/검색이 영구 불능 (K12/K16 의 원인 차원 변형)
- 위치: src/namifax/services/ocr.py:10-30 (`from avantfax.db.engine import DatabaseEngine; self.db = DatabaseEngine()` 미연결, `CREATE TABLE FaxOCR ... AUTO_INCREMENT ... INDEX ... ENGINE=InnoDB` 를 SQLite 로 실행하고 예외 대신 executed=False 로 흡수), :100-130 (`existing = self.db.query(...)` 의 QueryResult 는 항상 truthy, `rows[0]` 불가)
- 증상: OcrService() 는 연결 없는 엔진을 가져 모든 쿼리가 "No active database connection" 으로 조용히 실패. 연결하더라도 DDL 이 SQLite 에서 실패. K12 를 고쳐도(faxname) OCR 인덱스는 저장되지 않고 search_faxes 는 항상 빈 결과. pytesseract 는 tesseract 바이너리 필요(의존성에 미기재). helpers.bardecode/ocr_faxcontent 는 항상 None 을 반환하는 스텁이라 faxrcvd 의 바코드 라우팅과 OCR 본문 저장이 영구 비활성.
- 재현: `OcrService().db._conn is None` -> True, `index_fax("f","/nonexistent.tif",1)` -> False. bardecode/ocr_faxcontent 스텁은 코드 확인.
- 확인 수준: 재현(연결 없음), 추론(DDL 실패는 구문상 확실, 미실행)

## COR-28 [중간] archive_base: 파일 삭제 불능, 미리보기 파일명 불일치, 권한 조건 생성 오류
- 위치: src/namifax/services/archive_base.py:delete_fax, load_vals(PREVIMG="page"), search_archive(else 분기 `({target_routes} OR userid = ...)`), src/namifax/common/helpers.py:static_preview(`preview{i}.png` 저장), src/namifax/services/archive_in.py:rotate_fax
- 증상:
  1. faxrcvd 는 절대 경로를 faxpath 로 저장하는데 delete_fax 는 `os.path.join(installdir="", faxpath.lstrip("/"))` 로 상대 경로를 만들어 파일을 지우지 못함. DB 행만 삭제되고 디스크에 고아 파일 잔존 (cron -d 포함)
  2. static_preview 는 preview0.png 로 저장하나 FaxPDFArchive 는 page0.png 를 참조(레거시는 prev0.gif) -> 웹 미리보기 경로와 삭제/회전 대상이 모두 불일치
  3. rotate_fax 는 TIFF 를 열어 둔 채 같은 경로에 저장하는 구조이고 예외를 삼켜 회전이 일어나지 않아도 True 반환 (비대칭 이미지로 확인: 회전 후 픽셀 불변)
  4. search_archive 는 sentrecvd 가 "s"/"r"/"*" 가 아니거나 권한 경로가 없는 비슈퍼유저에 대해 SQL 에 `None` 을 문자열로 삽입해 "no such column: None" 오류 -> 조용히 0건 반환
- 재현: faxrcvd 로 만든 fid 의 delete_fax -> True, 디렉터리/파일 그대로(fax.pdf, fax.tif, thumb, preview0/1). rotate 후 (5,5) 픽셀 0 유지. `FaxPDFArchive().search_archive({"sentrecvd":"x","userid":5})` -> 0, error "no such column: None".
- 확인 수준: 재현

## COR-29 [중간] 스키마 PK/컬럼 불일치로 엔티티 기반 CRUD 가 실패하는 테이블
- 위치: src/namifax/models/entities.py vs src/namifax/db/schema.py: BarcodeRoute(엔티티 PK barcode_id, 스키마 bcr_id), SysLog(엔티티 syslogid, 스키마 log_id), UserPasswords(COR-18), AddressBookFAX(COR-06), DynConf(COR-08)
- 증상: Repository/MDBObject 경로(load, save, delete)가 "no such column" 으로 실패하고 조용히 False. 서비스(barcode 등)는 자체 raw SQL 로 우회해 일부만 동작하므로 불일치가 잠복.
- 재현: 엔티티 속성 대 PRAGMA table_info 비교 스크립트로 BarcodeRoute(barcode_id 없음), SysLog(syslogid 없음) 확인.
- 확인 수준: 재현 (런타임 실패 경로는 추론)

## COR-30 [중간] 사용하지 않는 PHP 브리지 + bridge_cli 가 요청 파라미터로 임의 바이너리 실행/임의 SQL 허용
- 위치: src/{namifax,avantfax} 아래 *Bridge.php 48개(각 트리 24개), src/namifax/db/bridge_cli.py:~60-140,128 (`auth_pwauth` 의 `binary_path` 를 요청에서 수신, `query` 는 임의 SQL 실행), 인자 모드는 호출마다 새 프로세스라 `connect` 상태가 유지되지 않음
- 증상: Python 코드에서 bridge_cli 나 *Bridge.php 를 참조하는 곳이 없어 죽은 코드이며, 휠에도 24개가 그대로 배포된다. bridge_cli 는 JSON 입력만으로 지정 경로의 실행 파일을 pwauth 로 실행(종료코드 0 이면 로그인 성공)하고 임의 SQL 을 실행한다. 인자 모드에서는 AVANTFAX_DB_FILE 이 없으면 미연결이라 모든 요청이 실패. mypy: `PWAuthBackend.login(service=...)` call-arg 불일치.
- 재현: `bridge_cli.py '{"action":"auth_pwauth","binary_path":"/path/evil.sh",...}'` -> {"success": true}, evil.sh 실행 흔적 파일 생성. `{"action":"query","sql":"select 1"}` -> "No active database connection".
- 확인 수준: 재현

## COR-31 [낮음] 의존성 선언 불일치
- 위치: pyproject.toml, requirements.txt
- 증상:
  - pydantic 은 선언만 되고 src 에서 import 되지 않음. sqlalchemy/models 계층(models/__init__.py, meta.py)도 매핑 클래스가 없고 `sqlite:///:memory:` 기본 엔진을 만들 뿐 request.dbsession 사용처가 없어 죽은 의존성
  - pymysql(COR-12), tesseract 바이너리(COR-27), qrcode(K08)는 코드가 요구하지만 미선언. pam 은 try-import 로 선택 사항이나 선언/extra 없음
  - requirements.txt 는 구버전 고정(SQLAlchemy 2.1.1 등)이며 pillow, boto3, pyotp, webauthn, babel, defusedxml, pytesseract 가 빠져 있고 `-e git+https://github.com/YetOpen/avantfax.git@...#egg=namifax` 라는 외부 저장소를 참조, beautifulsoup4/legacy-cgi 는 pyproject 에 없음
  - pyramid 2.1 이 pkg_resources 를 import (setuptools<81 경고, setuptools 미선언)
- 확인 수준: 재현(grep/uv pip list 로 확인)

## COR-32 [낮음] storage_lifecycle.purge_expired_faxes 가 미연결 엔진과 잘못된 디렉터리 규칙으로 동작
- 위치: src/namifax/services/storage_lifecycle.py:28(`DatabaseEngine()` 미연결), :67-110 (`lastmod` 컬럼 기준, 디렉터리를 `fax{fid}` 이름으로 탐색, 못 찾아도 DB 행 삭제), run_lifecycle 외 호출처 없음
- 증상: 엔진 연결이 없어 records 가 빈 목록이거나(연결 시) 디렉터리를 찾지 못해 파일은 남기고 DB 행만 삭제(faxpath 규칙은 일자/번호/hylafaxid 경로). lastmod 는 faxrcvd/notify 가 채우지 않아 대부분 NULL -> 조건이 성립하지 않음.
- 확인 수준: 추론

## COR-33 [낮음] 파일 경로/권한, 로그 처리
- 위치: src/namifax/common/helpers.py:mkdirs(mode 0o777, 실패를 False 로 반환하나 faxrcvd/notify 는 확인하지 않음), avantfaxlog(syslog 실패를 삼키고 echo 무시, 호출마다 openlog/closelog), src/namifax/common/upload.py:movefile(`mkdir(mode=0o770)`, 복사 실패 시 예외 삼키고 False), src/namifax/cli/notify.py(fatal 분기의 임시 디렉터리 정리에서 OSError 무시, 언어 파일 선택 생략: 사용자 language 를 무시하고 영어 고정)
- 증상: 권한 오류가 있어도 작업이 계속 진행되어 이후 단계가 빈 디렉터리/파일로 오동작. 로그는 syslog 로만 가고 syslog 가 없으면 흔적 없음. 스레드 안전하지 않은 syslog openlog/closelog 반복.
- 확인 수준: 추론

---

### 참고: 정상 동작 확인 항목
- pserve development.ini 로 앱 로드(get_app) 및 /login 200, 보호 경로 401 확인.
- BarcodeRouting, DIDRouting, FaxPDFCategory 의 기본 create/load 는 정상(자체 SQL 사용).
- notify 의 qfile 콜론 분할은 레거시 PHP 와 동일한 한계(값에 ':' 가 있으면 잘림)이므로 회귀가 아님.
- phb 의 개행 없는 PBOOK1.1 출력은 레거시 동일.
