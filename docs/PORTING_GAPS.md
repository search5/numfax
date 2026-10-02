# 레거시(AvantFAX) 대비 미구현·결함 목록 (전수 조사)

네 영역(사용자 화면, 관리자 화면, AJAX·자바스크립트·화면 자원, 클래스·명령줄·설정·설치 스크립트)을 레거시 소스와 한 줄씩 대조한
결과입니다. 이미 원본 실행으로 확인해 맞춘 것(보관함·받은 팩스함 권한, 전송 명령, 출력함, 비밀번호 찾기, 팩스별 접근 권한 등)과
의도한 차이(SAML·패스키·TOTP 같은 새 기능, 페이지형 대화상자, 변경 요청은 POST+CSRF, 한국어 외 번역 보류)는 뺐습니다.

◐ = 일부만 처리(남은 부분은 그 줄에 적힌 내용). ✅ = 처리 완료(해당 커밋 메시지와 `ARCHITECTURE.md` 참고). 표기: **[확인]** = 제가 코드를 읽거나 실제로 실행해 확인함, **[보고]** = 조사 보고에만 있고 개별 확인은 하지 않음.

## A. 화면에 있는데 고장 난 것 (가장 먼저)

| # | 내용 | 근거 |
|---|---|---|
| A1 ✅ | `send_mail`에 첨부(`file=`)를 주면 `TypeError`, 참조(`cc=`/`bcc=`)를 주면 `AttributeError`로 죽는다. 영향: 팩스 메일 보내기(첨부), `FAXRCVD_INCLUDE_PDF`, notify의 PDF 첨부. 썸네일(`embedd`)도 메일에 들어가지 않는다 | **[확인]** 실행해 재현. `common/helpers.py:335-341` 대 `services/mailer.py:107`(인자명 `alt_name`, `set_cc` 없음) |
| A2 ✅ | 받은 팩스함이 **처음 25건만** 보인다. 페이지 나누기·"N-M (X건)"·쪽 이동이 없고, 사용자별 페이지 크기(`faxperpageinbox`)를 읽지도 저장하지도 않는다 | **[확인]** `views/inbox.py:82`, `archive_base.py` 기본 `limit=25` |
| A3 ✅ | 받은 팩스함 행의 "보관"·"삭제"가 `/archive/move/<id>`, `/delete/<id>`로 가는데 그런 라우트가 없다(404). 위의 "선택 보관/삭제" 버튼은 동작 코드가 없다. 선택 삭제는 `can_del` 없는 사용자에게도 보인다 | **[확인]** `inbox.jinja2:166,191`, `routes.py`, 정적 JS 폴더 없음 |
| A4 ✅ | 팩스 보기가 실제 페이지 이미지가 아니라 "High-Resolution Raster Preview" **모형**이고, 이전/다음 팩스 이동·메모/보관/삭제 버튼이 없다. 받은 팩스함 썸네일도 항상 빈 그림(이미지를 내주는 라우트 없음) | **[확인]** `viewfax.jinja2`, `routes.py` |
| A4a ✅ | (받은 팩스의 미리보기 파일 이름·크기, 보낸 팩스의 PDF 썸네일(Ghostscript 필요)까지 처리됨) 이전 내용: 보낸 팩스의 썸네일은 실제 렌더링이 아니라 120x160 회색 빈 이미지이고, 수신 시 만든 미리보기 파일 이름(`preview{i}.png`)을 보관소 코드(`page{i}.png`)가 못 찾아 회전·삭제·썸네일 재생성이 어긋난다 | **[보고]** `helpers.py:451`, `archive_base.py:13` |
| A5 ✅ | (OpenSearch `/search`까지 처리됨) 이전 내용: 카테고리가 DB가 아니라 `invoices`/`legal` 고정, "받은/보낸" 값이 `inbox`/`sent`라서(검색 코드는 `r`/`s`/`*`) 필터가 먹지 않는다. 쪽 나누기 없음(25건에서 끝), 업체·사용자(슈퍼유저) 필터·열·미리보기·행 동작(메모, 삭제, 전송 보고서) 없음, 날짜가 일·월·연 선택이 아니라 직접 입력, 검색어 없을 때 오늘 팩스를 보여 주지 않음, OpenSearch(`search.php`) 없음 | **[확인]** 필터 값, 페이지 나누기. 나머지 **[보고]** |
| A6 ✅ | 주소록 편집에서 "새 팩스 번호" 입력이 `required`라서, 기존 업체를 번호 추가 없이는 저장할 수 없다(제가 만든 화면의 결함) | **[확인]** `addressbook_edit.jinja2:121` |
| A7 ✅ | "업체 지정"(`/assign`) 모달이 항상 `abook_id=1`을 보낸다(숨은 값 고정). 업체 이름 바꾸기 경로는 업체를 불러오지 않고 `set_company`를 부른다 | **[확인]** `modal_assign.jinja2`(고정값), `modals.py` |
| A8 ✅ | 받은·보관 팩스의 "발신자" 링크가 `/addressbook?search=`인데 주소록은 `q`만 읽어서 검색이 적용되지 않는다 | **[확인]** `views/addressbook.py:50` |
| A9 ✅ | 팩스 메일 보내기: 팩스를 못 불러와도 **첨부 없이 그냥 보낸다**. CC/BCC, 파일 이름, 분류·"보낸 뒤 보관", 발신자 표시, 서명(`email_sig`), 주소록 선택, 제목 기본값(회사명)이 없다 | **[확인]** 첨부 없이 전송은 코드로 확인. 나머지 **[보고]** |
| A10 ✅ | 환경설정이 표지 선택·받은/보관 팩스 쪽당 개수를 저장하지 않고(고정 `standard/urgent`, 10/20/50), 이메일 형식·중복 검사가 서버에 없다 | **[확인]** `views/settings.py`에 `coverpage`/`faxperpage` 없음 |
| A11 ✅ | (회선 제한, 업로드 검사, 작업 번호 안내, 슈퍼유저 전용 필드, 연락처·배포 그룹 선택 창, 표지 자동 채우기(`prefillto`)는 처리됨; 표지 접기와 다중 파일 목록도 처리됨) 이전 내용: 연락처·배포 그룹 선택이 동작하지 않는다(팝업 도우미가 연결되지 않음), 표지 접기·다중 파일 목록 UI·자동 채우기(`prefillto`) 없음 | **[보고]** (회선 제한, 업로드 검사) |
| A12 ✅ | 배포 그룹: 구성원 추가·제거가 동작하지 않고(버튼에 동작 없음), 구성원 표시가 "업체 - 번호"로 풀리지 않고 저장된 값 그대로 나온다. 오류는 삼킨다 | **[보고]** |
| A13 ✅ | 환경설정의 TSI는 슈퍼유저 전용, 카테고리 선택 등 일부 권한 제한이 없다. 주소록 카테고리도 모두에게 보인다 | **[보고]** (가벼움) |

