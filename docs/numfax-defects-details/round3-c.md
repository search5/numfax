# 3라운드 C 파일 단위 전수 점검 결과 (services 15개 파일 + 공통 계층)

## 읽은 파일과 줄 수
src/namifax/services (처음부터 끝까지 정독, 총 3,417줄):
user_account.py 474, user_passwords.py 60, archive_base.py 646, archive_in.py 132, archive_out.py 52, faxqueue.py 193, mailer.py 194, covers.py 169, categories.py 126, barcode.py 259, did.py 267, distro.py 177, modem.py 335, addressbook.py 495, dynconf.py 138.
이 목록 밖의 services 파일은 smtp_settings, storage_lifecycle, cloud_storage, printer, totp, cover_studio, webauthn, saml, ocr, scheduler 로 전부 제외 대상이라 추가로 읽을 파일이 없었음.
동작 대조를 위해 함께 읽은 공통 계층(총 1,364줄): db/engine.py 270, db/repository.py 128, db/query.py 163, db/base.py 114, db/schema.py 421, models/entities.py 238, common/validators.py 230(일부), 호출자(web/views/inbox.py, archive.py, outbox.py, views/inbox.py, archive.py, modals.py, helpers.py 의 send_mail) 일부.
대조한 레거시 PHP(총 5,425줄): AFUserAccount, AFUserPasswords, FaxPDFArchive, ArchiveIn, ArchiveOut, FaxQueue, Mailer, Covers, FaxPDFCategory, BarcodeRouting, DIDRouting, DistributionList, FaxModem, AFAddressBook, DynamicConfig(+dynconf.php), legacy/create_tables.sql.

실행 방법: NAMIFAX_DB_PATH 를 scratchpad/agent-r3-c/tN.db 로 지정한 임시 SQLite 에서 서비스 함수를 직접 호출(t1~t8.py). 공격 페이로드는 실행하지 않음.

## 요약
새 결함 31건 (치명 0, 높음 1, 중간 15, 낮음 15). known3.md 의 항목과 같은 원인(barcode_id/bcr_id 불일치, UserPasswords 컬럼 불일치, 불리언 quote, AddressBookFAX 컬럼 부재, 실패 후 성공 메시지 등)은 제외하고, 다른 원인이거나 서비스 계층에서만 보이는 변형만 적었다.

---

## R3C-01 [높음] 모뎀/라우트 목록이 비어 있거나 None 이면 접근 제한이 사라짐 (fail-open)
- 위치: services/archive_base.py:348-356(_prepare_routes_clause), :260-300(search_archive 분기), :112-140(viewable_devices)
- 증상: 레거시는 빈 배열이면 `modemdev = ''` 조건을 만들어 아무것도 보이지 않게 한다. 이식본은 빈 리스트/None 에서 조건이 None 이 되어 분기가 통째로 건너뛰어진다. 모뎀이 하나도 배정되지 않은 비관리자가 받은 팩스 전체를 검색한다. `viewable_devices(None)` 은 sqlroutes 를 "" 로 두어 list_inbox(devices=None)/get_num_faxes(None) 이 전체 수신함을 돌려준다(레거시는 `modemdev = ''`). 기본 분기(sentrecvd 미지정)는 반대로 `AND (None OR userid = ...)` 가 되어 SQL 오류 -> 결과 0건으로 조용히 끝난다.
- 재현: 팩스 2건(ttyS0, ttyS1)을 보관 후 search_archive({sentrecvd:"r", modemdevs:[], userid:5}) = 2건, modemdevs=None 도 2건, sentrecvd "*" 도 2건, ["ttyS0"] 은 1건. 기본 분기는 0건과 오류 "no such column: None". ArchiveIn().list_inbox(devices=None)=2건, devices=[] =0건, get_num_faxes(None)=2 / ([])=0.
- 비고: USR-04/F3-06 은 뷰가 권한 값을 넘기지 않는 문제이고 이것은 서비스가 빈 권한을 "무제한"으로 해석하는 별개 원인이다. 뷰를 고쳐도 모뎀이 없는 사용자에게 남는다.
- 확인 수준: 재현

