# 2라운드 점검: 계정과 권한의 전체 수명주기 (agent-r2-acct)

범위: 사용자 생성 -> 첫 로그인 -> 비밀번호 변경 -> 설정 -> 권한별 화면/데이터 -> 비밀번호 정책 -> 로그아웃/세션 -> 수정/비활성화/삭제.
방법: 저장소는 수정하지 않았고, NAMIFAX_DB_PATH 를 scratchpad/agent-r2-acct/a.db 로 지정해 webtest 로 실제 앱(namifax.create_app)을 구동해 재현했다.
재현 스크립트는 scratchpad/agent-r2-acct/t*.py 이다. 공격 페이로드(명령/SQL 주입)는 실행하지 않았다.
표기: 경로의 줄 번호는 src/namifax 기준이다. K/SEC/USR/COR/ADM/UI 번호는 known2.md 의 기존 항목이다.

## 권한 판정 일관성 비교표

테스트 계정: plain(일반, modemdevs=ttyS0, faxcats=1, any_modem=0, can_del=0), supr(superuser=1 만), adm(is_admin=1 만), cd(can_del=1 만).
DB 에는 타 모뎀(ttyS1)/타 카테고리 팩스(fid 2, 3)를 넣어 두었다.

| 경로(같은 데이터) | 인증 | 모뎀/카테고리 제한 | can_del | superuser/is_admin 판정 | 관찰 결과 |
|---|---|---|---|---|---|
| GET /inbox (목록) views/inbox.py:16 | 필요 | 사실상 없음 (identity 에 modemdevs 키가 없어 None -> 전체) | - | superuser 또는 is_admin | plain 이 타 모뎀 fid 2 를 봄 (USR-04) |
| GET /ajax/inbox (배지) views/ajax.py:54 | 불필요 | 없음 | - | - | TypeError 로 항상 0 (F3-24) |
| GET /viewfax, /faxes/download, /faxes/rotate, /rotate, /setcompany | 필요 | 없음 (fid 만으로 접근) | - | - | plain 이 fid 2 의 미리보기/PDF 접근 (SEC-03) |
| GET /archive views/archive.py:14 | 필요 | 조건 미전달 (F3-06) | - | superuser = is_admin 만 | 비관리자 검색은 영구 0건, supr 은 inbox 와 달리 제한 사용자 취급 |
| GET /outbox views/outbox.py:11 | 필요 | 소유자 필터 없음 (F3-09) | - | 판정 자체가 없음 | plain 이 bob/admin 작업 전부 + 취소 버튼 노출 |
| POST /ajax/deletefaxes | 불필요 | 없음 | 미검사 (F3-03) | - | 비로그인/can_del=0 사용자가 삭제 성공 |
| POST /delete (modal) views/modals.py:146 | 필요 | 없음 | 미검사 (F3-03) | - | can_del=0 인 plain 이 타 모뎀 fax 포함 삭제 |
| POST /addressbook/edit delete views/addressbook.py:69 | 필요 | - | 미검사 (F3-03) | - | 코드상 can_del 확인 없음 |
| GET /ajax/book, /ajax/emailbook, /ajax/prefillto, /ajax/dlist, /ajax/archivebook, /helper/* | 불필요 (F3-04) | - | - | - | 로그아웃 상태에서 주소록/배포목록 전부 조회 |
| GET/POST /sendfax views/sendfax.py:75 | 필요 | 모뎀 선택 제한 없음 (F3-07) | - | any_modem 미사용 | plain 이 금지된 ttyS1 로 POST 성공(302 /outbox) |
| GET /admin, /admin/users (permission=admin) | 필요 | - | - | role:admin = is_admin 또는 superuser (F3-05) | supr(is_admin=0) 이 200, 레거시는 is_admin 만 |
| 상단 메뉴의 Admin 링크 layout.jinja2:90 | - | - | - | is_admin 만 | supr 은 링크가 없는데 URL 은 열림 |
| /inbox 의 Delete 버튼 inbox.jinja2:169 | - | - | 미검사 | - | can_del=0 이어도 버튼 표시 |

---

## 결함 목록

### F3-01 (높음) 2FA(TOTP) 가 로그인에서 전혀 강제되지 않음: TotpService 가 연결 없는 avantfax 엔진을 사용
- 위치: services/totp.py:5, 11-12 (avantfax.db.engine.DatabaseEngine, 인자 없음), views/auth.py:57-60, 91-93, views/settings.py:73
- 증상: UserTOTP 에 is_enabled=1 행이 있는 사용자가 비밀번호만으로 곧바로 /inbox 로 들어간다. 로그인 뷰는 request.db 가 없어 TotpService(None) 을 만들고, 이 서비스는 namifax 엔진이 아니라 연결이 없는 avantfax 엔진을 써서 쿼리가 실패(executed=False)하며 is_totp_enabled 가 False 를 돌려준다. verify_user_login 도 레코드를 못 읽으면 True(fail-open)를 돌려주므로 나중에 이 부분만 고쳐도 같은 조건에서 통과한다.
- 재현: UserTOTP(uid=4, is_enabled=1) 삽입 후 plain 으로 POST /login -> 302 /inbox, 이어서 GET /inbox 200 (t14.py). TotpService() 는 is_totp_enabled(4)=False, get_default_engine() 을 주입하면 True (t15.py).
- K02(세션 팩토리 없음), K08(활성화 UI 없음), SEC-07(평문 저장) 과 다른 결함이다. 세션 문제가 고쳐져도 2FA 는 여전히 우회된다.
- 확인 수준: 재현

### F3-02 (높음) 일반 사용자가 자기 비밀번호를 바꿀 수 있는 경로가 하나도 없고, 세 화면 모두 성공을 위장함
- 위치: views/auth.py:126-140 (forgot), 152-172 (pwdexpired), views/settings.py:37-67 (settings)
- 증상:
  1. /forgot POST 는 계정 조회도 reset_password 도 메일 발송도 하지 않고 "If an account matches ..., reset instructions have been dispatched" 를 항상 표시한다. DB 불변.
  2. /pwdexpired POST 는 old 비밀번호 검증과 변경 없이 /login 으로 리다이렉트한다. permission="public" 이라 로그인 없이도 호출되고, 틀린 old 비밀번호와 1글자 새 비밀번호도 같은 성공형 응답을 받는다. 레거시는 check_login 을 요구하고 set_newpassword 를 호출한다.
  3. /settings 는 old_password 를 검증하지 않고 잘못된 값에도 "Settings updated successfully." 를 띄운다.
  결과적으로 강제 변경(wasreset/첫 로그인/만료), 분실 재설정, 자발적 변경이 모두 죽어 있고, 관리자 화면 입력이 유일한 경로인데 그것도 ADM-05 로 깨져 있다. SEC-05(만료 미강제)와 UI-01(설정 미저장) 은 각각의 증상이고, 이 항목은 "비밀번호 수명주기 전체가 끊김"이라는 이음새 결함이다.
- 재현: t10.py. plain 으로 /pwdexpired(올바른 old), /pwdexpired(틀린 old), /settings(틀린 old) 전부 성공형 응답이고 password 해시 불변, 새 비밀번호로 로그인 불가(login newpass -> 302 없음), 옛 비밀번호로 로그인 성공. /forgot 은 존재하지 않는 이메일에도 "dispatched".
- 확인 수준: 재현

### F3-03 (높음) can_del 권한이 어디에서도 검사되지 않음 (삭제 경로 3곳 + UI)
- 위치: views/ajax.py:283-296, views/modals.py:146-166, views/addressbook.py:69-72, 151-, templates/inbox.jinja2:54, 169 (grep 결과 can_del 참조는 admin_users 템플릿/뷰뿐)
- 증상: 레거시는 ajax/delete.php, ajax/ajaxdeletefaxes.php, addressbook_edit.php 에서 can_del 을 요구한다. 새 앱은 can_del=0 사용자도 팩스와 주소록 항목을 삭제하고, UI 는 Delete 버튼을 모두에게 보여 준다. 관리자 폼의 can_del 체크박스는 저장만 되고 효과가 없다.
- 재현: can_del=0 인 plain 으로 POST /ajax/deletefaxes fids=3 (타 모뎀 팩스) -> fid 3 삭제, POST /delete?fid=4 -> fid 4 삭제 (t8.py). 주소록 경로는 코드 확인(추론).
- SEC-02(비인증 조작)와 별개로, 로그인한 정상 사용자에 대한 권한 미적용이다.
- 확인 수준: 재현(팩스), 추론(주소록)

### F3-04 (높음) 주소록/배포목록/이메일북/모뎀 상태가 로그아웃 상태에서 그대로 조회됨 (SEC-02 의 읽기 쪽 변형)
- 위치: views/ajax.py:15, 66, 106, 140, 186, 318 및 views/helpers.py:11-227 (view_config 에 permission 없음, 앱에 default permission 없음)
- 증상: 로그인 없이 /ajax/book, /ajax/emailbook, /ajax/prefillto?fnid=1, /ajax/dlist?dl_id=1, /ajax/archivebook, /helper/faxcontacts, /helper/emailcontacts, /ajax/modemstatus 가 200 으로 회사명, 팩스번호, 담당자명, 주소, 이메일, 배포목록, 모뎀 상태를 돌려준다. 같은 데이터의 /addressbook 은 401 이다. SEC-02 는 상태 변경 엔드포인트만 지적했다.
- 재현: 세션 없이 GET 위 경로들 모두 200 (t11.py), /addressbook /inbox /admin 은 401.
- 확인 수준: 재현

### F3-05 (높음) superuser 만 있는 계정이 관리자 영역 전체에 접근하고, 관리자 폼에서 저장만 해도 is_admin 이 영구 부여됨
- 위치: security.py:131 (is_admin or superuser -> role:admin), views/admin.py:30 (목록의 is_admin 을 is_admin or superuser 로 계산), 884-888 등 인라인 재검사, templates/admin_users.jinja2:116
- 증상: 레거시 admin/check_login.php 는 check_admin_login(is_admin) 만 본다. superuser 는 "모든 팩스를 본다"는 의미로 관리자 영역 권한이 아니다. 새 앱은 superuser 만 켠 계정에 /admin, /admin/users(사용자 생성/삭제), SMTP/SAML/스토리지 설정을 모두 열어 준다. 더 나쁜 점은 사용자 목록 헬퍼가 is_admin 을 superuser 와 OR 해서 편집 폼의 "Admin" 체크박스를 켠 채로 그리므로, 관리자가 그 사용자의 이름만 고쳐 저장해도 is_admin=1 이 DB 에 기록된다. 메뉴의 Admin 링크는 is_admin 만 보므로 UI 와 서버 판정도 어긋난다.
- 재현: supr(is_admin=0, superuser=1) 로그인 후 GET /admin 200, /admin/users 200 (cd, plain 은 403) (t4.py). 관리자로 supr 편집 폼 제출(이름만 변경) 전 is_admin=0 이었고 후 is_admin=1 (t16.py).
- ADM-06(자기 강등/세션 미반영)과 다른 결함이다.
- 확인 수준: 재현

### F3-06 (중간) 아카이브 검색이 권한 조건(모뎀/카테고리/userid)을 전혀 넘기지 않고 superuser 를 is_admin 으로 대체함
- 위치: views/archive.py:193-201
- 증상: criteria 에 superuser=identity.is_admin 만 들어가고 modemdevs, categories, userid 가 없다. FaxPDFArchive.search_archive 는 비슈퍼유저에서 target_routes=None 으로 "AND (None OR userid = None)" 같은 조건을 만들어 항상 0건이다. 그래서 (1) 일반 사용자는 자신에게 허용된 팩스도 아카이브에서 영원히 못 찾고, (2) superuser 만 켠 계정은 inbox 에서는 전체 조회(views/inbox.py:24)인데 아카이브에서는 제한 사용자로 취급되며, (3) USR-01/02 의 placeholder 버그가 고쳐지면 곧바로 드러난다. 현재는 fa.get_company 미존재(AttributeError, try/except 로 삼킴) 때문에 모든 사용자가 가짜 "Acme" 행만 본다.
- 재현: search_archive({"keywords":"ARCH","superuser":False}) = 0, 같은 기준에 modemdevs=['ttyS0'], faxcats=['1'], userid=4 를 주면 1건 (t6.py, t7.py). 화면에서는 전 계정이 placeholder 만 받음 (t5.py).
- 확인 수준: 재현

### F3-07 (높음) 팩스 발송이 사용자별 모뎀 권한(modemdevs, any_modem)을 무시함
- 위치: views/sendfax.py:79, 118-131 (get_all_admin_modems 를 전원에게 사용, POST 의 modem 값 무검증). 레거시 sendfax.php:21-30, 72, 153-160
- 증상: 레거시는 superuser 가 아니면 사용자의 modemdevs 목록만, any_modem 이 아니면 "any" 선택지를 없앤다. 새 앱은 모든 사용자에게 전 모뎀을 보여 주고, 폼에 없는 모뎀 값을 POST 해도 그대로 sendfax -h 로 넘긴다. 관리자 폼의 any_modem/모뎀 체크박스가 발송에 영향이 없다.
- 재현: any_modem=0, modemdevs=ttyS0 인 plain 의 GET /sendfax 옵션에 ttyS0, ttyS1 모두 표시, POST modem=ttyS1 -> 302 /outbox (t18.py).
- 확인 수준: 재현

### F3-08 (높음) 발송 시 사용자 신원(-o 사용자, -f 이메일, from_*/TSI)이 전혀 전달되지 않음
- 위치: views/sendfax.py:30, 35-63 (identity 매개변수는 받기만 하고 사용하지 않음). 레거시 sendfax.php:167-199
- 증상: 레거시는 -o username, -f user email, from_person/company/location/voice/fax, TSI 를 붙인다. 새 앱은 붙이지 않으므로 HylaFAX 작업 소유자는 웹 서버 사용자가 되고, 발송 결과 통지가 사용자에게 가지 않으며, 소유자별 큐(list_owner)가 성립하지 않아 F3-09 와 함께 "내 작업만 보기"가 불가능해진다. 설정 화면의 프로필이 저장되지 않는 점(UI-01)과 합쳐져 커버 페이지 발신자 정보도 비게 된다.
- 재현: 코드 읽기. HylaFAX 미설치 환경이라 실제 sendfax 호출은 실행하지 않음.
- 확인 수준: 추론