## B. 보안

| # | 내용 | 근거 |
|---|---|---|
| B1 ✅ | `/ajax/deletefaxes?fids=…` 확인 화면이 `fids`를 이스케이프 없이 HTML에 넣는다(반사형 XSS). 로그인한 사용자가 만든 링크를 열면 스크립트가 실행된다 | **[확인]** 실행해 재현(`ajax.py:281`) |
| B2 ✅ | 관리자 화면에서 사용자를 만들 때 비밀번호를 비우면 평문 `password`로 만들어지고, 첫 로그인 변경 강제(`wasreset`)도 안내 메일도 없다(원본은 무작위 비밀번호 + 강제 변경 + 메일) | **[확인]** `views/admin.py:146` |
| B3 ✅ | `/ajax/archivefax`, `/ajax/deletefaxes`, 환경설정·관리자 폼 등 상태 변경 POST에 CSRF 토큰이 없다(원본도 없음, 쿠키 `SameSite=Lax`에 의존) | **[확인]** (앞서 보고) |
| B4 ✅ | `/ajax/modemstatus`가 요청의 모뎀 목록을 무시하고 모든 모뎀 상태를 돌려준다(원본은 사용자 모뎀만) | **[보고]** |
| B5 ✅ | 로그인 성공·실패 감사 로그가 없다(원본은 실패 시 비밀번호 마지막 자리를 가려 기록). 계정 비활성과 비밀번호 오류 메시지를 구분하지 않는다 | **[보고]** |

## C. 관리자 화면