## R3C-02 [중간] user_has_rights 의 카테고리 비교가 문자열 대 정수라 카테고리 권한만 있는 사용자는 상세 접근이 거부됨
- 위치: services/archive_base.py:91 (`self.dbdata.get("faxcatid") in faxcat`), services/user_account.py:406-410 (get_faxcats 가 str 리스트 반환)
- 증상: 목록 SQL 은 `faxcatid = '1'` 로 비교해 SQLite/MySQL 형 변환으로 일치하지만, user_has_rights 는 파이썬 `in` 이라 int 1 이 ['1'] 에 없다. 그 결과 목록에는 보이는 팩스를 열면 권한 없음이 된다. route 쪽은 str() 로 맞춰 놓았으나 faxcat 은 누락. 레거시 PHP 는 느슨한 == 이라 문제가 없었다.
- 재현: faxcatid=1 인 팩스에 user_has_rights(99, [], [], ['1']) = False, [1] 이면 True.
- 확인 수준: 재현

## R3C-03 [중간] DID 라우팅 모드, RESTRICTED_USER_MODE, INBOX_LIST_MODEM 설정이 아카이브 서비스에 연결되지 않음
- 위치: services/archive_base.py:112(viewable_devices), :144(get_num_faxes), :189(search_archive), :361(list_inbox) 의 플래그 인자. 호출자: views/inbox.py:29, web/views/inbox.py:46-51, views/archive.py:28-39
- 증상: 레거시는 전역 설정($ENABLE_DID_ROUTING, RESTRICTED_USER_MODE, INBOX_LIST_MODEM)을 읽는다. 이식본 서비스는 설정을 읽지 않고 인자 기본값 False 만 쓰며, 앱 안의 어떤 호출자도 enable_did_routing/restricted_user_mode/order_by_modem 을 넘기지 않는다(bridge_cli 만 넘김). web/views/inbox.py 는 DID 사용 시 devices 에 라우트 ID 목록을 만들어 넘기지만 플래그는 넘기지 않아 `modemdev = '<route id>'` 로 필터되어 수신함이 비어 버린다. 설정을 켜는 방법도 없다.
- 재현: 코드 경로 확인(호출자 전수 grep 으로 플래그 전달처 없음 확인). 서비스 단에서 list_inbox(devices=["1"], enable_did_routing=False) 는 modemdev 조건 SQL 생성.
- 확인 수준: 추론(호출자 전수 확인)

## R3C-04 [중간] delete_fax 가 DB 삭제 실패를 무시하고 파일부터 지운 뒤 True 를 반환, prune_archive 는 실패를 세어 성공으로 집계
- 위치: services/archive_base.py:447-485(delete_fax), :486-500(prune_archive)
- 증상: `self.faxarchive.delete_entry(...)` 의 반환을 확인하지 않는다. DB 가 잠기거나 제약에 걸려 행이 남아도 미리보기, TIFF, PDF, 디렉터리를 지우고 True 를 돌려준다. 행은 남고 파일은 사라져 링크가 깨진 팩스가 생긴다. prune_archive 는 delete_fax 결과를 보지 않고 count 를 올려 "N건 정리"로 보고한다. (COR-28 은 파일 삭제 불능, 이것은 반대 방향의 순서/반환 문제)
- 재현: FaxArchive 에 BEFORE DELETE 트리거로 ABORT 를 걸고 delete_fax(fid) -> True, 오류 "locked", 행은 남고 faxes/a1 디렉터리와 파일은 소멸. prune_archive(30) -> 2 반환(실제 삭제 0건).
- 확인 수준: 재현

## R3C-05 [중간] create_fax 가 installdir 접두어를 구분자 없이 잘라 faxpath 가 "/"로 시작, get_pdfpath/get_tiffpath/get_thumbnail/get_faximages 가 절대경로처럼 보임
- 위치: services/archive_base.py:540-546, :585-600(load_vals), archive_out.py:28-32
- 증상: installdir 가 "/x/inst" (끝 슬래시 없음)이면 faxpath 는 "/faxes/a1" 이 되고 pdfpath 는 "/faxes/a1/fax.pdf". 레거시는 `$INSTALLDIR.$path` 문자열 연결이라 동작했으나 이식본 호출자가 `os.path.join(installdir, path)` 를 쓰면 installdir 가 버려져 루트 기준 경로가 된다. delete_fax 안에서만 lstrip("/") 로 보정하고 getter 들은 보정하지 않아 같은 클래스 안에서 규칙이 다르다. (F4-10 은 기존 DB 경로 해석 문제이고 이것은 신규 기록 경로 문제)
- 재현: ArchiveIn(installdir=".../inst").create(".../inst/faxes/a1", ...) -> dbdata.faxpath = "/faxes/a1", os.path.join(inst, get_pdfpath()) = "/faxes/a1/fax.pdf".
- 확인 수준: 재현

