# 2라운드 점검 결과: 팩스 발송 흐름 (sendfax -> 제출 -> outbox -> 수정/취소/재전송 -> notify -> 송신 아카이브 -> txreport)

점검 방법: Pyramid 앱을 webtest 로 구동하고, PATH 앞에 가짜 sendfax/faxstat/faxrm/faxalter 를 두어 subprocess 인자를 기록함. notify 는 가짜 qfile 로 실행.
환경: NAMIFAX_DB_PATH, TMPDIR, AVANTFAX_TMPDIR 모두 scratchpad/agent-r2-send/ 하위. 실제 HylaFAX 명령과 공격 페이로드는 실행하지 않음.
이미 known2.md 에 있는 결함(COR-03, COR-05, COR-06, COR-10, COR-15, COR-25, UI-18, UI-21, UI-25, UI-27, USR-07, ADM-14 등)은 제외하고, 이 흐름에서 새로 드러나는 것만 기록함.

---

## F2-01 [높음] sendfax 제출에 소유자(-o)와 발신자(-f) 바인딩이 없어 모든 작업이 서비스 계정 소유가 됨 (notify 와 이음새 단절)
- 위치: src/namifax/views/sendfax.py:19-63 (dispatch_sendfax, identity 인자는 받기만 하고 미사용), 76-131
- 증상: 조립되는 명령에 -o <username>, -f <email>, -X/-Y/-U/-W(발신 회사/위치/전화/팩스), -S(TSI), -D/-R 이 전혀 없음. 작업은 웹 서비스 실행 계정(systemd/namifax.service 의 User=uucp) 소유, mailaddr 도 uucp@호스트가 됨. 그 결과 notify 의 owner 해석(FAXMAILUSER=faxmail, WWWUSER=www-data 기본값과 불일치)에서 load_username('uucp') 실패 -> 송신 아카이브 userid=0, 완료/실패 통지 메일은 사용자가 아니라 uucp@호스트로 전송. 모든 사용자의 발송이 같은 소유자로 섞이므로 outbox 의 소유자별 필터도 원천적으로 불가능. -D/-R 이 없어 HylaFAX 가 통지 훅 자체를 호출하지 않을 가능성도 있음(레거시는 항상 -D 또는 -R).
- 재현 방법: 가짜 sendfax 를 PATH 앞에 두고 로그인 후 POST /sendfax (faxnumber=5551111, to_person, to_company, regarding, comments, cover, 파일). 기록된 argv: ['sendfax','-C','urgent','-d','"Bob"@5551111; 5552222', '<tmp>/sendfax_xxxx_a.pdf'] 등 -o/-f/-X/-S/-D/-R 없음. 레거시 legacy/avantfax/includes/functions.php:450-560 submit_fax 는 "-o user", "-f email", "-D|-R", -X/-Y/-U/-W/-S 를 붙임.
- 확인 수준: 명령 조립은 재현, notify 에서의 owner 불일치와 -D 미지정의 통지 영향은 추론(HylaFAX 동작 기준)

## F2-02 [높음] 다중 수신처가 하나의 -d 문자열로 전달되어 엉뚱한 번호로 발신됨 (화면 안내/팝업/서비스 구분자 3중 불일치)
- 위치: src/namifax/views/sendfax.py:52-53, src/namifax/templates/sendfax.jinja2:59,63, src/namifax/views/ajax.py:197 (dlist 는 "; " 로 결합)
- 증상: 화면은 "쉼표로 여러 번호 구분"이라고 안내하지만 서버는 분리하지 않음. 배포 목록은 "; " 로 이어 붙임. 두 경우 모두 전체 문자열이 단일 -d 값으로 나가 HylaFAX 에는 하나의 다이얼 문자열("5551111,5552222"의 쉼표는 모뎀 pause)이 됨. 레거시는 ";" 로 분리하고 번호별로 정제 후 -z 파일로 제출하며 중복 제거, 공백/줄바꿈 제거를 함(sendfax.php:120-151).
- 재현 방법: POST /sendfax faxnumber='5551111,5552222' -> argv [..., '-d', '5551111,5552222']. faxnumber='5551111; 5552222', to_person='Bob' -> '-d', '"Bob"@5551111; 5552222'. 번호 문자 정제도 없음(레거시 preg_replace("/[^\w,#*@\ \"]/")). to_person 에 따옴표가 있으면 '"O"Brien, Bob"@5551111' 처럼 깨진 문자열이 됨.
- 확인 수준: 재현(argv). 실제 발신 결과는 추론