| # | 내용 | 근거 |
|---|---|---|
| C1 ✅ | 사용자 편집: 사용자별 **회선·DID·카테고리 배정이 저장되지 않고**(폼은 있으나 뷰가 읽지 않으며 체크박스가 전부 `checked`), 계정 활성(`acc_enabled`), 비밀번호 주기(`pwdcycle`)·재사용, 언어, 발신자 정보(`from_*`), TSI, 표지, 음성 파일, 쪽당 개수 필드가 없다 | **[확인]** 배정 미저장. 필드 목록 **[보고]** |
| C2 ✅ | `any_modem` 체크를 해제해도 항상 1로 저장된다 | **[확인]** `views/admin.py:123` |
| C3 ✅ | 사용자 저장의 모든 오류(형식, 중복, 비밀번호 길이)를 조용히 삼키고 무조건 이동한다. 성공·오류 메시지가 없다. 길이 제한(`maxlength`)도 없다 | **[확인]** `except Exception: pass` |
| C4 ✅ | (사용자 목록, 실제 HylaFAX 버전, 모뎀 상태 색은 처리됨. 관리자 판정을 `is_admin`뿐 아니라 `is_admin or superuser`로 하는 것은 의도한 차이로 둠) 이전 내용: 대시보드의 HylaFAX 버전이 고정 문자열 `6.0.7`이고 모뎀 상태 색이 없다. 관리자 판정이 `is_admin`이 아니라 `is_admin or superuser`다 | **[보고]** |
| C5 ✅ | 모뎀 편집: 카테고리 선택·**삭제 버튼**(삭제 분기는 도달 불가)·메시지가 없고, 같은 장치명을 "생성"하면 오류 대신 조용히 수정한다. 바코드 라우트도 카테고리 선택·저장이 없다. dynconf 모뎀 목록이 별칭이 아니라 장치명이고 모뎀이 없으면 가짜 `ttyS0`를 넣는다 | **[보고]** |
| C6 ✅ | 카테고리를 삭제해도 그 카테고리를 가진 팩스의 `faxcatid`를 비우지 않아 존재하지 않는 카테고리를 가리키는 팩스가 남는다 | **[보고]** (`remove_category` 호출 없음) |
| C7 ✅ | 시스템 기능: 재부팅·종료 버튼이 동작하지 않고(메시지만), "백업"은 매니페스트 한 줄만 든 tar.gz다. 팩스 보관소·DB 덤프 내려받기가 없다 | **[보고]** (오해를 부르는 스텁) |
| C8 ✅ | 시스템 로그: (오늘 날짜 기본값·선택 유지·월 이름 처리됨) 100행에서 조용히 잘린다(안전 한도라 그대로 둠) | **[보고]** |
| C9 ✅ | 설정으로 메뉴·필드를 숨기는 동작(`ENABLE_DID_ROUTING`, `ENABLE_BARDECODE_SUPPORT`)이 없다 | **[보고]** |
| C10 ✅ | (DB 중단 안내 페이지, 대체 인증 `ALTERNATE_AUTH_*`(PAM·pwauth)와 웹 서버 인증 `WEBSERVER_AUTH`(REMOTE_USER)는 처리됨. 원본의 별도 관리자 전용 로그인 화면은 만들지 않음: 한 로그인에서 권한으로 나눔) | **[보고]** |

## D. 사용자 화면의 부가 기능

- ✅ 새 팩스 알림(처리됨: 모든 화면의 안 읽은 수, 30초 폴링, 소리 파일, 20초 모뎀 상태 폴링; 알림창은 모달 `alert` 대신 브라우저 알림) 이전 내용: 안 읽은 수 폴링(30초), 새 팩스 때 창 포커스·알림창·**음성 알림**, 모뎀 상태 줄(20초 폴링)이 없다. 기본 상단 배지는 렌더링 시점의 정적 값이고 `num_inbox`는 받은 팩스함 화면에서만 채워진다 **[보고]**.
- ✅ (처리됨: 주소록·이메일·배포 그룹 실시간 필터, 이메일/팩스/배포 그룹 이동 칩, 연락처·배포 그룹·이메일 선택 창) 이전 내용: 주소록·보관함·배포 그룹의 실시간 필터, 주소록 하위 메뉴(이메일 / 팩스 / 배포 그룹) 이동 칩, 이메일 주소 선택 팝업이 없다 **[보고]**.
- ✅ (처리됨) 전송 보고서(`txreport`)에 팩스 번호와 팩스 이미지가 없고 상태가 고정 문구다 **[보고]**.
- ✅ (받은 팩스 행의 회선/DID 그룹, 헤더의 전체 이름·슈퍼유저 표시, `ENABLE_DL_TIFF`, 서버 이름, 접근 키, 인쇄 CSS 처리됨) **[보고]**.

## E. 명령줄 훅·변환·설정