## R3C-06 [중간] Repository.update_entry 가 기본키가 없으면 UPDATE 대신 INSERT 로 떨어지고, 서비스들은 set_id 실패를 무시해 잘못된 행을 만들거나 지움
- 위치: db/repository.py:45-58(update_entry 마지막 `return self.data.save()`), services/categories.py:68-76(set_name), :114-125(delete_category); 같은 패턴: covers.delete_cover, did.delete_route, modem.delete_device, barcode.delete_route, dynconf.remove, distro.delete_list, addressbook.delete_cid/remove_contact
- 증상: catid 가 숫자가 아니면 set_id 가 False 를 반환하지만 무시된다. set_name 은 pk 없는 update_entry 가 save() 의 INSERT 로 넘어가 같은 이름의 새 카테고리를 만든다. delete_category 는 같은 인스턴스에서 직전에 create/load 한 행의 id 가 남아 있으면 그 행을 삭제하고 True 를 반환한다.
- 재현: FaxPDFCategory().set_name("Hacked","abc") -> True, FaxCategory 에 catid 3 "Hacked" 신규 생성. c.create("Keep")(catid 4) 직후 c.delete_category("abc") -> True 이며 catid 4 가 삭제됨.
- 확인 수준: 재현

## R3C-07 [중간] QueryBuilder 가 None 조건을 `col = NULL` 로 만들어 영원히 일치하지 않음 (중복 검사/조회 실패)
- 위치: db/query.py:113-116(find), :75-78(update where), services/dynconf.py:529-547(create), 기타 find({... None}) 호출부
- 증상: device=None(모든 모뎀) 규칙의 중복 검사가 작동하지 않아 같은 차단 규칙이 계속 쌓이고, 삭제/조회도 한 건만 대상이 되지 않는다. `IS NULL` 처리가 필요하다.
- 재현: DynConf 테이블을 만든 뒤 d.create(None,"555") 를 두 번 -> 둘 다 True, list_rules 에 device None 행 2개. create("ttyS0","555") 두 번째만 False(정상).
- 비고: ADM-08/COR-08 은 DynConf 테이블 부재이고 이것은 테이블이 있어도 남는 논리 결함.
- 확인 수준: 재현

## R3C-08 [중간] 사용자 생성이 공백 제거한 값으로 검증하고 원본을 저장; 줄바꿈과 유니코드 사용자명 통과
- 위치: services/user_account.py:77-97(검증 vs 저장), :78(`re.match(r"^[\.\w]+$")`)
- 증상: username/email 을 strip() 해서 검증·중복 검사하지만 dbdata 의 원본(앞뒤 공백 포함)을 INSERT 한다. " bob " 으로 만들면 로그인은 "bob" 으로는 실패하고 " bob " 이어야 성공한다. 정규식의 `$` 는 끝 개행 앞에서도 매치되어 "zed\n" 이 통과한다. `\w` 는 유니코드 문자를 허용해 한글 사용자명이 생성되는데 레거시는 ASCII 만 허용했고 HylaFAX 사용자 동기화(faxadduser)와 맞지 않는다. 중복 검사도 공백 차이로 우회된다.
- 재현: create({"username":" bob ","email":" bob@x.com ",...}) -> True, DB 에 "[ bob ]", "[ bob@x.com ]". login("bob") 실패, login(" bob ") 성공. "김철수", "zed\n" 모두 생성 성공.
- 확인 수준: 재현

