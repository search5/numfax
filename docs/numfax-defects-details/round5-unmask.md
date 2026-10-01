# 5라운드 round5-unmask: 2차 패치(광범위 차단 제거) 후 재점검

작업 복제본: scratchpad/agent-r5-unmask/repo (원본 numfax 미수정, .git/.venv 제외 복사, .venv 는 uv sync, DB 는 agent-r5-unmask/work/t.db, 가짜 sendfax/faxstat/faxrm/faxalter 는 work/bin 의 셸 스텁, 포트 미사용 webtest 인프로세스). 공격 페이로드는 실행하지 않음. 시험 스크립트는 agent-r5-unmask/t1.py..t7.py. 참고: 4라운드 patch-log.md 파일은 존재하지 않아 repo.orig 와 repo 의 diff 를 p1.diff 로 추출해 1차 패치 8건을 재적용했다.

## 적용한 패치 (1차 8건 + 2차 12건, 상세는 agent-r5-unmask/patch-log.md)
1차 P1~P8: 4라운드와 동일.
2차:
- P9 (a) engine.quote 가 bool 을 1/0 으로 저장 (COR-09, R4U-02 근거)
- P9b (a) AddressBook.abook_id 동기 트리거, AddressBookFAX 레거시 컬럼 추가
- P9c (a) AFAddressBook.loadbyfaxnum 의 튜플 반환(항상 참)을 bool 로, notify 의 multiple 속성명 수정
- P10 (b) 관리자 삭제 가드를 정수 비교로 (R4U-01 우회 차단)
- P11 (c) FaxQueue.kill_job/create_job 추가, sendfax 제출에 FAXUSER 와 jobid 파싱, 실패 시 오류 표시
- P12 (d) MailerService.send_mail 이 SMTP 설정 사용
- P12b (d) helpers.send_mail 이 SMTP 설정 사용, set_cc/set_bcc/attach_file(filename=)
- P13 (e) viewfax, txreport, 수신함 기본값, 아카이브 검색, ajax 자동완성/dlist/prefill 의 가짜 데이터를 실제 DB 조회로 치환
- P14 (f) emailbook_edit 숨은 id=1, modal_assign 숨은 abook_id=1, 모달 fid 기본값 1, inbox 삭제 링크 수정
- P15 (g) 관리자 사용자 폼이 modemdevs/faxcats/didrouting 저장, any_modem 체크 반영
- P15b (g) 기본 permission "view" 설정(정적 파일, SAML, 패스키 인증은 public)
- P16 (h) 수신함/아카이브가 사용자 DB 레코드의 모뎀/분류 목록으로 필터링

## 패치 후 정상 확인된 항목 (결함 아님)
비밀번호 재사용 금지(bool 수정 후 거부됨), 사용자 생성/로그인/비밀번호 이력, 삭제 후 같은 username 재생성, R4U-01 우회 6종 차단(P10 적용 상태), 팩스 수신 훅 end-to-end(모뎀 자동 생성, 주소록 자동 등록, faxfrom 카운트, 보관함 등록, PDF 다운로드 application/pdf), 모뎀 제한 사용자의 수신함 필터, 모뎀 없는 사용자의 수신함 빈 목록, sendfax 제출에서 outbox 큐 반영과 faxalter 호출.

## 결함 (패치 전에는 가려져 있었고 패치 후 새로 드러난 것)

### R5U-01 (높음) 모뎀/분류/DID 가 하나도 없는 사용자는 아카이브 검색에서 제한 없이 전체 팩스를 본다 (빈 목록 = 무제한)
- 위치: src/namifax/services/archive_base.py:189-345 (`search_archive` 의 `sentrecvd` 분기들과 `_prepare_routes_clause`:344-352)
- 드러난 패치: P16 + P13 (사용자별 modemdevs/categories/didroutes 를 criteria 로 전달하고 가짜 폴백 결과를 삭제한 뒤)
- 증상: `_prepare_routes_clause` 는 빈 목록이면 None 을 반환하고, 각 분기는 `if query_modemdevs and ...`/`elif not query_modemdevs and query_categories` 형태라 둘 다 None 이면 어떤 조건도 붙이지 않는다. 즉 접근 권한이 전혀 없는 사용자가 "제한 없음" 으로 평가된다. 수신함(viewable_devices)은 빈 목록을 `modemdev = ''` 로 올바르게 막는데 아카이브만 반대로 동작한다.
- 재현: 모뎀/분류 없이 사용자 al7 생성, FaxArchive 에 fid=10(modemdev=ttyS1, inbox=0, description='d10') 삽입 후 al7 로그인으로 `GET /archive?search=d10` -> fid 10 이 표시됨. 같은 조건에서 ttyS0 만 가진 bo7 은 정상적으로 0건(t7.py).
- 확인 수준: webtest 인프로세스 실행, 응답 HTML 에서 확인.