| # | 내용 | 근거 |
|---|---|---|
| E1 ✅ | 수신 팩스 **자동 인쇄**(`PRINTFAXRCVD`, `PRINTCMD` …)가 없다. 인쇄할 프린터를 계산만 하고 실행하지 않는다 | **[확인]** `cli/faxrcvd.py`에 실행 코드 없음 |
| E2 ✅ | `notify`가 `loadbyfaxnum`의 결과(항상 참인 튜플)로 분기해, 새 수신자 번호의 업체·번호가 만들어지지 않고 `ArchiveOut.companyid`가 비며 여러 업체 번호 처리도 동작하지 않는다(수신 쪽은 이미 고침) | **[확인]** `cli/notify.py:174` |
| E3 ✅ | `faxinfo`가 TIFF가 아닌 파일에 가짜 값(`Sender 00000000`)을 돌려줘 수신 훅의 "손상 파일" 검사가 무력화된다 | **[보고]** |
| E4 ✅ | (PS/PDF 변환·합치기, 변환 실패 시 중단, 복사 실패 시 중단, 팩스 ID 주석, `TIFF_TO_G4` 처리됨; PS는 Ghostscript 필요하며 리눅스 컨테이너의 실제 `gs`로 확인함) | **[보고]** |
| E5 ✅ | faxcover: HTML 표지(`html2ps`, `USE_HTML_COVERPAGE`)와 `NUM_PAGES_FOLLOW` 없음(시드의 HTML 표지는 쓸 수 없음), 치환값의 PostScript 이스케이프 없음(이름·제목에 괄호나 한글이 있으면 PS가 깨질 수 있음), `-C` 확장자 검사 없음 | **[보고]** |
| E6 ◐ | (`ARCHIVEFAX2EMAIL`, `FAXRCVD_INCLUDE_PDF`, `AUTOCONFDID`, 날짜 형식은 원본 기본값으로 처리됨; `WWWUSER`는 Debian 웹 사용자 `www-data`라 그대로 둠) 이전 내용: 기본값이 원본과 반대: `ARCHIVEFAX2EMAIL`, `FAXRCVD_INCLUDE_PDF`, `AUTOCONFDID`(원본 true), 날짜 형식(`FAXCOVER_DATE_FORMAT`, 메일 제목), `WWWUSER` | **[보고]** (일부는 운영 문서에 기록) |
| E7 ✅ | (`HYLASPOOL`, `BINARYDIR`, 날짜 형식, `PAPERSIZE`/`DPI`, 썸네일 크기 `PREV_TN`/`PREV_SP`는 `common/settings.py`로 처리됨) (`CALLIDN_*` 순서, 바코드·OCR 켜기·명령·언어, `EMAIL_ENCODING_*`도 처리됨) (`RESTRICTED_USER_MODE`·`INBOX_LIST_MODEM`도 같은 이름의 환경변수로 켤 수 있음: 아카이브 검색의 회선·분류 AND 조건, 수신함 회선별 정렬과 제목 행) (`SHOW_ALL_CONTACTS`도 처리됨: 기본 켜짐, 끄면 검색어 2글자 이상일 때만 `/ajax/book`·`/ajax/archivebook`·연락처 선택창이 조회) (`SENDFAX_USE_COVERPAGE`·`SENDFAX_REQUEUE_EMAIL`도 처리됨: 둘 다 기본 켜짐, 보내기 화면의 표지 스위치와 '재시도 알림' 체크의 시작 상태) (`MAX_USERNAME_SIZE`·`MAX_PASSWD_SIZE`·`MIN_PASSWD_SIZE`·`MAX_EMAIL_SIZE`도 같은 이름의 환경변수로 처리됨: 기본값은 원본의 15·15·8·99. 이식본이 쓰던 40·64에서 원본 값으로 되돌렸으므로 16자 이상 비밀번호가 필요하면 `MAX_PASSWD_SIZE`를 지정) (`DEFAULT_FAXES_PER_PAGE_INBOX`/`_ARCHIVE`도 처리됨: 수신함 25, 보관함 30, 아래 G4) 남은 것: 없음. `SENDFAX_*`는 원본에 두 항목뿐, `MAX/MIN_*_SIZE`. 이전 내용: 같은 이름 설정이 없는 것: HylaFAX 경로(`BINARYDIR`, `HYLAFAX_PREFIX`, `HYLASPOOL`), `CALLIDn_*` 순서, 바코드·OCR 사용 여부와 명령·언어, `EMAIL_ENCODING_*`, `EMAIL_DATE_FORMAT`, `PAPERSIZE`, `DPI`, 썸네일 크기, `RESTRICTED_USER_MODE`·`INBOX_LIST_MODEM`(코드는 있으나 켤 방법이 없음), `SHOW_ALL_CONTACTS`, `SENDFAX_*`, `DEFAULT_FAXES_PER_PAGE_*`, `MAX/MIN_*_SIZE` | **[보고]** |
| E8 ✅ | (dynconf 시스템 로그, 훅마다 마이그레이션하지 않는 단축, 보존 기간 정리용 cron 안내는 `docs/INSTALL_HYLAFAX.md`와 `deploy/cron.d/namifax`에 처리됨) 이전 내용: 내장 스케줄러는 임시 파일 정리만 돌리고 보존 기간 정리(`-i`/`-d`)는 별도 cron이 필요한데 안내가 없다. 훅이 호출될 때마다 스키마 검사·마이그레이션(DDL)을 시도한다(벨마다 호출되는 dynconf 포함) | **[보고]** |
| E9 ✅ | 업로드 검사 클래스(`FileUpload`)가 어디에서도 쓰이지 않는다(보내기·vCard는 형식·크기를 서버에서 검사하지 않음) | **[보고]** |
| E10 ✅ | 새 DB의 기본 표지가 `standard.ps`/`urgent.ps`인데 실제 파일은 `cover.ps`, `cover-letter.ps`, `coverpage.html`이라 가리키는 파일이 없다. 원본에 없는 카테고리 General/Invoices/Legal을 시드한다 | **[확인]** `db/seed.py:34`, 정적 파일 목록 |
| E11 ✅ | (`import_users`의 `FROM_*` 기본값·서명·오류 안내는 처리됨. 2.x 이전 DB를 옮기는 `update_contacts`는 지원하지 않기로 함: 3.x 이후 DB만 대상) | **[보고]** |

