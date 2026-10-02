# AvantFAX 3.x에서 NamiFAX로 옮기기

AvantFAX 3.x(3.0~3.3.5, MySQL/MariaDB)를 쓰던 설치를 NamiFAX로 옮기는 방법과, 옮긴 뒤 달라 보이는 점을 정리한 문서입니다.
AvantFAX 2.x는 지원하지 않습니다(3.x 이후 DB만 대상).

## 1. 한눈에 보기

| 질문 | 답 |
|---|---|
| 기존 DB를 그대로 쓸 수 있나 | **예.** 같은 DB와 팩스 보관 폴더에 그대로 붙습니다. 사용자·모뎀·카테고리·라우팅·주소록·배포 목록·보관 팩스가 모두 남습니다. |
| 비밀번호는 | 원본의 MD5 해시로 그대로 로그인합니다. 새 비밀번호를 다시 받을 필요가 없습니다. |
| 되돌릴 수 있나 | 예. 이식본은 DB에 추가만 하고 지우거나 바꾸지 않으며(아래 4장), 원본 PHP 앱이 같은 DB를 계속 쓸 수 있습니다. |
| 달라 보이는 것 | **영문 이외 글자의 표시**(원본이 HTML 엔티티로 저장함, 4.1), 기존 팩스의 미리보기 재생성(4.2), 옛 주소, 모든 사용자의 재로그인. |
| 확인하지 못한 것 | 실제 HylaFAX 서버와의 연동, 수년치 대용량 보관소의 첫 기동 시간. |

## 2. 예행연습으로 확인한 것

"DB를 그대로 쓸 수 있다"는 합성한 시험 데이터가 아니라 **원본 PHP 앱이 실제로 만든 데이터**로 확인했습니다.
`tools/migration_rehearsal/run.sh`가 이를 처음부터 재현합니다(Docker와 네트워크 필요, 이미지가 있으면 약 15초).

1. 원본 AvantFAX 3.3.5를 PHP 5.6 + MDB2 2.4.1 + MariaDB 10.3(2013년 무렵의 비엄격 SQL 모드)에서 실행합니다.
2. 원본의 웹 화면으로 사용자 3명, 모뎀 2개, 카테고리 3개, 주소록, 이메일 주소록을 만들고, 원본의 `ArchiveIn::create()`로 팩스 6건(2건은 보관)을 기록합니다.
3. 같은 DB와 팩스 폴더에 NamiFAX를 연결하고 원본과 비교합니다.

| 확인 항목 | 결과 |
|---|---|
| 원본이 만든 세 사용자와 관리자 로그인 | 모두 성공. 원본 관리자의 옛 비밀번호는 정상적으로 거부 |
| 사용자별 수신함 목록 | 원본과 **같음**(회선·카테고리 제한 포함) |
| 사용자별 각 팩스의 PDF 열람 가능 여부(보관 팩스 포함) | 원본과 **같음** |
| 팩스 썸네일과 쪽 이미지 | 응답함(처음 볼 때 새로 생성, 4.2) |
| 원본이 쓴 주소록·이메일 연락처를 NamiFAX가 읽기 | 읽힘. 단 엔티티가 글자 그대로 보임(4.1) |
| NamiFAX가 쓴 연락처를 원본이 읽기 | 정상(한글·악센트 포함) |
| NamiFAX가 DB를 사용한 뒤 원본 앱 | 로그인, 수신함, 주소록, 보관함, 설정, 출력함이 모두 정상 |

테스트 환경은 3.3.5 한 가지입니다. 3.0~3.2.x에서 업그레이드를 거듭한 설치는 `tests/unit/test_legacy_database_compat.py`가
3.2.0 스키마(MySQL 8.4, MariaDB)로 확인하지만, 실제 업그레이드 이력이 있는 DB로 시험한 것은 아닙니다.

## 3. 이전 절차

