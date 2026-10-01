# 3라운드 F 점검 결과 (db/, models/, web/ 파일 단위 전수 정독)

## 읽은 파일과 줄 수 (src/namifax 기준)

| 파일 | 줄 수 | 비고 |
|---|---|---|
| db/engine.py | 270 | 전부 정독 |
| db/base.py | 114 | 전부 정독 |
| db/query.py | 163 | 전부 정독 |
| db/repository.py | 128 | 전부 정독 |
| db/__init__.py | 19 | 전부 정독 |
| db/schema.py | 421 | 전부 정독 (DDL, 마이그레이션, seed 를 legacy/create_tables.sql 및 db-update-300~335.sql 과 대조) |
| db/bridge_cli.py | 912 | 1-420, 690-912 정독. 420-690 은 동일 패턴의 액션 디스패치라 grep 으로 훑음 |
| db/SQLBridge.php, MDBObjectBridge.php, MDBOBridge.php(일부) | 133, 63, 약 60/136 | 정독 (MDBODataBridge.php 77줄, models/EntitiesBridge.php 99줄은 미정독) |
| models/__init__.py, meta.py, entities.py | 60, 19, 238 | 전부 정독. SQLAlchemy 매핑 클래스는 0개(Base.metadata 는 빈 상태), 실제 쓰이는 체계는 MDBObject(entities.py)와 schema.py |
| web/__init__.py, app.py, session.py | 1, 146, 76 | 전부 정독 |
| web/views/auth.py, inbox.py, outbox.py, archive.py, sendfax.py, admin.py | 60, 134, 71, 164, 89, 140 | 전부 정독 |
| (교차 확인용) services/archive_base.py, archive_in.py, archive_out.py, addressbook.py(1-300), user_account.py, user_passwords.py, smtp_settings.py, totp.py, distro.py, covers/modem/did 의 find 사용부, common/helpers.py(165-260), views/admin.py(345-392, 740-760, 1050-1080), views/modals.py(70-100) | 부분 | 이 영역의 SQL 과 DB 호출 의미를 확인할 때만 읽음 |

실행 환경: NAMIFAX_DB_PATH 를 scratchpad/agent-r3-f/w1/ 아래로 지정하고 cwd 도 같은 하위로 고정. 저장소 소스는 수정하지 않았고 서브에이전트는 쓰지 않았음. 공격 페이로드는 실행하지 않음.

## SQL 참조 교차 검증 결과

방법: src/namifax 전체 .py 를 ast 로 파싱해 SQL 로 시작하는 문자열 200건(f-string 의 치환부는 `1` 로 대체, 문자열 덧셈 포함)을 추출했습니다. schema.py 를 실제로 실행해 만든 SQLite DB 에 `EXPLAIN` 으로 준비해 보고, 결과를 수동 분류했습니다. 별도로 entities.py 의 MDBObject 14개 클래스의 속성을 `PRAGMA table_info` 와 대조했습니다(QueryBuilder 가 만드는 동적 SQL 대상). 스크립트는 scratchpad/agent-r3-f/xcheck.py, ent.py 입니다.

| 참조 위치 | 존재하지 않는 테이블/컬럼 | 기보고 여부 |
|---|---|---|
| services/dynconf.py:66, entities.DynConf | 테이블 DynConf (스키마에는 DynamicConfig) | COR-08, ADM-08 |
| services/barcode.py:101 | BarcodeRoute.barcode_id (실제 PK 는 bcr_id) | ADM-07 |
| entities.BarcodeRoute | barcode_id | ADM-07 |
| entities.SysLog | SysLog.syslogid (실제 log_id) | ADM-20 |
| entities.UserPasswords | upid, pwdhash (실제 pwd_id, password) | COR-18, ADM-20 |
| entities.AddressBookFAX | description, email, faxcatid, faxfrom, faxto, printer, to_location, to_voicenumber | COR-06 |
| services/addressbook.py:151 | AddressBookFAX.email | COR-06 |
| entities.AddressBook | PK abook_id 는 ALTER 로 추가된 비 PK 컬럼(실제 PK ab_id) | COR-07 |
| services/webauthn.py:121~254 | 테이블 UserWebAuthnCredentials (MySQL 전용 DDL 이 SQLite 에서 실패) | K09 |
| services/ocr.py:93~128 | 테이블 FaxOCR (동일 원인) | COR-27 |
| views/admin.py:1063 등 | `key` 컬럼명은 MySQL 예약어 | ADM-19, COR-12 |