## F. 설치·운영

- ◐ (처리됨: 훅 스크립트·설정 조각·sudoers·cron·nginx/apache·postfix 안내·설치 문서 `docs/INSTALL_HYLAFAX.md`, 사용자 동기화 `HYLAFAX_USER_SYNC`; 실제 HylaFAX에서는 시험하지 못함) 이전 내용: 이메일-팩스 게이트웨이(`email2fax`, postfix/sendmail 설정)와 HylaFAX 훅 배선(`CoverCmd`, `JobFmt`(`Mailaddr` 열), `UseJobTSI`, `FaxRcvdCmd`/`DynamicConfig`/`NotifyCmd`), 크론 등록, 파일 권한·소유자, 웹 서버 설정, `sudoers`(`faxadduser`/`faxdeluser`) 설치 스크립트와 문서가 없다. 연동 문서는 개념 설명과 예시 한두 줄뿐이다 **[보고]**.
- ✅ (처리됨, 기본은 꺼짐) HylaFAX 사용자 동기화(`faxadduser`/`faxdeluser`)가 없다. 포트는 `FAXUSER` 환경변수만 지정하므로 `hosts.hfaxd`에 없는 사용자로 `faxrm`/`faxalter`가 실패하는지 확인이 필요하다 **[보고, 확인 필요]**.

## G. 레거시와 다시 대조한 결과 (진입점·설정·스키마·스크립트·화면 문구·JS)

앞의 A~F는 조사 보고에 근거한 항목이 많아서(**[보고]**), 레거시 소스를 직접 열어 기계적으로 다시 대조했습니다. 아래는 모두 **[확인]**(코드를 읽거나 스크립트로 비교)입니다.

**범위별 결과**

