# Round 1 UI / 템플릿 / 다국어 결함 보고

대상: numfax 저장소의 src/namifax/templates, static, locale, tailwind.config.js, package.json, babel.cfg.
점검 스크립트와 임시 DB는 scratchpad/agent-ui/ 에 있습니다. 저장소는 수정하지 않았습니다.
K01~K16과 겹치는 항목은 제외했고, 변형 사례만 적었습니다.
기준 경로 접두어 S = src/namifax

## 요약
- 전체 38건 (치명 0, 높음 7, 중간 25, 낮음 6).
- 사전 점검: 모든 /static/ 참조 자산은 실제로 존재함. 템플릿 변수 미전달은 StrictUndefined 기준으로 layout.jinja2의 num_inbox, num_outbox, error, flash_message, current_user 등이 여러 페이지에서 미정의이나(아래 UI-24, UI-19), 기본 설정에서는 조건부라 500이 나지 않음. 24개 로케일의 .mo 는 모두 존재하고 .po 와 placeholder 불일치는 0건.

---

## 치명/높음

### UI-01 (높음) 설정 화면이 아무것도 저장하지 않으면서 "Settings updated successfully." 표시
- 위치: S/views/settings.py:38-75, S/templates/settings.jinja2:29-35
- 증상: 이름, 이메일, 회사, 팩스번호, 서명, 기본 표지, 페이지당 팩스 수, 비밀번호 변경이 전부 DB에 쓰이지 않는다. 언어만 _LOCALE_ 쿠키에 저장된다(사용자 프로필에는 저장 안 됨). 비밀번호 변경 입력(old/new)은 일치 검사만 하고 적용하지 않는다. 프로필 기본값은 "Enterprise Inc.", "+1-555-0100", "ENTERPRISE-HQ" 같은 하드코딩이다. 폼의 coverpage_id, faxperpageinbox 는 뷰가 읽지 않고, 템플릿은 20건 옵션을 항상 selected 로 고정한다.
- 재현: POST /settings name=Zed Person, from_company=ZCo, new_password=n3wpass 후 응답에 "Settings updated" 포함 확인, 이어서 GET /settings 하면 name=Administrator, from_company=Enterprise Inc. 그대로.
- 확인 수준: 재현

### UI-02 (높음) admin_layout.jinja2 가 `message` 를 렌더하지 않아 관리자 화면 다수에서 성공 피드백이 사라짐
- 위치: S/templates/admin_layout.jinja2:346-360 (error, flash_message 만 출력), S/views/admin.py 다수(`"message": message`)
- 증상: 뷰는 `message` 를 전달하지만 레이아웃은 `flash_message` 만 그린다. `message` 를 자체 렌더하는 템플릿은 barcodes, covers, saml, routing_did, storage, smtp, printers 7개뿐이다. categories, dynconf, fax2email, sysfunc, users, modems, system_logs 는 저장/삭제 성공해도 알림이 없다. error 만 보이므로 성공과 무반응을 구분할 수 없다.
- 재현: POST /admin/categories name=UiCatZ create=1 -> 목록에 UiCatZ 생성됨, 응답에 "created successfully" 없음. 빈 이름으로 POST 하면 "required" 오류는 표시됨.
- 확인 수준: 재현

### UI-03 (높음) 시스템 기능 화면(재시작, 종료, 백업 다운로드) 버튼이 뷰와 계약이 안 맞아 전부 무동작
- 위치: S/templates/admin_sysfunc.jinja2:75-130 (submit name=reboot, shutdown, download_ar, download_db), S/views/admin.py:860-878 (`action` == backup/reboot 만 확인)
- 증상: 버튼은 name=reboot 등으로 전송하지만 뷰는 params["action"] 만 본다. 네 버튼 모두 아무 일도 하지 않고 같은 페이지만 다시 렌더한다. 또 뷰는 설령 action=reboot 이어도 `message` 만 세팅하는데 UI-02 때문에 화면에 안 보인다. 실제 재시작, 백업 동작은 구현 자체가 없다("signal sent" 문구만 있음).
- 재현: POST /admin/system_func {"reboot":"1"}, {"shutdown":"1"}, {"download_db":"1"}, {"action":"reboot"} 모두 200, 본문 길이 동일(28510), Content-Disposition 없음, 메시지 없음.
- 확인 수준: 재현

