# 2라운드: 레거시 AvantFAX 대비 기능 패리티 및 데이터 이전 점검

점검 대상: numfax (NamiFAX) 대 legacy/avantfax. 원본 소스는 수정하지 않았고, 모든 실험은 scratchpad/agent-r2-parity/ 아래에서만 수행했다.
동작 판정 기준: 구현(레거시와 같은 결과를 내는 실제 동작), 부분(코드는 있으나 일부 동작이 빠졌거나 깨짐), 스텁(가짜 값을 돌려주거나 아무 일도 하지 않으면서 성공처럼 보임), 누락(대응 코드 없음 또는 연결되지 않음).
"1라운드 기존 결함(K/SEC/USR/COR/ADM/UI)"이 원인인 깨짐은 해당 ID를 비고에 표시하고 '부분'으로 분류했다(새 결함으로 중복 기재하지 않음).
NamiFAX 경로 약어: S = src/namifax, V = S/views, SV = S/services.

## 1. 패리티 표

### 1-1. 사용자 화면 진입점 (legacy/avantfax 루트 PHP)

| # | 레거시 | NamiFAX 대응 | 동작 | 비고 |
|---|---|---|---|---|
| 1 | index.php (로그인) | V/auth.py login_post_view | 부분 | MD5 로그인은 실행 확인. 대체 인증(PAM/pwauth/webauth) 미연결(F4-04), 만료/초기화 강제 없음(SEC-05), admin/password 우회(K10) |
| 2 | check_login.php | S/security.py 권한 정책 | 부분 | 세션 팩토리 없음(K02), 모뎀 접근 제어 우회(SEC-03) |
| 3 | logout.php | V/auth.py logout_view | 구현 | |
| 4 | forgot.php | V/auth.py forgot_post_view | 스텁 | F4-02 |
| 5 | pwdexpired.php | V/auth.py pwdexpired_post_view | 스텁 | F4-03 |
| 6 | no-database.php | 없음 | 누락 | DB 연결 실패 안내 화면 없음(예외를 pass 로 삼킴) |
| 7 | inbox.php | V/inbox.py inbox_view | 부분 | 페이지네이션/faxperpageinbox 없음(F4-09), RESTRICTED_USER_MODE, INBOX_LIST_MODEM 없음, UI-23 |
| 8 | viewfax.php | V/inbox.py viewfax_view | 스텁 | UI-07(가짜 문서)과 동일 |
| 9 | pdf.php | fax_download_view (/faxes/download/{fid}) | 스텁 | 파일이 없으면 합성 PDF 반환(F4-12), 레거시 경로 해석 불가(F4-10) |
| 10 | file.php | 위와 동일 | 부분 | 모든 경로가 fax_download 하나에 합쳐짐. 미리보기 gif/png 이미지 서빙 경로 없음(F4-11) |
| 11 | rotate.php | V/inbox.py fax_rotate_view | 부분 | USR-05 |
| 12 | setcompany.php | V/inbox.py setcompany_view | 부분 | 권한 검사 없음(SEC-03) |
| 13 | assign.php | V/modals.py modal_assign_view | 부분 | UI-20 |
| 14 | assignx.php | 없음 | 누락 | 회사 일괄 재배정(정규식 기반) 확인 단계 화면 없음. modal_assign 의 regexp 분기는 set_company 만 호출 |
| 15 | email.php | V/modals.py modal_email_view | 부분 | 메일이 발송되지 않음(COR-04), 주소록 저장만 동작 |
| 16 | refax.php | V/modals.py modal_refax_view | 스텁 | F4-01 |
| 17 | txreport.php | V/modals.py modal_txreport_view | 스텁 | UI-20 |
| 18 | search.php | 없음 | 누락 | 레거시 통합 검색 폼 화면 대응 없음(/archive 로 대체) |
| 19 | outbox.php | V/outbox.py outbox_view | 부분 | kill_job 미존재인데 성공 메시지(F4-14), 소유자 필터 없음(USR-07) |
| 20 | archive.php | V/archive.py archive_view | 부분 | companyid, userid, 페이지네이션 필터 없음(F4-09), 가짜 결과(USR-02) |
| 21 | sendfax.php | V/sendfax.py sendfax_view | 부분 | 옵션 대부분 누락(F4-06), 실패 은폐와 가짜 잡 ID(F4-07) |
| 22 | settings.php | V/settings.py settings_view | 스텁 | UI-01. 추가로 F4-13 |
| 23 | addressbook.php | V/addressbook.py | 부분 | 이전 데이터의 팩스번호와 이메일이 안 보임(F4-15) |
| 24 | addressbook_edit.php | V/addressbook.py | 부분 | COR-07, USR-03 |
| 25 | rubrica.php, rubrica_edit.php (구 주소록 별칭) | 없음 | 누락 | 레거시에서도 addressbook 으로 넘기는 호환 페이지. 영향 낮음 |
| 26 | emailbook.php, emailbook_edit.php | V/addressbook.py (emailbook 라우트) | 부분 | USR-03 |
| 27 | emailcontacts.php | popup_email_contacts 라우트 | 부분 | |
| 28 | faxcontacts.php | popup_fax_contacts 라우트 | 부분 | |
| 29 | distrolist.php, distrolist_edit.php | V/distrolist.py | 부분 | UI-36 |
| 30 | distrolist_helper.php | popup_distrolist_helper | 부분 | |
| 31 | distrocontacts.php | popup_distro_contacts | 부분 | |
| 32 | upload_contacts.php | upload_contacts 라우트 (S/common/upload.py) | 부분 | 실행 미확인, 코드상 vCard 파싱 구현 |
| 33 | upload_faxcontacts.php | upload_faxcontacts 라우트 | 부분 | 위와 동일 |
| 34 | faxes/ (recvd, sent 디렉터리) | 없음 (ARCHIVE 기본값이 /var/spool/hylafax/archive) | 부분 | 경로 체계 불일치(F4-10) |

### 1-2. ajax/ (13개)