| 대조 대상 | 결과 |
|---|---|
| 웹 진입점 74개(`*.php` 36, `ajax/` 13, `admin/` 25) ↔ 라우트 | 이름으로 대응시켜 빠진 것이 없음을 확인했고, 이름만으로 불분명한 것(`rubrica*`, `no-database`, `file`·`pdf`, `archivefax`와 `ajaxarchivefax`)은 소스를 읽어 확인했다(나머지의 동작 동일성은 이 대조의 범위 밖). `rubrica.php`·`rubrica_edit.php`는 템플릿이 없고 링크되지 않는 죽은 코드라 제외(`ARCHITECTURE.md` 17.8에 기록). 관리자 전용 로그인 4개(`admin/index·check_login·logout·pwdexpired`)는 한 로그인에서 권한으로 나누기로 한 결정(C10) |
| DB 테이블 14개(`create_tables.sql`, `db-update-*.sql`) ↔ 모델 | 테이블·컬럼 모두 있음(`UserAccount` 32/32, `FaxArchive` 17/17). 이식본에만 있는 6개는 새 기능(`FaxOCR`, `NetworkPrinters`, `SystemConfig`, `SystemSettings`, `UserTOTP`, `UserWebAuthnCredentials`) |
| 명령줄·훅 14개(`includes/` 6, `tools/` 8) ↔ `namifax.cli` | `update_contacts`(2.x 이전 DB용, 지원하지 않기로 함)를 뺀 13개 모두 대응 |
| 설정 변수 147개 ↔ 코드·문서 | 이름이 없는 약 70개 중 대부분은 대체됨(`AFDB_*`→`DATABASE_URL`, 테마 경로→Tailwind, `SMTP_*`·`SYSTEM_EMAIL_SIG_*`→관리자 SMTP 화면, 변환 도구 변수→Ghostscript 등, `SYSTEM_IP`→요청 주소). 아래 G1~G8이 실제 차이 |
| 화면 문구 332개 ↔ `namifax.pot` | 144개가 문구 일치로는 찾아지지 않았으나 대부분 문구를 다르게 쓴 것이라 누락 개수로 보지 않음. 동작을 암시하는 문구(모뎀 상태, 오디오 선택, 비밀번호 재사용 등)만 골라 확인했고 추가 누락은 없었음 |

**실제 차이** (모두 처리함)

| # | 내용 | 근거 |
|---|---|---|
| G1 ✅ | 업체 지정(`/assign`) 화면에 "White Pages에서 찾기" 링크(`WHITEPAGES`)가 없었다. 업체 이름이 숫자로만 이루어졌을 때만 보인다(원본의 규칙) | `assign.tpl:20`, `assign.php:27` |
| G2 ✅ | `FOCUS_ON_NEW_FAX`·`FOCUS_ON_NEW_FAX_POPUP` 스위치가 없고, 이식본은 새 팩스가 오면 항상 창을 앞으로 가져오고 알림·소리를 실행했다. 이제 둘 다 기본이 꺼짐이고, 포커스는 앞의 것, 알림(브라우저 알림, 원본의 `alert` 대신)과 소리는 뒤의 것이 켜졌을 때만 실행한다 | `avantfax.js:375-387`, `inbox.tpl:147` |
| G3 ✅ | 보관함에서 행에 마우스를 올리면 큰 미리보기를 옆에 띄우는 동작(`previewImage`, `#faxpreview`)이 없었다. 행을 `#FFF0B6`으로 강조하고, 상자는 행 왼쪽 110px에 두며, 페이지 끝까지 130px 미만이면 끌어올린다 | `avantfax.js:218`, `archive.tpl:50,103` |
| G4 ✅ | 수신함 한 쪽 기본 건수가 원본은 25인데 이식본은 10이었고(상수와 컬럼 기본값), 환경변수도 없었다. `DEFAULT_FAXES_PER_PAGE_INBOX`(25)·`_ARCHIVE`(30)로 처리했고, 컬럼 기본값은 마이그레이션 0025로 없앴다. **이미 저장된 값(예전 기본값 10 포함)은 사용자가 고른 값과 구분할 수 없어 그대로 둔다** | `inbox.php:28`, `models/useraccount.py` |
| G5 ✅ | 수신함에서 새 팩스가 와도 목록이 새로고침되지 않았다(배지만 갱신). 원본은 수신함 화면에서 건수가 바뀌면 `window.location.reload()`로 목록을 다시 불러오고, 소리가 재생 중이면 끝난 뒤에 불러온다. 다른 화면은 건수만 갱신한다 | `avantfax.js:359-395`, `inbox.tpl:141-145` |
| G6 ✅ | TIFF→PDF 대체 경로(libtiff·HylaFAX의 `tiff2pdf`가 없을 때)가 쪽을 RGB로 바꾸고 해상도를 버렸다. 3쪽 팩스가 TIFF의 6.7배(833KB 대 125KB)이고 쪽 크기가 24×30.6인치여서 PDF를 인쇄하면 크기가 틀어졌다. 이제 흑백 그대로, 팩스 해상도(204×196 또는 204×98dpi, 없으면 204×196)로 저장한다. 보내기 파일의 TIFF 합치기(`convert2pdf`)도 같은 함수를 쓰고, `PAPERSIZE`(기본 a4)는 PostScript 변환의 Ghostscript에 `-sPAPERSIZE`로 전달한다(설정은 있었으나 쓰이지 않았다) | `functions.php:982,1006`, `config.php:382-386`, `helpers.py` |
| G7 ✅ | 원본이 DB에 **HTML 엔티티로 저장한** 이름(`M&uuml;ller`, `&amp;`)이 이식본 화면에 글자 그대로 보였다. 원본은 값을 HTML에 그대로 출력해서 브라우저가 글자로 그렸고, 이식본은 이스케이프한다. 원본이 만든 실제 데이터로 확인했다(`tools/migration_rehearsal/check_text.py`). **읽을 때 풀어서 보여 주는 방식**으로 처리했다: 사람이 입력하는 텍스트 컬럼의 타입(`LegacyHtmlString`, `LegacyHtmlText`)이 완전한 참조(`&uuml;`, `&#039;`, `&#xFC;`)만 풀고, 검색은 검색어의 원본 인코딩 형태도 함께 비교한다. DB는 건드리지 않는다. 한계: 원본이 이중 인코딩해 깨뜨린 값(사용자 이름의 한글)은 복원하지 않고, 엔티티 모양을 글자 그대로 입력한 값도 풀린다 | `docs/MIGRATING_FROM_AVANTFAX3.md` 4.1 |
| G8 ✅ | 이식본의 영어 화면 문구가 원본과 같은 뜻인데 표현이 달라서, 원본의 번역(22개 언어)을 이어받지 못했다. **같은 화면에서 같은 역할로 쓰이는 26개 문구**를 원본의 영어 원문으로 맞췄다(`Modem created`→`The modem was created`, `Notify on retry`→`Notify on requeue`, `Destination Number`→`Destination fax numbers` 등. 전체 목록은 `tools/i18n_import_legacy.py`의 `RENAMES`). 여러 화면에서 함께 쓰는 짧은 문구(`Company`, `Address`, `City`)와 뜻이 다른 문구(`Reboot Services`와 `Reboot server`)는 바꾸지 않았다. 원문이 같아진 문구 가운데 번역이 없거나 fuzzy였던 것에는 원본의 번역을 채웠다(언어당 55~85개, 이미 번역이 있으면 유지, 제품명 `AvantFAX`가 든 문구와 마크업이 든 문구는 제외). 번역되어 보이는 문구는 한국어 외 로케일에서 약 35%에서 42~47%로 늘었다. 원본의 일본어 파일에서 반대 뜻으로 번역된 두 문구(`ADMIN_MODEM_CREATED`, `ADMIN_MODEM_DELETED`)는 가져오지 않았다. 한계: 같은 뜻인지를 사람이 한 건씩 판단했고, 짝이 안 맞는 나머지 문구(원본 209개 중 26개만 짝을 찾음)의 번역은 이어지지 않는다 | `tools/i18n_import_legacy.py` |