1. **백업.** DB(`mysqldump`)와 팩스 보관 폴더를 백업합니다. 스키마 보정이 일어납니다.
2. **설정.** 아래 5장의 대응표로 `local_config.php`의 값을 환경변수로 옮깁니다. 최소한 다음이 필요합니다.
   - `DATABASE_URL` = `mysql+pymysql://사용자:비밀번호@호스트/avantfax` (원본의 `AFDB_*` 값)
   - `AVANTFAX_INSTALLDIR` = 원본 설치 디렉터리(예: `/var/www/avantfax`). DB에 상대 경로로 저장된 팩스 경로를 찾는 기준입니다.
   - `AVANTFAX_ARCHIVE` = 받은 팩스 보관 폴더(원본의 `$ARCHIVE`, 기본 `<설치 디렉터리>/faxes/recvd`)
   - `NAMIFAX_SESSION_SECRET`, `NAMIFAX_SECRET_KEY` (`docs/OPERATIONS_CHECKLIST.md` 1장)
3. **기동.** 첫 기동에서 NamiFAX가 새 테이블과 인덱스를 만듭니다. 큰 `FaxArchive`는 인덱스를 만드느라 오래 걸릴 수 있습니다.
4. **로그인.** 모든 사용자가 다시 로그인해야 합니다(PHP 세션은 이어지지 않습니다). `wasreset` 상태인 계정은 첫 로그인에서 비밀번호를 바꿉니다.
5. **HylaFAX와 cron.** 원본의 PHP 훅과 cron을 NamiFAX 명령으로 바꿉니다. `docs/INSTALL_HYLAFAX.md`, `deploy/hylafax/`(훅 스크립트와 설정 조각), `deploy/cron.d/namifax`를 보십시오.
6. **웹 서버.** 옛 주소를 새 주소로 보내는 규칙을 넣습니다(6장).
7. **SMTP.** 관리자 화면의 SMTP 설정에서 다시 입력합니다(원본의 `SMTP_*` 변수는 읽지 않습니다).

원본 PHP 앱을 한동안 함께 돌려도 됩니다(같은 DB). 다만 이 병행 운영은 위 예행연습의 읽기·쓰기 범위에서만 확인했습니다.

## 4. 달라 보이는 점과 한계

### 4.1 영문 이외 글자가 HTML 엔티티로 보입니다 (알려진 문제)

원본은 이름 같은 텍스트를 **HTML 엔티티로 저장**했습니다. 예행연습에서 원본이 만든 값은 다음과 같았습니다.

| 입력 | DB에 저장된 값 | 원본 화면 | NamiFAX 화면 |
|---|---|---|---|
| Müller & Söhne GmbH | `M&uuml;ller &amp; S&ouml;hne GmbH` | Müller & Söhne GmbH (브라우저가 변환) | `M&uuml;ller &amp; S&ouml;hne GmbH` |
| Soporte Línea | `Soporte L&iacute;nea` | Soporte Línea | `Soporte L&iacute;nea` |
| 사용자 이름의 한글 | 이중 인코딩되어 깨진 값(`ÃªÂ¹â‚¬`) | (원본도 깨져 보임) | 같음 |

원본은 HTML에 값을 그대로 출력해서 브라우저가 엔티티를 글자로 그렸고, NamiFAX는 안전하게 이스케이프해서 **엔티티가 글자 그대로 보입니다.**
한글·일본어 같은 비라틴 문자는 대부분 그대로 저장되어 영향이 없지만, 유럽 언어의 악센트 문자와 `&`가 있는 이름은 영향을 받습니다.
NamiFAX가 새로 쓰는 값은 순수 UTF-8이고 원본 앱에서도 정상으로 보입니다. 이 문제의 처리 방법은 아직 정하지 않았습니다
(표시할 때 풀기, DB의 값을 한 번 변환하기 등).
`tools/migration_rehearsal/check_text.py --strict`가 이 문제를 점검합니다.