### F3-09 (높음) 송신 큐(outbox)가 모든 사용자에게 전체 사용자의 작업을 노출
- 위치: views/outbox.py:27-36 (fq.process_queue() 결과를 그대로 사용, superuser/소유자 분기 없음). 레거시 outbox.php:18-22, 42-47, 85-90 은 superuser 면 get_queue, 아니면 list_owner(username)
- 증상: 일반 사용자의 /outbox 에 타 사용자의 작업 번호, 상태, (대상 번호 필드가 맞으면) 수신처와 취소 버튼이 모두 표시된다. 헤더의 "Outbox N" 배지도 전체 건수다. USR-07 은 취소의 소유자 검증만 지적했다.
- 재현: scratchpad 안에 faxstat 스텁(owner=bob, owner=admin 작업 2건)을 PATH 에 두고 plain 으로 GET /outbox -> #101(bob), #102(admin) 이 Cancel 버튼과 함께 표시 (t19.py, t20.py).
- 확인 수준: 재현

### F3-10 (높음) 관리자 하드코딩 로그인이 비밀번호 변경, 계정 비활성화, 마지막 로그인 기록을 모두 무력화 (K10 의 변형)
- 위치: views/auth.py:42 (username == "admin" and password == "password" 이면 user.login 을 건너뜀), security.py:328-344
- 증상: K10 은 우회 존재 자체를 보고했다. 추가로 드러난 영향: admin 의 비밀번호를 바꿔도, admin 계정을 acc_enabled=0 으로 비활성화해도 admin/password 로 계속 로그인된다(acc_enabled, wasreset, 만료 검사 전부 건너뜀). user.login 이 호출되지 않아 admin 의 last_login/last_ip 가 영원히 기록되지 않고 사용자 목록에 "Never" 로 남는다. 계정이 없거나 이름이 바뀌면 remember() 가 user_id=None 세션을 만든다.
- 재현: admin 해시를 다른 값으로 바꾼 뒤, 그리고 acc_enabled=0 으로 바꾼 뒤 POST /login admin/password -> 둘 다 302 /inbox (t9.py). 이후 admin 행 last_login 은 NULL.
- 확인 수준: 재현