## R3C-09 [낮음] is_valid_email 이 앞뒤 공백/끝 개행을 허용하고 호출 서비스들은 원본을 저장 (DID, 바코드, 모뎀 연락처, 주소록 이메일)
- 위치: common/validators.py:23-27 (`.strip()` 후 `$` 매치), services/did.py:63-73, barcode.py:231-245, addressbook.py:368-385
- 증상: " a@b.com\n" 이 유효로 판정되고 그대로 contact 에 저장된다. 이후 알림 메일 To 헤더에 개행이 들어가면 EmailMessage 가 ValueError 를 던진다(R3C-21 참조).
- 재현: DIDRouting().create("300","x"," a@b.com\n") -> True, DB 값 "[ a@b.com\n]".
- 확인 수준: 재현

## R3C-10 [중간] 비밀번호 없이 사용자를 만들면 생성된 임시 비밀번호가 어디에도 전달되지 않아 계정을 쓸 수 없음
- 위치: services/user_account.py:99-108, :74-136
- 증상: 레거시 create 는 임시 비밀번호를 생성해 새 사용자 메일로 보낸다. 이식본은 pwdxemail 을 지역 변수로만 쓰고 반환도 저장도 메일도 하지 않는다(create 는 bool 반환). 계정은 wasreset=1 로 만들어지지만 아무도 비밀번호를 모른다. 사용자가 비밀번호 찾기를 써야 하는데 그것도 스텁(F4-02)이라 잠긴 계정이 된다.
- 재현: create({"username":"nopw","email":"np@x.com"}) -> True, 저장된 해시 0ff73150... 로 알 수 있는 평문이 호출자에게 전달되지 않음.
- 확인 수준: 재현

## R3C-11 [중간] change_password/reset_password/update 가 캐시된 dbdata 전체를 되써서 동시 변경을 되돌림 (비활성화한 계정이 되살아남)
- 위치: services/user_account.py:143-147(update), :180-186(change_password), :205-208(reset_password)
- 증상: 레거시는 변경한 컬럼(pwdexpire, password, wasreset)만 갱신한다. 이식본은 로드 시점의 전체 행을 update_entry 로 저장해, 그 사이 관리자가 acc_enabled=0 으로 바꾼 계정이 사용자의 비밀번호 변경 한 번으로 다시 1 이 된다. is_admin, superuser, modemdevs 등 다른 권한 변경도 같은 방식으로 되돌려진다.
- 재현: a.load(2); b.load(2); b.dbdata["acc_enabled"]=0; b.update() -> DB 0. a.change_password("NewPass123") -> True 후 DB acc_enabled=1.
- 확인 수준: 재현

## R3C-12 [중간] AFUserAccount.load() 가 NULL 컬럼을 dbdata 에 반영하지 않아 같은 인스턴스를 재사용하면 이전 사용자의 값이 남음
- 위치: services/user_account.py:323-333 + db/base.py:61-69 (to_dict(include_none=False)) + user_account.py:69-72(load_vals 는 dict.update)
- 증상: load(uid) 는 get_info() -> to_dict() 로 None 값을 버리므로 새 사용자의 NULL 컬럼이 이전 로드 값을 덮지 못한다. 권한 컬럼(modemdevs, didrouting, faxcats)이 NULL 인 사용자가 앞서 로드한 사용자의 모뎀/카테고리 권한을 그대로 갖는다. 또 NULL 키가 get_allvalues 에 없어 KeyError 위험, update() 로 컬럼을 NULL 로 되돌릴 수도 없다. (find 기반 load_username/loadbyemail 은 None 포함이라 정상 -> 경로마다 동작이 다름)
- 재현: modemdevs='ttyS0|ttyS1' 인 uid1 을 load 한 뒤 같은 인스턴스로 load(2) (modemdevs NULL) -> get_modemdevs() 가 여전히 ['ttyS0','ttyS1'].
- 확인 수준: 재현

## R3C-13 [낮음] 로그인 상태 플래그가 성공 시에만 True 로 바뀌고 초기화되지 않음 (admin_logged_in 잔존)
- 위치: services/user_account.py:246-284, :301-321
- 증상: 같은 인스턴스에서 관리자 로그인 후 일반 사용자 로그인(또는 실패 로그인)을 하면 admin_logged_in 이 True 로 남는다. pwdexpired 도 실패 경로에서 초기화되지 않는다. 레거시도 같은 구조이나 이식본은 서비스 객체를 여러 곳에서 재사용할 수 있어 위험이 커졌다.
- 재현: u.login("admin",...,admin=True) 후 u.login("operator",...) -> check_admin_login() True, 이어서 틀린 비밀번호 로그인 -> check_login False, check_admin_login True.
- 확인 수준: 재현