| # | 레거시 | NamiFAX | 동작 | 비고 |
|---|---|---|---|---|
| 35 | ajaxarchivefax.php | V/ajax.py ajax_archive_fax | 부분 | 권한 없음(SEC-02), 템플릿 링크 404(K11) |
| 36 | archivefax.php | 위와 동일 (중복 엔드포인트 하나로 합침) | 부분 | |
| 37 | ajaxbook.php | ajax_addressbook_suggest | 스텁 | 결과 없으면 가짜 "Acme Corp" 반환(F4-16) |
| 38 | ajaxdeletefaxes.php | ajax_deletefaxes_view | 부분 | SEC-04 |
| 39 | ajaxdlist.php | ajax_distrolist_faxes | 스텁 | 없는 목록이면 "1234567; 9876543" 반환(F4-16) |
| 40 | ajaxemailbook.php | ajax_emailbook_suggest | 스텁 | 결과 없으면 user@example.com(F4-16) |
| 41 | ajaxinbox.php | ajax_inbox_count | 부분 | 사용자 범위 없는 전체 집계 |
| 42 | ajaxmodemstatus.php | ajax_modem_status | 부분 | modems 파라미터 무시, 가짜 ttyS0 행(F4-16) |
| 43 | ajaxprefillto.php | ajax_addressbook_prefill | 스텁 | 빈 필드를 "123 Street / 12345 / City / HQ / 555-1234" 로 채움(F4-16) |
| 44 | archivebook.php | ajax_archivebook_view | 스텁 | 결과 없으면 가짜 "Acme Corp"(F4-16) |
| 45 | delete.php | V/modals.py modal_delete_view | 부분 | SEC-03 |
| 46 | faxalter.php | ajax_faxalter | 부분 | 폼의 jid 가 1 로 고정(F4-14 참고), USR-06 |
| 47 | set_note.php | V/modals.py modal_note_view | 부분 | USR-08 |

### 1-3. 관리자 (legacy/avantfax/admin)

| # | 레거시 | NamiFAX | 동작 | 비고 |
|---|---|---|---|---|
| 48 | admin.php, index.php (대시보드, 로그인) | V/admin.py admin_dashboard | 부분 | UI-31(가짜 수치) |
| 49 | users.php, users_list.php (신규, 목록, 수정) | admin_users | 부분 | ADM-04, ADM-05 |
| 50 | deluser.php | admin_users 삭제 분기 | 부분 | ADM-03 (항상 조용히 실패) |
| 51 | conf_modems(_edit).php | admin_modems | 부분 | ADM-23 |
| 52 | conf_didroute(_edit).php | admin_routing_did | 부분 | ADM-22 |
| 53 | conf_barcoderoute(_edit).php | admin_barcodes | 부분 | ADM-07 |
| 54 | conf_covers(_edit).php | admin_covers | 부분 | ADM-30 |
| 55 | conf_dynconf(_edit).php | admin_dynconf | 스텁 | ADM-08 |
| 56 | fax2email(_edit).php | admin_fax2email | 부분 | ADM-09 |
| 57 | fax_categories.php, fax_cat_edit.php | admin_categories | 부분 | ADM-22 |
| 58 | system_func.php | admin_sysfunc | 스텁 | ADM-10, UI-03 |
| 59 | system_logs.php | admin_system_logs | 부분 | ADM-02, ADM-26 |
| 60 | admin/pwdexpired.php, check_login.php, logout.php | 공용 로그인 흐름 | 부분 | 관리자 전용 만료 화면 스텁(F4-03) |
| 61 | admin/no-database.php | 없음 | 누락 | |
| 62 | NamiFAX 신규(프린터, SMTP, 스토리지, SAML) | admin_printers/smtp/storage/saml | (범위 밖) | 레거시에 없는 기능이라 집계에서 제외. 저장 불가(K01) |

### 1-4. includes/ 및 CLI, cron, tools