### 4.2 기존 팩스의 미리보기

원본이 만든 `thumb.gif`와 `prev*.gif`는 쓰지 않습니다. NamiFAX는 처음 볼 때 Ghostscript로 `thumb.png`와 `page*.png`를 **팩스 폴더 안에** 새로 만듭니다
(원본 파일은 그대로 둡니다). 따라서 웹 서버 사용자가 팩스 폴더에 쓸 수 있어야 하고 Ghostscript가 설치되어 있어야 합니다.
보관함 첫 화면은 최대 한 쪽 분량(기본 30건)을 한꺼번에 변환합니다. 미리 만들려면 `namifax create-thumbnails`를 쓰십시오.

### 4.3 NamiFAX가 DB에 추가하는 것 (원본 PHP 앱에 영향 없음)

- 새 테이블 6개: `SystemConfig`, `SystemSettings`, `NetworkPrinters`, `UserTOTP`, `UserWebAuthnCredentials`, `FaxOCR`(과 `alembic_version`)
- 검색용 인덱스 12개
- `AddressBook`에 컬럼 10개 추가, `UserAccount.last_ip`의 길이를 15자에서 45자로 확장(IPv6)
- 기존 행은 지우거나 바꾸지 않습니다. 기본 카테고리와 표지는 기존 DB에 추가하지 않습니다.

### 4.4 그 밖의 차이

- 비밀번호 길이는 원본과 같게 8~15자입니다(`MIN_PASSWD_SIZE`, `MAX_PASSWD_SIZE`로 바꿀 수 있음).
- 화면은 Tailwind CSS로 새로 만든 것입니다. 원본의 테마와 `custom.css`는 지원하지 않습니다.
- 대화상자는 별도 창이 아니라 페이지입니다. 변경 요청(삭제, 보관 등)은 POST와 CSRF 토큰이 필요하므로, 외부 스크립트가 원본의 `ajax/*.php?fid=…`를 GET으로 부르던 방식은 동작하지 않습니다.
- 수신함·보관함의 날짜는 고정 형식으로 표시합니다(원본의 `ARCHIVE_DATE_FORMAT` 설정은 없음).
- 한국어 외의 번역은 부분적입니다. 실제로 번역되어 보이는 문구는 한국어 외 로케일에서 695개 중 약 240~255개(약 35%)이고 나머지는 영어입니다.

## 5. `local_config.php` 설정 대응표

원본의 `local_config.php`는 읽지 않습니다. 같은 이름의 **환경변수**로 지정합니다(systemd라면 `Environment=` 또는 `EnvironmentFile=`).
켜고 끄는 값은 `1` 또는 `true`가 켜짐입니다(PHP의 `true`/`false`를 그대로 쓰지 마십시오). 미지정이면 기본값을 따르고, 대부분 원본과 같게 맞췄지만 일부는 다릅니다(`docs/PORTING_GAPS.md` E6, E7).

### 5.1 같은 이름으로 지정하는 것