## R3C-14 [낮음] 비밀번호 주기 계산/검사가 레거시와 다름 (pwdexpire NULL 은 만료 아님, 3/6개월을 90/180일로 계산)
- 위치: services/user_account.py:118-125, :171-178, :252
- 증상: 레거시는 `$expire >= NULL`(빈 문자열) 이 참이라 pwdcycle!=0 인데 pwdexpire 가 없으면 즉시 변경을 요구한다. 이식본은 pwdexpire 가 없으면 만료가 아니라서 기존 사용자에게 주기를 켜도 비밀번호를 바꿀 때까지 영원히 적용되지 않는다(update 도 pwdexpire 를 재계산하지 않음). 또 "3/6개월"을 90/180일로 계산해 달력상 만료일이 하루에서 나흘 일찍 온다(mktime 의 month+3/+6 과 다름).
- 재현: pwdcycle=3, pwdexpire=NULL, last_login 설정 사용자로 login -> is_expired() False. create(pwdcycle="3") 의 pwdexpire = 오늘+90일.
- 확인 수준: 재현

## R3C-15 [낮음] reset_password 가 (bool, str|None) 튜플을 반환해 실패도 참으로 평가됨
- 위치: services/user_account.py:190-212
- 증상: 레거시는 bool 이다. `if not svc.reset_password(email):` 식 호출은 (False, None) 이 참이라 실패를 성공으로 처리한다. 현재 호출자는 없지만(forgot 스텁 F4-02) 구현 시 바로 함정이 된다. 또 비활성/삭제 계정도 재설정된다.
- 재현: reset_password("nobody@x.com") -> (False, None), bool(...) True. 존재 계정은 (True, 새 비밀번호).
- 확인 수준: 재현

## R3C-16 [낮음] AFUserPasswords.clear_hashes 가 db 없이 만들어지면 삭제에 성공해도 False 를 반환
- 위치: services/user_passwords.py:49-60
- 증상: self.db 가 None 이면(AFUserAccount() 기본 생성 시 항상) repository.query 결과 [] 를 bool() 해서 성공한 DELETE 가 False 가 된다. db 가 있으면 `:uid` 이름 파라미터가 MySQL 드라이버(%(uid)s)에서 깨진다(COR-12 계열). remove() 는 반환을 무시해 드러나지 않음.
- 재현: UserPasswords 에 uid=9 행을 넣고 AFUserPasswords().clear_hashes(9) -> False, 행은 삭제됨.
- 확인 수준: 재현

## R3C-17 [중간] AFAddressBook.reassign / delete_companyfaxids 가 db 를 명시하지 않으면 아무것도 하지 않고 False 를 반환, 회사 삭제는 팩스번호를 고아로 남김
- 위치: services/addressbook.py:196-204, :260-280, 호출자 views/modals.py:75-90, views/addressbook.py:71-72
- 증상: 두 메서드는 `if self.db:` 일 때만 동작하는데 모든 호출자가 AFAddressBook() 로 기본 생성해 db 가 None 이다. "회사 병합(modal_assign)" 은 항상 실패하고(메시지 없이), 주소록에서 회사를 지울 때 호출되어야 할 팩스번호 삭제도 호출되지 않아 AddressBookFAX 가 고아로 남는다. db 를 넘긴 경우에도 reassign 은 UPDATE 결과를 확인하지 않고 이전 회사를 삭제해(레거시는 결과 확인) UPDATE 실패 시 팩스번호가 지워진 회사를 가리키게 된다(이 부분은 코드 읽기).
- 재현: AFAddressBook().loadbycid(cid) 후 reassign(다른 cid) -> False, 오류 "No abook_id loaded"(COR-07 때문에 abook_id 가 NULL 인 신규 행은 별개). delete_companyfaxids(cid) -> False. (seed 행 대상 확인)
- 확인 수준: 재현(기본 생성 경로), 추론(UPDATE 실패 시 데이터 손실)