**변환 도구 변수 대조** (레거시 `config.php:354-386`)

| 변수 | 레거시에서 하는 일 | 이식본 |
|---|---|---|
| `TIFFCP`, `TIFFCPG4` | 받은 팩스 TIFF 복사(`TIFF_TO_G4`이면 G4 재압축) | `helpers.copy_tiff(group4=)` ✅ |
| `TIFFSPLIT`, `CONVERT`, `GSCMD` | 팩스 주석 달기(쪽 나누기→글자 넣기→PDF) | `helpers.annotate_fax`(Pillow) ✅ |
| `TIFFPS`+`GSR`, `HYLATIFF2PS` | TIFF→PDF | libtiff `tiff2pdf`, 없으면 Pillow. `HYLATIFF2PS`(HylaFAX 동봉 `bin/tiff2pdf`)는 쓰지 않는다. G6 처리 ✅ |
| `GSCMD`, `TIFFPS`, `GSR` | 보내기 파일 합치기(`convert2pdf`) | `helpers.convert2pdf` ✅ (G6) |
| `GSN`, `GSN2`, `PNMSCALE`, `PNMDEPTH`, `PPMTOGIF`, `PNMQUANT` | 쪽 이미지·썸네일(GIF) | `services/fax_images`(Ghostscript+Pillow, PNG). GIF→PNG는 의도한 차이 ✅ |
| `PRINTFAXCMD` | 받은 팩스 인쇄 | `services/printing.py`(`PRINTFAX2PS`, `PRINTCMD`, `PDFPRINTCMD`) ✅ |
| `PSRESIZE`, `GSTIFF`, `DPIS` | 정의만 있고 레거시 코드 어디에서도 쓰이지 않음(죽은 변수) | 이식하지 않음 |
| `HAS_MIME_FUNCTION`, `HAS_FILEINFO`, `HAS_NEGATIVE_TIFF` | PHP 확장 유무 판정 | 해당 없음 |