### F3-11 (높음) 비활성화/삭제/비밀번호 변경이 이미 발급된 세션과 다른 인증 경로에 반영되지 않음
- 위치: web/session.py:39-65 (세션은 로그인 시점 스냅샷이고 사용자 테이블을 다시 읽지 않음), security.py:102-114, views/webauthn.py:115-132, services/saml.py:141-143 (acc_enabled 검사 없음)
- 증상: 비활성화(acc_enabled=0)나 비밀번호 변경 후에도 기존 세션은 TTL(비활성 2시간, 요청마다 연장) 동안 계속 유효하다. 로그아웃 시에만 폐기된다. 패스키(load_by_id 후 로그인)와 SAML(provision_or_get_user)은 레거시 login_webauth 와 달리 acc_enabled/deleted 를 확인하지 않아 비활성 계정도 통과하도록 작성돼 있다. 삭제 시에도 UserTOTP, WebAuthn 자격증명은 정리되지 않는다(remove 는 UserPasswords 만 정리). ADM-06 은 권한 변경 미반영만 다뤘다.
- 재현: plain 로그인 후 DB 에서 acc_enabled=0 으로 변경 -> 기존 세션의 GET /inbox 200 (새 로그인은 거부). 비밀번호 해시 변경 후에도 기존 세션 200 (t9.py). 패스키/SAML/삭제 정리는 코드 읽기(추론).
- 확인 수준: 재현(세션), 추론(패스키/SAML/삭제)