## R3C-18 [낮음] 모뎀 상태 표시가 수신 중 발신자 회사 조회(phone_lookup)와 modem-recv-from 클래스를 구현하지 않음
- 위치: services/modem.py:52-61 (레거시 FaxModem.php get_status 의 phone_lookup 분기)
- 증상: 레거시는 "Receiving from" 번호를 주소록에서 회사명으로 바꾸고 class 를 modem-recv-from 으로 바꾼다. 이식본은 번호 문자열 그대로, class 는 항상 modem-recv.
- 재현: parse_faxstat_output 에 `Receiving from "555 1234"` -> {'class':'modem-recv','status':'Receiving from 555 1234'}.
- 확인 수준: 재현

## R3C-19 [낮음] 같은 MailerService 인스턴스로 sendmail 을 여러 번 호출하면 첨부가 중복되고 스풀 목록의 메시지가 동일 객체
- 위치: services/mailer.py:136-184 (attachments 를 매 호출 add_attachment, _current_message 재사용), :71-92(_current_subject 잔존)
- 증상: 두 번째 호출부터 첨부 PDF 가 누적(2개, 3개...)되고 첫 스풀 메시지의 To 도 나중 수신자로 바뀐다. set_message 를 subject 없이 다시 호출하면 이전 제목이 유지된다. 현재 helpers.send_mail 은 호출마다 새 인스턴스라 드러나지 않으나 수신자별 반복 발송 구현 시 바로 발생.
- 재현: spool_mode 로 attach_file 후 sendmail("a"), sendmail("b") -> 마지막 메시지에 application/pdf att.pdf 가 2개, msgs[0] is msgs[1]. 두 번째 set_message 후 제목이 첫 제목으로 유지.
- 확인 수준: 재현

## R3C-20 [중간] embed_image 로 넣은 인라인 이미지가 메일에 전혀 포함되지 않음
- 위치: services/mailer.py:117-134 (저장만 함), :136-184 (sendmail 이 _embedded_images 를 사용하지 않음), common/helpers.py:275-277 (embed_image 호출)
- 증상: embed_image 는 성공(True)을 반환하지만 MIME 에 related 파트가 생기지 않는다. 알림 메일 HTML 의 cid 참조(로고, 썸네일)가 깨진 이미지로 보인다. K13 은 set_cc/attach_file 인자 문제이고 이것은 별개.
- 재현: embed_image("img.png", cid="logo") 후 sendmail -> 파트 목록에 image 파트 없음(multipart/mixed, alternative, text/plain, text/html, application/pdf 뿐).
- 확인 수준: 재현

## R3C-21 [중간] 제목/수신자에 개행이 있으면 set_message/sendmail 이 예외를 던지고 bool 계약을 깨며, 빈 수신자도 스풀 모드에서 True
- 위치: services/mailer.py:76-78, :143-151, :163-165
- 증상: EmailMessage 가 헤더에 개행을 거부해 ValueError 가 try 밖에서 발생한다. notify 는 팩스 설명/발신자명이 들어간 제목을 만들 수 있어(R3C-09 와 합쳐져) 통지 전체가 중단될 수 있다. 수신자가 ""/[] 여도 스풀 경로는 True 를 반환한다.
- 재현: set_message("x", subject="Fax from Bob\nBcc: e@x.com") -> ValueError: Header values may not contain linefeed or carriage return characters. sendmail("a@x.com", subject="bad\nsubj") 도 동일. sendmail("") / sendmail([]) -> True.
- 확인 수준: 재현

## R3C-22 [낮음] 생성 메일에 Date/Message-ID 헤더가 없고 본문 텍스트를 HTML 이스케이프하지 않고 HTML 파트에 삽입
- 위치: services/mailer.py:76-90
- 증상: Date, Message-ID 가 없어 외부 릴레이/스팸 필터에서 감점되거나 거부될 수 있다. `<`, `&` 가 든 설명이 그대로 HTML 본문이 되어 원격 발신자가 정한 문자열(발신자명)이 메일 HTML 로 해석된다(레거시도 이스케이프하지 않았으나 이식본은 수정 기회가 있었음).
- 재현: 스풀된 메시지에 "Date" in msg == False, "Message-ID" in msg == False. set_message("hello <b>x</b> & y") 의 HTML 파트에 `<b>x</b> &` 가 그대로 들어감.
- 확인 수준: 재현

