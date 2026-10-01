# 5라운드 레거시 페이지 스크립트 대조 결과 (round5-legacy)

범위: legacy/avantfax 루트 PHP 33개, admin/ PHP 21개(일부), ajax/ PHP 13개. NamiFAX 대응은 src/namifax/views/*.py 와 templates/*.jinja2 (실제 라우팅되는 쪽).
이미 보고된 결함(known5.md 452건)과 겹치는 항목은 제외했고, 겹침이 일부 있는 경우 "차이점"만 적었습니다.
실행 환경: scratchpad/agent-r5-legacy/data/r5.db (임시 SQLite), webtest 를 통해 프로세스 내 호출. 공격 페이로드 미사용.
시간 제약(45분)으로 admin 의 conf_* 편집 화면 일부와 upload_* 는 정독 대조까지만 했고 신규 결함은 찾지 못했습니다(표에 표시).

## 레거시 파일별 대조 결과 표

| 레거시 파일 | NamiFAX 대응 코드 | 일치 | 불일치(신규 결함 수) |
|---|---|---|---|
| index.php / check_login.php / logout.php | views/auth.py login_*, logout_view | 기본 흐름 | 0 (기존 SEC-05, F3-22 등으로 이미 보고) |
| inbox.php | views/inbox.py inbox_view | - | 0 (페이징, 가짜값은 기존 F1-08, F1-11, F4-09) |
| viewfax.php | views/inbox.py viewfax_view | 일부 | 2 (R5L-01, R5L-02) |
| file.php / pdf.php | views/inbox.py fax_download_view | - | 0 (기존 F1-15, F4-12, R4Z-02) |
| rotate.php | views/inbox.py fax_rotate_view | - | 0 (기존 USR-05, R3B-19) |
| setcompany.php | views/inbox.py setcompany_view | 일부 | 1 (R5L-07) |
| archive.php / search.php | web/views/archive.py | - | 0 (기존 USR-01, UI-26, R3B-07/08/09) |
| outbox.php | views/outbox.py | 일부 | 1 (R5L-09) |
| sendfax.php | views/sendfax.py | 일부 | 2 (R5L-03, R5L-04) |
| refax.php / txreport.php | views/modals.py refax, txreport | - | 0 (기존 F4-01, F2-08, F2-15) |
| email.php | views/modals.py modal_email_view | 일부 | 1 (R5L-11) |
| settings.php | views/settings.py | - | 0 (기존 UI-01, F4-13, H-15) |
| forgot.php / pwdexpired.php | views/auth.py | - | 0 (기존 F4-02, F4-03) |
| addressbook.php / addressbook_edit.php (rubrica*) | views/addressbook.py | 일부 | 2 (R5L-05, R5L-06) |
| emailbook*.php / emailcontacts.php | views/addressbook.py, helpers.py | - | 0 (기존 R3B-01/06, R3H-10) |
| distrolist.php / distrolist_edit.php / distrolist_helper.php / distrocontacts.php | views/distrolist.py, helpers.py | - | 0 (기존 R3B-02, R3B-17, UI-36, R4U-04) |
| faxcontacts.php / upload_contacts.php / upload_faxcontacts.php | views/helpers.py | - | 0 (기존 R3B-11) |
| ajax/ajaxinbox.php | views/ajax.py ajax_inbox_count | 일부 | 1 (R5L-08) |
| ajax/ajaxbook.php, archivebook.php | views/ajax.py | 일부 | 1 (R5L-12) |
| ajax/ajaxemailbook.php, ajaxprefillto.php, ajaxdlist.php | views/ajax.py | - | 0 (기존 F4-16) |
| ajax/ajaxmodemstatus.php | views/ajax.py | - | 0 (기존 R3B-24) |
| ajax/ajaxarchivefax.php, archivefax.php, delete.php, ajaxdeletefaxes.php, set_note.php | views/ajax.py, modals.py | - | 1 (R5L-14: 감사 로그), 나머지 기존 SEC-03, F3-03, R3B-05 |
| ajax/faxalter.php | views/ajax.py ajax_faxalter + services/faxqueue.py | 일부 | 1 (R5L-13) |
| admin/users.php / users_list.php / deluser.php | views/admin.py admin_users_view | 일부 | 1 (R5L-10) |
| admin/system_logs.php | views/admin.py get_all_syslogs | - | 0 (기존 ADM-02, ADM-26) |
| admin/system_func.php, conf_*.php, fax2email*.php, fax_cat*.php | views/admin.py | - | 0 (기존 ADM-07~10, ADM-22, ADM-23 등) |
| 합계 | | | 신규 결함 14건 |

## 결함 목록

### R5L-01 [중간] viewfax 가 이전/다음 팩스 이동 정보를 전혀 넘기지 않아 이동 버튼이 영원히 안 보임
- 레거시: viewfax.php (get_fid_prev, get_fid_next 를 inbox_data 로 전달, viewfax.tpl 의 이전/다음 링크)
- NamiFAX: src/namifax/views/inbox.py:73-99 viewfax_view 의 반환 dict 에 prev_fid/next_fid 없음. templates/viewfax.jinja2:34,39 는 이 값이 있을 때만 링크를 그림. (services/archive_base.py:155,172 에 메서드는 존재하며 web/views/inbox.py:115 의 죽은 뷰만 호출)
- 증상: 수신함의 팩스 여러 건을 연속 검토하는 레거시의 핵심 흐름(이전/다음)이 불가능.
- 재현: fid 1,2,3 이 있는 DB 에서 GET /viewfax?fid=2 → 응답에 "Previous Fax"/"Next Fax" 문자열 없음(실측 False, False).
- 확인 수준: 재현

### R5L-02 [중간] 수신함에서 이미 보관(inbox=0)된 팩스나 존재하지 않는 fid 도 viewfax 가 정상 화면(200)으로 열림
- 레거시: viewfax.php (load_fax 실패 또는 get_inbox() 거짓이면 Location: inbox.php)
- NamiFAX: src/namifax/views/inbox.py:77-99 (예외 삼킴, 기본값 pages=2 등 사용, 리다이렉트 없음)
- 증상: 보관된 팩스를 수신함 화면 경로로 열 수 있고, 없는 fid 도 200. (기존 UI-07 은 가짜 문서 표시 자체를 다룸. 여기는 "수신함에 없는 팩스 접근 시 inbox 로 되돌리는 가드" 부재.)
- 재현: inbox=0 인 fid 와 fid=9999 에 GET /viewfax → 둘 다 200 OK, Location 없음.
- 확인 수준: 재현

### R5L-03 [중간] 표지도 첨부파일도 없는 팩스 제출이 허용되고 outbox 로 리다이렉트됨
- 레거시: sendfax.php `if (!$error && ($formdata->coverpage || count($fax_data['files'])))` 일 때만 submit_fax. 둘 다 없으면 제출 안 하고 폼 재표시.
- NamiFAX: src/namifax/views/sendfax.py:84-134 는 팩스번호만 있으면 dispatch_sendfax 호출(-n, 파일 없음)하고 항상 /outbox 로 302.
- 증상: 보낼 내용이 없는 작업이 HylaFAX 에 제출되거나(sendfax 설치 시 오류가 나도 무시됨, 기존 F2-03) 성공한 것처럼 보임.
- 재현: POST /sendfax destinations=5551234 (coverpage, file 없음) → 302 Location /outbox.
- 확인 수준: 재현

### R5L-04 [낮음] 단일 수신번호의 공백, 개행, 세미콜론 정규화가 없음
- 레거시: sendfax.php 의 단일 대상 분기에서 ";", " ", "\r", "\n" 제거 후 escapeshellarg. 다중일 때도 `[^\w,#*@\ "]` 이외 문자 제거.
- NamiFAX: src/namifax/views/sendfax.py:86,33,52 는 strip() 만 하고 내부 공백, 개행을 그대로 -d 에 전달.
- 증상: "555 12 34" 나 줄바꿈이 섞인 번호가 그대로 다이얼 문자열이 되어 HylaFAX 가 거부하거나 다른 수신처로 해석. (기존 F2-02 는 다중 수신처 전달 방식, 이 항목은 입력 정리 부재.)
- 확인 수준: 코드 확인

### R5L-05 [중간] 주소록 회사 삭제 시 수신 팩스 재지정과 팩스번호 정리가 없음
- 레거시: addressbook_edit.php delete 분기: RESERVED_FAX_NUM 회사 로드 → FaxPDFArchive::reassign(삭제 회사 → 예약 회사), delete_companyfaxids, delete_cid, 메시지 RUBRICA_DELETED. can_del 권한 필요.
- NamiFAX: src/namifax/views/addressbook.py:69-75 는 ab.delete_cid() 한 번만 호출하고 예외도 삼킨 뒤 목록으로 리다이렉트.
- 증상: 삭제된 회사를 가리키는 FaxArchive 의 회사 연결과 AddressBookFAX 행이 고아로 남음(수신함의 회사명이 사라지거나 엉뚱하게 표시). 삭제 메시지도 없음.
- 재현: 회사(ab_id=1) 삭제 POST 후 AddressBook 에서는 사라지지만 AddressBookFAX 의 abook_id=1 행이 그대로 남음(실측).
- 확인 수준: 재현

### R5L-06 [높음] 주소록 편집이 팩스번호별 속성 편집과 복수 번호 관리를 지원하지 않음
- 레거시: addressbook_edit.php 는 회사 1개에 팩스번호 N개를 abookfax_id[] 배열로 받아 번호마다 description, faxcatid, faxnumber, to_person, to_location, to_voicenumber, to_address, to_zip, to_city 를 save_settings 로 갱신하고, new_* 필드로 번호를 추가함.
- NamiFAX: src/namifax/views/addressbook.py:60-111 은 company, faxnumber(1개), email 만 읽고, 기존 회사 편집 시 faxnumber 가 있으면 매번 create_faxnumid 로 새 번호를 추가만 함(기존 번호 수정/삭제 불가).
- 증상: 수신 팩스 자동 회사 매칭, 팩스 분류, 담당자/주소 프리필(ajax prefillto)에 필요한 데이터를 화면에서 입력 불가. 같은 번호로 저장을 반복하면 번호가 계속 추가되는 구조.
- 확인 수준: 코드 확인 (번호 저장 자체의 실패는 기존 COR-06)

### R5L-07 [낮음] /setcompany 가 rurl/vf/va 복귀 경로를 무시하고 GET 으로도 동작
- 레거시: setcompany.php 는 POST 전용, 성공 후 rurl → viewfax(vf) → HTTP_REFERER(va) → inbox 순으로 복귀.
- NamiFAX: src/namifax/views/inbox.py:146-163 는 request.params(GET/POST 둘 다)를 읽고 항상 /inbox 로 이동.
- 증상: viewfax 나 보관함에서 회사를 지정해도 원래 화면으로 돌아가지 못하고, 링크 한 번(GET)으로 회사 지정 및 카운터 증가가 일어남.
- 재현: POST /setcompany fid,faxnumid,vf=1 → Location /inbox. GET /setcompany?fid=1&faxnumid=1 도 302 /inbox(실측).
- 확인 수준: 재현

### R5L-08 [중간] 새 팩스 도착 알림음(audiofile) 기능이 통째로 없음
- 레거시: ajax/ajaxinbox.php 가 "건수|파일명" 을 반환(사용자 audiofile 이 includes/audio 에 있으면), js/avantfax.js:367-382 가 새 팩스 증가 시 Audio 재생, admin/users.php 의 audio_list 선택.
- NamiFAX: src/namifax/views/ajax.py:54-63 은 건수만 반환, 사용자 폼/설정에 audiofile 선택 없음, templates 에 audio 문자열 없음(grep 0건).
- 증상: 알림음 설정과 재생이 불가능(무회귀 이식 목표 위반).
- 재현: GET /ajax/inbox → '0' 만 반환 (audiofile 지정 경로 자체가 없음).
- 확인 수준: 코드 확인

### R5L-09 [낮음] outbox 의 60초 자동 새로고침(meta refresh)이 없음
- 레거시: outbox.php INC_LIST 의 `<meta http-equiv="refresh" content="60;URL=outbox.php">`.
- NamiFAX: templates/outbox.jinja2, views/outbox.py 에 refresh, 타이머 없음(grep 0건).
- 증상: 전송 진행 상태가 수동 새로고침 전까지 갱신되지 않음.
- 확인 수준: 코드 확인

### R5L-10 [중간] 관리자 사용자 폼에 프로필, 환경 필드가 없고 신규 사용자 기본값도 적용되지 않음
- 레거시: admin/users.php 가 coverpage_id, audiofile, language, from_company/location/voicenumber/faxnumber, user_tsi, email_sig, faxperpageinbox/archive 를 받아 저장하고, 신규 값 기본은 $FROM_COMPANY, $DEFAULT_TSI_ID, $DEFAULT_FAXES_PER_PAGE_* 등 설정값.
- NamiFAX: templates/admin_users.jinja2 의 입력은 name, username, password, email, is_admin, superuser, can_del, any_modem, didrouting[], modemdevs[], faxcats[] 뿐이고 views/admin.py:91-148 도 그 값만 처리.
- 증상: 관리자가 사용자별 표지, 알림음, 언어, 발신자 정보(TSI 포함), 페이지당 건수를 지정할 수 없고 신규 사용자에 사이트 기본값이 들어가지 않음. (기존 F3-12 는 활성화, 비밀번호 주기, 재사용만 지적.)
- 확인 수준: 코드 확인

### R5L-11 [중간] 이메일 전송 모달이 cc/bcc, 첨부 파일명, 분류, 보관 옵션과 레거시 기본값을 모두 누락
- 레거시: email.php 폼 규칙 emails, cc_emails, bcc_emails, subject(기본 회사명), filename(기본 fax-회사명.pdf, 공백은 -, 콜론 제거), msg(기본 "\n\n\n"+사용자 email_sig), category, archive, url(취소 복귀). 발신은 "이름 <email>" 형식, 성공 시 category 지정과 archive 처리, 메시지 EMAIL_SUCCESS/FAILURE.
- NamiFAX: src/namifax/views/modals.py:365-416 은 emails, subject, msg 만 읽음. 기본 제목은 "Forwarded Fax Document #<fid>", 본문 기본은 고정 영문 문장, 발신자 이름/서명 미사용.
- 증상: 레거시에서 가능했던 참조/숨은참조, 파일명 지정, 발송 후 분류 지정과 수신함 보관이 불가능하고 서명이 삽입되지 않음.
- 확인 수준: 코드 확인

### R5L-12 [낮음] 주소 자동완성이 최소 2자 조건, 예약 번호 제외, "(설명)" 표기를 지키지 않음
- 레거시: ajaxbook.php/archivebook.php 는 `$SHOW_ALL_CONTACTS || strlen($query) > 1` 일 때만 검색, ajaxbook 은 company === RESERVED_FAX_NUM 건너뜀, 번호별 한 행에 "회사 (설명) - 번호".
- NamiFAX: src/namifax/views/ajax.py:66-103, 318-349 는 길이 제한 없이 검색(1자도 전체 반환, 빈 q 는 전체 목록), 예약 회사 제외 없음, 설명 미표기.
- 증상: 한 글자 입력마다 전체 회사 목록이 응답되고, 레거시가 숨기던 "삭제된 회사의 팩스" 예약 항목이 후보에 노출됨. (기존 R3B-10 은 fnid/행 구성, F4-16 은 플레이스홀더 응답.)
- 재현: GET /ajax/book?q=a → 1자 질의에도 행 반환(실측).
- 확인 수준: 재현

### R5L-13 [중간] faxalter 모달의 폼 필드/연산 키가 서비스가 이해하는 키와 달라 대부분의 수정이 적용되지 않음
- 레거시: ajax/faxalter.php 는 operations 를 tries, device, priority(* 이면 생략), sendtime(HH:MM), killtime("now + N 단위"), sendnow("now"), resubmit 으로 구성하고 modem, 시/분, 단위, "지금 보내기" 입력을 제공.
- NamiFAX: src/namifax/views/ajax.py:222-238 은 numtries, sendtime(체크박스 값 "1"), killtime(단위 없이 "3"), priority("*" 그대로)를 그대로 전달. services/faxqueue.py:164-193 faxalter 는 `tries` 키를 기대하므로 numtries 는 버려지고, `-a "1"`, `-k "3"`, `-P "*"` 같은 잘못된 값이 faxalter 에 전달됨. 모뎀 변경, 즉시 전송, 시각 지정, 단위 선택은 폼에 없음.
- 증상: 재시도 횟수 변경이 무시되고, 전송 시각/종료 시각/우선순위는 의미 없는 값으로 바뀌거나 명령이 실패. (기존 F2-07 은 작업 번호가 항상 1인 문제.)
- 확인 수준: 코드 확인

### R5L-14 [낮음] 보관/삭제/노트 등 사용자 동작이 SysLog 감사 기록을 남기지 않음
- 레거시: ajaxarchivefax, archivefax, delete, ajaxdeletefaxes, set_note 가 성공/실패/접근거부 때마다 avantfaxlog("... by 사용자") 를 호출(관리자 system_logs 화면에서 확인).
- NamiFAX: src/namifax/views, web/views 어디에도 avantfaxlog/SysLog 쓰기 호출이 없음(grep 0건). (기존 F3-18 은 계정 이벤트, R3D-40 은 avantfaxlog 구현이 OS syslog 로만 간다는 점 — 여기서는 "호출 자체가 없음".)
- 증상: 누가 어떤 팩스를 삭제/보관/주석했는지 관리자 로그 화면에서 추적 불가.
- 확인 수준: 코드 확인