### UI-04 (높음) 빌드된 main.css 가 템플릿과 어긋나 있어 다수 클래스가 스타일 없음 (예: 2FA 활성화 버튼이 흰 글씨 무배경)
- 위치: S/static/css/main.css (마지막 갱신 커밋 a320eb9), tailwind.config.js, S/templates/*.jinja2
- 증상: 템플릿이 쓰는 클래스 중 69종이 main.css 에 없다. 대표 사례:
  - settings.jinja2 의 "Enable 2FA (Setup Authenticator)" 링크: `bg-emerald-600 hover:bg-emerald-500 text-white` 둘 다 없음 -> 흰 배경 위 흰 글씨로 보이지 않음. 같은 파일의 `text-rose-500`, `hover:text-rose-800`, `italic` 도 없음.
  - `shadow-xs`(addressbook_edit, admin_users, admin_system_logs), `backdrop-blur-xs`(모달 3종)는 Tailwind v4 전용 유틸리티라 v3.4.19(package.json)에서는 생성되지 않음.
  - admin_smtp/admin_printers: `grid-cols-3`, `col-span-2`, `bg-emerald-950/40`, `bg-rose-950/50`, `border-rose-500/40`, `text-rose-300`, `hover:bg-blue-500`, `shadow-lg` 누락 -> 암호화 방식 라디오 3열 배치 깨짐, 테스트 결과 배너 배경 투명.
  - login.jinja2: `hover:bg-slate-800`, `my-2`, `pb-6` 누락 -> 패스키/SAML 영역 간격과 hover 없음.
  - home.jinja2 는 tailwind.config.js 에 없는 `brand-*` 색을 사용(하지만 UI-19 참조, 사실상 죽은 템플릿).
  - layout.jinja2 의 `has-tooltip`, `tooltip-text` 는 인라인 style 로 정의되어 있어 정상.
- 재현: templates 의 class 속성에서 토큰을 뽑아 main.css 선택자와 대조하는 스크립트(agent-ui 의 분석)로 69건 확인. 렌더링 픽셀 확인은 하지 않음.
- 확인 수준: 재현(CSS 대조). 시각 영향은 추론.

### UI-05 (높음) 템플릿이 쓰는 문자열 68개가 번역 카탈로그(.pot)와 전 로케일에 없음
- 위치: S/locale/namifax.pot(455건) vs 템플릿의 `_()` 514건
- 증상: 관리자 SMTP/프린터/스토리지/SAML 화면, 설정의 2FA/패스키 섹션, 로그인의 SSO/패스키 버튼, login_totp 등 "Network Printers", "Sign in with Passkey (Touch ID / Security Key)", "Save SAML Configuration", "Enable 2FA (Setup Authenticator)" 같은 68개 msgid 가 pot/po/mo 어디에도 없어 모든 로케일에서 영어로 나온다. ko 도 예외 아님(ko 는 pot 455건은 전부 번역됐으나 이 68건이 없음). pot 갱신(babel extract)이 최근 기능 추가 이후 실행되지 않았다.
- 재현: 템플릿 `_('…')` 를 정규식으로 수집해 pot msgid 집합과 차집합(68건), ko .mo 에서도 미존재 확인(`tmpl ids missing in mo` = ko 68, 나머지 22개 로케일 189).
- 확인 수준: 재현

### UI-06 (높음) 로그인하지 않은 브라우저 요청이 로그인 화면이 아니라 원시 JSON 401 을 받음
- 위치: S/views/forbidden.py:9 (`@forbidden_view_config(renderer="json")`)
- 증상: 세션 만료나 북마크로 /inbox, /admin 등에 접근하면 `{"status": "error", "code": 401, ...}` JSON 텍스트가 화면에 표시된다. /login 리다이렉트 없음.
- 재현: 미인증 TestApp 으로 GET /inbox -> 401 application/json, Location 헤더 없음. GET /admin 도 동일.
- 확인 수준: 재현

### UI-07 (높음) /viewfax 가 실제 팩스 대신 하드코딩된 가짜 문서를 표시
- 위치: S/templates/viewfax.jinja2:15-16, 79-148 (`company or 'Acme Global (+1-555-0100)'`, `archstamp or '2026-09-29 10:00:00'`, `modemdev or 'ttyS0'`, `fid or 1`)
- 증상: 팩스 이미지 자체를 렌더하지 않고 "High-Resolution Raster Preview" 플레이스홀더 종이와 가짜 페이지 썸네일만 그린다. 존재하지 않는 fid 나 fid 없이 접근해도 "ID #N / Acme Global" 을 정상 문서처럼 보여준다. 레거시 viewfax.tpl 의 페이지별 이미지, 썸네일, 회전 표시가 없다. 회전 링크는 JSON 을 돌려주는 GET 라우트(/faxes/rotate/{id})로 이동해 사용자는 JSON 화면을 본다.
- 재현: GET /viewfax -> "Acme", "2026-09-29", "ID #1" 포함. GET /viewfax?fid=99999 -> "ID #99999" 와 Acme 표시.
- 확인 수준: 재현

---

## 중간

### UI-08 (중간) login_totp.jinja2 는 main.css 대신 cdn.tailwindcss.com 런타임 스크립트에 의존
- 위치: S/templates/login_totp.jinja2:7
- 증상: 나머지 페이지는 자체 main.css 를 쓰지만 2FA 화면만 외부 CDN JIT 스크립트를 로드한다. 폐쇄망/온프레미스 어플라이언스(로그인 화면이 "On-Premise Appliance"를 자처)에서는 스타일 없는 화면이 된다. favicon, main.css 링크도 없다. label 에 for, input 에 id 없음, placeholder 영어.
- 확인 수준: 재현(소스). 오프라인 렌더는 추론.

### UI-09 (중간) 전역 `input[type=text|password]` 규칙이 관리자 다크 테마 입력 필드를 덮어쓸 가능성
- 위치: S/static/css/input.css:19-21 -> main.css (`.inputtext,.m3-textfield,input[type=password],input[type=text],select,textarea{background-color:#fff;color:#1a1b1f;padding:.5rem .75rem;…}`)
- 증상: 태그+속성 선택자(0,1,1)가 `bg-slate-900`, `text-white` 같은 유틸리티(0,1,0)보다 우선한다. 관리자 콘솔(다크)의 text/password 입력은 흰 배경에 어두운 글씨가 되고, email/number/select/textarea 는 다크 그대로여서 같은 폼 안에서 모양이 섞인다. 포털 쪽 입력도 `px-4 py-3` 같은 패딩이 무시된다.
- 확인 수준: 추론(CSS 명시도 분석, 브라우저 렌더 미확인)

### UI-10 (중간) 22개 로케일에 fuzzy 100건, 미번역 30건 -> .mo 에서 빠져 영어 노출, fuzzy 내용은 오역
- 위치: S/locale/*/LC_MESSAGES/namifax.po (en, ko 제외 22개)
- 증상: 각 로케일에서 100건이 fuzzy 로 표시되어 컴파일된 .mo 에 들어가지 않는다(po 와 mo 불일치 100건). 대표 fuzzy 값이 틀려 있다(de): "New Company"->"Firma", "No contacts yet"->"Kontakte", "General"->"Normal", "SYSTEM OPERATIONAL"->"System Funktionen", "DID Routes"->"DID/DTMF Route groups". 추가로 30건(SMTP Gateway, Two-Factor Authentication, Verify & Log In, Cover page … successfully 등)은 msgstr 이 비어 있다. 결과적으로 22개 로케일에서 신기능 화면 대부분이 영어다. 번역가가 fuzzy 를 검수 없이 확정하면 오역이 그대로 배포된다.
- 재현: babel read_po/read_mo 로 fuzzy/빈 msgstr/mo 대조(de 샘플 확인).
- 확인 수준: 재현