## R3C-23 [중간] SMTP STARTTLS/SSL 이 인증서와 호스트명을 검증하지 않음
- 위치: services/mailer.py:169-180
- 증상: smtplib.SMTP_SSL(...)/starttls() 를 context 없이 호출하면 ssl._create_stdlib_context()(verify_mode=CERT_NONE, check_hostname=False)를 쓴다. 중간자가 SMTP 자격 증명과 팩스 첨부 PDF 를 가로챌 수 있다.
- 근거: 실행 중인 Python 3.14 의 smtplib 소스와 `ssl._create_stdlib_context().verify_mode == 0, check_hostname == False` 를 확인. 실제 SMTP 접속은 하지 않음.
- 확인 수준: 추론

## R3C-24 [중간] rotate_fax 가 회전 후 TIFF 의 해상도 정보를 잃고 원본을 제자리 덮어쓰며 실패를 삼킴
- 위치: services/archive_in.py:60-105
- 증상: Pillow 의 rotate() 결과는 dpi/resolution 태그가 없어 저장된 TIFF 의 해상도가 204x196 에서 1x1 이 된다. 팩스 뷰어/변환기가 페이지 크기를 잘못 계산한다(F1-05 는 읽기 측 PDF 문제, F1-07 은 페이지 수 손실). 또 임시 파일 없이 같은 경로에 save 하고 `except Exception: pass` 로 삼켜서 저장 중 실패하면 원본이 손상된 채 True 가 반환된다. `convert` 폴백은 타임아웃과 반환코드 확인이 없다.
- 재현: 2쪽 G4 TIFF (dpi 204x196)를 rotate_fax -> True, 결과 n_frames=1, dpi=(1,1).
- 확인 수준: 재현(해상도 손실), 추론(원본 손상)

## R3C-25 [낮음] 페이지 크기 검증 부재: pagelimit=0 이면 ZeroDivisionError, 음수면 전체 행 반환
- 위치: services/archive_base.py:333-343 (search_archive), :361-375 (list_inbox)
- 증상: pagelimit 0 은 예외(500), 음수는 `LIMIT 0, -1`(SQLite 에서 무제한)이 되어 API(web/app.py 는 limit 을 int 로만 변환)에서 ?limit=-1 로 전체를 덤프할 수 있다. index*limit 는 문자열이 오면 문자열 반복이 된다.
- 재현: search_archive({"sentrecvd":"s","userid":2,"pagelimit":0}) -> ZeroDivisionError.
- 확인 수준: 재현(0), 추론(음수와 문자열)

## R3C-26 [낮음] FaxQueue 가 타임아웃 없는 셸 실행을 생성자에서 수행
- 위치: services/faxqueue.py:92-100(shell_exec), :72-90(auto_process=True 기본)
- 증상: FaxQueue() 는 기본으로 `faxstat -s` 를 즉시 실행한다. views/ajax.py 의 faxalter 나 outbox kill_job 처럼 큐 조회가 필요 없는 호출도 먼저 faxstat 을 돌리고, hylafaxd 가 응답하지 않으면 타임아웃이 없어 요청이 무기한 대기한다(modem.get_status 는 5초 타임아웃이 있음). 예외는 문자열로 삼켜져 stdout 처럼 파싱된다. web/views/outbox.py 는 생성 직후 process_queue 를 다시 호출해 faxstat 이 요청당 두 번 실행된다.
- 근거: 코드 읽기. 재현 없음.
- 확인 수준: 추론

## R3C-27 [낮음] set_note, set_faxcontent 가 DB 갱신 결과를 무시하고 True 를 반환; ArchiveIn.create 는 비원자적
- 위치: services/archive_base.py:415-440, services/archive_in.py:24-40
- 증상: update_entry 실패(잠금, 제약)에도 True 를 반환한다(레거시도 동일하나 set_category 등은 결과를 반환해 불일치). create_fax 가 행을 넣은 뒤 set_modemdev 가 별도 UPDATE 로 inbox 를 켜므로 그 사이 실패하면 스키마 기본값 inbox=0 으로 "발신도 수신도 아닌" 행이 남는다(레거시 스키마의 기본값은 TRUE 였음: create_tables.sql 의 `inbox BOOL DEFAULT TRUE` 대 schema.py 의 DEFAULT 0).
- 근거: 코드 읽기와 스키마 대조.
- 확인 수준: 추론