## F2-03 [높음] sendfax 실패를 사용자에게 알리지 않고 항상 outbox 로 성공 리다이렉트, 바이너리가 없으면 가짜 작업번호로 성공 처리
- 위치: src/namifax/views/sendfax.py:120-134, 65-72
- 증상: dispatch_sendfax 의 반환값({"success":False,"output":...})을 버림. 가짜 sendfax 가 "Cannot connect to hfaxd" 로 종료코드 1 을 내도 302 -> /outbox, 오류 문구 없음(outbox 에서도 안 보임). HylaFAX 미설치 시에는 무작위 6자리 jobid 를 만들어 success=True 로 돌려주고 아무것도 제출하지 않음(재현: {'success': True, 'jobid': '110066', ...}). 레거시는 "FAX_FAILED<br />sendfax: <출력>" 을 화면에 표시하고 avantfaxlog 에 기록함. 제출 성공 시의 request id(jobid) 파싱/표시도 없음.
- 재현 방법: 가짜 sendfax 를 exit 1 로 만들고 POST /sendfax -> 302 Location /outbox, 이후 /outbox 본문에 오류 없음. PATH 에서 sendfax 제거 후 dispatch_sendfax('5551111', []) 호출.
- 확인 수준: 재현
- 참고: 파일도 cover 도 없이 제출하는 경우(레거시는 제출하지 않음, sendfax.php:207)도 그대로 'sendfax -n -d 번호'가 실행됨.

## F2-04 [높음] outbox 작업 취소가 실제로는 아무것도 하지 않고 항상 성공 메시지를 표시
- 위치: src/namifax/views/outbox.py:19-25 (fq.kill_job 호출), src/namifax/services/faxqueue.py:158 (실제 메서드명은 killjob(user, jid))
- 증상: FaxQueue 에 kill_job 이 없어 AttributeError 가 나고, except 분기가 성공과 동일한 "Job #N successfully killed and removed from queue." 를 표시. faxrm 은 호출되지 않음. 존재하지 않는 작업(abc)이나 남의 작업도 같은 성공 문구. 취소는 GET /outbox?kill= 이라 링크 하나로 동작(UI-28 의 일반론과 별개로 이 흐름에서는 동작조차 안 함).
- 재현 방법: 가짜 faxstat/faxrm 을 두고 GET /outbox?kill=102 -> 기록된 호출은 faxstat -s, -d 뿐이고 faxrm 없음, 본문에 "Job #102 successfully killed..." 가 출력됨. kill=abc 도 동일.
- 확인 수준: 재현

## F2-05 [높음] outbox 가 로그인한 모든 사용자에게 전체 사용자의 송신 작업을 보여줌 (소유자 필터 없음)
- 위치: src/namifax/views/outbox.py:12-47 (identity 를 읽기만 하고 필터에 쓰지 않음)
- 증상: 레거시는 superuser 가 아니면 list_owner(username) 로 본인 작업만 보여줌(outbox.php:19-24). 새 구현은 process_queue()/process_failed_queue() 전체를 그대로 반환. 다른 사용자의 작업 번호, 상태, 취소 링크가 모두 노출됨. F2-01 때문에 작업 소유자가 전부 서비스 계정이라 list_owner 로 고치더라도 동작하지 않는 이음새 문제가 겹침.
- 재현 방법: 가짜 faxstat 출력에 owner=bob, owner=faxmail(mailaddr=bob@...) 행을 넣고 admin 계정으로 GET /outbox -> #102, #103 (bob 소유)이 표시됨. 일반 사용자 계정으로의 표시는 코드상 동일 경로이므로 추론.
- 확인 수준: 재현(admin 계정), 일반 사용자 영향은 추론

## F2-06 [중간] outbox 템플릿과 뷰의 키 불일치: 수신처, 회사, 실패 작업 번호가 비어 있고 재시도/수정/실패작업 취소 동선이 없음
- 위치: src/namifax/templates/outbox.jinja2:63-64,135-136,139 / src/namifax/views/outbox.py:28-33 / src/namifax/services/faxqueue.py:9-10
- 증상: 서비스는 jid, number, pri, owner 키를 주는데 템플릿은 j.jobid, j.destination/j.dest 를 읽음. 대기 작업은 Destination 과 Company 가 항상 "—" (회사 조회 loadbyfaxnum 자체가 뷰에 없음), 실패 작업은 Job ID 가 "#" 만 나오고 Destination 칸이 비며 Retry 링크가 "/sendfax?refax=" (값 없음)이 됨. 실패 작업 표에는 취소(kill) 링크가 없고, 대기/실패 표 모두 레거시의 작업 수정(dialogFaxAlter) 버튼이 없어 /ajax/faxalter 로 들어가는 UI 경로가 없음. 소유자, 우선순위, dials, tts 열도 사라짐.
- 재현 방법: 가짜 faxstat 출력(JID Pri S Owner Mailaddr Number Pages Dials TTS Status)으로 GET /outbox -> "#101 — — 0:2 Queued", 실패 표 "# ... No carrier detected Retry", href 목록 ['/outbox?kill=101', ..., '/sendfax?refax='].
- 확인 수준: 재현