신규로 발견된 존재하지 않는 테이블/컬럼: 없음. 위 표의 항목은 모두 known3.md 에 있는 유형입니다. 대신 이 교차 검증에서 나오지 않는 종류의 결함(반환 형태, 트랜잭션, 마이그레이션 순서, 스키마 기본값 드리프트)에서 아래 신규 결함을 찾았습니다. 성능은 FaxArchive 10만 행(82MB)에서 get_num_faxes 0.10초, 이전/다음 탐색 0.16초, 키워드 검색 0.06초로 측정되어 SQLite 에서는 결함으로 보고하지 않습니다.

---

## 결함 목록

### R3F-01 [높음] AFAddressBook 을 기본 생성하면 reassign 과 delete_companyfaxids 가 조용히 실패하고, 회사 삭제가 팩스번호와 이메일 행을 고아로 남김
- 위치: services/addressbook.py:201, 270 (`if self.db:`), views/addressbook.py:68-72, views/modals.py:76-90, views/admin.py:752
- 증상: 뷰가 `AFAddressBook()` 처럼 db 없이 만들면 `self.db` 가 None 이라 `reassign()` 이 오류 메시지 없이 False 를 반환하고(`get_error()` 도 None), 회사 재할당 모달은 아무 일도 하지 않습니다. `delete_companyfaxids()` 도 동일하게 False 이며, 애초에 뷰가 호출하지 않습니다(레거시 addressbook_edit.php:126-127 은 `delete_companyfaxids` 후 `delete_cid` 를 호출). 결과로 회사 삭제 뒤 AddressBookFAX 와 AddressBookEmail 행이 남아 해당 번호의 수신 팩스가 존재하지 않는 회사로 귀속됩니다. db 를 주어 reassign 이 동작해도 AddressBookEmail 은 새 회사로 옮기지 않아 고아가 됩니다. FK 도 없어 DB 가 막아 주지 않습니다.
- 재현: scratchpad/agent-r3-f/r2.py. 시드 DB 에서 `AFAddressBook().loadbycid(1); reassign(2)` 는 False/None. `AFAddressBook(db=db).reassign(2)` 는 True 이나 AddressBookEmail 1번 행은 abook_id=1 로 남음. `delete_cid(2)` 는 True 인데 AddressBookFAX 의 abook_id=2 행이 그대로 남고 AddressBook 만 비어 있음.
- 확인 수준: 재현

### R3F-02 [높음] 쓰기 실패 시 롤백하지 않아 트랜잭션과 쓰기 잠금이 열린 채 남고 다른 프로세스가 "database is locked" 를 받음
- 위치: db/engine.py:130-156 (`except` 에 rollback 없음), 연결 생성 db/engine.py:87 (기본 isolation)
- 증상: UNIQUE 위반 같은 실패한 INSERT/UPDATE 뒤 연결이 `in_transaction=True` 로 남고 RESERVED 잠금을 쥡니다. 이 프로세스가 다음에 쓰기에 성공해 commit 할 때까지 faxrcvd 훅, notify, cron 등 다른 프로세스의 쓰기가 전부 잠금 오류가 됩니다. 웹 프로세스에서 중복 모뎀 등록 같은 흔한 입력 오류 한 번으로 수신 훅이 5초 뒤 실패합니다. 이후 성공하는 쓰기는 그 사이 끼어든 미완료 상태까지 함께 commit 합니다. (F1-04 는 잠금이 길 때의 결과이고, 이것은 잠금을 만드는 원인입니다.)
- 재현: scratchpad/agent-r3-f/e1.py. `INSERT INTO Modems (device) VALUES ('ttyS0')` 중복 실행 -> `executed=False`, `in_transaction True`, 다른 연결의 INSERT 는 1.0초 뒤 "database is locked".
- 확인 수준: 재현