**JavaScript 대조** (레거시 `js/` 12개 파일)

| 레거시 | 이식본 |
|---|---|
| `ajaxbook.js`, `archivebook.js`, `emailbook.js`, `faxcontacts.js`, `dlcontacts.js` (업체·연락처 실시간 필터, 선택 창에서 값 넣기, 표지 자동 채우기) | `livefilter.js`, 선택 창 스크립트, `/ajax/prefillto` ✅ |
| `ajaxmodemstatus.js` (20초마다 모뎀 상태) | `notify.js` ✅ |
| `multifile_upload.js` (여러 파일 목록) | `sendfax.js` ✅ |
| `sendfax_coverpage.js` (표지 접기) | `sendfax.js` ✅ (`SENDFAX_USE_COVERPAGE` 반영) |
| `avantfax.js`: `checkInbox`·`performInboxCheck` | `notify.js` ✅ (G2, G5) |
| `avantfax.js`: `previewImage` | `archive.js` ✅ (G3) |
| `avantfax.js`: `selectAllFaxes`, `getSelectedFaxIDs` | 수신함 일괄 선택·처리 ✅ |
| `avantfax.js`: `changeDisplayedFax`, `showNextImage`, `showDisplayedFax` (팩스 보기의 쪽 넘김) | `viewfax.jinja2` 안의 스크립트 ✅ (페이드 효과만 없음) |
| `avantfax.js`: `highlightrow`, `imageRoll` | Tailwind `hover:`로 대체(표시 효과뿐) |
| `avantfax.js`: `mkwin`·`mknoteswin`·`mkpdfwin`, `dialog.js`의 `dialogDeleteFax`·`archiveFax`·`dialogNote`·`dialogFaxAlter` 등 | 페이지형 대화상자(의도한 차이). 레거시는 보관·삭제 뒤 행을 화면에서 지우고 건수를 줄이며(`removeFaxDIV`, `decFaxCount`) 이식본은 화면을 다시 불러온다 |
| `xhrobject.js`, `scriptaculous-js` | 해당 없음(`fetch`와 CSS 효과로 대체) |
| `avantfax.js`: `newfax`, `gotoInbox`, `serialize_array`, `preloadImg`, `basename` | 보조 함수(`newfax`는 호출하는 곳을 찾지 못함) |
| `PN_PAGE_UP`·`PN_PAGE_DN`, `ADMIN_STATS`, `ADMIN_ROUTEBY_KEYWORD` 문구 | 레거시에서도 쓰이지 않는 문구 |

**확인하지 못한 것**

- 실제 HylaFAX 연동(훅, `faxstat` 파싱, 사용자 동기화)과 큰 `FaxArchive`의 첫 기동 시간. 실서버가 없어서 이번 대조에서 제외했다.
- 화면 레이아웃과 스타일의 시각 대조(스크린샷 비교).
- JavaScript는 함수와 동작 단위로 대조했고, 이식본의 클라이언트 동작은 Node에서 가짜 DOM으로 실행해 검증했다(G2, G3, G5). 실제 브라우저에서 눈으로 확인한 것은 아니다.
- 이름으로 대응시킨 웹 진입점의 세부 동작 동일성.

## 제외(이미 결정했거나 대체됨)

SAML·패스키·TOTP·클라우드 저장소·네트워크 프린터·SMTP 관리(새 기능), 한국어 외 번역 보류, 페이지형 대화상자, 변경 요청의 POST+CSRF, 레거시 CSS(Tailwind로 대체), 레거시 이미지·파비콘(모두 정적 폴더에 있음), 죽은 코드(`rubrica*.php`), 원본 DB 컬럼·인덱스(전부 대응됨), 언어 매핑(24개 대응됨), 영문 기본 `Smarty` 테마 구조.

## 권장 순서

1. **A1, B1, B2, A3, A6, A7, A8**: 지금 화면에서 곧바로 오류가 나거나 보안상 위험한 것(작고 독립적).
2. **A2/A5(페이지 나누기·필터), A4(팩스 이미지·썸네일), C1~C3(사용자 관리)**: 원본의 핵심 기능이라 영향이 크다.
3. **A9~A12, C5~C8, E1~E5**: 메일, 회선 제한, 배포 그룹, 시스템 기능, 수신 훅.
4. **D, E6~E11, F**: 알림·폴링, 설정 항목, 설치 문서.