| # | 레거시 | NamiFAX | 동작 | 비고 |
|---|---|---|---|---|
| 63 | includes/avantfaxcron.php (-i -d -t) | S/cli/cron.py | 부분 | COR-14(prune 불능). 임시파일 정리 경로가 sendfax 업로드 경로와 다름(F4-08) |
| 64 | includes/dynconf.php | S/cli/dynconf.py | 부분 | COR-08 |
| 65 | includes/faxrcvd.php | S/cli/faxrcvd.py | 부분 | 바코드 스텁(F4-17), 주석 누락(F4-18), COR-05/06/20 |
| 66 | includes/notify.php | S/cli/notify.py | 부분 | COR-03 |
| 67 | includes/faxcover.php, tools/faxcover.php | S/cli/faxcover.py | 부분 | COR-16 |
| 68 | includes/phb.php | S/cli/phb.py | 부분 | |
| 69 | tools/create_thumbnails.php | avantfax/cli/create_thumbnails.py (namifax 서브커맨드 경유) | 부분 | avantfax 트리 의존(COR-25), 경로 해석(F4-10) |
| 70 | tools/import_archive.php | avantfax/cli/import_archive.py | 스텁 | F4-19 |
| 71 | tools/import_blacklist.php | avantfax/cli/import_blacklist.py | 부분 | |
| 72 | tools/import_users.php | avantfax/cli/import_users.py | 부분 | |
| 73 | tools/ocr_import.php | avantfax/cli/ocr_import.py | 스텁 | ADM-15/COR-27 (ENABLE_OCR_SUPPORT 류 설정 자체가 없음) |
| 74 | tools/reroute.php | avantfax/cli/reroute.py | 부분 | |
| 75 | tools/update_contacts.php | 없음 | 누락 | F4-20 |
| 76 | includes/PAMAuth.php, PWAuth.php (ALTERNATE_AUTH_*) | S/auth/pam.py, password.py | 누락 | 모듈은 있으나 로그인에서 호출되지 않음(F4-04) |
| 77 | includes/Mailer.php, htmlMimeMail5.php | SV/mailer.py | 스텁 | COR-04, ADM-17 |
| 78 | includes/AFAddressBook.php 외 클래스 13종 | SV/*.py | 부분 | COR-05~07 등 |
| 79 | includes/functions.php 주요 함수 (annotate_fax, bardecode, ocr_faxcontent, submit_fax 등) | S/common/helpers.py | 부분 | bardecode, ocr_faxcontent 는 항상 None 을 반환하는 스텁. annotate_fax, submit_fax, exec_sendfax, get_inbox_count 는 대응 없음 |
| 80 | includes/templates/plugins (PLUGINS_DIR), custom.css 테마 | 없음 | 누락 | F4-21 |
| 81 | 설치/업그레이드 스크립트 (rh/debian/sles-install.sh, upgrade*.sh, setup-postfix/sendmail.sh, fixlink-faxcover.sh, create_user.sql) | systemd 유닛 2개만 | 누락 | F4-13(이전 도구 부재), F4-21 |

### 1-5. 이메일, 알림, 언어

| # | 레거시 | NamiFAX | 동작 | 비고 |
|---|---|---|---|---|
| 82 | email2fax (email2fax.txt, setup-postfix.sh, setup-sendmail.sh, FAXMAILUSER 수신 메일을 팩스로 발송) | 없음 (FAXMAILUSER 는 notify 소유자 매핑에만 사용) | 누락 | F4-05 |
| 83 | 수신 팩스 이메일 전달 (Fax2Email 라우팅, PDF/썸네일 첨부) | cli/faxrcvd.py | 부분 | 메일 미발송(COR-04), 라우팅 테이블 불능(COR-06/ADM-09) |
| 84 | 발송 결과 통지 메일 (notify) | cli/notify.py | 부분 | COR-03, COR-04 |
| 85 | 팩스를 이메일로 전달하는 모달 | modal_email | 부분 | COR-04 |
| 86 | 수신 팩스 인쇄(PRINTFAXRCVD) | faxrcvd.py 는 프린터 이름만 계산 | 스텁 | ADM-16 과 동일 |
| 87 | 언어 지원 23종 | S/locale 24종 (ko 추가) + i18n.py 별칭 정규화 | 부분 | 사용자별 language 미적용(F4-22), 번역 품질은 UI-05, UI-10~13 |
| 88 | 로그인 계정 보안 기능(TOTP, WebAuthn, SAML) | (레거시에 없는 신규) | (범위 밖) | 집계 제외. K02~K09 |

### 1-6. 설정 옵션 (config.php, local_config-example.php)

레거시 옵션 약 80개 중, NamiFAX 가 환경변수 또는 코드에서 실제로 읽고 쓰는 것은 아래 그룹뿐이다.

| # | 그룹 | 동작 | 비고 |
|---|---|---|---|
| 89 | ADMIN_EMAIL, FROM_COMPANY/LOCATION/FAXNUMBER/VOICENUMBER, FAXMAILUSER, WWWUSER, NOTIFY_INCLUDE_PDF, NOTIFY_ON_SUCCESS, FAXRCVD_INCLUDE_THUMBNAIL, ENABLE_DID_ROUTING, COVERPAGE_FILE/MATCH, CPAGE_LINELEN, PRINTERNAME | 구현 | 기본값 중 일부가 바뀜(F4-23) |
| 90 | ARCHIVEFAX2EMAIL, FAXRCVD_INCLUDE_PDF, AUTOCONFDID, FAXCOVER_DATE_FORMAT | 부분 | 기본값이 레거시와 다름(F4-23) |
| 91 | ENABLE_FAX_ANNOTATION, ANN_GRAVITY, PRINTFAXRCVD, PRINTCMD, PRINTFAX2PS, PRINTFAXCMD, PDFPRINTCMD, FAXRCVD_PRINT_PDF | 스텁 | 읽기만 하고 사용하지 않음 또는 상수 자체가 없음 |
| 92 | AFDB_USER/PASS/NAME/ENGINE/HOST | 누락 | NAMIFAX_DB_PATH(SQLite)로 대체. MySQL 접속 설정 경로 없음(COR-12) |
| 93 | RESTRICTED_USER_MODE, INBOX_LIST_MODEM, FOCUS_ON_NEW_FAX(_POPUP), SHOW_ALL_CONTACTS, NUM_PAGES_FOLLOW, ARCHIVE_WIDE, ENABLE_DL_TIFF, DEFAULT_FAXES_PER_PAGE_INBOX/ARCHIVE | 누락 | UI 동작 옵션 전체 |
| 94 | SENDFAX_USE_COVERPAGE, SENDFAX_REQUEUE_EMAIL, PAPERSIZE, DEFAULT_TSI_ID, BINARYDIR, HYLAFAX_PREFIX, HYLASPOOL, HYLATIFF2PS, HTML2PS, USE_HTML_COVERPAGE | 누락 | |
| 95 | ENABLE_BARDECODE_SUPPORT, BARDECODE_BINARY/COMMAND, ENABLE_OCR_SUPPORT, OCR_BINARY/COMMAND/LANGUAGE | 누락 | 바코드, OCR 활성화 스위치 자체가 없음(F4-17) |
| 96 | USE_SMTPSERVER, SMTP_SERVER/PORT/AUTH/USERNAME/PASSWORD/LOCALHOST, EMAIL_ENCODING_TEXT/HTML/CHARSET, EMAIL_DATE_FORMAT, SYSTEM_EMAIL_SIG_HTML/TEXT | 스텁 | DB 기반 SMTP 화면은 있으나 발송에 쓰이지 않음(ADM-17) |
| 97 | ALTERNATE_AUTH_ENABLE/FALLBACK/CLASS, CALLIDn_CIDNumber/CIDName/DIDNum | 누락 | |
| 98 | MIN/MAX_PASSWD_SIZE, MAX_USERNAME_SIZE, MAX_EMAIL_SIZE, CONTACTFILETYPES, SENDFAXFILETYPES, WHITEPAGES, NOTHUMB, HAS_NEGATIVE_TIFF, AVANTFAX_DEBUG, SHOWSERVER_DETAILS, AVANTFAX_SERVERNAME | 부분 | 비밀번호 길이만 사용. 나머지 누락 |
| 99 | ARCHIVE_DATE_FORMAT | 부분 | 기본 포맷 다름, COR-14 |
| 100 | local_config.php 읽기 (설정 파일 이전 경로) | 누락 | 기존 설치의 local_config.php 를 읽거나 변환하는 기능 없음(F4-23) |

### 1-7. 집계 (번호 행 100개 중 범위 밖 2행 제외, 스크립트로 계수)

| 구분 | 개수 |
|---|---|
| 구현 | 2 (로그아웃, 설정 그룹 89) |
| 부분 | 60 |
| 스텁 | 20 |
| 누락 | 16 |
| 합계 | 98 |

참고: 구현으로 센 것은 2건뿐이며, '부분' 다수는 1라운드 결함(K/COR/ADM/UI 등)이 원인이다. 스텁과 가짜 데이터 반환은 구현으로 세지 않았다.

---

## 2. 결함 목록 (F4-xx)

(ID 는 F4-01부터. 확인 수준: 재현 = 실제 실행으로 확인, 추론 = 코드 읽기 근거)

## F4-01 (높음) 팩스 재전송/답장(refax)이 스텁: 항상 잡 ID 1001 을 반환하고 아무것도 전송하지 않음
- 위치: V/modals.py modal_refax_view (`from avantfax.services.faxqueue import FaxQueue`), src/avantfax/services/faxqueue.py:195-205 create_job
- 증상: create_job 본문이 `dest_list` 를 만들고 `return 1001` 만 한다. sendfax 를 호출하지 않고, 원본 팩스 파일(fid)도 첨부하지 않는다. 레거시 refax.php 는 원본 문서를 다시 큐에 넣는다. 성공 시 "Fax queued for sending (Job ID: 1001)" 가 화면 문구로 만들어지므로(UI-18 때문에 출력되지 않아도) 사용자는 재전송이 됐다고 믿는다. namifax.services.faxqueue 에는 create_job 자체가 없다(이중 트리 문제로 avantfax 쪽 스텁이 쓰임).
- 재현: 마이그레이션 DB 로 로그인 후 `POST /refax fid=1&destinations=0212345678` 이 200, 큐 변화 없음. `hasattr(namifax.services.faxqueue.FaxQueue,'create_job')` 는 False, avantfax 쪽은 True 이며 본문이 `return 1001`.
- 확인 수준: 재현

## F4-02 (높음) "비밀번호 찾기"(forgot.php)가 스텁: 성공 문구만 출력하고 재설정/메일 발송 없음
- 위치: V/auth.py forgot_post_view
- 증상: 입력만 검사하고 `"If an account matches '...' password reset instructions have been dispatched."` 를 돌려준다. 레거시 forgot.php 는 이메일로 계정을 찾아 임시 비밀번호를 생성(wasreset=1)하고 메일로 보낸다. 계정 조회, 비밀번호 갱신, 메일 발송이 전혀 없다. 잠긴 사용자가 복구할 방법이 없다.
- 재현: `POST /forgot username=nobody` 응답에 "dispatched" 문구. DB 변경 없음(코드에 DB 접근 없음).
- 확인 수준: 재현

## F4-03 (높음) 비밀번호 만료/초기화 강제 변경 화면(pwdexpired)이 스텁: 비밀번호를 바꾸지 않고 로그인 화면으로 리다이렉트
- 위치: V/auth.py pwdexpired_post_view (관리자용 admin/pwdexpired.php 대응도 동일 화면)
- 증상: 세 필드가 채워지고 새 비밀번호가 같으면 곧바로 `/login` 으로 302 한다. 기존 비밀번호 검증, UserAccount.password 갱신, UserPasswords 이력, pwdexpire/wasreset 해제가 없다. SEC-05(로그인 시 강제하지 않음)와 별개로, 강제되더라도 변경 경로가 동작하지 않는다. 레거시에서 wasreset=1 또는 최초 로그인 사용자는 이 화면을 통해서만 정상 사용이 가능하다.
- 재현: bob 로 로그인, `POST /pwdexpired oldpwd=a&newpwd=b&conpwd=b` 가 302 → /login. 이후 DB 의 bob 비밀번호 해시가 그대로(f64ec58f...).
- 확인 수준: 재현

## F4-04 (높음) 대체 인증(ALTERNATE_AUTH: PAM/pwauth)과 웹서버 인증(REMOTE_USER)이 로그인에 연결되지 않음
- 위치: V/auth.py login_post_view, S/auth/pam.py, S/auth/password.py(PWAuthBackend), SV/user_account.py(login_webauth)
- 증상: 레거시 index.php 는 ALTERNATE_AUTH_ENABLE/FALLBACK/CLASS 설정에 따라 PAMAuth/PWAuth 로 인증한다(LDAP/시스템 계정 연동 설치본이 많다). NamiFAX 의 로그인은 MD5 조회만 하고, PAM/pwauth/login_webauth 는 어디에서도 호출되지 않는다(`grep PAMAuth|PWAuth|login_webauth` 결과가 auth 모듈 자신과 정의뿐). 설정 키도 없다. PAM 으로만 인증하던 사용자는 (UserAccount.password 가 더미이므로) NamiFAX 로 옮긴 뒤 로그인할 수 없다.
- 재현: grep 근거. 로그인 뷰 코드 전체 확인.
- 확인 수준: 추론(코드상 호출 경로 없음)

## F4-05 (높음) 이메일 → 팩스(email2fax) 기능 전체 누락
- 위치: legacy/email2fax.txt, setup-postfix.sh, setup-sendmail.sh, FAXMAILUSER/WWWUSER 연동. NamiFAX 에는 대응 코드 없음.
- 증상: 레거시는 Postfix/Sendmail 을 통해 수신 이메일(faxmail 사용자)을 HylaFAX faxmail 로 넘겨 팩스를 발송하고, notify 가 그 잡의 소유자를 faxmail/www 로 식별해 통지한다. NamiFAX 에는 메일 수신 설정, 스크립트, 문서, 진입점이 없고 FAXMAILUSER 는 notify/faxqueue 의 소유자 비교에서만 쓰인다. 이메일로 팩스를 보내던 운영 설치본의 핵심 사용 시나리오가 사라진다.
- 재현: `grep -ril "email2fax|setup-postfix"` 에 src/, docs/, systemd/ 결과 없음.
- 확인 수준: 재현(부재 확인)

## F4-06 (높음) sendfax 화면이 레거시 옵션 대부분을 폼에서도 서버에서도 처리하지 않음
- 위치: V/sendfax.py sendfax_view / dispatch_sendfax, S/templates/sendfax.jinja2
- 증상: 레거시 폼 필드 26개 중 NamiFAX 는 12개(comments, coverpage, faxnumber, file, modem, notify_requeue, numtries, priority, regarding, to_company, to_person, whichcover)만 갖고, 서버는 그중에서도 coverpage/whichcover/to_person/to_company/regarding/comments/modem 만 sendfax 인자로 전달한다. 누락: 세미콜론 다중 수신번호(-z 파일), killtime(+단위), sendtime(시/분), numtries, priority, notify_requeue, user_tsi(-i TSI), to_address/to_zip/to_city/to_location/to_voicenumber(표지 및 comments 임베드), 여러 파일 업로드(multifile_upload), 업로드 MIME 제한(pdf/ps/tiff/text), MAX_FILE_SIZE, 발신자 정보(from_person/company/location/voice/fax) 전달. 폼에 있는 priority, numtries, notify_requeue 도 서버가 읽지 않는다. 또한 업로드는 `request.POST.get("file")` 하나만 처리한다. 모뎀 목록은 사용자 권한과 무관하게 전체 모뎀(`get_all_admin_modems`)이며 any_modem 여부, 사용자 첫 모뎀 기본값도 없다.
- 재현: S/templates/sendfax.jinja2 의 name 목록(12개)과 legacy sendfax.tpl 의 name 목록(26개) 비교, dispatch_sendfax 인자 확인.
- 확인 수준: 재현(코드/템플릿 대조)

## F4-07 (높음) 팩스 발송 실패가 은폐되고, sendfax 가 없으면 가짜 잡 ID 로 성공 처리. 소유자(-o), 발신 이메일(-f) 미전달
- 위치: V/sendfax.py dispatch_sendfax, sendfax_view
- 증상: (1) `shutil.which("sendfax")` 가 None 이면 난수 6자리 `jobid` 를 만들어 `success: True` 를 돌려준다. (2) 뷰는 dispatch 결과를 버리고 항상 `/outbox` 로 리다이렉트하므로 returncode != 0 이나 예외도 사용자에게 보이지 않는다. 레거시는 results 배열 여부로 "FAX_SUBMITTED"/"FAX_FAILED + sendfax 출력"을 표시한다. (3) 레거시가 붙이는 `-o <username>`(잡 소유자), `-f <email>` 이 없어 잡이 웹 서버 사용자 소유로 들어가고, notify.php/faxqueue 의 소유자 매핑(사용자별 outbox 필터, 통지 메일 수신자, 발송 보관 userid)이 깨진다. (4) 업로드 파일을 tempfile.gettempdir()+uuid 로 저장하고 발송 후에도 삭제하지 않는다. (5) `to_person` 을 `"{to_person}"@번호` 로 만들 때 이스케이프가 없다.
- 재현: 코드 경로 확인. sendfax 미설치 환경에서 호출하면 성공 dict 반환(코드 65-73행).
- 확인 수준: 재현(코드), 소유자 영향은 추론

## F4-08 (낮음) 임시 업로드 정리가 cron 과 어긋남
- 위치: V/sendfax.py(`tempfile.gettempdir()`), S/cli/cron.py(`AVANTFAX_TMPDIR` 기본 /tmp/avantfax/)
- 증상: sendfax 는 시스템 임시 디렉터리에 `sendfax_<8hex>_<원본명>` 으로 저장하고, cron -t 는 /tmp/avantfax/ 만 청소한다. 업로드 원본이 영구 잔존한다(전송된 팩스 문서가 /tmp 에 계속 남음).
- 재현: 경로 대조
- 확인 수준: 추론

## F4-09 (중간) 수신함/아카이브에 페이지네이션, 사용자별 페이지 크기, 회사/사용자 필터가 없음
- 위치: V/inbox.py inbox_view, V/archive.py archive_view, S/templates/archive.jinja2
- 증상: 레거시는 pageindex/pagelimit 과 사용자 설정 faxperpageinbox/faxperpagearchive(기본 25/30), 아카이브의 companyid, userid, 기간(일/월/연) 필터를 제공한다. NamiFAX 수신함은 전체를 한 번에 렌더하고 faxperpage* 는 코드 어디에서도 읽지 않는다. 아카이브 뷰는 pageindex/pagelimit 를 전달하지 않고(서비스 기본 25로 잘리고 이동 UI 없음), companyid/userid 입력도 없다. 운영 이관 후 수만 건 아카이브에서 25건 이후 열람이 불가능하다.
- 재현: `grep -rn "faxperpage\|pageindex" src/namifax/views src/namifax/templates` 결과 없음(web/views/archive.py 는 미등록 트리). archive 템플릿 input name 은 category/date_from/date_to/faxid/search/sentrecvd 6개.
- 확인 수준: 재현(코드 대조)

## F4-10 (높음, 데이터 이전) 기존 아카이브 파일 경로를 해석하지 못함: DB 의 faxpath 는 INSTALLDIR 기준 상대경로, NamiFAX 웹은 installdir="" 로 루트 기준 조회
- 위치: SV/archive_base.py (`installdir: str = ""`, pdfpath/thumbnail 조립), V/inbox.py(`ArchiveIn()` 무인자), S/cli/faxrcvd.py(`AVANTFAX_ARCHIVE` 기본 /var/spool/hylafax/archive), 레거시 config.php:347-349
- 증상: 레거시는 `$ARCHIVE = $INSTALLDIR/faxes/recvd`, `$ARCHIVE_SENT = $INSTALLDIR/faxes/sent` 이고 FaxArchive.faxpath 에 INSTALLDIR 를 뺀 `/faxes/recvd/2019/05/05/<번호>/<id>` 형태를 저장한다(FaxPDFArchive.php:842). NamiFAX 는 모든 웹 경로에서 installdir 없이 ArchiveIn()/FaxPDFArchive() 를 만들어 `os.path.exists("/faxes/recvd/...")`(파일시스템 루트)를 검사하고, AVANTFAX_INSTALLDIR 환경변수는 faxcover.py 에서만 읽힌다. 새 수신분은 절대경로(/var/spool/hylafax/archive/...)로 저장되어 동작하지만 기존 faxpath 는 전부 깨진다. 결과적으로 이전한 모든 팩스가 미리보기/다운로드/삭제/회전 대상이 되지 못한다(다운로드는 F4-12 의 가짜 PDF 가 나옴). 아카이브 디렉터리 이동 가이드도 없다.
- 재현: 레거시 스키마 기반 DB(faxpath '/faxes/recvd/..' 형태 가정)를 NamiFAX 에 붙여 `/faxes/download/2` 요청 시 "synthetic PDF" 가 반환(실제 파일 유무와 무관, 경로 조립이 installdir "" 이므로 루트 기준). installdir 사용처 grep: 웹 경로에서 한 곳도 넘기지 않음.
- 확인 수준: 재현(다운로드 가짜 응답) + 추론(경로 해석)

## F4-11 (중간, 데이터 이전) 미리보기/썸네일 파일명 규칙이 달라 기존 이미지가 전부 무효
- 위치: SV/archive_base.py:11-15, 레거시 config.php:411-416
- 증상: 레거시 THUMBNAIL=thumb.gif, PREVIMG=prev, PREVIMGSFX=.gif (prev0.gif…) 이고 NamiFAX 는 thumb.png, page, .png 이다. 이전된 아카이브의 기존 썸네일/미리보기는 새 이름으로 조회되어 없는 파일이 되고, 재생성은 F4-10 경로 문제로 잘못된 디렉터리에서 일어난다. 삭제 시에도 기존 prev*.gif 는 지워지지 않고 남는다.
- 재현: 상수 대조
- 확인 수준: 추론

## F4-12 (높음) 팩스 다운로드가 파일이 없거나 fid 가 없어도 "합성 PDF" 를 200 으로 반환
- 위치: V/inbox.py fax_download_view (:118-124)
- 증상: 파일을 못 찾으면 `%PDF-1.4 % NamiFAX synthetic PDF binary stream for fax #N` 를 그대로 `application/pdf` 로 내려준다. 존재하지 않는 fid, 경로 불일치(F4-10), 삭제된 파일 모두 "정상적으로 열리는 빈 문서"가 되어 사용자는 데이터 유실을 알아챌 수 없다(404 여야 함). `?format=tiff` 도 content-type 만 tiff 이고 본문은 동일한 가짜 PDF.
- 재현: 마이그레이션 DB(파일 없음)로 로그인 후 `GET /faxes/download/1`, `/faxes/download/999` 모두 200 + "NamiFAX synthetic PDF binary stream for fax #..".
- 확인 수준: 재현 (UI-07 은 /viewfax 화면이며 이것은 다운로드 엔드포인트, 변형)

## F4-13 (중간) 설정 화면이 본인 데이터를 읽지 않고 가짜 프로필을 표시하며, 레거시 항목(커버 페이지, 아카이브당 건수, 비밀번호 변경 필드)이 없음
- 위치: V/settings.py, S/templates/settings.jinja2
- 증상: 프로필 기본값이 "Enterprise Inc.", "+1-555-0100", "ENTERPRISE-HQ", admin@avantfax.local 하드코딩(저장 불가는 UI-01 로 기보고). 추가로 레거시 폼의 coverpage_id, faxperpagearchive 가 없고, faxperpageinbox 선택지는 10/20/50 3개(레거시 10~100 7개), 기존 비밀번호(opass/npass/vpass)는 이름이 달라졌으며 서버가 old_password 를 검증하거나 변경하지 않는다. cover 선택지는 standard/urgent/confidential 고정.
- 재현: bob(language=ko, 이메일 bob@x.com)으로 로그인 후 `GET /settings`: "Enterprise Inc." 표시, bob@x.com 미표시.
- 확인 수준: 재현

## F4-14 (높음) 아웃박스 작업 삭제가 실제로 호출할 수 없는 메서드를 쓰면서 항상 "삭제되었다" 는 메시지를 표시
- 위치: V/outbox.py (`fq.kill_job(kill_jid)` + except 에서도 동일한 성공 메시지), SV/faxqueue.py(`killjob` 만 존재, kill_job 없음), V/ajax.py faxalter 폼(jid 기본 hidden 값 1)
- 증상: namifax.services.faxqueue.FaxQueue 에는 kill_job 이 없어 AttributeError 가 나고 except 블록이 같은 성공 문구를 만든다. 즉 어떤 잡도 실제로 취소되지 않는데 "Job #N successfully killed and removed from queue." 가 표시된다. 또 `/ajax/faxalter` GET 폼의 jid 가 `value="1"` 로 고정이라 요청한 잡이 아니라 잡 1 이 수정 대상이 된다. (USR-07 은 소유자 검증 부재만 다루며 메서드 부재/거짓 성공은 다루지 않음. 같은 줄을 호출하는 변형)
- 재현: `GET /outbox?kill=77` 응답 본문에 "successfully killed" 가 포함됨(실제 큐에 77번 없음). `hasattr(FaxQueue,'kill_job')` False.
- 확인 수준: 재현

## F4-15 (높음, 데이터 이전) 레거시 주소록의 팩스번호/이메일이 화면에 나타나지 않고 편집 폼도 비어 있음
- 위치: SV/addressbook.py, V/addressbook.py, S/templates/addressbook*.jinja2, S/db/schema.py (AddressBook/AddressBookFAX/AddressBookEmail 정의)
- 증상: 레거시는 AddressBook(abook_id, company) + AddressBookFAX(faxnumber, to_person, …) + AddressBookEmail(contact_name, contact_email) 로 회사당 번호/이메일 N개를 정규화해 저장한다. NamiFAX 화면과 서비스는 AddressBook.faxnum/email/address… 컬럼(신규 DB 기준 단일 행)을 기대하므로, 레거시 스키마에서는 목록의 팩스 번호/이메일 칸이 "—" 로 나오고 회사 편집 폼에 번호와 이메일이 채워지지 않는다. 그 상태로 저장하면 번호가 지워질 수 있다. (COR-06/07 은 CLI/스키마 컬럼 불일치이며, 이 항목은 웹 화면에서의 이전 데이터 가시성)
- 재현: create_tables.sql 을 SQLite 로 옮겨(scratchpad/agent-r2-parity/mig/conv.py) 회사 'Real Corp', 번호 0212345678, 이메일 kim@real.com 을 넣고 NamiFAX 기동 후 bob 로 `GET /addressbook` → 행에 "Real Corp — —". `GET /addressbook/edit?id=2` 본문에 0212345678, kim@real.com 없음.
- 확인 수준: 재현

## F4-16 (높음) AJAX 자동완성/프리필 엔드포인트가 결과가 없을 때 가짜 데이터를 반환하고, 실제 연락처의 빈 칸도 가짜 값으로 채움
- 위치: V/ajax.py ajax_addressbook_suggest, ajax_emailbook_suggest, ajax_archivebook_view, ajax_distrolist_faxes, ajax_addressbook_prefill, ajax_modem_status
- 증상: 검색 결과 0건이면 "Acme Corp - 1234567"(cid 1), user@example.com, "1234567; 9876543"(배포목록) 을 돌려주고, prefillto 는 주소록에 없거나 칸이 비어 있으면 "John Doe / 123 Street / 12345 / City / HQ / 555-1234" 를 채운다. 사용자가 잘못된 번호와 주소로 팩스를 보내거나 표지 페이지를 만들 수 있다. modemstatus 는 요청의 modems 파라미터를 무시하고 전체 모뎀을 내보내며 목록이 비면 가짜 ttyS0 행을 반환하고, 상태 없을 때 class 가 CSS 클래스가 아닌 "2.0" 이 된다(레거시 class 는 modem-ok 등 CSS 클래스). (USR-02 는 검색 화면 placeholder 이며 AJAX 는 별도)
- 재현: 마이그레이션 DB 로그인 상태에서 `GET /ajax/book?q=zzzz` → Acme Corp - 1234567, `/ajax/dlist?dl_id=999` → "1234567; 9876543", `/ajax/prefillto?fnid=2`(Real Corp, 이름 Kim) → 주소 "123 Street", zip 12345, city "City", 전화 555-1234, `/ajax/emailbook?q=qq` → user@example.com
- 확인 수준: 재현

## F4-17 (높음) 바코드 라우팅이 영구 비활성: bardecode 헬퍼가 항상 None 을 반환
- 위치: S/common/helpers.py:455-457 (`return None`), S/cli/faxrcvd.py:211-224
- 증상: 수신 팩스의 바코드 판독 결과가 항상 None 이라 BarcodeRoute(관리자 화면에서 설정 가능)가 동작할 수 없다. ENABLE_BARDECODE_SUPPORT/BARDECODE_BINARY/BARDECODE_COMMAND 설정도 없다(ADM-07 은 PK 이름 문제만 다룸). ocr_faxcontent 도 동일하게 `return None`.
- 재현: helpers.py 소스 확인.
- 확인 수준: 재현(소스)

## F4-18 (중간) 수신 팩스 주석(annotate_fax / ENABLE_FAX_ANNOTATION / ANN_GRAVITY)이 구현되지 않음
- 위치: S/cli/faxrcvd.py:44 (플래그를 읽기만 함), S/common/helpers.py (annotate_fax 없음)
- 증상: 레거시 faxrcvd.php:199 는 활성 시 PDF 에 "FaxID: N" 을 찍는다. NamiFAX 는 플래그를 읽고도 사용하지 않는다.
- 재현: `grep -rn annotate_fax src/namifax` 결과 없음.
- 확인 수준: 재현(부재)

## F4-19 (높음) import_archive 도구가 스텁이고 진입점에도 없음: "Imported N faxes" 만 출력
- 위치: src/avantfax/cli/import_archive.py, S/main.py (서브커맨드 목록에 없음)
- 증상: 레거시 tools/import_archive.php(169행)는 faxinfo 를 읽어 주소록 회사/번호를 만들고 ArchiveIn/ArchiveOut 레코드를 생성한다. NamiFAX 는 `recvd` 경로의 .tif 개수만 세고 `inbox = ArchiveIn()` 만 만든 뒤 DB 에 아무것도 넣지 않은 채 "Imported N faxes into category X" 를 출력하며, sent 폴더(.pdf)는 처리조차 하지 않는다. `namifax import-archive` 는 "Unknown command". 기존 팩스 파일을 DB 에 재등록하는 유일한 수단이 없다.
- 재현: `namifax import-archive` → Unknown command 사용법 출력. 소스상 DB 삽입 호출 없음.
- 확인 수준: 재현

## F4-20 (낮음) tools/update_contacts.php 대응 없음
- 위치: 없음 (legacy/avantfax/tools/update_contacts.php)
- 증상: 구 주소록(Rubrica) 데이터를 AddressBook 으로 갱신하는 도구가 없고, import-users/import-blacklist 는 `--help` 를 파일명으로 해석한다(`Error: File not found: --help`).
- 재현: `namifax update-contacts` → Unknown command.
- 확인 수준: 재현

## F4-21 (낮음) 플러그인/테마, 설치, 업그레이드 스크립트와 HylaFAX 연동 설치 문서 없음
- 위치: 레거시 PLUGINS_DIR, rh/debian/sles-install.sh, upgrade.sh, upgrade-from-2.3.sh, setup-postfix.sh, fixlink-faxcover.sh
- 증상: NamiFAX 에는 systemd 유닛 2개뿐이며 HylaFAX FaxDispatch/faxrcvd/notify/dynconf 훅 설치, 로그 회전, DB 생성/권한, 업그레이드 절차 문서와 스크립트가 없다(README.md 0바이트는 K14). 이전 대상 설치본의 운영 절차가 끊긴다.
- 재현: 디렉터리 확인.
- 확인 수준: 재현(부재)

## F4-22 (중간) 사용자 DB 의 language 설정이 화면 언어에 적용되지 않음
- 위치: S/i18n.py custom_locale_negotiator (`getattr(request, "current_user", None)`), S/security.py
- 증상: 협상기는 request.current_user.language 를 보는데 request 에 current_user 속성이 어디에서도 설정되지 않는다(identity 만 있음). 기존 사용자들이 레거시에서 저장한 language('ko', 'pt-br', 'zh-tw', 'cz', 'rs' 등, 별칭 정규화는 있음)가 로그인 후 무시되어 모두 영어로 표시되고, 쿠키나 ?lang= 지정 때만 바뀐다. 설정 화면의 언어 select 도 저장된 값을 선택 상태로 표시하지 않는다.
- 재현: language='ko' 인 bob 로그인 후 `GET /inbox` 에 "받은" 없음(한국어 미적용), `GET /settings` 의 ko option 에 selected 없음, `GET /settings?lang=ko` 는 한국어.
- 확인 수준: 재현

## F4-23 (중간) 설정 기본값 변경과 설정 이전 경로 없음
- 위치: S/cli/faxrcvd.py:42-49, S/cli/faxcover.py:41, 레거시 config.php
- 증상: 같은 이름의 옵션 기본값이 레거시와 반대이다: ARCHIVEFAX2EMAIL(레거시 true, NamiFAX "0"), FAXRCVD_INCLUDE_PDF(true vs "0"), AUTOCONFDID(true vs "0"), FAXCOVER_DATE_FORMAT("%d.%m.%Y %H:%M" vs "%Y-%m-%d %H:%M:%S", 그리고 문법은 PHP strftime 대 Python). 기존 local_config.php 에서 값을 읽거나 환경변수로 변환하는 도구가 없어 운영자가 옵션 80여 개를 수동으로 재확인해야 하며, 설정하지 않으면 동작이 조용히 바뀐다(수신 팩스 이메일에 PDF 미첨부, Fax2Email 수신분이 수신함에 안 보이는 대신 기본 보관 안 됨 등). 옵션 별 상태는 1-6 절 표 참고.
- 재현: 기본값 대조(config.php:208-219, faxrcvd.py:42-49)
- 확인 수준: 재현(소스 대조)

## F4-24 (높음, 데이터 이전) MySQL 레거시 스키마 이전 경로가 없고, 이전 도구/문서도 없음
- 위치: README.md(0바이트), ARCHITECTURE.md, docs/, S/db/engine.py (MySQL 드라이버 미선언은 COR-12)
- 증상: 레거시는 MySQL 전용(create_tables.sql, db-update-*.sql)이며 NamiFAX 는 SQLite 전용 스키마이다. 이전을 위한 덤프 변환기, 스키마 매핑 문서, 검증 스크립트, 이전 절차 설명이 저장소 어디에도 없다("migration"은 Strangler Fig 이식 전략 문구뿐). 실험 결과 레거시 스키마 SQLite 변환본을 그대로 NamiFAX 에 붙이면 동작하는 부분과 아닌 부분이 섞인다: 로그인(MD5)과 사용자, 모뎀, 커버, 카테고리, 배포목록, 시스템 로그 화면은 나오지만 주소록 번호(F4-15), 아카이브 파일(F4-10/11), 비밀번호 이력(pwdhash vs password, COR-18), 바코드 PK(ADM-07), DynConf(COR-08), SysLog PK(ADM-20) 는 깨진다. 비밀번호 MD5 자체는 호환(admin=md5('password')). 즉 '있는 테이블 이름은 같지만 컬럼이 다른' 호환 문제를 해결하는 마이그레이션이 없다.
- 재현: `scratchpad/agent-r2-parity/mig/conv.py` 로 legacy 스키마+샘플 SQLite 생성 → NAMIFAX_DB_PATH 지정 후 init_database_tables 및 webtest 로 화면 확인(위 F4-15, F4-10 결과 참고).
- 확인 수준: 재현

## F4-25 (중간, 데이터 이전) 스키마 마이그레이션이 이전 데이터 행 전체를 수정: faxnumid, modemdev 기본값 강제
- 위치: S/db/schema.py `_apply_schema_migrations` 의 마지막 두 UPDATE (`faxnumid = 1 WHERE faxnumid IS NULL`, `modemdev = 'ttyS0' WHERE modemdev IS NULL`), 자리표시 회사 행 'XXXXXXX'
- 증상: 기동할 때마다 FaxArchive 전체에 대해 faxnumid 가 NULL 인 행(레거시에서 회사 미매칭 수신, 그리고 사용자 발송분)이 1 번 주소록 번호에 연결되고, 레거시에서 modemdev 가 NULL 인 발송분(송신 팩스에는 수신 모뎀이 없음)이 'ttyS0' 모뎀 소속으로 바뀐다. 결과: 화면에서 미매칭 수신 팩스의 발신 회사가 모두 "XXXXXXX"(레거시 설치 시 넣는 자리표시 회사)로 표시되고(실험에서 재현), 모뎀 기반 접근 제어와 모뎀별 필터가 틀어진다. 또한 이 UPDATE 는 idempotent 가 아니라 레거시 NULL 의미(미매칭)를 영구 삭제한다. (seed 덮어쓰기 COR-02/ADM-01 제외 항목이며, 이 UPDATE 들은 seed 가 아닌 스키마 마이그레이션 구간)
- 재현: legacy 샘플에서 fid 1,3(faxnumid NULL, modemdev ttyS1)과 fid 2(발송, modemdev NULL) 생성 → init_database_tables 후 fid 1,3 faxnumid=1, fid 2 modemdev='ttyS0'. bob 의 /inbox 행의 발신이 모두 "XXXXXXX".
- 확인 수준: 재현

## F4-26 (높음, 데이터 이전) 레거시 '|' 구분자(modemdevs, didrouting, faxcats)와 수신함 모뎀 필터의 ',' 분리가 불일치
- 위치: V/inbox.py:25-29 (`devices.split(",")`), 레거시 AFUserAccount.php:602-636 (`explode("|", …)`), SV/user_account.py get_modemdevs(|)
- 증상: 레거시 UserAccount.modemdevs/didrouting/faxcats 는 "ttyS0|ttyS1" 식으로 저장된다. 서비스 계층은 '|' 로 분리하지만 수신함 뷰는 쉼표로 분리하므로 다중 모뎀 사용자는 장치명이 "ttyS0|ttyS1" 하나로 취급되어 어떤 모뎀 팩스도 매칭되지 않는다(필터가 동작한다면). USR-04 의 "제한 자체가 동작하지 않음"이 고쳐지더라도 이전 데이터에서는 모뎀 2개 이상 사용자가 빈 수신함을 보게 된다.
- 재현: 코드 대조(뷰는 identity["modemdevs"] 문자열을 ','로만 분리). 현재는 identity 에 modemdevs 가 없어 효과가 가려짐.
- 확인 수준: 추론

## 부록: 실험 메모
- 레거시 create_tables.sql 을 정규식으로 SQLite DDL 로 변환(mig/conv.py)해 샘플(사용자 bob MD5, 주소록 1건+번호+이메일, 카테고리 'Orders', 모뎀 2, DID 1, 바코드 1, DynConf 1, 배포목록 1, 로그 1, 팩스 3건)을 넣고 NAMIFAX_DB_PATH 로 NamiFAX 에 연결했다. 로그인(MD5), 사용자/모뎀/카테고리/배포목록/로그 목록은 표시되나 위 결함이 재현되었다.
- 비밀번호: 레거시 저장 해시는 MD5 32자이며 NamiFAX PasswordManager 는 동일한 MD5 를 비교하므로 이전 사용자 로그인은 가능하다(admin 의 경우 admin/password 하드코딩 우회 K10 도 있음).
- seed 는 비어 있지 않은 레거시 DB 에도 가짜 행을 주입한다(예: DID 'Accounting Direct', 카테고리 'Contracts'). COR-02/ADM-01 의 변형이므로 별도 결함으로 세지 않았다.
- 실행한 모든 DB 는 scratchpad/agent-r2-parity/ 아래. 공격 페이로드는 실행하지 않았다.
