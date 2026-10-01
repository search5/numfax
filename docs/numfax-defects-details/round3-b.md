# 3라운드 B: views 파일 단위 전수 정독 결과

## 읽은 파일과 줄 수 (src/namifax/views, admin.py, settings.py, auth.py 제외)
ajax.py 352, helpers.py 346, modals.py 237, inbox.py 163, outbox.py 48, archive.py 88, sendfax.py 144, addressbook.py 199, distrolist.py 122, webauthn.py 170, saml.py 72, forbidden.py 39, notfound.py 7, default.py 10, __init__.py 0 (합계 약 1997줄).
호출 대상 확인을 위해 함께 읽은 파일: services/addressbook.py, distro.py, archive_base.py, archive_in.py, modem.py, webauthn.py, saml.py, avantfax/services/mailer.py, faxqueue.py, security.py, routes.py, 관련 템플릿(modal_*, emailbook_edit, addressbook_edit, distrolist_edit, archive, home, viewfax, inbox, login, settings의 WebAuthn JS), 레거시 assign.php, email.php, setcompany.php, ajax/*.php, js/ajaxbook.js, emailbook.js, dlcontacts.js, ajaxmodemstatus.js, DistributionList.php.
모든 재현은 NAMIFAX_DB_PATH=scratchpad/agent-r3-b/r3b.db 로 webtest 와 서비스 직접 호출로 수행했다. 공격 페이로드(명령, SQL 주입)는 실행하지 않았다.

---

## R3B-01 [높음] 새 이메일 연락처 폼이 숨은 id=1 을 보내 "추가"가 1번 연락처를 덮어쓰고 "삭제"가 1번을 지움
- 위치: templates/emailbook_edit.jinja2:54-55 (`value="{{ contact.id or 1 }}"`), 61 (삭제 버튼 무조건 표시), views/addressbook.py:429-447, 431-436
- 증상: `/emailbook/edit` (신규)에서 이름과 주소를 입력해 저장하면 숨은 email_id=1 때문에 `if eid:` 분기로 들어가 새 행이 생기지 않고 기존 1번 연락처의 이름과 주소가 교체된다. 같은 폼의 삭제 버튼(confirm 만 있음)을 누르면 1번 연락처가 삭제된다. 신규 연락처는 이 화면으로는 절대 만들어지지 않는다.
- 재현: GET /emailbook/edit 의 폼에서 email_id=1, abookemail_id=1 확인. contact_name="Brand New", contact_email="brandnew@example.com" 제출 후 SELECT 결과 abookemail_id=1 이 "Jane Doe"에서 "Brand New"로 바뀌고 행 수는 그대로.
- 확인 수준: 재현

## R3B-02 [높음] 배포목록 도우미가 회사 ID 를 목록 항목으로 저장하고, 레거시 "fnid|팩스번호" 형식은 ajax/dlist 와 목록 화면이 해석하지 못함
- 위치: views/helpers.py:19-25, 32-36 (option value 가 cid), views/ajax.py:173-176 (entries 전체를 "; " 로 결합), views/distrolist.py:23-26 (entry 를 company 와 faxnumber 양쪽에 그대로 표시)
- 증상: /helper/distrolist 에서 선택한 값은 회사 abook_id 인데 DistroList.listdata 에 그대로 추가된다. /ajax/dlist 는 그 값을 팩스 번호처럼 반환하므로 sendfax 대상이 "1; 5; 77" 같은 번호가 된다. 레거시는 항목을 "fnid|팩스번호" 로 저장하고 ajaxdlist.php 가 explode("|")[1] 만 추출했다. 레거시에서 이관된 목록은 새 코드에서 "12|5551234" 전체가 번호로 나가고, 목록 화면은 회사명과 팩스번호 칸에 같은 원문을 출력한다. 도우미는 lastmod_user 도 설정하지 않는다(레거시는 set_moduser(uid)).
- 재현: POST /helper/distrolist dl_id=1, myselect[]=1,5 후 listdata 가 '1234567:9876543:1:5' 가 되고 GET /ajax/dlist?dl_id=1 이 "1234567; 9876543; 1; 5" 반환. 레거시 형식은 legacy/avantfax/ajax/ajaxdlist.php 와 js/ajaxbook.js('mix' = fnid|faxnum) 근거.
- 확인 수준: 재현 (레거시 형식 해석 부분은 레거시 코드 근거)

## R3B-03 [높음] /assign 모달: 회사명 변경 분기는 회사를 로드하지 않아 항상 무동작이고, 회사 병합(reassign)은 db 없는 인스턴스라 항상 실패하는데 결과는 조용함
- 위치: views/modals.py:75-94. services/addressbook.py:201, 270 (`if self.db:` 가드), set_company:124
- 증상: (a) regexp 분기는 `ab.loadbycid` 없이 `ab.set_company(regexp)` 를 호출하므로 abook_id 가 None 이라 항상 "No abook_id loaded" 로 실패하는데 반환값을 무시하고 message="Company updated successfully" 를 설정한다. 또한 이 입력칸(레이블 "Search Company Name", placeholder "filter")은 필터용인데 제출하면 회사명 변경으로 해석된다. (b) myselect 분기는 `AFAddressBook()` 이 db=None 이라 `reassign()` 이 `if self.db:` 에서 False 를 반환하고 `arc.reassign` 도 호출되지 않는다. 레거시는 실패 시 "Error reassigning company" 를 보여 줬다. 사용자는 아무 변화 없는 화면을 받는다.
- 재현: POST /assign abook_id=1 myselect=5 후 AddressBook 과 AddressBookFAX 의 abook_id 가 변하지 않음. POST /assign abook_id=99 regexp=Renamed 후 회사명 불변. `AFAddressBook().db` 는 None.
- 확인 수준: 재현

## R3B-04 [높음] 필수 파라미터가 없으면 fid 가 "1" 로 기본값이 되어, fid 없는 POST /delete 가 1번 팩스를 삭제함
- 위치: views/modals.py:17, 71, 123, 150, 173, 210 (`request.params.get("fid", "1")`), views/inbox.py:314, 342, 370, 386
- 증상: POST /delete (fid 생략)가 팩스 #1 의 DB 행과 파일을 삭제한다. /note, /email, /refax, /txreport, /rotate, /setcompany 도 fid 생략 시 1번 팩스에 동작한다. 오타 링크, 스크립트 오류, 북마크가 실제 팩스를 지운다. 레거시는 load_fax 실패 시 종료하거나 inbox 로 이동했다.
- 재현: fid 1 존재를 확인한 뒤 `POST /delete` (파라미터 없음) 응답 200, 이후 SELECT fid FROM FaxArchive WHERE fid=1 이 빈 결과.
- 확인 수준: 재현

## R3B-05 [중간] /note 저장이 팩스의 카테고리를 NULL 로 지움
- 위치: views/modals.py:132 (`arc.set_note(description=desc, category=None, ...)`), services/archive_base.py:420-431
- 증상: set_note 는 전달된 category 를 그대로 faxcatid 에 쓰므로, 메모만 추가해도 기존 카테고리가 사라진다. set_note 는 update 성공 여부와 무관하게 True 를 반환하고 뷰는 반환값을 쓰지 않는다.
- 재현: fax 1 의 faxcatid=2 로 설정 후 POST /note fid=1 description=hello 하면 faxcatid=None, description='hello'.
- 확인 수준: 재현

## R3B-06 [중간] 이메일북 수정 경로가 서비스의 검증을 우회해 빈 이름과 잘못된 주소를 그대로 저장
- 위치: views/addressbook.py:438-447 (`MDBOData("AddressBookEmail").update_entry` 직접 호출, AFAddressBook.update_contact 미사용)
- 증상: 수정 시 이름 비어 있음, 이메일 형식 오류, 다른 연락처와 중복을 전혀 검사하지 않고 저장 후 성공 리다이렉트한다. 서비스에 update_contact 검증이 있지만 호출하지 않는다. USR-03 은 "오류를 삼키고 성공 리다이렉트"이고 이 건은 검증 자체가 호출되지 않는 별도 원인이다. 잘못 저장된 행은 이후 자동완성에서 깨진 주소로 나온다.
- 재현: POST /emailbook/edit email_id=1 contact_name="" contact_email="not-an-email" 후 행이 ('', 'not-an-email') 로 저장됨.
- 확인 수준: 재현

## R3B-07 [중간] 보관함 방향(sentrecvd) 필터 값이 서비스가 이해하는 값과 달라 필터가 무시되고, 비관리자는 잘못된 SQL 이 됨
- 위치: templates/archive.jinja2 (option value "inbox", "sent"), views/archive.py:82, services/archive_base.py:230-300 (서비스는 "s", "r", "*" 만 인식)
- 증상: "Received only"와 "Sent only" 를 골라도 서비스는 마지막 else 분기(전체)로 처리해 같은 결과를 준다. 비관리자(superuser=False)는 이 분기에서 `AND (None OR userid = None)` SQL 이 만들어져 질의가 실패하고 오류가 삼켜져 0건이 된다(view 의 fallback 이 가짜 행을 채움). 레거시 archive.php 는 s/r/* 를 사용했다.
- 재현: FaxPDFArchive.search_archive({"keywords":"foo","superuser":True,"sentrecvd":"inbox"}) 가 방향 필터 없이 1건, superuser=False 는 0건. 같은 조건으로 "s"/"r" 는 각각 다른 결과.
- 확인 수준: 재현 (서비스 직접 호출. 뷰 경로는 F1-10 으로 행 로드가 깨져 결과 행 확인 불가)

## R3B-08 [중간] 보관함 날짜 필터가 원시 YYYY-MM-DD 를 넘겨 종료일이 제외되고, 종료일만 주면 무시되며, 시작일만 주면 그 하루만 검색
- 위치: views/archive.py:83-84, 70-71 (date_from, date_to 를 그대로 전달), services/archive_base.py 날짜 절(start/end), 레거시 archive.php:71-107 (00:00:00 과 23:59:59 로 변환)
- 증상: start 와 end 모두 있으면 `archstamp > 'YYYY-MM-DD' AND archstamp < 'YYYY-MM-DD'` 라서 종료일 당일 팩스가 전부 빠지고 시작일=종료일이면 항상 0건. end 만 있으면 조건이 아예 적용되지 않는다(전체 반환). start 만 있으면 `LIKE 'date%'` 로 그날 하루만 나온다("From" 의미와 다름).
- 재현: 2026-09-15 10:00 팩스에 대해 start=end=2026-09-15 는 0건, start=2026-09-01 end=2026-09-15 도 0건, end 만 2026-09-15 는 전 기간 2건, start 만 2026-09-15 는 해당일 1건.
- 확인 수준: 재현 (서비스 직접 호출)

## R3B-09 [중간] 보관함 faxid 에 유니코드 숫자(예: "²")를 주면 500, 매우 큰 수는 오류가 삼켜져 가짜 결과 표시 (webauthn.py 에 같은 패턴)
- 위치: views/archive.py:80 (try 안에서는 잡힘), 109 (`int(faxid_q) if faxid_q.isdigit()` 가 try 밖 fallback 블록), views/webauthn.py:287 (`str(cred_db_id).isdigit()` 후 int())
- 증상: str.isdigit() 는 "²" 같은 문자에 True 인데 int() 는 ValueError. 보관함은 검색 예외를 삼킨 뒤 fallback 블록에서 같은 int() 를 다시 호출해 500 이 난다. 20자리 숫자는 SQLite OverflowError 가 삼켜져 가짜 "Quarterly Financial Fax" 행이 나온다. webauthn 삭제 뷰는 try 밖이라 같은 입력에서 500 이 될 것이다.
- 재현: GET /archive?faxid=² 는 ValueError 트레이스백(500). GET /archive?faxid=99999999999999999999 는 가짜 행. webauthn 쪽은 K03 (load_by_username 부재) 때문에 그 지점까지 도달하지 못해 코드 근거만 있음.
- 확인 수준: 재현 (archive), 추론 (webauthn.py:287)

## R3B-10 [중간] /ajax/book 이 fnid 에 회사 ID 를 넣고 회사당 1행만 반환해, 이어지는 /ajax/prefillto 가 엉뚱한 레코드(또는 가짜 값)를 읽음
- 위치: views/ajax.py:84-96 (`<fnid>{cid}</fnid>`, AddressBook.faxnum 컬럼 사용), views/ajax.py:139-149 (fnid 를 abookfax_id 로 조회). 레거시 ajaxbook.php 는 팩스번호마다 1행, fnid 는 abookfax_id
- 증상: 레거시 JS(ajaxbook.js)는 fnid 를 "fnid|팩스번호"(mix) 값으로 쓰고 prefillto 는 loadbyfaxnumid(fnid) 로 조회한다. 새 구현은 회사 ID 를 fnid 로 주므로 회사 ID 와 abookfax_id 가 다르면 다른 회사의 팩스 레코드가 조회되거나 전혀 조회되지 않아 "John Doe / 123 Street" 기본값이 채워진다. 여러 팩스번호를 가진 회사는 하나만 나오고, AddressBookFAX 에 있는 실제 번호 대신 AddressBook.faxnum 컬럼만 본다.
- 재현: GET /ajax/book?q=Initech 가 cid=6, fnid=6 반환. 이어서 GET /ajax/prefillto?fnid=6 은 to_person "John Doe"(가짜), GET /ajax/prefillto?fnid=2(실제 abookfax_id)는 "Initech Main".
- 확인 수준: 재현

## R3B-11 [중간] vCard 가져오기: 카드 경계를 무시한 이름 이월, ORG 연결, 연락처 미표시, 기존 회사 팩스번호 누락
- 위치: views/helpers.py:230-272 (이메일 업로드), 275-346 (팩스 업로드)
- 증상: (1) BEGIN:VCARD 에서 current_name 을 초기화하지 않아 FN 이 없는 카드의 EMAIL 이 앞 카드의 이름으로 저장된다. (2) `ORG:Globex;Sales` 의 구분자 ";" 를 제거만 해서 회사명이 "GlobexSales" 가 된다. (3) 이미 있는 회사(두 번째 카드 또는 한 카드의 두 번째 FAX)는 `ab.create()` 가 False 라서 그 팩스번호가 조용히 버려지고 카운트되지 않는다. (4) TEL;TYPE=WORK 는 current_work 에 저장되지 않고(변수가 항상 None) to_voicenumber 가 항상 비어 있다. (5) 가져온 개수 numcontacts 를 화면에 출력하지 않아 성공과 실패를 알 수 없다. (6) 같은 `ab` 인스턴스를 재사용하므로 EMAIL 연락처가 직전에 만든 회사에 연결된다. (7) `"FAX:" in line` 과 `"EMAIL" in line` 이 NOTE 등 임의 줄에 일치한다.
- 재현: 카드 3개(Alice/Globex;Sales, Bob/Globex;Sales 의 FAX, FN 없는 NoName Inc + noname@x.com)를 POST /upload/faxcontacts 로 올리면 회사 "GlobexSales" 생성, 응답 HTML 에 개수 없음, noname@x.com 이 이름 "Bob B" 로 저장됨. (팩스번호 자체는 COR-07 로 저장되지 않음)
- 확인 수준: 재현

## R3B-12 [중간] 대시보드(home) 수신함 카운트 fetch 가 HTML 을 받아 영구히 0 으로 표시
- 위치: templates/home.jinja2:201-208, views/inbox.py:294 (JSON 은 Accept 에 application/json 또는 Authorization 헤더일 때만)
- 증상: `fetch('/inbox')` 기본 Accept 는 */* 이므로 HTML 이 오고 r.json() 이 예외를 던져 catch 로 사라진다. stat-inbox-count 는 초기값 0 그대로다. (설령 JSON 이 와도 F1-08 로 최대 25)
- 재현: GET /inbox Accept: */* 응답 content-type text/html.
- 확인 수준: 재현

## R3B-13 [중간] /email 모달이 팩스 로드 실패를 무시하고 첨부 없는 메일을 보내며 발신자, 파일명, cc, bcc 를 전달하지 않음
- 위치: views/modals.py:29-53. 레거시 email.php:15-27, 78-84
- 증상: 존재하지 않는 fid 이거나 PDF 경로가 없으면 attachment=None 으로 그대로 send_mail 을 호출한다(Mailer 는 첨부가 없으면 조용히 건너뜀). 성공 시 "Email sent successfully". 레거시는 잘못된 fid 면 inbox 로 이동했다. from_addr, filename(fax-회사명.pdf), cc/bcc, 카테고리 지정, 보관 옵션이 전혀 없고 발신자가 기본값("AvantFAX Notification" 계열)이다. 수신자 입력이 ","로 구분되면 create_contacts(";" 분리)가 주소록 자동 등록을 못한다.
- 재현: Mailer.send_mail 을 mock 해 POST /email fid=99999 emails=a@example.com 호출 시 kwargs 가 {to, subject, message, attachment: None, thumbnail: None} 로 호출되고 성공 경로로 진행.
- 확인 수준: 재현

## R3B-14 [중간] WebAuthn 챌린지가 일회용이 아님 (등록, 인증 모두 세션에서 읽기만 하고 삭제하지 않음)
- 위치: views/webauthn.py:180, 223 (`request.session.get(...)`; pop 없음, 성공/실패 후에도 유지)
- 증상: 한 번 발급된 챌린지가 다음 options 호출 전까지 계속 유효해 같은 assertion 을 다시 제출(재전송)할 수 있다. WebAuthn 은 챌린지 일회 사용을 요구한다. 서명 카운터 갱신(update_sign_count 의 `NOW()` 는 SQLite 에서 실패하고 except pass 로 삼켜짐)도 동작하지 않아 복제 탐지로 보완되지 않는다.
- 재현: 코드 읽기 근거(K02, K03 때문에 실행 경로 도달 불가).
- 확인 수준: 추론

## R3B-15 [중간] WebAuthn 등록: credential_id 를 원시 바이트 .decode("utf-8") 하여 실패하고, 성공해도 저장 형식이 인증 조회 형식(base64url)과 다름
- 위치: services/webauthn.py verify_registration_response (`verification.credential_id.decode("utf-8")`), views/webauthn.py:190-202, 230-233
- 증상: py_webauthn 의 VerifiedRegistration.credential_id 는 원시 bytes(설치된 라이브러리 소스로 확인)라서 임의 바이트에 utf-8 디코드는 대부분 UnicodeDecodeError 이고, 뷰는 그 메시지를 400 JSON 으로 노출한다. 설령 디코드되어도 저장값이 base64url 이 아니라서 auth/verify 가 받는 `credential_data["id"]`(base64url)와 `get_credential_by_id` 가 일치하지 않고, authentication options 의 `base64url_to_bytes(cid)` 도 깨진다. K03 을 고쳐도 패스키 등록/로그인은 성립하지 않는다.
- 재현: 라이브러리 구조체 정의(credential_id: bytes)와 뷰/서비스 코드 대조. 실제 인증기 없이는 끝단 재현 불가.
- 확인 수준: 추론

## R3B-16 [중간] /distrolist/edit 의 리다이렉트가 dl_id 를 인코딩 없이 Location 에 넣어 제어문자 입력이 500 을 일으키고 임의 문자열이 반사됨
- 위치: views/distrolist.py:95 (`f"{request.route_url('distrolist')}?dl_id={dl_id}"`), 106
- 증상: POST dl_id 에 줄바꿈이 있으면 webob 이 ValueError("Header value may not contain control characters")를 던져 잡히지 않고 500 이 난다. 그 외 값은 "#", 공백, "&" 가 그대로 Location 에 들어가 이후 쿼리를 오염시킨다. 존재하지 않는 dl_id 도 성공처럼 리다이렉트한다(업데이트 미실행).
- 재현: POST /distrolist/edit dl_id="1&x=\r\nSet-Cookie: a=b" listname=zz 에서 ValueError 트레이스백. dl_id="abc#frag x" 는 Location: http://localhost/distrolist?dl_id=abc#frag x.
- 확인 수준: 재현

## R3B-17 [낮음] 배포목록 도우미는 dl_id 가 없으면 기본값 1 번 목록에 항목을 추가함
- 위치: views/helpers.py:14 (`request.params.get("dl_id", "1")`), 레거시 distrolist_helper.php 는 list 로드 실패 시 중단
- 증상: dl_id 없이 POST 하면 목록 #1 이 수정된다. 페이지를 dl_id 없이 열어도 폼 hidden 값이 "1" 이 되어 잘못된 목록에 추가된다.
- 재현: POST /helper/distrolist myselect[]=77 (dl_id 없음) 후 목록 1 의 listdata 끝에 ":77" 추가.
- 확인 수준: 재현

## R3B-18 [낮음] 이메일북 목록 및 자동완성이 `"이름" <주소>` 문자열을 재파싱하여 이름에 따옴표나 "<" 가 있으면 주소가 깨짐
- 위치: views/addressbook.py:403-406, views/ajax.py:113-120 (services/addressbook.py:421 이 문자열로 합친 뒤 뷰가 split("<"))
- 증상: 이름이 `Tom "TJ" <Smith>` 이면 목록의 이메일이 `Smith"` 로, 이름은 따옴표가 제거된 `Tom TJ` 로 표시되고 /ajax/emailbook 이 `<email>Smith&quot;</email>` 을 반환한다. 원본 행(contact_email)은 멀쩡한데 뷰가 구조화 데이터를 문자열로 만들었다 다시 분해한다. 또 레거시 ajaxemailbook 는 `"이름" <주소>` 전체를 돌려줘 표시 이름이 수신자에 유지됐지만 새 구현은 주소만 돌려 이름이 사라진다.
- 재현: contact_name=`Tom "TJ" <Smith>`, contact_email=tj@x.com 등록 후 GET /emailbook 과 GET /ajax/emailbook?q=tj 에서 `Smith"` 확인.
- 확인 수준: 재현

## R3B-19 [낮음] 회전 링크가 원시 JSON 페이지로 이동하고, viewfax 는 이전/다음 탐색 컨텍스트를 전혀 전달하지 않음
- 위치: templates/inbox.jinja2:160, templates/viewfax.jinja2:45 (href="/faxes/rotate/{id}" , redirect 파라미터 없음), views/inbox.py:378-380, views/inbox.py:328-336 (prev_fid, next_fid 미전달), templates/viewfax.jinja2:34-40
- 증상: "Rotate" 클릭 시 브라우저가 `{"status": "ok", "fid": "1", "rotation": 90}` JSON 화면으로 이동하고 원래 화면으로 돌아오지 않는다(뷰는 ?redirect=inbox 만 지원하는데 링크가 붙이지 않음). viewfax 템플릿이 prev_fid, next_fid 를 쓰지만 뷰가 넘기지 않아 이전/다음 버튼이 영원히 안 보인다(ArchiveIn.get_fid_prev/get_fid_next 는 있음).
- 재현: GET /faxes/rotate/1 → application/json. GET /viewfax?fid=1 응답에 "Previous"와 "Next" 없음.
- 확인 수준: 재현

## R3B-20 [낮음] /ajax/archivefax 가 목록 중 잘못된 ID 를 만나면 나머지를 처리하지 않고 200 으로 응답
- 위치: views/ajax.py:196-204 (int() 예외가 for 밖 try 에서 잡혀 반복 중단)
- 증상: fids="1,abc,50" 이면 1만 보관되고 50 은 보관되지 않는데 200 빈 응답. 존재하지 않는 fid 도 조용히 무시. 레거시는 항목별로 계속 처리하고 로그를 남겼다.
- 재현: fax 1, 50, 51 모두 inbox=1 에서 POST /ajax/archivefax fids=1,abc,50 후 1만 inbox=0.
- 확인 수준: 재현

## R3B-21 [낮음] SAML 메타데이터/AuthnRequest 가 Host 헤더로 만든 URL 을 XML 에 이스케이프 없이 삽입
- 위치: views/saml.py:13-16 (`request.application_url`), services/saml.py generate_sp_metadata, create_authn_request (f-string)
- 증상: Host 헤더에 따옴표와 꺾쇠가 있으면 entityID, ACS, SLS 값과 XML 구조가 깨지거나 조작된다. 또한 IdP 에 등록하는 entityID 와 ACS URL 이 요청 Host 에 따라 달라진다(호스트 헤더 오염으로 잘못된 ACS 를 광고). 설정 가능한 고정 base URL 이 없다.
- 재현: GET /auth/saml/metadata Host: `evil.example"><x:y/` 응답에 `entityID="http://evil.example"><x:y//auth/saml/metadata">` 출력.
- 확인 수준: 재현

## R3B-22 [낮음] SAML ACS 실패 시 내부 예외 문자열을 인코딩 없이 /login?error= 로 반사
- 위치: views/saml.py:340-341, services/saml.py process_saml_response
- 증상: `Invalid SAML XML response: no element found: line 1, column 0` 같은 파서 내부 메시지가 URL 인코딩 없이 Location 에 들어간다. 오류 조건 일부에는 요청 데이터가 섞인다. 또 SAML 사용자 프로비저닝(provision_or_get_user)에서 발생하는 예외는 잡지 않아 500 이 된다(NameID 없음 성공 응답 재현: AttributeError 500, K03 영향). NameID 가 비어 있어도 거부하지 않고 username="" 로 사용자 조회와 JIT 생성을 시도한다.
- 재현: POST /auth/saml/acs SAMLResponse=!!! 시 Location: http://localhost/login?error=Invalid SAML XML response: no element found: line 1, column 0. NameID 없는 Success 응답 제출 시 AttributeError 500.
- 확인 수준: 재현

## R3B-23 [낮음] /auth/saml/sls 는 서명 없는 GET 으로 호출되고 실제 세션을 끊지도 못함
- 위치: views/saml.py:358-364
- 증상: request.session 이 존재하지 않아(K02) hasattr 가드로 아무것도 하지 않고 /login 으로 리다이렉트만 한다. IdP 가 보낸 LogoutRequest 의 서명, NameID, SessionIndex 를 검증하지 않고 LogoutResponse 도 돌려주지 않는다. 현재 인증 쿠키(namifax_session)는 그대로라 "로그아웃" 후에도 로그인 상태가 유지된다.
- 재현: GET /auth/saml/sls 302 이후 GET /inbox 가 200(로그인 유지).
- 확인 수준: 재현

## R3B-24 [낮음] /ajax/modemstatus 가 요청의 modems 파라미터를 무시하고 모든 모뎀을 반환하며, 요청마다 모뎀 수만큼 faxstat 을 재시도할 수 있음
- 위치: views/ajax.py:15-38, services/modem.py:get_status (status 비어 있으면 매번 subprocess, timeout=5)
- 증상: 레거시는 `modems=` 로 요청된(사용자가 볼 수 있는) 모뎀만 응답했지만 새 구현은 전 모뎀 장치명을 모두 노출한다. faxstat 결과가 비었거나 hfaxd 가 응답하지 않으면 모뎀 수 × 최대 5초씩 워커를 붙잡는다. 이 엔드포인트는 permission 이 없어 비인증으로 호출 가능하다(F3-04/SEC-02 의 읽기 쪽).
- 재현: GET /ajax/modemstatus?modems=ttyS0 이 ttyS0, ttyS1 두 행을 반환. faxstat 재시도는 코드 읽기 근거.
- 확인 수준: 재현 (modems 무시), 추론 (faxstat 재시도 지연)

## R3B-25 [낮음] 존재하지 않는 id "1" 을 요청하면 첫 번째 레코드를 대신 보여 주는 폴백이 있음
- 위치: views/addressbook.py:383-384, views/distrolist.py:113-114
- 증상: 삭제된 회사나 목록의 북마크(id=1)로 편집 화면을 열면 다른 회사나 목록의 폼이 그 레코드의 hidden id 로 나타나 사용자가 엉뚱한 레코드를 수정 또는 삭제하게 된다.
- 재현: 코드 읽기 근거.
- 확인 수준: 추론

## R3B-26 [낮음] /setcompany 가 팩스 갱신 성공 여부와 무관하게 회사 카운터를 증가시킴 (GET)
- 위치: views/inbox.py:393-396 (`arc.load_fax` 와 `ab.loadbyfaxnumid/inc_faxfrom` 가 독립). 레거시 setcompany.php 는 set_faxnumid 성공 시에만 inc_faxfrom
- 증상: 존재하지 않는 fid 이거나 이미 같은 faxnumid 인 팩스에 대한 호출도 faxfrom 을 올려 링크를 새로고침하거나 재호출할 때마다 카운터가 부풀고 이전 번호의 카운터는 줄지 않는다. (현재 스키마에는 faxfrom 컬럼이 없어 COR-06 으로 증가 자체도 실패)
- 재현: 코드 읽기 근거.
- 확인 수준: 추론

## R3B-27 [낮음] WebAuthn 자격 삭제는 대상이 없거나 남의 것이어도 success:true
- 위치: services/webauthn.py delete_credential (항상 True), views/webauthn.py:291-292
- 증상: uid 조건으로 타인 자격은 안 지워지지만 응답은 성공이고 영향 행 수를 확인하지 않아 UI 가 잘못된 성공을 보인다. register options 는 excludeCredentials 를 주지 않아 같은 인증기를 여러 번 등록 시도하면 UNIQUE 위반 메시지가 400 으로 그대로 노출된다.
- 재현: 코드 읽기 근거.
- 확인 수준: 추론