### F3-12 (높음) 관리자 사용자 폼에 활성화, 비밀번호 주기, 재사용 금지, 언어 등 레거시 필드가 없어 비활성화와 만료 정책을 설정할 방법이 없음
- 위치: templates/admin_users.jinja2:86-200 (필드: name, username, password, email, is_admin, superuser, can_del, any_modem, didrouting[], modemdevs[], faxcats[]), views/admin.py:108-146. 레거시 users.tpl:13-21 의 acc_enabled, pwdcycle, pwd_reuse, language, coverpage_id, audiofile, from_*, user_tsi, faxperpage* 가 없음
- 증상: 관리자가 UI 로 계정을 비활성화할 수 없고(레거시는 비활성화 시 wasreset 까지 세팅), 비밀번호 만료 주기(3/6개월)와 재사용 허용도 설정할 수 없다. create()/change_password() 의 pwdcycle 계산은 입력이 없어 영구히 None 이다. 편집 폼의 modemdevs/didrouting/faxcats 체크박스는 전부 무조건 checked 로 그려지므로(템플릿 143, 156, 169), ADM-04 가 고쳐져도 사용자를 편집해 저장할 때마다 모든 모뎀/분류가 재부여된다. 사용자 목록에도 활성 상태 열이 없다.
- 재현: GET /admin/users?uid=5 의 form.fields 에 acc_enabled, pwdcycle, pwd_reuse 없음 (t16.py), 체크박스는 템플릿상 고정 checked.
- 확인 수준: 재현