### R3F-03 [높음] seed 의 `INSERT OR REPLACE ... fid=1` 이 수신함이 비어 있는 기존 DB 에서 실제 보관 팩스 #1 을 데모 레코드로 덮어씀 (COR-02, ADM-01 의 다른 원인 변형)
- 위치: db/schema.py:400-420 (조건 `COUNT(*) FROM FaxArchive WHERE inbox = 1` 이 0), 같은 블록의 else UPDATE
- 증상: 수신함 팩스를 전부 보관 처리한 레거시 이관 DB(흔한 상태)에서는 기동할 때 fid=1 이 고정값으로 REPLACE 됩니다. REPLACE 는 행을 지우고 다시 넣으므로 faxpath, pages, description, userid, faxcatid, faxcontent, lastmoduser, 모뎀 정보를 모두 잃고, 원본 팩스 파일은 DB 와 연결이 끊긴 채 남습니다. 수신함에 팩스가 하나라도 있는 DB 에서는 else 분기가 매 기동마다 fid=1 의 inbox 를 1 로 되돌립니다.
- 재현: scratchpad/agent-r3-f/m2.py. inbox=0 인 실제 보관 팩스(fid=1, faxpath 'faxes/real/2019/001', userid 12, faxcontent, description 'Signed contract #881')를 넣고 `init_database_tables` 실행 -> 행이 faxpath 'faxes/2026/09/29/fax001', 'Monthly Financial Report', userid NULL, faxcontent NULL, inbox 1 로 교체됨.
- 확인 수준: 재현

### R3F-04 [높음] 폴백 웹앱 `/api/inbox/list` 가 종료되지 않는 무한 루프에 빠지고 메모리가 계속 늘어남
- 위치: web/views/inbox.py:111 (`while inbox.list_inbox(devices, page, limit, faxcats):`)
- 증상: `ArchiveIn.list_inbox` 는 매번 같은 페이지의 행 리스트를 돌려주는 메서드이고 소진되는 이터레이터가 아니라서, 수신함에 팩스가 1건이라도 있으면 루프가 끝나지 않습니다. 이 요청을 처리하는 워커가 100% CPU 로 묶이고 items 리스트가 무한히 커집니다. 인증된 사용자가 요청 한 번으로 서버를 멈출 수 있습니다(F5-02 의 폴백 앱이 실제로 뜨는 상황에서). 이 루프는 `inbox.get_modemdev()` 등 로드되지 않은 dbdata 를 읽으므로 설령 끝나도 값이 비어 있습니다.
- 재현: scratchpad/agent-r3-f/w4.py 로 list_inbox 를 계측하면 2000번 호출 뒤에도 매번 len=1 로 truthy. w3.py 로 WSGI 요청을 보내면 20초 타임아웃(1GB 주소공간 제한 하에서도 끝나지 않음).
- 확인 수준: 재현

### R3F-05 [중간] 폴백 웹앱 핸들러가 Session 객체를 받아 AFUserAccount 전용 API 를 호출해 일반 사용자는 전 기능이 500
- 위치: web/app.py:112-124 (session 을 그대로 전달), web/views/inbox.py:90-91,156-161, sendfax.py:452, archive.py:293-294, 389-393
- 증상: `web.session.Session` 은 user_id, username, is_admin, superuser 만 있는데 핸들러는 `user.get_modemdevs()`, `get_faxcats()`, `get_didrouting()`, `uid`, `any_modem` 을 호출합니다. 비 superuser 는 `/api/inbox/list`, `/api/sendfax/options` 가 AttributeError 로 500 이 되고, `/api/archive/search` 는 `hasattr` 폴백으로 빈 권한 목록(`modemdev = ''`)이 되어 항상 0건입니다. `getattr(user, "uid", 0)` 은 항상 0 이라 "내가 보낸 팩스" 권한 판정(`userid` 일치)도 동작하지 않습니다.
- 재현: w2.py/w3.py 로 operator 세션 생성 후 `/api/sendfax/options` -> `AttributeError("'Session' object has no attribute 'get_modemdevs'")`.
- 확인 수준: 재현