| 구분 | 변수 (괄호는 확인한 기본값) |
|---|---|
| 화면 동작 | `SHOW_ALL_CONTACTS`(켜짐), `RESTRICTED_USER_MODE`, `INBOX_LIST_MODEM`, `FOCUS_ON_NEW_FAX`, `FOCUS_ON_NEW_FAX_POPUP`, `SENDFAX_USE_COVERPAGE`(켜짐), `SENDFAX_REQUEUE_EMAIL`(켜짐), `ENABLE_DL_TIFF`, `SHOWSERVER_DETAILS`, `WHITEPAGES` |
| 쪽 크기·길이 제한 | `DEFAULT_FAXES_PER_PAGE_INBOX`(25), `DEFAULT_FAXES_PER_PAGE_ARCHIVE`(30), `MAX_USERNAME_SIZE`(15), `MAX_PASSWD_SIZE`(15), `MIN_PASSWD_SIZE`(8), `MAX_EMAIL_SIZE`(99) |
| 라우팅·인식 | `ENABLE_DID_ROUTING`, `AUTOCONFDID`, `ENABLE_BARDECODE_SUPPORT`, `BARDECODE_BINARY`, `BARDECODE_COMMAND`, `ENABLE_OCR_SUPPORT`, `OCR_BINARY`, `OCR_COMMAND`, `OCR_LANGUAGE`, `CALLIDN_CIDNUMBER`, `CALLIDN_CIDNAME`, `CALLIDN_DIDNUM` |
| 수신·알림 | `ARCHIVEFAX2EMAIL`, `FAXRCVD_INCLUDE_PDF`, `FAXRCVD_INCLUDE_THUMBNAIL`, `FAXRCVD_PRINT_PDF`, `NOTIFY_INCLUDE_PDF`, `NOTIFY_ON_SUCCESS`, `PRINTFAXRCVD`, `PRINTERNAME`, `PRINTCMD`, `PRINTFAX2PS`, `PDFPRINTCMD`, `TIFF_TO_G4`, `ENABLE_FAX_ANNOTATION`, `ANN_GRAVITY` |
| 표지·보내기 | `COVERPAGE_FILE`, `COVERPAGE_MATCH`, `USE_HTML_COVERPAGE`, `NUM_PAGES_FOLLOW`, `CPAGE_LINELEN`, `FAXCOVER_DATE_FORMAT`, `EMAIL_DATE_FORMAT`, `EMAIL_ENCODING_TEXT`, `EMAIL_ENCODING_HTML`, `EMAIL_ENCODING_CHARSET`, `FROM_COMPANY`, `FROM_LOCATION`, `FROM_VOICENUMBER`, `FROM_FAXNUMBER`, `DEFAULT_TSI_ID` |
| 변환 | `PAPERSIZE`(a4), `DPI`(200), `PREV_TN`(80), `PREV_SP`(750) |
| 경로·실행 파일 | `HYLASPOOL`, `HYLAFAX_PREFIX`, `BINARYDIR`(도구 이름으로도 지정: `SENDFAX`, `FAXSTAT` 등), `PHONEBOOK`, `ARCHIVE_SENT`, `WWWUSER`(원본은 `apache`, 이식본의 기본은 Debian의 `www-data`), `SUDO` |
| 인증 | `ALTERNATE_AUTH_ENABLE`, `ALTERNATE_AUTH_CLASS`, `ALTERNATE_AUTH_FALLBACK`, `WEBSERVER_AUTH`, `PWAUTHPATH` |

날짜 형식은 문법이 다릅니다. 원본의 `ARCHIVE_DATE_FORMAT`은 MySQL 형식(`%i`가 분)이고 NamiFAX의 `EMAIL_DATE_FORMAT`과 `FAXCOVER_DATE_FORMAT`은 파이썬 형식(`%M`이 분)입니다. 값을 그대로 옮기지 마십시오.

### 5.2 이름이 바뀌거나 다른 곳에서 설정하는 것