### UI-11 (중간) 스웨덴어(sv) 카탈로그에 깨진 인코딩(U+FFFD) 13건, 네덜란드어(nl) 1건
- 위치: S/locale/sv/LC_MESSAGES/namifax.po (43행), S/locale/nl/LC_MESSAGES/namifax.po
- 증상: 레거시 Latin-1 문자열이 UTF-8 변환 중 손상되어 "V�lj"(Välj), "L�senord"(Lösenord), "Inst�llningar", "Anv�ndarnamn", "categorie�n" 으로 표시된다. 로그인, 설정, 사용자 화면 등 기본 UI 에 노출.
- 재현: GET /inbox, /sendfax, /settings ... ?lang=sv 응답에 `Anv�nd`, `Inst�llningar`, `L�senord`, `S�k` 포함 확인. nl 은 `categorie�n`.
- 확인 수준: 재현

### UI-12 (중간) fr, pt_BR, de 번역에 HTML 엔티티가 그대로 들어 있어 화면에 "&eacute;" 문자열로 표시
- 위치: S/locale/fr (12건), pt_BR (9건), de (2건) namifax.po/mo. fr 은 "Réception\xa0" 처럼 NBSP 꼬리 공백 3건도 있음.
- 증상: Jinja 자동 이스케이프가 `&` 를 `&amp;` 로 바꾸므로 "S&eacute;lectionner", "T&eacute;l&eacute;charger", "Distribui&ccedil;&atilde;o", "N&uacute;mero", "Usu&aacute;rios" 가 글자 그대로 보인다.
- 재현: fr/pt-br 로 /inbox, /sendfax, /settings, /addressbook, /admin 렌더 후 `&amp;eacute;` 등 검출(`Derni&amp;egrave;re`, `S&amp;eacute;lectionner`, `Distribui&amp;ccedil;&amp;atilde;o`).
- 확인 수준: 재현