### R3F-06 [중간] 폴백 웹앱 로그인이 구조적으로 성공할 수 없음
- 위치: web/views/auth.py:31-43, services/user_account.py 의 login (last_login 검사)
- 증상: (1) `AFUserAccount.login` 은 `last_login is None` 이면 첫 로그인으로 보고 `pwdexpired=True` 로 만들고, AuthHandler 는 만료를 401 "Password expired" 로 돌려주지만 폴백 앱에는 비밀번호 변경 경로가 없습니다. (2) 그 첫 시도가 last_login 을 기록하므로 두 번째 시도는 만료를 통과하는데, 그 뒤 `user.username` 을 읽다가 AFUserAccount 에 `username` 속성이 없어 AttributeError(500)가 납니다. 세션은 한 번도 만들어지지 않습니다. (시드 admin 비밀번호가 평문이라 첫 시도부터 실패하는 K10 은 별개이며, 해시를 고쳐도 위 문제가 남습니다.)
- 재현: w.py. 시드 비밀번호를 md5 로 바꾼 DB 에서 1회차 `401 Password expired`, 2회차 `AttributeError("'AFUserAccount' object has no attribute 'username'")`.
- 확인 수준: 재현

### R3F-07 [중간] 폴백 웹앱 입력 처리 부재와 가짜 팩스 발송
- 위치: web/app.py:55,62-66,112-113,120 (int 변환), web/views/sendfax.py:483,506-511
- 증상: (a) `page`/`limit` 쿼리에 숫자가 아닌 값이 오면 ValueError 로 500(재현). limit 상한과 음수 검사가 없습니다. (b) JSON 본문이 배열이거나 `destinations` 가 문자열이 아니면 AttributeError(재현: 본문이 `[1,2]` 인 로그인 -> `'list' object has no attribute 'get'`). (c) `/api/sendfax/send` 는 `file_paths=[]` 로 호출하고 `secrets.randbelow` 로 만든 가짜 작업 번호와 `success: True` 를 돌려주며 sendfax 를 실행하지 않고 사용자 모뎀 권한도 확인하지 않습니다. (F2-03, F4-07 은 주 앱 경로의 같은 유형이며, 이것은 폴백 앱의 별도 코드입니다.)
- 재현: w3.py `/api/inbox/list` 에 `page=abc` -> ValueError. (c)는 코드 확인.
- 확인 수준: (a)(b) 재현, (c) 추론

### R3F-08 [중간] TOTP 검증이 DB 오류에서 fail-open: 오류나 연결 끊김이면 아무 코드나 통과
- 위치: services/totp.py:34-39 (`is_totp_enabled`), 70-78 (`verify_user_login`: `if not records: return True`)
- 증상: `SELECT ... FROM UserTOTP` 이 실패(잠금, 연결 끊김, 테이블 없음)하면 `records=[]` 가 되어 "2FA 미사용 사용자" 와 같은 경로로 `True` 를 반환합니다. R3F-02 의 잠금이나 일시적 DB 오류가 곧 2FA 우회가 됩니다. (F3-01 은 TOTP 가 로그인에서 호출조차 되지 않는 문제이고, 이것은 호출되더라도 생기는 fail-open 입니다.)
- 재현: scratchpad/agent-r3-f/o1.py. 2FA 를 활성화한 사용자의 틀린 코드 `000000` 은 정상 상태에서 False, `db.disconnect()` 후에는 `verify_user_login` 이 True, `is_totp_enabled` 는 False.
- 확인 수준: 재현