### F3-13 (중간) 설정 화면이 모든 사용자에게 하드코딩된 관리자 프로필과 고정 발신자 정보를 표시
- 위치: views/settings.py:15-24 (name "Administrator", email admin@avantfax.local, from_company "Enterprise Inc.", from_faxnumber +1-555-0199, email_sig 등 고정값), 11 (identity 에 name/email 키가 없음)
- 증상: DB 의 본인 프로필(name, email, from_*, tsi, email_sig, faxperpage, language)을 읽지 않는다. plain 이 들어가도 "Administrator / admin@avantfax.local" 이 표시된다. UI-01 은 저장 안 됨을 지적했고, 이 항목은 조회도 타인(시드 관리자) 값으로 채워진다는 점이다. 사용자가 이를 그대로 저장하려 하면 타인 정보로 착각하거나 잘못된 발신자 값을 입력하게 된다.
- 재현: plain/supr/adm/cd 로 GET /settings, 모두 "Administrator"와 "admin@avantfax.local" 포함 (t4.py).
- 확인 수준: 재현

### F3-14 (중간) 설정 화면의 2FA 상태가 항상 "미사용"으로 표시되어 해제 폼이 나타나지 않음
- 위치: views/settings.py:70-75 (identity.get("uid") 사용, 그러나 security.py:103-110 의 identity 키는 user_id), templates/settings.jinja2:212-236
- 증상: TOTP 가 활성화된 사용자의 설정 화면에도 "Enable" 링크(/login/totp?setup=1)만 나오고 Disable 폼이 렌더되지 않는다. 사용자가 2FA 를 끌 방법도 상태를 확인할 방법도 없다(F3-01 과 별개의 키 이름 불일치).
- 재현: UserTOTP(uid=4, is_enabled=1) 삽입 후 GET /settings: "Disable 2FA" 없음, setup=1 링크 있음 (t13.py).
- 확인 수준: 재현