## F2-07 [높음] 작업 수정(/ajax/faxalter)이 항상 작업 #1 을 대상으로 하고, 전달되는 faxalter 옵션도 레거시와 다름
- 위치: src/namifax/views/ajax.py:222-280 (폼의 hidden jid value="1" 하드코딩, GET 의 jid/owner 무시), src/namifax/services/faxqueue.py:164-193
- 증상: (1) GET /ajax/faxalter?jid=102 로 열어도 폼의 jid 는 항상 1. 저장하면 다른 작업(#1)이 수정됨. (2) 뷰가 numtries 키로 넘기는데 서비스는 "tries" 만 처리해 재시도 횟수가 버려짐. (3) 우선순위 "*"(Normal)가 그대로 -P "*" 로 전달(레거시는 '*' 이면 생략). (4) killtime "3" 이 "now + 3 hours" 가 아니라 원문 그대로 -k "3", sendtime 체크박스 값 "1" 이 -a "1" 로 전달(레거시는 HH:MM, "now"). (5) resubmit(-r), modem(-m), sendnow 입력이 폼에 없어 실패 작업 재제출 불가. (6) FAXUSER 가 작업 소유자가 아니라 세션 사용자로 설정되어(레거시는 owner 파라미터) 관리자가 타인 작업을 고칠 때 소유권이 어긋남. 옵션이 하나도 없어도 'faxalter 102' 를 실행하고 성공 200 을 돌려줌.
- 재현 방법: POST /ajax/faxalter jid=102&destination=5550000&priority=*&numtries=5&killtime=3&sendtime=1 -> argv ['faxalter','-d','5550000','-P','*','-k','3','-a','1','102'] (-t 없음). GET 으로 받은 HTML 의 name="jid" value="1".
- 확인 수준: 재현 (USR-06, COR-10 의 인증/주입 문제와는 별개의 기능 결함)

## F2-08 [높음] 재전송(refax) 모달이 아무것도 제출하지 않으면서 작업번호 1001 로 성공 처리
- 위치: src/namifax/views/modals.py:9,169-203 (avantfax.services.faxqueue 사용), src/avantfax/services/faxqueue.py:195-202 (create_job 이 return 1001)
- 증상: create_job 은 sendfax 를 호출하지 않고 상수 1001 을 반환. 뷰는 "Fax queued for sending (Job ID: 1001)" 를 만들지만 템플릿이 message 를 렌더하지 않아(UI-18) 사용자는 결과조차 못 봄. 원본 팩스(fid)를 읽어 PDF/TIFF 를 재첨부하는 로직이 전혀 없고(레거시 refax.php 는 archive->get_pdfpath 로 원본을 첨부), 접근 권한(user_has_rights) 검사도 없음. 수신처 기본값이 원본 번호가 아니라 하드코딩 "+1-555-0199", 제목 "Re: Document Transmission", 본문 "Resending previous transmission." 이라 그대로 제출하면 가짜 번호로 작업이 생성되는 것처럼 보임.
- 재현 방법: POST /refax fid=5&destinations=5551111 -> 기록된 외부 명령은 faxstat 뿐(sendfax 없음), 반환 jid=1001. GET /refax?fid=5 의 수신처 입력값이 +1-555-0199.
- 확인 수준: 재현 (ADM-14/COR-26 의 print-to-fax 스텁과 같은 계열이나 재전송 흐름에서 독립적으로 발생)

## F2-09 [높음] 업로드 검증 부재: MIME/크기 제한 미적용(FileUpload 미연결), 빈 파일과 임의 형식 모두 sendfax 로 전달, 긴 파일명은 500
- 위치: src/namifax/views/sendfax.py:100-109, src/namifax/common/upload.py (FileUpload 는 어디서도 사용되지 않음), src/namifax/templates/sendfax.jinja2:123-124
- 증상: 레거시는 application/pdf, postscript, image/tiff, text/plain 만 허용하고 크기 0 은 건너뜀. 새 구현은 accept 속성과 안내문("Max 10 MB")뿐 서버 검증이 없음. evil.exe(application/x-msdownload), .docx, 0바이트 pdf 모두 그대로 임시 저장되어 sendfax 인자로 전달됨. 크기 제한이 없어 대용량 업로드가 /tmp 를 채울 수 있음. 파일명 300자는 open() 에서 OSError(Errno 36)로 미처리 500. 업로드 필드가 단일 file 뿐이라 레거시의 다중 파일 첨부도 사라짐. 형식 변환(PS/TIFF/PDF 구분, 오류 문구 fupload_error_code)도 없음.
- 재현 방법: upload_files 로 evil.exe, a.docx, 빈 e.pdf 를 POST -> 모두 302, argv 마지막 인자로 <tmp>/sendfax_xxxx_evil.exe 등. 파일명 'x'*300+'.pdf' -> OSError: File name too long.
- 확인 수준: 재현

## F2-10 [중간] 업로드 임시 파일이 지워지지 않고, 크론이 청소하는 디렉터리와도 다른 곳에 저장됨
- 위치: src/namifax/views/sendfax.py:104-109 (tempfile.gettempdir()), src/namifax/cli/cron.py:31,86-99 (AVANTFAX_TMPDIR 기본 /tmp/avantfax/ 만 청소)
- 증상: 제출 성공, 실패, 예외 어느 경우에도 uploaded_files 를 삭제하지 않음(레거시도 $TMPDIR 에 두지만 cron 이 그 디렉터리를 청소). 새 구현은 시스템 /tmp 에 sendfax_<8hex>_<원본명> 으로 쌓이며 cron 의 정리 대상 디렉터리(AVANTFAX_TMPDIR)와 달라 영구 누적됨. 팩스 원본(개인정보 포함 가능)이 world-readable 일 수 있는 /tmp 에 잔존하고, 파일 권한 설정도 없음. 실패한 제출(F2-03)에서도 그대로 남음.
- 재현 방법: 5회 POST 후 TMPDIR 하위에 sendfax_* 파일 5개 잔존(파일 목록 확인). cron 의 청소 경로와 비교.
- 확인 수준: 재현(누적), 권한 노출은 추론

## F2-11 [중간] 표지(-C) 값이 템플릿 파일로 해석되지 않고 사용자 입력이 그대로 전달됨, 표지만 발송 경로도 없음
- 위치: src/namifax/views/sendfax.py:39-43,112-113, src/namifax/services/covers.py (CoverPages.file)
- 증상: 레거시는 -C $INSTALLDIR/images/<whichcover> 로 해석하고, 파일 없이 표지만 보낼 때는 faxcover 로 PS 를 만든 뒤 sendfax 로 제출함(functions.php:529-548). 새 구현은 폼 값을 그대로 '-C urgent' 로 전달(상대 이름이라 HylaFAX 가 템플릿을 못 찾을 가능성). whichcover 가 CoverPages 테이블 값인지 검증하지 않아 임의 경로(-C /etc/passwd)가 그대로 나감 -> 서버 파일 내용이 표지 템플릿으로 읽혀 팩스에 실릴 수 있음. 파일 없이 표지만 체크하면 문서 없는 sendfax 가 실행됨. 표지를 선택했는데 faxcover CLI(-p 0 -n, 발신자 -f 등)를 경유하는 구성도 없음.
- 재현 방법: POST /sendfax coverpage=1&whichcover=/etc/passwd -> argv ['sendfax','-C','/etc/passwd','-d','5551111']. 정상값 urgent -> '-C','urgent'.
- 확인 수준: 인자 조립은 재현, 임의 파일 노출과 실제 sendfax 동작은 추론

## F2-12 [중간] 주소록, 배포 목록 선택 팝업이 작성 화면과 연결되지 않고, 비어 있으면 가짜 수신처를 만들어 냄
- 위치: src/namifax/templates/sendfax.jinja2 (팝업 호출, JS, /ajax 호출 없음), src/namifax/views/helpers.py:128-178 (Add 버튼 type=button 에 핸들러 없음, option value 가 팩스번호가 아니라 company id), src/namifax/views/ajax.py:66-103,186-204
- 증상: 작성 화면에는 주소록/배포 목록 링크(페이지 이동)만 있고 레거시의 팝업 선택, 자동완성 스크립트(js/sendfax_coverpage.js)가 없음. 팝업 자체도 Add 버튼이 동작하지 않고 선택값이 company id 라 호출해도 수신처 입력에 번호가 들어가지 않음. 더 위험한 점은 /ajax/dlist 가 목록이 없거나 비어 있으면 "1234567; 9876543" 을, /ajax/book 이 결과가 없으면 "Acme Corp - 1234567" 을 돌려줘서, 연결되는 순간 존재하지 않는 배포 목록이 임의 번호 2개로 채워져 실제 발신될 수 있음(USR-02 의 검색 결과 가짜 레코드와 같은 패턴이지만 발송 입력으로 직접 흘러감).
- 재현 방법: GET /ajax/dlist?dl_id=9999 -> 본문 "1234567; 9876543". /helper/faxcontacts 의 HTML 에서 Add 버튼은 type="button", onclick 없음. sendfax.jinja2 에 window.open, fetch, /ajax, /helper 참조 없음.
- 확인 수준: 재현(ajax/dlist), 팝업 동작 불능은 코드 읽기

## F2-13 [낮음] 송신 큐 조회 오류가 "큐 비어 있음"으로 표시됨 (faxstat 실패 은폐)
- 위치: src/namifax/services/faxqueue.py:82-88 (shell_exec 가 stdout 만 반환, stderr/returncode 버림), src/namifax/views/outbox.py:27-35 (except -> [])
- 증상: hfaxd 에 연결할 수 없어 faxstat 이 종료코드 1 로 실패해도 outbox 는 "No jobs in queue / There are no faxes waiting to be sent" 를 표시. 사용자는 대기 작업이 없다고 오인함.
- 재현 방법: 가짜 faxstat 을 "Cannot connect to server" + exit 1 로 만들고 GET /outbox.
- 확인 수준: 재현

## F2-14 [낮음] 작성 화면 오류 재표시 때 표지 체크 해제 상태와 입력이 복원되지 않음, 주소록 "Send Fax" 링크가 URL 인코딩되지 않음
- 위치: src/namifax/templates/sendfax.jinja2:144, src/namifax/templates/addressbook.jinja2:69
- 증상: 수신처를 비우고 표지를 해제한 채 제출하면 재표시된 폼에서 체크박스가 다시 체크됨(`form_data.coverpage != '0'` 이 미체크일 때 항상 참). 업로드 파일은 당연히 사라짐. 주소록 링크는 company/faxnumber 를 인코딩 없이 붙여서 "AT&T" 같은 회사명이 쿼리를 깨뜨림(prefill 자체가 무시되는 문제는 UI-21 로 기보고).
- 재현 방법: POST /sendfax faxnumber='' coverpage='' -> 응답의 coverpage input 에 checked 포함.
- 확인 수준: 재현(체크박스), 링크는 코드 읽기

## F2-15 [낮음] txreport 모달: 권한 검사 없음, 존재하지 않는 fid 에도 가짜 전송 확인서를 발급 (UI-20, SEC-03, USR-02 의 변형)
- 위치: src/namifax/views/modals.py:206-237
- 증상: fid 기본값 "1", 사용자 권한 검사 없음(레거시 txreport.php 는 user_has_rights 와 없는 fid 는 inbox 로 리다이렉트). 없는 fid(9999)를 넣으면 "Company: Acme Global / Date: 2026-09-29 10:15:00 / Pages: 2 / Transmitted Successfully (OK)" 공식 확인서가 출력됨. 송신 실패 작업이나 수신 팩스에도 "전송 성공"이 나오므로 법적 증빙으로 쓰이는 문서가 사실과 무관하게 발급됨. 이음새 관점: notify 가 만든 보관 레코드(회사 미연결, COR-05)는 회사란에 번호만 나옴.
- 재현 방법: GET /txreport?fid=9999, GET /txreport?fid=2 (notify 로 보관된 송신 건).
- 확인 수준: 재현

---

## 흐름 점검에서 새 결함이 없거나 기존 항목에 포함된다고 판단한 지점
- notify CLI 끝단: 사용자 속성 오류(COR-03)를 우회해 실행해 보면(AFUserAccount.email 을 테스트에서만 주입) 이후 단계는 PDF/썸네일 생성, FaxArchive 행 생성(inbox=0, origfaxnum 정제)까지 진행되나 companyid 가 비고(COR-05/06), convert2pdf 는 PS/PDF 를 못 열어 가짜 PDF(COR-15), 보관 경로가 installdir 없이 절대경로로 저장되어 삭제가 cwd 상대로 해석(COR-28), qfile 값에서 ':' 이후 잘림(regarding "Re: PO" -> "Re")은 레거시와 동일 동작이라 제외.
- 셸 명령 주입: dispatch_sendfax 는 인자 리스트로 subprocess 를 호출하므로 sendfax 경로 자체에는 셸 주입이 없음(값이 옵션 값 자리로만 들어감). faxrm/faxalter 는 COR-10 으로 기보고.
- 페이지 렌더마다 faxstat 호출 등 성능 문제는 이번 범위에서 제외.