### R3F-09 [중간] enable_totp 가 DELETE 후 INSERT 를 비원자적으로 실행하고 INSERT 실패를 무시한 채 성공과 백업 코드를 반환
- 위치: services/totp.py:47-62
- 증상: 기존 설정을 먼저 지우고 INSERT 결과를 확인하지 않습니다. INSERT 가 실패해도 "enabled successfully" 와 8개 백업 코드를 사용자에게 보여 주는데 DB 에는 아무것도 없어서, 사용자는 2FA 가 켜졌다고 믿지만 실제로는 꺼져 있고(기존 비밀키도 삭제됨) 백업 코드는 무효입니다.
- 재현: o1.py. UserTOTP 테이블이 없는 DB 에서 `enable_totp` -> `{'success': True, 'backup_codes': [...]}`.
- 확인 수준: 재현

### R3F-10 [중간] `find()` 반환 형태가 0건/1건/N건에서 list, dict, list 로 달라 호출부가 중복 행에서 깨지거나 "없음" 으로 오판
- 위치: db/query.py:130-133 (reduce_single), services/covers.py:112-130 (`data.get` 무방비), modem.py:152,205,227, did.py:146,168, barcode.py:145,166, categories.py:106, addressbook.py:221,455 (`isinstance(data, dict)` 만 허용)
- 증상: 같은 키로 2행 이상이 있으면 covers 는 `AttributeError: 'list' object has no attribute 'get'` 로 500, 나머지 서비스는 "존재하지 않는다" 로 판단해 로드도 삭제도 못 합니다. 스키마가 CoverPages.file 에 UNIQUE 를 주지 않고(레거시도 없음) 레거시 이관 데이터에는 중복이 있을 수 있습니다.
- 재현: scratchpad/agent-r3-f/c1.py. CoverPages 에 file='cover.ps' 중복 행을 넣고 `Covers().load_cover('cover.ps')` -> AttributeError.
- 확인 수준: 재현

### R3F-11 [중간] DIDRouting->DIDRoute, FaxPDFCategory->FaxCategory 이름 변경 마이그레이션이 실행 순서 때문에 영원히 동작하지 않음
- 위치: db/schema.py:204-208 (테이블 생성 후 마이그레이션), 215-229
- 증상: `init_database_tables` 가 SCHEMA_STATEMENTS 로 빈 DIDRoute 와 FaxCategory 를 먼저 만들고 나서 마이그레이션이 "새 이름 테이블이 없으면 rename" 을 검사하므로 조건이 항상 거짓입니다. 구 이름 테이블의 데이터는 새 테이블로 오지 않고, `CREATE VIEW IF NOT EXISTS DIDRouting` 도 같은 이름의 테이블이 있어 무시됩니다. 그 뒤 seed 가 빈 DIDRoute 에 샘플 경로 '1000', '1001' 과 카테고리 'Invoices', 'Contracts' 를 채웁니다.
- 재현: scratchpad/agent-r3-f/m1.py. DIDRouting 에 '7001'/'Real Route', FaxPDFCategory 에 'RealCat' 이 있는 DB 를 초기화 -> DIDRoute 에는 샘플 2건만, 실제 데이터는 구 테이블에 고립됨.
- 확인 수준: 재현