### F3-15 (중간) SAML/패스키 로그인이 성공해도 보안 정책이 인식하는 세션이 만들어지지 않음, RelayState 오픈 리다이렉트
- 위치: views/saml.py:58-64, views/webauthn.py:129-132 (request.session["username"]/["uid"] 만 설정), security.py:260-275 (identity 는 namifax_session 쿠키, Bearer, session["token"] 만 인식), views/saml.py:41, 64 (RelayState 무검증 리다이렉트)
- 증상: K02/K03 을 고쳐 세션 객체가 생겨도 두 경로는 remember()/create_session 을 호출하지 않으므로 이후 요청의 request.identity 는 None 이다. 즉 /inbox 로 보내진 뒤 다시 로그인 화면으로 돌아온다. (webauthn _get_current_user 는 session["username"] 을 별도로 받아 주므로 일부 API 만 동작하는 비대칭도 생긴다.) 또한 ACS 는 POST 된 RelayState 를 그대로 Location 으로 사용하므로 절대 URL 이면 오픈 리다이렉트다(K04 로 SAMLResponse 위조가 가능해 누구나 트리거).
- 재현: 코드 읽기(세션 팩토리 부재로 실행 불가).
- 확인 수준: 추론

### F3-16 (중간) SAML 사용자 매핑이 NameID 의 로컬 파트로 로컬 계정(admin 포함)에 매핑되고 로컬 정책을 우회
- 위치: services/saml.py:137-143, 145-154
- 증상: username = name_id.split("@")[0] 이므로 IdP 가 admin@anything 을 주장하면 로컬 admin(uid 1)으로, bob@x 와 bob@y 는 같은 로컬 사용자 bob 으로 로그인된다. 이메일 일치나 도메인 제한이 없다. 매핑된 계정의 acc_enabled, wasreset, pwdexpire, TOTP 검사도 없다(F3-11). K04(서명 검증 없음)가 고쳐져도 IdP 네임스페이스 충돌만으로 권한 상승이 가능한 설계 결함이다.
- 재현: 코드 읽기. SAML 실행 경로가 K02/K03 으로 동작하지 않아 실행 불가.
- 확인 수준: 추론

### F3-17 (중간) PAM/pwauth/웹서버 인증이 로그인 흐름에 연결되어 있지 않고, PAM 은 python-pam 없이는 항상 실패
- 위치: views/auth.py:29-73 (login 뷰에 alternate auth 분기 없음), auth/pam.py:24-50, pyproject.toml (pam 의존성 없음), services/user_account.py:286 (login_webauth 호출처 없음). 레거시 index.php:66-101 의 ALTERNATE_AUTH_ENABLE/FALLBACK, login_alternate_auth, PHP_AUTH_USER
- 증상: PAMAuthBackend/PWAuthBackend 는 어디서도 호출되지 않는다(bridge_cli 제외). 대체 인증 설정 키(ALTERNATE_AUTH_*)도 없다. 또 pam 모듈이 없고 libpam 만 있을 때 ctypes 분기는 드라이버를 만들지 않는 스텁(주석만 있음)이라 libpam 이 존재해도 "PAM is not supported" 로 항상 실패한다. 레거시의 "로컬 계정이 존재하고 활성일 때만 외부 인증 성공" 규칙도 구현되지 않았다.
- 재현: PAMAuthBackend().login("jiho","x") -> False, "PAM is not supported or library is unavailable" (libpam 은 있는 호스트, driver=None) (t12.py). 로그인 뷰에 호출 없음은 코드 확인.
- 확인 수준: 재현(PAM 스텁), 추론(연결 부재는 코드 확인)

### F3-18 (중간) 계정 관련 이벤트가 SysLog 에 전혀 기록되지 않아 감사 추적이 없음
- 위치: services/user_account.py 전체(로그 호출 없음), views/auth.py, views/admin.py:91-148. 레거시 AFUserAccount.php 는 로그인 성공/실패(마스킹 비밀번호 포함), 계정 생성/삭제, 비밀번호 변경/재설정을 avantfaxlog() -> SysLog 에 기록
- 증상: 새 코드에서 SysLog 로 쓰는 곳이 없어(시드 2행뿐) 관리자 "시스템 로그" 화면에서 로그인 실패 추적, 계정 변경 이력 확인이 불가능하다. ADM-26/COR-33 은 화면 한계와 파일 로그를 다뤘고, 이 항목은 계정 수명주기 이벤트가 기록 자체가 안 된다는 점이다.
- 재현: 로그인 4회, 사용자 생성 다수, 실패 로그인 후에도 SELECT count(*) FROM SysLog = 2 (시드) (t21.py).
- 확인 수준: 재현