### R5U-02 (중간) 분류 삭제 시 FaxArchive.faxcatid 도 정리되지 않음 (R4U-03 의 추가 사례), remove_category 는 호출처 없음
- 위치: src/namifax/services/categories.py:112-122, services/archive_base.py `remove_category` (미사용)
- 드러난 패치: P15 (사용자 폼이 faxcats 를 실제로 저장), P1
- 증상: 분류를 삭제해도 FaxArchive.faxcatid 가 삭제된 catid 로 남는다. 사용자 faxcats 에 삭제된 번호가 남아 있어, 같은 번호로 분류가 다시 생성되면(AUTOINCREMENT 가 아니라 재사용 여부는 DB 에 따라 다름) 권한이 되살아난다. 수신함 분류 필터는 이 값을 기준으로 하므로 삭제된 분류의 팩스가 일부 사용자에게만 보이는 상태로 남는다.
- 재현: 분류 CatZ 생성, bo7 의 faxcats 에 지정, fid=10 의 faxcatid 지정, `POST /admin/categories delete=1&catid=N` -> UserAccount.faxcats='3', FaxArchive.faxcatid=3, Modems.faxcatid=3 이 그대로 (t7.py).
- 확인 수준: 실제 POST 후 SQLite 조회.

### R5U-03 (중간) 모뎀 삭제 후 UserAccount.modemdevs 에 장치 이름이 남아 같은 이름으로 모뎀을 다시 만들면 권한이 조용히 부활
- 위치: src/namifax/services/modem.py:142-159 (`delete_device`), views/admin.py 모뎀 삭제 분기
- 드러난 패치: P15 (modemdevs 저장)
- 증상: Modems 행만 삭제된다. 제한 사용자의 modemdevs, 수신 팩스의 modemdev 는 그대로 남고, 사용자 편집 폼에는 삭제된 모뎀 체크박스가 없어 관리자가 정리할 방법이 없다(저장 시에는 폼에 있는 값만 쓰므로 다음 저장에서 암묵적으로 사라질 뿐). faxrcvd 는 알 수 없는 장치를 자동 생성하므로(alias 가 장치명) 같은 이름의 모뎀이 새로 생기면 이전 사용자의 접근이 별도 승인 없이 부활한다.
- 재현: bobr(modemdevs=ttyS0) 생성 후 `POST /admin/modems delete=1&devid=1` -> UserAccount.modemdevs 는 'ttyS0' 유지 (t2.py).
- 확인 수준: 실제 POST 후 DB 조회. 재부활 부분은 코드 읽기(faxrcvd 자동 생성은 실행으로 확인: ttyS9 자동 생성).

### R5U-04 (중간) 주소록 UI/훅으로 만든 회사의 팩스번호가 목록, 검색, 자동완성에서 보이지 않음
- 위치: src/namifax/views/addressbook.py:12-35 (`get_all_companies` 가 AddressBook.faxnum/faxnumber 만 읽음), views/ajax.py `ajax_book`/`ajax_archivebook`, views/helpers.py 의 faxnum 읽기
- 드러난 패치: P9b (AddressBookFAX 컬럼/abook_id 가 맞춰져 create_faxnumid 가 실제로 저장하기 시작함)
- 증상: 새 서비스 코드는 번호를 AddressBookFAX 에 저장하지만 화면은 구버전 AddressBook.faxnum 열을 읽는다. 시드 회사 2곳만 번호가 보이고, UI 로 만든 회사나 faxrcvd 가 자동 등록한 회사는 번호 열이 빈칸이며 번호로 검색(`q in c.faxnumber`)해도 찾을 수 없다. ajax/book 라벨도 "회사 - " 로 번호가 비어 발송 화면에서 팩스번호를 자동 입력할 수 없다.
- 재현: `POST /addressbook/edit company=Zeta Co&faxnumber=02-555-1111` 후 AddressBookFAX 에는 '025551111' 이 있으나 `GET /addressbook` 응답에 번호가 없음 (t2.py "ab list shows faxnumber col? False").
- 확인 수준: 실행 및 응답 확인.

