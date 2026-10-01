# 3라운드 H: 브라우저 기준 UI/JS 점검 결과

## 읽은 템플릿과 JS 파일 목록
- static 아래에는 JS 파일이 없음 (css/input.css, css/main.css(0바이트), theme.css, images/*). JS는 전부 템플릿 인라인.
- 인라인 JS가 있는 템플릿: inbox(드롭다운, 전체선택), sendfax(파일명 표시), login(패스키 로그인), settings(패스키 등록/목록/삭제), admin_layout(menuObj onchange), home(죽은 스크립트), login_totp(1라운드에서 확인됨)
- 끝까지 읽은 템플릿: layout, login, home, inbox, sendfax, outbox, archive, viewfax, settings, addressbook, addressbook_edit, emailbook, emailbook_edit, distrolist, distrolist_edit, modal_email/assign/note/delete/refax/txreport, admin_layout, admin_printers(확인 구간)
- 폼 name 대 뷰 파라미터, href 쿼리 파라미터 대 뷰 읽기 이름은 전 템플릿을 스크립트로 대조(admin_* 포함). 이미 known 에 있는 항목만 나와 제외.
- 함께 읽은 뷰/서비스: views/ajax.py, inbox, outbox, archive, modals, addressbook, distrolist, auth, webauthn, services/webauthn.py
- 레거시 대조: includes/templates/main_theme/templates 의 sendfax, inbox, outbox, settings, viewfax .tpl
- 브라우저: playwright-core + 시스템 chromium 으로 로그인 후 주요 화면 45개를 1280px, 375px 로 열어 콘솔/네트워크/접근성/가로 스크롤 수집, 스크린샷은 agent-r3-h/shots. (콘솔 오류는 /api/webauthn/credentials 500, /login/totp 500, /helper/distrolist 404 뿐이며 모두 known 범주)
- 참고: 기동 경로 `namifax-server` 는 이 환경에서 18731 포트를 열지 않고 멈춤(F5-01 계열로 보이나 미분석). 점검은 create_app()+wsgiref 로 구동.

## 결함

### R3H-01 (높음) POST /delete 가 fid 없이도 1번 팩스를 삭제
- 위치: views/modals.py modal_delete_view (`fid = request.params.get("fid", "1")`, 이후 `arc.delete_fax(int(fid))`), 같은 패턴이 modal_note/modal_txreport/viewfax/rotate (`"1"` 기본값)
- 증상: fid 가 없거나 빠진 요청이 조용히 1번 팩스를 영구 삭제함. 링크 오기나 북마크 재제출로 즉시 데이터 손실.
- 재현: 로그인 후 /delete 를 GET 으로 열고 Delete 제출 -> /inbox 행이 1건에서 0건으로 감소(실제 재현).
- 확인 수준: 재현

### R3H-02 (중간) 링크 쿼리 값이 URL 인코딩되지 않아 '&', '+', '#' 가 포함되면 깨짐
- 위치: addressbook.jinja2:69 (`/sendfax?to_company={{ c.company }}&faxnumber={{ c.faxnumber }}`), inbox.jinja2:93, archive.jinja2:128 (`/addressbook?search={{ ... }}`)
- 증상: 회사명 "A & B Co" 는 `to_company=A & B Co&faxnumber=` 로 출력되어 "A " 까지만 전달되고 나머지가 별도 파라미터가 됨. 팩스번호 "+1-555-0199" 의 `+` 는 공백으로 해석됨. Jinja 자동 이스케이프는 HTML 용이라 URL 을 보호하지 않음. `|urlencode` 필요. known UI-21/22 는 파라미터 이름 불일치이고 이 건은 값이 깨지는 별개 원인.
- 재현: 주소록에 "A & B Co" 생성 후 목록 Send Fax 링크 href 확인.
- 확인 수준: 재현(링크 출력), `+` 해석은 추론(표준 동작)

### R3H-03 (중간) Rotate 링크가 GET 으로 JSON 엔드포인트를 열어 사용자가 원시 JSON 화면으로 이동
- 위치: inbox.jinja2:~148 (`/faxes/rotate/{{ fax.id }}`), viewfax.jinja2:42; views/inbox.py fax_rotate_view 는 `redirect=inbox` 일 때만 리다이렉트
- 증상: Rotate 를 누르면 `{"status": "ok", "fid": "1", "rotation": 90}` 텍스트 페이지가 뜨고 돌아갈 링크가 없음.
- 재현: /faxes/rotate/1 열기 -> JSON 본문 확인.
- 확인 수준: 재현

### R3H-04 (중간) 플래시/오류 배너가 두 번 출력됨 (layout 과 페이지가 각각 출력)
- 위치: layout.jinja2 (`error`, `flash_message` 출력) + outbox.jinja2:22-28 (`flash_message` 재출력), sendfax.jinja2:~29-34 (`error` 재출력)
- 증상: 작업 취소 후 "Job #5 successfully killed..." 가 화면에 2개. sendfax 오류도 같은 구조.
- 재현: /outbox?kill=5 -> 문구 출현 횟수 2.
- 확인 수준: 재현(outbox), 추론(sendfax)

### R3H-05 (중간) "실시간 갱신" 문구와 달리 폴링/자동완성 JS 가 전혀 없고 /ajax/* 엔드포인트 7개가 어떤 템플릿에서도 호출되지 않음
- 위치: inbox.jinja2:14 ("appear here automatically in real time"), 모든 템플릿(`ajax/` 참조 0건), views/ajax.py 전체
- 증상: 레거시의 ajaxmodemstatus, ajaxinbox, ajaxbook, ajaxprefillto, ajaxdlist, ajaxemailbook, ajaxarchivebook 에 해당하는 화면 동작(모뎀 상태 갱신, 새 팩스 카운트, 수신처 자동완성, 주소록 프리필, 배포목록 번호 채움, 이메일 자동완성, 보관함 회사 검색)이 없음. 새 팩스가 와도 새로고침 전에는 배지/목록이 안 바뀌고 sendfax 는 번호를 전부 수동 입력. F2-12(팝업 미연결)와 달리 자동완성/폴링 전체 부재.
- 재현: `grep -rn "ajax/" templates` 결과 없음, 페이지 네트워크 요청에 /ajax/* 없음.
- 확인 수준: 재현

### R3H-06 (중간) 설정 화면 패스키 목록: 서버 오류(500)를 "등록된 키 없음" 으로 표시, 삭제 결과도 무시
- 위치: settings.jinja2:~266-268 (`if (!res.ok) { ... No Passkeys registered yet }`), deletePasskey ~294-300 (응답 확인 없이 목록만 재조회)
- 증상: /api/webauthn/credentials 가 500(K03)이어도 사용자에게는 정상적으로 "키 없음" 으로 보임. 삭제 실패도 알리지 않음.
- 재현: /settings 열면 콘솔에 500, 화면은 "No Passkeys registered yet."
- 확인 수준: 재현

### R3H-07 (낮음) 패스키 목록이 서버 문자열을 innerHTML 에 그대로 삽입
- 위치: settings.jinja2:~275-288 (`${item.device_name}`, `${item.created_at}`, `onclick="deletePasskey(${item.id})"`)
- 증상: 등록 시 사용자가 입력한 device_name(prompt)이 이스케이프 없이 HTML 로 삽입되어 본인 화면에 저장형 스크립트 삽입이 가능한 구조. 페이로드는 실행하지 않음.
- 확인 수준: 추론

### R3H-08 (중간) WebAuthn credential_id 저장/조회 형식이 브라우저가 보내는 형식과 어긋남
- 위치: services/webauthn.py:~110 (`verification.credential_id.decode("utf-8")` 로 raw 바이트를 문자열화), views/webauthn.py 로그인 verify 는 브라우저의 base64url `id` 로 조회, generate_authentication_options 는 저장값을 `base64url_to_bytes` 로 해석
- 증상: 실제 인증기의 credential id 는 임의 바이트라 utf-8 디코드가 실패하거나, 성공해도 저장값이 base64url 이 아니어서 로그인 시 조회 불일치. 화면에는 "Passkey registration failed" 경고만 표시. K03/K09 를 고쳐도 남는 별개 원인.
- 확인 수준: 추론 (인증기 없어 미재현)

### R3H-09 (중간) Email Book 화면으로 가는 링크가 어디에도 없음
- 위치: addressbook.jinja2, distrolist.jinja2, inbox/sendfax 등 (emailbook 링크는 emailbook.jinja2:22-24 자신에게만 존재)
- 증상: /emailbook, /emailbook/edit 는 URL 직접 입력으로만 접근. 배포목록 화면 칩에도 Email Book 이 없음.
- 재현: /inbox, /addressbook, /distrolist 에서 `a[href^="/emailbook"]` 0개.
- 확인 수준: 재현

### R3H-10 (낮음) 이메일북 "새 연락처" 폼의 기본 id 가 1 이고 새 폼에도 Delete 버튼이 있음
- 위치: emailbook_edit.jinja2:51-52 (`{{ contact.id or 1 }}`), 58-60 (Delete 항상 출력)
- 증상: 신규 작성 폼이 hidden email_id=1 을 싣고 있어 뷰의 `if eid:` 분기(수정/삭제 경로)로 처리될 수 있음. 값을 채운 뒤 Delete 를 누르면 1번 연락처 삭제 요청이 됨. 신규 저장 자체는 재현에서 정상 생성.
- 재현: /emailbook/edit 의 hidden 값 `email_id=1`, `abookemail_id=1` 및 Delete 버튼 존재 확인.
- 확인 수준: 재현(폼 값), 삭제 영향은 추론

### R3H-11 (낮음) 수신함 View 버튼 아이콘이 흰 사각형으로 보임
- 위치: inbox.jinja2:~120 (`<img src="/static/images/viewfax.png" class="... brightness-[10]">`)
- 증상: 컬러 PNG 에 brightness(10) 필터가 걸려 흰 네모가 렌더링됨(shots/1280__inbox.png).
- 재현: 계산 스타일 `filter: brightness(10)` 확인, 스크린샷에서 흰 사각형.
- 확인 수준: 재현

### R3H-12 (중간) 모바일(375px): 관리자 사이드바가 본문 앞에 전부 펼쳐지고 표가 잘리며, 주소록은 가로 스크롤 발생
- 위치: admin_layout.jinja2 <aside> (모바일 접힘 없음), admin_users.jinja2 사용자 표, addressbook.jinja2 표 컨테이너
- 증상: 관리자 화면 375px 에서 내비게이션 20여 항목이 본문 위에 세로로 길게 차지(페이지 높이 약 2600px), 사용자 표의 Email 열이 잘리고 스크롤 수단 없음. /addressbook 은 문서 폭 431px 로 가로 스크롤 발생. (known UI-24 는 사용자 화면 헤더 내비게이션.)
- 재현: shots/375__admin_users.png, audit 결과 hscroll=431 (/addressbook).
- 확인 수준: 재현

### R3H-13 (중간) 송신함이 레거시 대비 열/조작 누락: 사용자, 시도 횟수, 우선순위, 작업 수정(Modify) 링크가 없음
- 위치: outbox.jinja2 표, 대조 legacy outbox.tpl (USER, NUM_DIALS, PRIORITY, MODIFY_FAXJOB, KILL_JOB)
- 증상: 작업을 수정할 진입점이 없고(/ajax/faxalter 는 어디에서도 링크되지 않음) 시도 횟수, 우선순위, 소유 사용자를 볼 수 없음. 실패 작업 표에는 Company, Pages 도 없음.
- 확인 수준: 재현(화면/코드 대조)

### R3H-14 (중간) 팩스 보기 화면에서 Archive/Delete/Note/Assign 동작과 이전/다음 이동이 빠짐
- 위치: viewfax.jinja2:29-65, views/inbox.py viewfax_view (prev_fid/next_fid 를 컨텍스트로 넘기지 않음), 대조 legacy viewfax.tpl
- 증상: `{% if prev_fid %}` 는 뷰가 값을 주지 않아 영원히 숨김. 보기 화면에서 보관/삭제/메모/회사 지정 불가. 수신함 행 메뉴에도 Assign(회사 지정)이 없어 /assign 모달은 도달 경로가 없음. (UI-07 은 가짜 문서 문제)
- 확인 수준: 재현(링크 없음)

### R3H-15 (낮음) 설정 화면이 레거시 필드/안내를 일부 누락하고 일부 select 가 하드코딩
- 위치: settings.jinja2:~135-148, 대조 legacy settings.tpl
- 증상: faxperpagearchive(보관함 페이지당 개수), url, 비밀번호 요구사항 안내(PWD_REQUIREMENTS)가 없음. 기본 표지 select 는 standard/urgent 고정에 `selected` 고정, 페이지당 개수는 항상 20 선택.
- 확인 수준: 재현(필드 목록 대조)

### R3H-16 (낮음) assign 모달: 회사 검색 입력이 무동작이고 fid 를 제출하지 않음
- 위치: modal_assign.jinja2:31-44
- 증상: "Search Company Name" 입력에 필터 JS 가 없어 입력해도 목록이 줄지 않음(레거시는 즉시 필터). 폼에 fid hidden 이 없어 어떤 팩스에 대한 지정인지 서버에 전달되지 않음. (UI-20 은 abook_id=1 고정)
- 확인 수준: 재현(템플릿)

### R3H-17 (중간) refax/note 모달이 GET 으로 열릴 때 가짜 기본값을 입력칸에 미리 채움
- 위치: views/modals.py modal_refax_view (destinations 기본 "+1-555-0199", regarding "Re: Document Transmission", comments "Resending previous transmission."), modal_note_view (description 기본 "Reviewed and verified by operator.")
- 증상: 원본 팩스의 발신번호 대신 가짜 번호가 들어가 그대로 Send 하면 엉뚱한 번호로 발송 시도. 메모 모달은 검토하지 않은 팩스에 "검토 완료" 메모를 저장하게 유도.
- 재현: /refax, /note 열기 -> 값 확인.
- 확인 수준: 재현

### R3H-18 (낮음) sendfax 파일 입력의 접근성/검증: sr-only 입력에 포커스 표시가 없고 파일이 필수가 아님
- 위치: sendfax.jinja2:112-121
- 증상: 드롭존 label 안의 input 이 sr-only 라 키보드 Tab 포커스가 보이지 않음(`focus-within` 스타일 없음). `required` 가 없어 파일 없이 전송 가능(서버 측은 F2-09).
- 확인 수준: 추론(접근성), 재현(required 없음)

### R3H-19 (낮음) home.jinja2 는 도달 불가이거나 깨진 죽은 템플릿
- 위치: home.jinja2:198-209, views/default.py
- 증상: `{% block scripts %}` 는 layout 에 없는 블록(layout 은 extra_scripts)이라 통계 스크립트가 출력되지 않고, 출력돼도 `fetch('/inbox').then(r => r.json())` 은 HTML 을 받아 실패. lucide 아이콘, `brand-*` 색 클래스, 한국어 고정 문구도 로드되지 않거나 스타일 없음. 같은 route 의 login 뷰가 우선이라 사실상 죽은 코드.
- 확인 수준: 추론

### R3H-20 (낮음) 로그인 화면의 사실과 다른 문구와 항상 보이는 SSO/패스키 버튼
- 위치: login.jinja2:~194 ("SHA-256 / PBKDF2 Auth"), ~111-121 (버튼 무조건 출력), ~84-85 (password maxlength=64)
- 증상: 실제 해시는 MD5(SEC-06)인데 화면은 PBKDF2 라고 표기. SAML 사용 설정 여부와 무관하게 SAML/패스키 버튼을 표시(K05 의 화면 쪽 증상). 64자 초과 비밀번호는 입력 단계에서 잘림.
- 확인 수준: 재현(문구), 추론(나머지)

### R3H-21 (낮음) 수신함 드롭다운/전체 선택의 키보드 및 상태 동기화 결함
- 위치: inbox.jinja2 스크립트 (more-btn 핸들러, selectAll)
- 증상: 드롭다운에 aria-expanded/role 이 없고 Esc 로 닫히지 않으며 열린 메뉴로 포커스가 이동하지 않음. 개별 체크를 해제해도 "Select All" 이 체크 상태로 남고, 체크박스에는 행 식별 label 이 없음. (일괄 버튼 무동작은 UI-23)
- 확인 수준: 추론

### R3H-22 (낮음) 주소록 검색어가 소문자로 바뀌어 다시 표시됨
- 위치: views/addressbook.py (`query = ...lower()` 를 템플릿에도 그대로 전달), addressbook.jinja2:18
- 증상: "Acme" 를 검색하면 입력칸과 "No contacts matched" 문구가 "acme" 로 바뀜.
- 확인 수준: 추론(코드)

### R3H-23 (낮음) 프린터 삭제 confirm 이 번역 문자열을 JS 작은따옴표 안에 직접 삽입
- 위치: admin_printers.jinja2:138 (`onsubmit="return confirm('{{ _('...') }}')"`)
- 증상: 번역 문구에 아포스트로피(프랑스어, 이탈리아어 등)가 들어가면 HTML 이스케이프 후 속성이 디코드되어 JS 구문 오류가 나고, 핸들러가 동작하지 않아 확인창 없이 삭제 폼이 제출됨. 현재는 해당 msgid 가 카탈로그에 없어(UI-05) 잠복 상태. `|tojson` 사용 필요.
- 확인 수준: 추론