### F3-19 (중간) HylaFAX 사용자 동기화(faxadduser/faxdeluser)가 계정 생성/비밀번호 변경/비활성화/삭제 어디에도 없음
- 위치: services/user_account.py:74-136, 152-188, 367-388 (grep 으로 faxadduser, faxdeluser, hosts.hfaxd 참조 없음). 레거시 AFUserAccount.php:116-118, 243-245, 570-572, admin/users.php:145-148
- 증상: 웹에서 만든 사용자가 hfaxd 에 등록되지 않아 그 사용자 이름으로 하는 faxrm/faxalter(FAXUSER 환경변수)가 거부되고, 비활성화/삭제된 사용자의 hfaxd 계정은 옛 비밀번호로 남는다. 비밀번호 변경이 hfaxd 에 반영되지 않는다. 비활성화 시 레거시가 하던 wasreset=true 세팅(재활성화 후 강제 변경)도 없다.
- 재현: 코드 읽기와 grep. HylaFAX 미설치.
- 확인 수준: 추론

### F3-20 (중간) remember() 가 계정 플래그를 bool() 로 해석해 login() 의 엄격 판정과 어긋남 (COR-09 와 결합하면 비관리자가 관리자 세션)
- 위치: security.py:331-334 (bool(user.dbdata.get("is_admin")), superuser 도 동일) vs services/user_account.py:264 ("is_admin" in (1, True, "1"))
- 증상: login() 은 "False"/"0" 문자열을 관리자 아님으로 보지만 세션 생성은 bool("False") 가 True 이므로 관리자+superuser 세션이 만들어진다. COR-09(불리언을 'True'/'False' 문자열로 저장)로 오염된 행이 있으면 해당 계정이 관리자로 로그인한다.
- 재현: cd 계정의 is_admin, superuser 를 문자열 'False' 로 바꾼 뒤 로그인 -> GET /admin 200 (t17.py). 전제 조건(오염된 저장값)은 COR-09 경로에 의존.
- 확인 수준: 재현(조건부)

### F3-21 (낮음) 사용자명/이메일 대소문자 구분 때문에 대소문자만 다른 계정이 공존하고 로그인이 어긋남
- 위치: services/user_account.py:88-96, 237-241 (find 의 = 비교), db/schema.py:12 (username TEXT UNIQUE, 대소문자 구분 기본). 레거시 MySQL 은 대소문자 비구분
- 증상: "PLAIN" 으로 로그인 불가, 관리자가 "Plain" 을 별도 계정으로 생성 가능(이메일 대소문자도 같음). 레거시에서는 중복으로 거부되고 로그인도 된다. 같은 이름이 HylaFAX 계정으로는 충돌하거나 혼동을 일으킨다.
- 재현: t9.py (uppercase login -> 200 로그인 화면 유지, uid 4 plain 과 uid 8 Plain 공존).
- 확인 수준: 재현

### F3-22 (낮음) 로그인 실패 사유와 복귀 경로(next) 유실
- 위치: views/auth.py:45-53 (user.get_error() 를 버리고 고정 문구), 72-73 (next 무시), views/forbidden.py:330 (next 를 붙여 리다이렉트)
- 증상: 비활성 계정도 "Invalid username or password" 로 나와 사용자가 비활성 상태를 알 수 없다(레거시 LOGIN_DISABLED). 미로그인 상태에서 /archive 같은 딥링크로 들어와 /login?next=... 로 보내진 뒤 로그인하면 next 를 버리고 항상 /inbox 로 간다.
- 재현: acc_enabled=0 계정 로그인 응답에 "disabled" 문구 없음 (t9.py). /archive -> /login?next=http%3A%2F%2Flocalhost%2Farchive, POST /login?next=%2Farchive -> Location /inbox (t22.py).
- 확인 수준: 재현