| 원본 | NamiFAX |
|---|---|
| `AFDB_ENGINE`, `AFDB_HOST`, `AFDB_USER`, `AFDB_PASS`, `AFDB_NAME` | `DATABASE_URL`(예: `mysql+pymysql://user:pw@host/avantfax`) |
| `$INSTALLDIR`, `$ARCHIVE`, `$TMPDIR` | `AVANTFAX_INSTALLDIR`, `AVANTFAX_ARCHIVE`, `AVANTFAX_TMPDIR` |
| `$RESERVED_FAX_NUM` | `AVANTFAX_RESERVED_FAX_NUM` |
| `$AVANTFAX_SERVERNAME` | `AVANTFAX_SERVERNAME` |
| `SF_MAXSIZE`, `SF_FILESIZE`(업로드 크기) | `NAMIFAX_MAX_UPLOAD_BYTES`(바이트) |
| `USE_SMTPSERVER`, `SMTP_SERVER`, `SMTP_PORT`, `SMTP_AUTH`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SYSTEM_EMAIL_SIG_TEXT`, `SYSTEM_EMAIL_SIG_HTML` | **관리자 화면의 SMTP 설정**(DB에 저장, 비밀번호는 `NAMIFAX_SECRET_KEY`로 암호화) |

### 5.3 필요 없는 것

- 테마와 플러그인: `ADMINTHEME_DIR`, `ADMIN_THEME_PATH`, `USERTHEME_DIR`, `USER_THEME_PATH`, `PLUGINS_DIR`, `PLUGINS_PATH`, `ARCHIVE_WIDE`, `NOTHUMBIMG`
- 변환 도구: `CONVERT`, `TIFFCP`, `TIFFCPG4`, `TIFFPS`, `TIFFSPLIT`, `GSR`, `GSN`, `GSN2`, `GSTIFF`, `GSCMD`, `PNMSCALE`, `PNMDEPTH`, `PPMTOGIF`, `PNMQUANT`, `PSRESIZE`, `DPIS`, `HYLATIFF2PS` (Ghostscript와 Pillow 등으로 대체됨, `docs/PORTING_GAPS.md` G절)
- PHP 환경: `HAS_MIME_FUNCTION`, `HAS_FILEINFO`, `HAS_NEGATIVE_TIFF`, `AVANTFAX_DEBUG`, `AVANTFAX_VERSION`, `USERSESSION`
- 화면 문구에만 쓰이던 것: `CONTACTFILETYPES`, `SENDFAXFILETYPES`, `SYSTEM_IP`(새 사용자 메일의 주소는 요청 주소를 씁니다)

## 6. 웹 서버에서 옛 주소를 새 주소로 보내기

북마크와 외부 링크가 깨지지 않게 하려면 **웹 서버에서** 영구 이동(301)을 설정합니다. 애플리케이션이 아니라 웹 서버의 일이어서 NamiFAX 코드에는 넣지 않았습니다.
규칙은 `deploy/legacy-redirects/`에 있고, Apache와 nginx에서 각각 실제 서버로 17개 주소를 시험했습니다.

- Apache: `apache.conf`를 `deploy/apache/namifax.conf`의 `<VirtualHost>` 안, `ProxyPass` 앞에 `Include`합니다(`mod_rewrite` 필요).
- nginx: `nginx.conf`를 `server` 블록 안, `location /` 앞에 `include`합니다.

| 옛 주소 | 새 주소 |
|---|---|
| `/inbox.php?pageindex=2` | `/inbox?pageindex=2` (쿼리 문자열은 그대로 유지) |
| `/index.php` | `/login` |
| `/addressbook_edit.php?abook_id=5` | `/addressbook/edit?abook_id=5` |
| `/pdf.php?fid=12` | `/faxes/download/12?format=pdf` |
| `/refax.php?fid=12` | `/sendfax?refax=12` |
| `/admin/conf_modems_edit.php?devid=1` | `/admin/modems?devid=1` |
| `/admin/users.php?uid=4` | `/admin/users?uid=4` |

사람이 여는 화면만 다룹니다. 원본의 `ajax/*.php`와 `file.php`는 화면이 스스로 부르는 주소여서 규칙에 없습니다.
`tests/unit/test_legacy_redirects.py`가 규칙의 도착 주소가 앱에 실제로 있는지 지켜봅니다.

## 7. 사용자에게 알릴 것

- 처음 한 번 다시 로그인해야 합니다.
- 화면 모양과 대화상자가 바뀌었습니다. 기능과 권한 규칙은 같습니다.
- 이름에 악센트가 있는 항목이 `&uuml;`처럼 보일 수 있습니다(4.1, 처리 방법 결정 전).
- 비밀번호 찾기, 2단계 인증(TOTP), 패스키는 새 기능입니다.