## R3C-28 [낮음] ARCHIVE_DATE_FORMAT 설정이 반영되지 않고 기본 표기도 레거시와 다름
- 위치: services/archive_base.py:14(DEFAULT_ARCHIVE_DATE_FORMAT), :22-36 (date_format 인자), ArchiveIn/ArchiveOut 생성자(인자 없음)
- 증상: 레거시 기본은 `%d.%m.%Y %H:%i`(예: 29.09.2026 10:00)이고 local_config 로 바꿀 수 있다. 이식본은 기본 `%Y-%m-%d %H:%M` 이며 ArchiveIn/ArchiveOut 은 date_format 인자를 받지 않고 어떤 호출자도 전달하지 않아 설정할 방법이 없다.
- 재현: load_fax 후 get_archstamp() -> "2026-09-29 10:00" 형식.
- 확인 수준: 재현

## R3C-29 [낮음] 고유 제약 위반으로 이름/코드 변경이 실패해도 get_error() 가 비어 있음
- 위치: services/categories.py:68-76, services/did.py:217-227, 기타 set_* (modem, barcode, covers)
- 증상: 스키마의 UNIQUE(FaxCategory.name, DIDRoute.routecode 등) 때문에 중복 이름으로 바꾸면 UPDATE 가 실패해 False 가 반환되지만 error 는 None 이라 화면에는 빈 오류가 나온다(create 는 사전 조회로 메시지를 만든다). 레거시 스키마에는 UNIQUE 가 없어 이 상황 자체가 이식본에서 새로 생김.
- 재현: FaxPDFCategory().set_name("A", B의 catid) -> False, get_error() None. DIDRouting.set_routecode("200") 중복 -> False, None.
- 확인 수준: 재현

## R3C-30 [낮음] DistroList.lastmod_date, UserAccount.last_mod, FaxArchive.lastoperation 이 갱신되지 않음
- 위치: db/schema.py:10-40(컬럼 TEXT, 기본값/트리거 없음), services/distro.py:401-440
- 증상: 레거시 MySQL 은 각 테이블의 첫 TIMESTAMP 컬럼이 ON UPDATE CURRENT_TIMESTAMP 로 자동 갱신된다. SQLite 스키마는 TEXT 이고 서비스도 값을 쓰지 않아 목록의 "마지막 수정 일시" 는 항상 NULL 이다.
- 재현: add_entries 후 DistroList 행의 lastmod_date None.
- 확인 수준: 재현

## R3C-31 [낮음] FaxPDFArchive.search_archive 의 superuser + DID 모드 "*" 분기가 레거시와 다르게 userid 필터를 적용
- 위치: services/archive_base.py:289-296
- 증상: 레거시 DID 모드의 superuser "*" 분기는 userid 필터가 없다(모든 팩스). 이식본은 모뎀 모드의 분기와 합쳐 `if userid:` 로 userid 필터를 걸어 DID 모드의 관리자가 자기 팩스만 본다.
- 근거: FaxPDFArchive.php 의 ENABLE_DID_ROUTING 분기와 대조(R3C-03 의 플래그가 켜진 경우에만 해당).
- 확인 수준: 추론

---

## 새 결함이 없다고 판단한 영역
- user_passwords.py: log/password_used 의 컬럼 불일치는 COR-18/ADM-20 과 같은 원인이라 제외(clear_hashes 반환만 R3C-16).
- covers.py, did.py, distro.py, modem.py, barcode.py 의 CRUD 와 set_* : 레거시와 같은 구조. barcode 의 PK 이름(barcode_id 대 bcr_id)은 ADM-07, 빈 테이블에서 get_*() 가 None 을 주는 차이는 호출자가 모두 `or []` 로 받아 영향 없음(확인).
- faxqueue.py 의 파서(parse_queue_output): 실제 faxstat -s/-d 형식의 샘플 출력으로 레거시와 동일한 결과를 확인. 명령 주입은 COR-10 으로 이미 보고.
- archive_out.py: create 는 레거시와 동등(NOW() 대신 로컬 시각 문자열, inbox=0).
- dynconf.py 의 lookup/분기: 레거시와 동일(테이블 부재는 COR-08).