### R5U-05 (중간) faxrcvd: 이미 있는 회사명으로 들어온 새 번호는 번호 등록이 건너뛰어져 faxnumid=0 으로 보관함에 들어감
- 위치: src/namifax/cli/faxrcvd.py:138-146, services/addressbook.py:56-77 (`create` 가 이미 있으면 False)
- 드러난 패치: P9c (loadbyfaxnum 의 튜플 반환이 항상 참이라 else 분기 자체가 실행되지 않던 것을 고침)
- 증상: 발신 번호가 주소록에 없어도 발신자 이름(CID name)이 이미 있는 회사와 같으면 `create(company)` 가 False 이므로 `create_faxnumid` 가 호출되지 않는다. 이 팩스는 faxnumid=0 으로 저장되어 회사명 표시, 통계 카운트, Fax2Email/분류 라우팅이 모두 적용되지 않는다. 같은 이름의 다른 발신 번호(지점 번호 등)는 영구히 미등록이다. 레거시 faxrcvd.php 와의 대조는 하지 않음(레거시가 같은 구조일 수 있음).
- 재현: CID name 'ACME Sender' 로 번호 +8225550001 팩스 수신 후 +8225550002, 02-555-0003 으로 수신 -> FaxArchive fid 3,5 의 faxnumid=0, AddressBookFAX 에는 +8225550001 만 존재 (t2.py).
- 확인 수준: faxrcvd 를 실제 실행하여 DB 확인.

### R5U-06 (중간) /ajax/inbox 신규 팩스 수가 사용자별 접근 제한을 무시
- 위치: src/namifax/views/ajax.py:46-57
- 드러난 패치: P13 (이전에는 TypeError 로 항상 0)
- 증상: 모뎀 권한이 없는 사용자도 전체 수신함 건수를 받아 본다(수신함은 0건). 접근 불가 팩스의 존재와 양이 노출되고 배지가 실제 목록과 어긋난다.
- 재현: 모뎀 없는 사용자 alice 로 `GET /ajax/inbox` -> 5, 같은 사용자의 `/inbox` 는 0건 (t2.py).
- 확인 수준: 실행.

### R5U-07 (높음) 재전송(/refax) 모달이 원본 팩스 문서를 전혀 첨부하지 않고 fid 를 사용하지 않음
- 위치: src/namifax/views/modals.py:169-205 (`modal_refax_view` 의 `fq.create_job(...)`)
- 드러난 패치: P11 (create_job 이 생기고 sendfax 호출이 실제로 일어나기 시작함)
- 증상: 폼의 fid 는 어디에서도 읽히지 않고 sendfax 가 파일 인자 없이 호출된다. 가짜 sendfax 로그: `sendfax FAXUSER=admin args: -n -r re -c c -d 555-9` (문서 없음). 실제 sendfax 는 문서가 없으면 실패하거나 빈 제출이 되므로 "Reply/Resend" 가 동작하지 않는다.
- 재현: `POST /refax fid=1&destinations=555-9` 후 work/sendfax.log 확인.
- 확인 수준: 실행 및 로그 확인(실제 HylaFAX 아님).

### R5U-08 (낮음) 작업 삭제(`/outbox?kill=`) 가 존재하지 않는 작업에도 성공 메시지를 표시
- 위치: src/namifax/views/outbox.py:20-28, services/faxqueue.py:158-162 (`killjob` 가 faxrm 종료코드와 상관없이 True)
- 드러난 패치: P11 (kill_job 이 연결되어 호출이 일어남)
- 증상: 없는 jid(99999)도 "Job #99999 successfully killed and removed from queue." 가 표시되고, except 분기도 같은 문구다. 실패를 구분할 수 없다.
- 재현: `GET /outbox?kill=99999`.
- 확인 수준: 실행.

### R5U-09 (낮음) 이메일북 폼의 `company` 입력이 버려져 연락처가 회사에 연결되지 않음
- 위치: src/namifax/views/addressbook.py:139-175 (`company` 를 읽지만 사용하지 않음), services/addressbook.py `create_contact` (abook_id=None)
- 드러난 패치: P14 (숨은 id=1 제거로 신규 생성이 가능해짐)
- 증상: 새 연락처가 abook_id=NULL 로 저장되어 회사별 조회에 나타나지 않는다. 폼의 회사 필드는 장식이다.
- 재현: `POST /emailbook/edit contact_name=E1&contact_email=e1@x.com&company=Zeta` -> AddressBookEmail.abook_id NULL.
- 확인 수준: 실행.

## 요약
신규 9건: 높음 2 (R5U-01, R5U-07), 중간 5 (R5U-02~06), 낮음 2 (R5U-08, R5U-09). 이미 known5 에 있는 것으로 판단해 제외한 항목: 비밀번호 만료 미강제(SEC-05, F4-03), 설정 화면 스텁(UI-01), 삭제/비활성 후에도 기존 세션 유지(F3-11), 마지막 관리자 보호 없음과 자기 강등(ADM-06), 회사 병합/삭제 reassign 실패와 고아 팩스번호(R3C-17, R3B-03, R3F-01), 배포목록이 회사 ID 저장(R3B-02), 타인 작업 kill/faxalter(USR-07), can_del 미검사(F3-03), 모달 결과 메시지 미출력(UI-18), 필터만 쓴 아카이브 검색 숨김(USR-01), 직접 URL 접근의 모뎀 제한 우회(SEC-03).