### R3F-12 [중간] 새 DB 에 데모 데이터를 심고 위조된 SysLog 감사 기록까지 만든다. 시드 순서 때문에 첫 기동의 시드 회사는 조회 불가
- 위치: db/schema.py:284-420 (특히 388-398, 401-406), 208-209 (마이그레이션이 seed 보다 먼저 실행)
- 증상: 신규 설치에서 운영 DB 에 operator 계정(비밀번호 'password', any_modem=1), 샘플 모뎀 ttyS0/ttyS1, 주소록 Acme/Initech, 존재하지 않는 파일을 가리키는 수신함 팩스 #1(`faxes/2026/09/29/fax001`), 샘플 배포 목록이 생성됩니다. 특히 SysLog 에 고정 일시 2026-09-29 의 "Fax job #12 dispatched ... SUCCESS", "User 'admin' successfully authenticated from IP 127.0.0.1" 이 실제 이벤트인 것처럼 기록됩니다. 또 마이그레이션(`abook_id = ab_id` 보정)이 seed 보다 먼저 실행되어 첫 기동에서 시드 회사의 abook_id 가 NULL 이고 시드 팩스의 companyid 도 NULL 이며, 두 번째 기동에서야 채워집니다.
- 재현: r2.py 의 첫 출력에서 첫 기동 직후 `AddressBook.abook_id` 가 NULL, `AFAddressBook().loadbycid(1)` 이 False.
- 확인 수준: 재현 (COR-07, F1-01 의 시드 측 변형)

### R3F-13 [중간] 스키마 기본값과 제약이 레거시와 달라 새 행의 의미가 바뀜
- 위치: db/schema.py:133-159 (FaxArchive: `inbox INTEGER DEFAULT 0`, `pages DEFAULT 1`), 9-42 (UserAccount: faxperpage* DEFAULT 10, language DEFAULT 'en', username UNIQUE), 49-86 (Modems.device, DIDRoute.routecode, BarcodeRoute.barcode, FaxCategory.name UNIQUE), 160-164 (SysLog.logdate NOT NULL 기본값 없음), 87-93, 27, 261-264 (레거시 TIMESTAMP 자동 갱신 컬럼 lastmod_date, last_mod, lastoperation 이 기본값 없는 TEXT)
- 증상: (1) 레거시 `inbox BOOL DEFAULT TRUE` 가 여기서는 0 이라 inbox 를 지정하지 않고 넣은 행은 곧바로 보관함으로 갑니다. (2) TIMESTAMP 자동 채움이 사라져 DistroList.lastmod_date, UserAccount.last_mod, FaxArchive.lastoperation 은 코드가 쓰지 않는 한 영원히 NULL 이고, SysLog 는 logdate 없는 INSERT 가 NOT NULL 위반으로 실패합니다(레거시 PHP 는 logtext 만 넣음). (3) 레거시에 없는 UNIQUE 가 추가되어 중복 행이 있는 레거시 덤프를 그대로 가져올 수 없습니다. (4) db-update-334 의 AddressBookFAX to_address/to_zip/to_city 컬럼이 스키마에 없습니다.
- 재현: e2.py. `INSERT INTO FaxArchive (faxpath) VALUES ('p')` -> inbox=0, archstamp NULL. `INSERT INTO SysLog (logtext) ...` -> `NOT NULL constraint failed: SysLog.logdate`.
- 확인 수준: 재현

### R3F-14 [중간] 시드 CoverPages 가 레거시 표지 3종 중 1종만 등록하고 이름도 다름
- 위치: db/schema.py:336-339
- 증상: 레거시 create_tables.sql 과 db-update-320 은 'Generic A4'(cover.ps), 'Generic Letter'(cover-letter.ps), 'Generic HTML'(coverpage.html) 를 등록하는데, 여기서는 'Standard Cover'(cover.ps) 하나뿐입니다. static/images 에는 cover-letter.ps 와 coverpage.html 이 들어 있어 사용자가 고를 방법이 없고(Letter 용지, HTML 표지 불가), 관리자가 추가하기 전에는 UI-25 의 표지 선택지가 1개입니다.
- 재현: 시드 DB 의 `SELECT * FROM CoverPages` 1행.
- 확인 수준: 재현