### F3-23 (중간) createuser CLI 의 기본값이 위험: 지정만 해도 관리자/superuser 승격, 비활성 계정 재활성화, 첫 로그인 변경 우회, 기본 비밀번호 고정
- 위치: cli/user.py:20-25 (--admin 이 store_true + default=True 라 플래그가 무의미, 기본 비밀번호 admin1234!), 36-50, 63, 75-76
- 증상: `createuser -u bob` 처럼 옵션 없이 호출하면 신규/기존 bob 모두 is_admin=1, superuser=1 이 되고(--user-only 를 줘야 일반), 기존 계정이면 acc_enabled=1 로 되살리며, last_login=now 와 wasreset=0 을 써서 "첫 로그인 시 비밀번호 변경" 규칙을 건너뛴다. 비밀번호 옵션이 없으면 문서화된 공개 기본값 admin1234! 가 쓰인다(COR-17 은 기존 사용자의 비밀번호가 바뀌지 않는다는 점만 다룸).
- 재현: argparse 정의 읽기 기준. CLI 는 실행하지 않음.
- 확인 수준: 추론

### F3-24 (낮음) 헤더 받은편지함 배지 엔드포인트가 TypeError 로 항상 0 을 반환
- 위치: views/ajax.py:57-63 (arc.get_num_faxes(inbox=True), 실제 시그니처에 inbox 인자 없음, 예외를 삼키고 0)
- 증상: 권한 필터와 무관하게 모든 사용자의 미확인 팩스 배지가 0 이다. (UI-24 의 배지 불일치의 구체 원인.) 로그인 필요 여부도 없다(F3-04).
- 재현: get_num_faxes(inbox=True) -> TypeError, GET /ajax/inbox -> 0, 실제 inbox 는 2건 (t5.py, t6.py).
- 확인 수준: 재현

### F3-25 (낮음) 관리자 사용자 생성/수정의 검증 오류와 약한 비밀번호가 조용히 무시됨 (ADM-05 변형)
- 위치: views/admin.py:118-148 (create 반환값 미확인, set_username/set_email 실패 무시, 오류 메시지 렌더 없음)
- 증상: 잘못된 사용자명("bad name!"), 중복 사용자명, 중복 이메일로 생성해도 성공처럼 302 되고 오류가 표시되지 않는다. 길이 1 의 비밀번호도 생성된다(레거시의 MIN_PASSWD_SIZE 검사는 change_password 에만 있어 첫 로그인 강제 변경이 죽어 있는 F3-02 와 결합하면 그대로 남는다).
- 재현: t21.py. 생성 요청 후 사용자 수 불변, 화면에 오류 없음, password="a" 로 shortpw 계정 생성.
- 확인 수준: 재현

### F3-26 (낮음) 세션 쿠키에 Secure 속성이 없고 세션이 프로세스 메모리에만 존재
- 위치: security.py:346-349 (Set-Cookie: HttpOnly; SameSite=Lax 만), web/session.py:32-37 (인메모리 dict, 만료된 항목은 조회될 때만 삭제)
- 증상: HTTPS 종단 뒤에서도 쿠키가 평문 HTTP 로 전송 가능하고, 서버 재시작/다중 프로세스(serve 와 별도 scheduler, 여러 워커)에서 전원 로그아웃 또는 세션 불일치가 난다. 조회되지 않는 만료 세션이 계속 쌓인다.
- 재현: 로그인 응답의 Set-Cookie 확인 (t22.py). 나머지는 코드 읽기.
- 확인 수준: 재현(쿠키), 추론(메모리/다중 프로세스)

---

## 요약
- 새 결함 26건 (F3-01 ~ F3-26).
- 이음새 관점의 핵심: 권한 판정이 경로마다 제각각이다(inbox 는 superuser 또는 is_admin, archive 는 is_admin 만, 관리자 영역은 superuser 까지, 메뉴는 is_admin 만). can_del, any_modem, 모뎀/카테고리 제한은 저장만 되고 소비하는 곳이 없거나 일부 경로만 소비한다.
- 제외한 기존 항목: SEC-05, UI-01, USR-04, SEC-03, SEC-02, K02, K03, K04, K10, ADM-03, ADM-04, ADM-05, ADM-06, COR-09, COR-17, COR-18 은 원인 또는 증상으로만 참조했고 같은 결함으로는 재보고하지 않았다.