### UI-13 (중간) 레거시에서 이관된 번역이 용어 충돌로 오역: "Address Book"이 20개 로케일에서 "이메일 주소록"
- 위치: S/locale/*/namifax.po 의 msgid "Address Book", "Select", "Archive"
- 증상: "Address Book" 이 de "E-Mail Adressen", es "Direcciones de Correo Electrónico", fr "Adresses email", ar "عناوين البريد الإلكتروني", it/pl/ru/tr/… 모두 "이메일 주소" 계열이다(ko 는 "주소록" 정상). 사용자는 팩스 주소록 링크가 이메일북인 줄 안다. 다른 예: ja "Select" -> "タイトル"(제목), ja "Archive" -> "送信履歴"(발송 이력), ro/sv "Reply to FAX" 는 영어 그대로, 여러 로케일에서 "password"/"contraseña" 소문자 잔존.
- 재현: 각 로케일 .mo 에서 키 15개 조회(agent-ui/cat4.py 결과).
- 확인 수준: 재현

### UI-14 (중간) 뷰에서 만든 `_()` 메시지(TranslationString)는 템플릿에서 번역되지 않음
- 위치: S/i18n.py:37 (TranslationStringFactory), S/views/admin.py, S/views/auth.py 의 `error = _("…")`, `message = _("…")`
- 증상: pyramid_jinja2 는 `{{ error }}` 출력 시 TranslationString 을 localizer 로 번역하지 않고 msgid 문자열을 그대로 출력한다. 따라서 카탈로그에 msgid 를 추가해도 뷰 메시지는 영어로 남는다. 또 뷰의 다른 메시지는 `_()` 없이 일반 문자열("Fax category created successfully", "New passwords do not match." 등)이다.
- 재현: ko 로케일 요청에서 forgot.jinja2 를 error=_("Inbox") 로 렌더 -> 출력에 "Inbox" 있고 "받은 팩스함" 없음.
- 확인 수준: 재현

### UI-15 (중간) `<html lang>` 이 항상 "en", 아랍어 RTL 미지원
- 위치: S/templates/layout.jinja2:2, admin_layout.jinja2:2, login.jinja2:2 등 전 템플릿. 레거시 header.tpl 은 `dir="{$LANG.DIRECTION}"` 사용.
- 증상: 로케일이 ko, ja, ar 이어도 lang="en"(스크린리더 발음, 하이픈, 글꼴 선택 오류). 아랍어도 dir=rtl 없이 LTR 배치.
- 재현: GET /inbox?lang=ar -> `<html lang="en" class="h-full">`, `dir=` 없음. ja, de, pt-br 도 lang="en".
- 확인 수준: 재현

### UI-16 (중간) 영문 하드코딩과 `_()` 미적용 문자열이 화면, 플레이스홀더, alert, confirm 전반에 다수
- 위치(대표): layout.jinja2 (nav 툴팁 "View received faxes" 등 5건, "{{n}} Line(s) Ready"/"Standby", "Fax line status", "Admin panel", "Error", 푸터 문구), login.jinja2 (placeholder 2, "Enterprise Facsimile System", "Vendor Spec", 상태 문구, 모든 alert), admin_layout.jinja2 (Module Switcher, 메뉴 옵션 전체, "Quick Jump...", "Superuser", "Error:", 푸터), admin.jinja2 (Workflow Guide 3개 카드 본문 전체, "Config →"), settings.jinja2 (비밀번호 placeholder 3, 패스키 JS 문구 "Registered:", "Error loading passkeys", prompt, confirm "Disable 2FA…?", alert 3종), sendfax.jinja2 (placeholder 5, "Line N —", JS "Click to select a file"), archive, addressbook, distrolist, viewfax(title 속성 7), 모달(title, placeholder), 각 admin 폼의 placeholder 대부분. 제목(`<title>`)도 전부 영문 고정.
- 증상: 스캔상 템플릿 텍스트 노드/속성 약 240건이 `_()` 없이 영어 고정. confirm()/alert()/prompt() 총 22곳 중 번역되는 것은 admin_printers 1곳뿐(그것도 `'{{ _('…') }}'` 형태라 번역문에 `'` 가 있으면 JS 문자열이 깨짐, 추론).
- 재현: 템플릿 정규식 스캔(agent-ui) + ko 렌더 확인(예: 영문 잔존).
- 확인 수준: 재현(스캔). 번역문 따옴표 깨짐은 추론.

### UI-17 (중간) 문장 조각을 이어 붙이는 번역 구조와 가짜 복수형
- 위치: S/templates/inbox.jinja2:25,57-59,237-241 (`{{ _('Showing') }} N {{ _('of') }} M`), viewfax.jinja2 (`{{ _('Page 1 of') }} {{ pages }}`), outbox.jinja2:39, archive.jinja2:15,153 (`_('results') if n != 1 else _('result')`), sendfax.jinja2 (`{{ _('Saved contacts are available in the') }} <a>…</a>.`)
- 증상: 어순이 다른 언어(ko, ja, ar, tr)에서 어색하거나 틀린 문장이 된다. ngettext 미사용이라 러시아어, 폴란드어, 체코어, 아랍어의 복수형 규칙이 적용되지 않는다.
- 확인 수준: 추론

### UI-18 (중간) 모달 6종이 뷰가 넘기는 `message`/`error` 를 전혀 출력하지 않음
- 위치: S/templates/modal_{assign,delete,email,note,refax,txreport}.jinja2 (message/error 참조 0건), S/views/modals.py 의 `"message": message`
- 증상: POST 후 같은 폼이 다시 그려질 뿐 성공/실패 안내가 없다. 삭제, 메모 저장, 이메일 전송 성공 여부를 알 수 없다. 팝업을 닫거나 부모 창을 갱신하는 스크립트도 없다.
- 재현: POST /note fid=1 note=hello, POST /delete fid=1 -> 200, 응답에 성공/실패 문구 없음.
- 확인 수준: 재현

### UI-19 (중간) 모달의 취소/닫기 버튼이 window.close() 인데 링크는 같은 탭 이동
- 위치: S/templates/modal_*.jinja2 (onclick="window.close()" 12곳), 호출부 S/templates/inbox.jinja2:147-171 (`<a href="/email?fid=…">`, target 없음, window.open 없음), viewfax.jinja2
- 증상: 레거시는 mkwin() 팝업으로 열었지만 신규는 일반 링크라 window.close() 가 브라우저에서 차단된다(스크립트로 연 창이 아니면 닫히지 않음). 취소 버튼이 동작하지 않고 사용자는 뒤로 가기를 써야 한다. 모달 html 자체가 전체 페이지(레이아웃 없음)다. 닫기 아이콘 버튼은 aria-label 도 없다.
- 확인 수준: 추론(브라우저 동작)

### UI-20 (중간) modal_assign 이 abook_id 를 1로 고정하고 txreport 는 항상 "전송 성공"을 표시
- 위치: S/templates/modal_assign.jinja2:41 (`<input type="hidden" name="abook_id" value="1" />`, 뷰가 넘기는 값 무시, fid 필드도 없음), S/templates/modal_txreport.jinja2:50 (Status 고정 "Transmitted Successfully (OK)"), S/views/modals.py:67-117 (회사 목록 fallback "Acme Global", "Initech Corp")
- 증상: 할당 대상 회사가 항상 1번으로 처리되고, 실패한 전송의 리포트도 성공으로 표시되며, 회사 목록이 비면 가짜 회사가 나타난다.
- 재현: GET /assign?fid=1 에 name="fid" 없음(확인), txreport 는 소스상 고정 문구.
- 확인 수준: 재현(assign 필드), 추론(나머지 동작)

### UI-21 (중간) 팩스 답장/재시도/주소록 "팩스 보내기" 링크의 prefill 파라미터를 sendfax 가 무시
- 위치: S/templates/inbox.jinja2:137, viewfax.jinja2:66, archive.jinja2:134, outbox.jinja2:133 (`/sendfax?refax=ID`), addressbook.jinja2:68 (`/sendfax?to_company=…&faxnumber=…`), S/views/sendfax.py (GET 분기)
- 증상: Reply, Re-send, Retry 는 빈 폼만 열고, 주소록의 Send Fax 도 번호와 회사를 채우지 않는다. 주소록 링크는 값을 URL 인코딩하지 않아 회사명에 `&`, 공백, `#` 이 있으면 파라미터가 깨진다(추론).
- 재현: GET /sendfax?refax=5, GET /sendfax?faxnumber=123&to_company=Acme -> faxnumber, to_company 입력 value 가 빈 문자열.
- 확인 수준: 재현

### UI-22 (중간) 주소록 검색 링크가 잘못된 파라미터 이름(search) 사용
- 위치: S/templates/inbox.jinja2:108, archive.jinja2:118 (`/addressbook?search={{…}}`) vs S/views/addressbook.py:44 (`request.params.get("q")`), 템플릿 addressbook.jinja2:18 (`name="q"`)
- 증상: 수신함의 발신자명/보관함 결과의 회사명 링크를 눌러도 필터가 적용되지 않고 전체 목록이 나온다. 값 URL 인코딩도 없음.
- 재현: GET /addressbook?search=zzz 에 "No contacts matched" 미표시(필터 미적용).
- 확인 수준: 재현

### UI-23 (중간) 수신함이 레거시 대비 핵심 요소 누락, 일괄 동작 버튼은 무동작
- 위치: S/templates/inbox.jinja2:39-55 (Archive Selected, Delete Selected 가 type=button 이고 핸들러 없음, 체크박스는 form 밖), 237-247 (페이지네이션은 고정된 "1" 버튼 하나), 88 (썸네일 항상 nothumb.gif), 255-303(스크립트는 드롭다운과 전체선택만)
- 증상: 레거시 inbox.tpl 대비 누락: 모뎀 상태 바(#modem-status-div, /ajax/modemstatus 폴링. 신규 템플릿 어디에도 /ajax/* 호출이 없음), 실제 팩스 썸네일, 페이지 이동, 모뎀/DID 그룹 표시, 발신번호와 회사 할당(assign, setcompany), 권한별 삭제 버튼 숨김(SESSION_CAN_DEL), 개별 메모 표시. 선택 후 보관/삭제 버튼이 눌러도 아무 일도 안 일어난다.
- 확인 수준: 재현(소스 확인, 핸들러 부재). 누락 비교는 legacy/avantfax inbox.tpl 기준.

### UI-24 (중간) 헤더의 회선 상태와 배지가 페이지마다 다르게 나옴, 모바일 내비게이션 없음
- 위치: S/templates/layout.jinja2:41 (`hidden md:flex` 내비), 66-72, 85-94 (num_inbox, num_outbox, modem_list 사용), 뷰는 inbox/outbox/sendfax/archive 만 전달
- 증상: 같은 사용자, 같은 시점인데 /inbox, /outbox, /sendfax, /archive 에서는 "2 Lines Ready", /settings, /addressbook, /viewfax 에서는 "Standby" 가 표시된다. 수신/송신 건수 배지도 해당 뷰에서만 나타나고 `num_inbox = len(faxes)` 는 한 페이지 분량이다. md 미만 화면에서는 주 내비게이션(받은함/보내기/보관함/연락처)이 통째로 사라지고 대체 메뉴가 없다(추론).
- 재현: 로그인 후 각 경로 헤더 텍스트 비교(위 결과).
- 확인 수준: 재현(상태 불일치), 추론(모바일)

### UI-25 (중간) 표지 템플릿, 카테고리 선택지가 하드코딩되어 관리자가 만든 값이 UI에 반영되지 않음
- 위치: S/templates/sendfax.jinja2:148-152 (standard/urgent/confidential 고정, 뷰가 넘기는 cover_names 무시), archive.jinja2:54-56 (invoices/legal 고정, 뷰의 categories 무시), settings.jinja2:127-131 (standard/urgent 고정)
- 증상: /admin/covers, /admin/categories 에서 추가한 표지와 카테고리를 선택할 수 없고, 존재하지 않을 수 있는 "confidential", "legal" 이 보인다. 레거시는 cover_list, category 목록을 동적으로 사용.
- 재현: GET /sendfax 의 whichcover 옵션 = ['standard','urgent','confidential'] 고정. archive 의 category select 는 옵션 3개 고정.
- 확인 수준: 재현

### UI-26 (중간) 보관함: 키워드 없는 필터는 결과를 숨기고, 결과 없을 때 가짜 "Acme" 레코드를 표시
- 위치: S/templates/archive.jinja2:108 (`{% if search or faxid %}` 조건으로만 결과 표시), S/views/archive.py:40-52 (결과 없으면 가짜 레코드 1건 삽입)
- 증상: 카테고리, 날짜, 방향 필터만으로 검색하면 상단에 "1 result" 배지가 뜨지만 본문은 "Search the Archive"(검색 전 상태)이고 결과 표는 없다. 키워드로 검색해 0건이어도 "Quarterly Financial Fax Transmission …" 가짜 행 1건이 표시된다. 날짜 입력은 type=text 라 형식 검증 없음(레거시는 달력 사용).
- 재현: GET /archive?category=invoices -> "1 result" 와 "Search the Archive" 동시 출력. GET /archive?search=zzzznotfound -> "1 result"(가짜 행).
- 확인 수준: 재현

### UI-27 (중간) 폼 필드 중 뷰가 읽지 않는 것들(입력해도 버려짐)
- 위치: S/templates/sendfax.jinja2 (numtries, priority, notify_requeue; 레거시 sendtime, killtime, 다중 파일, to_address/zip/city/voicenumber 등은 아예 없음), admin_users.jinja2:140-170 (didrouting[], faxcats[], modemdevs[] 권한 체크박스), admin_smtp.jinja2 (email_sig_text), settings (coverpage_id, faxperpageinbox), addressbook_edit/distrolist_edit/emailbook_edit 의 `save`
- 증상: 템플릿 input name 집합과 뷰 소스의 params 키를 대조해 뷰가 전혀 참조하지 않는 이름을 추출. 사용자 권한(DID, 카테고리, 모뎀) 지정이 저장되지 않고, SMTP 서명 텍스트가 버려지며, 재시도 횟수, 우선순위가 무시된다. 또 sendfax 는 첨부 파일 1개만 받는다(레거시 multifile_upload).
- 확인 수준: 재현(이름 대조, grep). 각 필드의 실제 저장 여부 런타임 검증은 일부만 수행.

### UI-28 (중간) 상태 변경 동작이 GET 링크로 구현됨
- 위치: S/templates/outbox.jinja2:78 (`/outbox?kill=JOBID`), distrolist.jinja2:116 (`/distrolist?dl_id=…&delete=1`), inbox.jinja2 의 `/faxes/rotate/{id}`(상태 변경 GET)
- 증상: 링크 미리보기/프리페치, 브라우저 확장, 메일 클라이언트가 호출하면 작업이 취소되거나 배포 리스트가 삭제된다. CSRF 에도 무방비.
- 재현: GET /outbox?kill=5 -> "successfully killed" 플래시 표시.
- 확인 수준: 재현

### UI-29 (중간) 모든 POST 폼에 CSRF 토큰이 없음
- 위치: S/templates/*.jinja2 전체(`csrf` 문자열 0건), S/views, S/security.py. 폼은 `_submit_check` 숨은 필드만 사용(레거시 패턴, 보안 효과 없음).
- 증상: 관리자 사용자 삭제, 설정, 모뎀, SMTP, SAML 설정 등 모든 상태 변경 POST 가 교차 사이트 요청에 취약. 세션 쿠키 SameSite 설정도 확인되지 않음(세션 팩토리 자체가 K02).
- 확인 수준: 추론(저장소 전체 grep, 실제 CSRF 공격은 미시도)

### UI-30 (중간) SMTP 비밀번호가 HTML 에 평문 value 로 다시 출력됨
- 위치: S/templates/admin_smtp.jinja2:146 (`<input type="password" name="smtp_password" value="{{ config.smtp_password or '' }}"`), S/services/smtp_settings.py:39-63 (get_settings 가 smtp_password 반환)
- 증상: 저장된 SMTP 비밀번호가 페이지 소스와 개발자도구에 그대로 노출된다. 같은 분류의 스토리지는 secret_key 를 플레이스홀더 "••••"로 숨기는 올바른 패턴을 쓰므로 불일치.
- 확인 수준: 추론(저장 경로가 K01 로 깨져 있어 값 주입 재현 불가)

### UI-31 (중간) 관리자 화면에 하드코딩된 가짜 상태/수치
- 위치: S/templates/admin_sysfunc.jinja2:54-62 ("faxq daemon RUNNING (pid 1024)", "hfaxd RUNNING (port 4559)", "web worker pid 2048"), 104-112 ("12.4 GB in 1,420 files", "18.2 MB (SQLAlchemy ORM)", "Last Snapshot: Today, 04:00 AM"), admin_layout.jinja2:300 ("Appliance Engine Online" 항상 점등), admin.jinja2 ("SYSTEM OPERATIONAL", "Hardware Ready", "Running", "v6.0.7" 기본값, "SQLAlchemy / SQLite" 고정), admin_layout.jinja2:341 ("Superuser" 고정), login.jinja2:208,213 ("SHA-256 / PBKDF2 Auth", "HylaFAX Engine Active")
- 증상: 실제 데몬이 죽어도, DB 가 MySQL 이어도 항상 정상처럼 표시. 로그인 화면의 "SHA-256 / PBKDF2 Auth" 는 시드 비밀번호가 평문(K10)인 현실과 불일치하는 허위 문구.
- 재현: /admin/system_func 렌더 결과에 고정 값 존재.
- 확인 수준: 재현

### UI-32 (중간) 접근성: label 미연결, 중복 id, 아이콘 전용 버튼, 대체 텍스트
- 위치:
  - admin_smtp, admin_printers, admin_saml, admin_storage 의 입력 약 31개: `<label>` 에 for 없고 input 에 id 없음(스크린리더 이름 없음, 클릭 포커스 안 됨).
  - admin_layout.jinja2:70,317: `id="menuObj"` 가 두 번 존재(모바일용과 데스크톱용, CSS 로 숨김만 하므로 DOM 에는 둘 다 있음) -> 잘못된 HTML, label for 가 첫 요소를 가리킴.
  - inbox.jinja2: 행 체크박스(removefax[])에 label/aria-label 없음, "선택" 헤더만 sr-only.
  - admin_users 체크박스 7개, addressbook 검색(name=q), distrolist 멤버 추가 입력(name 도 없음), login_totp 코드 입력, admin_system_logs select 2개: 접근 가능한 이름 없음.
  - 모달 닫기(X) 아이콘 버튼 4종: aria-label 없음. 인박스 "…" 버튼의 aria-label="More actions", 이미지 alt "Fax preview" 는 번역되지 않음.
  - 사이트 전체에서 포커스 링이 sr-only 파일 입력(sendfax)에는 없음(키보드 사용자는 첨부 버튼 포커스를 알 수 없음).
- 재현: 템플릿 스캔 스크립트로 unlabeled 입력 집계(위 수치).
- 확인 수준: 재현

---

## 낮음

### UI-33 (낮음) 404 페이지가 Pyramid 스타터 문구이고 로그인 사용자여도 내비게이션 없음, 죽은 템플릿/자산 잔존
- 위치: S/templates/404.jinja2 ("Pyramid Starter project"), S/views/notfound.py, S/templates/mytemplate.jinja2 (Cookiecutter 안내문), S/templates/home.jinja2(한국어 하드코딩 "NamiFAX 엔터프라이즈 포털" 등, 존재하지 않는 `brand-*` 색상, fetch('/inbox')), S/static/theme.css(빨간 배경 스타터 CSS), S/static/pyramid.png, pyramid-16x16.png
- 증상: 404 는 current_user 가 전달되지 않아 헤더 없는 깡통 페이지에 스타터 문구를 출력한다. `/` 라우트는 auth 뷰(GET)가 우선하므로 home.jinja2 는 어디서도 렌더되지 않고, mytemplate.jinja2, theme.css, pyramid*.png 도 참조 0건.
- 재현: 로그인 상태에서 GET /nope -> 404, 본문에 "Starter" 포함, `<header` 없음. 익명도 동일.
- 확인 수준: 재현

### UI-34 (낮음) 관리자 빠른 이동, 브레드크럼에 프린터, 스토리지, SAML 누락
- 위치: S/templates/admin_layout.jinja2:92-103(모바일 select 에는 있음), 317-332 (데스크톱 Quick Jump 에 printers, storage, saml 옵션 없음), 281-296 (브레드크럼 분기에 printers, storage, saml 없음 -> `{{ current_admin_tab }}` 원시 슬러그)
- 증상: 데스크톱 Quick Jump 드롭다운은 12개 항목뿐이고, /admin/printers, /admin/storage, /admin/saml 에서는 브레드크럼이 "printers"/"storage"/"saml"(번역 없는 소문자 슬러그, CSS capitalize)로 나온다.
- 재현: GET /admin/printers 등의 브레드크럼 텍스트 = 'printers', 'storage', 'saml'.
- 확인 수준: 재현

### UI-35 (낮음) 브랜드, 버전 표기 불일치, 캐시 버스터 불일치
- 위치: layout.jinja2:155 ("NamiFAX Enterprise Edition 3.3.5"), login.jinja2:189, 14 ("NamiFAX v3.3.5", sr-only ":: AvantFAX LOGIN :: AvantFAX 3.3.5", "Vendor Spec" -> avantfax.com), admin_layout.jinja2:366 ("© 2005 - 2008 iFAX Solutions, Inc."), 패키지 버전은 4.0.0(`S/__init__.py`, pyproject). main.css 링크의 쿼리가 layout/login/admin_layout 은 `?v=3.5.1`, 모달 6종, forgot, pwdexpired 는 `?v=3.3.5`. package.json 의 name="avantfax", repository 가 YetOpen/avantfax, 스크립트 build:css 는 있으나 postcss 설정 없이 autoprefixer 가 devDependency 로만 존재.
- 증상: 화면마다 버전과 저작권이 다르고, CSS 를 재빌드해도 모달 페이지는 예전 버전 문자열로 캐시(max-age 3600)되어 갱신이 늦다.
- 확인 수준: 재현(소스/HTTP 헤더 확인)

### UI-36 (낮음) 배포 리스트 편집의 "Remove"/"Add Member" 버튼과 입력이 무동작
- 위치: S/templates/distrolist.jinja2:88-103 (`type="button"` 이고 핸들러 없음, 입력에 name 없음)
- 증상: 멤버 제거와 추가 UI 가 있지만 동작하지 않는다(폼 제출은 listname 만 보냄). 레거시의 연락처 선택 팝업(distrocontacts, dlcontacts.js)도 없음.
- 확인 수준: 재현(소스상 핸들러 부재)

### UI-37 (낮음) 정적 디렉터리에 표지 원본과 불필요 자산이 공개
- 위치: S/static/images/cover.ps, cover-letter.ps(각 약 239KB), coverpage.html; routes.py:8 `add_static_view("static","static")`(인증 없음), 폰트 `Roboto` 를 tailwind.config.js 에서 지정했지만 로드하는 링크가 어디에도 없음(시스템 폰트로 대체).
- 증상: 로그인 없이 /static/images/cover.ps 등 다운로드 가능(표지 템플릿 내용 노출). 로컬 폰트 번들/링크 없음.
- 재현: 익명 GET /static/images/avantfax-big.png 200(정적 공개 확인). 표지 파일도 동일 경로 구조이므로 공개(개별 요청은 생략).
- 확인 수준: 재현(정적 공개), 추론(표지 노출 영향)

### UI-38 (낮음) 번역 카탈로그 메타데이터 손상
- 위치: S/locale/*/LC_MESSAGES/namifax.po 머리말, S/locale/namifax.pot
- 증상: 모든 .po 의 첫 헤더 줄이 "Project-Id-Version: NamiFAX 4.0.Language: kMIME-Version: 1.Content-Type: text/plain; charset=utf-Content-Transfer-Encoding: 8bi"처럼 여러 헤더가 잘려 붙은 깨진 문자열이다(뒤에 정상 헤더가 중복). 주석 출처가 개발자 홈 절대경로(/home/jiho/numfax/src/…)이고, pot 자체가 `#, fuzzy` 헤더와 "PROJECT VERSION" 플레이스홀더를 가진다. `pybabel update` 시 충돌 위험, 번역 도구 호환성 저하. PO-Revision-Date, Last-Translator 는 템플릿 기본값 그대로.
- 재현: `head -8 S/locale/ko/LC_MESSAGES/namifax.po` 등.
- 확인 수준: 재현

---

## 점검했으나 결함이 아니었던 항목
- /static/ 참조 경로: 템플릿 전체에서 참조하는 이미지 전부 실재. main.css 는 CDN 이 아닌 로컬 빌드 산출물을 사용(login_totp 만 예외, UI-08).
- 24개 로케일 모두 .mo 존재, .po 의 placeholder(%s, %(x)s, {}) 불일치 0건.
- 로케일 전환: ?lang= 과 _LOCALE_ 쿠키로 ko, ja, de, ar, zh-tw, pt-br 전환 동작. 알 수 없는 코드(xx)는 쿠키 값(ko)을 유지. 다만 사용자 프로필 언어 영구 저장은 UI-01 에 해당.
- Jinja 자동 이스케이프: `|safe` 사용 0건, 사용자 입력 출력은 이스케이프됨.
- 폼 action, fetch 경로와 라우트: /api/webauthn/* 를 포함한 fetch 경로와 메서드는 라우트와 일치(뷰 내부 오류는 K02, K03, K09). 링크 중 404 는 K11 의 `/archive/move/`, `/delete/{id}` 외 없음.