### R3F-15 [중간] 전체 행 write-back 방식 update_entry 로 동시 수정이 서로를 덮어씀 (lost update)
- 위치: services/archive_base.py:408,430,439,508,519, services/user_account.py:147,183,208, archive_in.py:46,55 (`update_entry(self.dbdata)` 로 로드 시점의 전 컬럼을 UPDATE)
- 증상: 로드 시점 스냅샷의 모든 컬럼을 그대로 써서, 사용자가 메모/분류를 저장하는 동안 OCR 이나 훅이 faxcontent 를 갱신하거나 그 반대가 되면 나중에 쓴 쪽이 다른 쪽 변경을 되돌립니다. 사용자 계정도 같은 방식이라 다른 곳에서 바뀐 비밀번호 해시와 권한이 관리자 저장 때 이전 값으로 복원될 수 있습니다.
- 재현: scratchpad/agent-r3-f/lu.py. 같은 fid 를 두 인스턴스가 로드, A 가 `set_note('Operator note')`, B 가 `set_faxcontent('OCR TEXT')` -> 최종 description 이 'Monthly Financial Report' 로 되돌아가고 lastmoduser 는 NULL.
- 확인 수준: 재현

### R3F-16 [낮음] QueryBuilder 가 None 조건을 `= NULL` 로 만들어 영원히 불일치하고, offset 은 limit 없이는 무시됨
- 위치: db/query.py:73-140 (get/find/update/delete 모두 `col = NULL`), 116-120 (`offset` 은 `limit` 이 있을 때만 적용), db/engine.py:184-189 (None -> `NULL`)
- 증상: `find({"alias": None})` 은 alias 가 NULL 인 행이 있어도 `[]` 입니다(IS NULL 을 쓰지 않음). `find(offset=1)` 은 offset 을 조용히 무시하고 전부 반환합니다.
- 재현: e2.py. alias NULL 모뎀이 있을 때 `find('Modems', {'alias': None})` -> `[]`, `find(offset=1)` -> 3행.
- 확인 수준: 재현

### R3F-17 [낮음] QueryBuilder.quote 가 사용자 문자열 "now()", "curdate()" 등을 SQL 함수로 취급하고, bytes 는 repr 로 저장
- 위치: db/query.py:16-22,48-49, db/engine.py:188
- 증상: 회사명이나 설명이 `now()`, `CURDATE()`, `LOCALTIME()` 등과 같으면(공백/대소문자 무시) 값이 아니라 함수로 삽입됩니다. SQLite 에는 NOW(), CURDATE() 가 없어 INSERT 가 "no such function" 으로 실패해 해당 이름의 회사를 만들 수 없고, MySQL 에서는 입력 문자열이 시각으로 저장됩니다. `bytes` 값은 `str()` 을 거쳐 `b'...'` 문자열이 저장됩니다.
- 재현: e2.py. `qb.insert('AddressBook', {'company': 'now()'})` -> False, 오류 "no such function: NOW". `engine.quote(b'ab\xff')` -> `'b''ab\xff'''`.
- 확인 수준: 재현

### R3F-18 [낮음] get_default_engine 이 연결과 스키마 초기화가 끝나기 전에 전역 엔진을 공개함
- 위치: db/engine.py:254-263
- 증상: `_DEFAULT_ENGINE = DatabaseEngine()` 을 먼저 대입하고 그 뒤 connect 와 `init_database_tables` 를 실행하므로, 다른 스레드가 초기화 도중 같은 엔진을 받아 "no such table" 로 실패합니다. 초기화가 실패(`return False`)해도 그 엔진이 영구히 캐시됩니다. 락도 없습니다. 운영에서는 waitress 스레드 여러 개가 첫 요청에 동시에 들어올 때 창이 열립니다(초기화가 짧으면 드묾).
- 재현: scratchpad/agent-r3-f/t2.py. 초기화에 1초 지연을 주입한 상태에서 두 번째 스레드의 `SELECT ... FROM UserAccount` -> `no such table: UserAccount`. 실제 타이밍에서의 발생 빈도는 측정하지 못함.
- 확인 수준: 재현(지연 주입)

### R3F-19 [낮음] PHP 브리지가 호출마다 새 프로세스라 connect 상태가 유지되지 않고, bridge_cli 는 BLOB/날짜를 JSON 직렬화하지 못함
- 위치: db/SQLBridge.php:24-33,36-48, db/bridge_cli.py:12-15,912 이하 main, 각 `json.dumps(res)`
- 증상: PHP 는 호출마다 `python3 bridge_cli.py '<json>'` 를 새로 실행하므로 `connect` 액션으로 연 연결이 다음 `query` 에서 사라지고 "No active database connection" 이 됩니다(환경변수 AVANTFAX_DB_FILE 이 없으면). `quote()` 도 호출마다 프로세스를 띄우며, `genXML` 은 항상 빈 결과 `<noelement>` 입니다. 또 MySQL 의 datetime/Decimal, BLOB 같은 값이 든 결과는 `TypeError: Object of type bytes is not JSON serializable` 로 인자 모드에서 예외로 죽습니다(스트림 모드는 `{"error": ...}` 만 출력).
- 재현: bridge_cli.py 를 인자 모드로 `connect` 후 `query` -> `No active database connection`, `xml` -> `<noelement></noelement>`. `SELECT X'41'` -> TypeError. (COR-30 은 임의 SQL/바이너리 실행 문제로 별개)
- 확인 수준: 재현

### R3F-20 [낮음] SQLite DB 파일이 기본 umask 로 0644 로 만들어져 해시, TOTP 비밀키, SMTP 비밀번호가 다른 로컬 사용자에게 읽힘. 외래키 PRAGMA 도 꺼져 있음
- 위치: db/engine.py:83-93 (권한, PRAGMA 설정 없음)
- 증상: `UserAccount.password`(MD5), `UserTOTP.secret_key`, `SystemSettings.smtp_password` 가 든 파일이 `-rw-r--r--` 입니다(재현: w.db 가 0644). `PRAGMA foreign_keys` 를 켜지 않아 앞으로 FK 를 선언해도 집행되지 않고, journal_mode 기본값(DELETE)이라 읽기와 쓰기가 서로 막습니다(R3F-02 와 F1-04 의 배경).
- 재현: `ls -l w.db` -> `-rw-r--r--`.
- 확인 수준: 재현

### R3F-21 [낮음] MySQL 연결에 재연결/ping 이 없어 wait_timeout 이후 모든 쿼리가 영구히 실패하고 오류는 삼켜짐
- 위치: db/engine.py:64-74, 152-156
- 증상: 연결 1개를 프로세스 수명 동안 쓰며 `ping(reconnect=True)` 나 재시도가 없습니다. MySQL 의 wait_timeout(기본 8시간) 뒤 "MySQL server has gone away" 가 모든 `query()` 에서 나고 `executed=False` 로만 반환됩니다. (COR-12 는 MySQL 드라이버/문법 전반, 이것은 연결 수명)
- 확인 수준: 추론

### R3F-22 [낮음] DatabaseEngine.gen_xml 이 본문의 리터럴 "&amp;" 를 "&" 로 바꾸고 XML 금지 제어문자를 그대로 내보냄
- 위치: db/engine.py:216-233 (`html.escape` 후 `fix_amp` 가 `&amp;amp;` -> `&amp;`)
- 증상: 값이 실제 문자열 `a &amp; b` 이면 올바른 이스케이프는 `a &amp;amp; b` 인데 결과는 `a &amp; b` 라서 XML 파서가 `a & b` 로 읽습니다(원문 손상). 값의 `\x01` 같은 문자는 그대로 출력되어 XML 이 파싱되지 않습니다. 컬럼명(태그명)과 `mysql_style` 의 `name` 속성은 이스케이프하지 않습니다.
- 재현: e2.py. `SELECT 'a &amp; b' AS t, 'x\x01y' AS c` -> `<t>a &amp; b</t>`, `<c>x` + 0x01 + `y</c>`.
- 확인 수준: 재현

---

## 요약
- 신규 결함 22건: 높음 4, 중간 11, 낮음 7
- 치명 0건
- 새로 발견된 "존재하지 않는 테이블/컬럼 참조" 는 없음(전부 기보고 유형)
