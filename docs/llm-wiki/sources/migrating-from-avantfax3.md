---
title: AvantFAX 3.x에서 NamiFAX로 옮기기
type: source
updated: 2026-10-02
sources: [docs/MIGRATING_FROM_AVANTFAX3.md]
verified: false
---

## 요약

AvantFAX 3.x(3.0~3.3.5, MySQL/MariaDB)를 NamiFAX로 옮기는 방법 및 이전 후 달라 보이는 점. AvantFAX 2.x는 미지원. 기존 DB와 팩스 보관 폴더를 그대로 사용 가능하며, 원본 PHP 앱과 함께 운영 가능(읽기·쓰기 범위 내). 비밀번호 해시는 원본 MD5로 로그인하고, 로그인 성공 시 Argon2id로 업그레이드. 예행연습으로 실제 원본 PHP 데이터와의 호환성 확인함.

## 핵심 내용

### 1장: 한눈에 보기

| 질문 | 답변 | 비고 |
|---|---|---|
| 기존 DB를 그대로 쓸 수 있나 | **예** | 같은 DB와 팩스 보관 폴더에 붙음. 사용자·모뎀·카테고리·라우팅·주소록·배포 목록·보관 팩스 모두 유지 |
| 비밀번호는 | 원본의 MD5로 그대로 로그인. **로그인 성공 시 Argon2id로 업그레이드** | 새 비밀번호 재발급 불필요 |
| 되돌릴 수 있나 | 조건부 예 | 이식본은 DB에 추가만 하고 지우거나 바꾸지 않음. 원본과 함께 운영 가능하되, 이식본에서 로그인한 계정은 원본이 읽지 못하는 Argon2id 해시가 됨. 되돌릴 가능성 열어둘 때는 `NAMIFAX_PASSWORD_HASH=md5` 설정 권장 |
| 달라 보이는 것 | 기존 팩스의 미리보기 재생성, 옛 주소, 모든 사용자 재로그인 | 원본이 HTML 엔티티로 저장한 글자는 풀어서 보여줌(같게 보임) |
| 확인하지 못한 것 | 실제 HylaFAX, 수년치 대용량 보관소의 첫 기동 시간 | - |

### 2장: 예행연습으로 확인한 것

**재현 방법**: `tools/migration_rehearsal/run.sh`(원본 소스 필요: `git checkout 9408385 -- legacy`. Docker와 네트워크 필요. 이미지 있으면 약 15초)

**절차**:
1. 원본 AvantFAX 3.3.5를 PHP 5.6 + MDB2 2.4.1 + MariaDB 10.3(2013년 무렵 비엄격 SQL 모드)에서 실행
2. 원본의 웹 화면으로 사용자 3명, 모뎀 2개, 카테고리 3개, 주소록, 이메일 주소록 생성 후, 원본의 `ArchiveIn::create()`로 팩스 6건(2건 보관) 기록
3. 같은 DB와 팩스 폴더에 NamiFAX 연결해 원본과 비교

**확인 항목과 결과**:
- 원본이 만든 세 사용자와 관리자 로그인: 모두 성공. 원본 관리자의 옛 비밀번호는 정상적으로 거부
- 사용자별 수신함 목록: 원본과 **같음**(회선·카테고리 제한 포함)
- 사용자별 각 팩스의 PDF 열람 가능 여부(보관 팩스 포함): 원본과 **같음**
- 팩스 썸네일과 쪽 이미지: 응답함(처음 볼 때 새로 생성)
- 원본이 쓴 주소록·이메일 연락처를 NamiFAX가 읽기: 읽힘. 엔티티는 풀려서 글자로 보임
- NamiFAX가 쓴 연락처를 원본이 읽기: 정상(한글·악센트 포함)
- NamiFAX가 DB 사용 뒤 원본 앱: 로그인, 수신함, 주소록, 보관함, 설정, 출력함 모두 정상

**스키마 호환성**: 테스트는 3.3.5 한 가지. 3.0~3.2.x에서 업그레이드 거듭한 설치는 `tests/unit/test_legacy_database_compat.py`가 3.2.0 스키마(MySQL 8.4, MariaDB)로 확인하지만, 실제 업그레이드 이력 있는 DB는 시험 미완료

### 3장: 이전 절차

1. **백업**: DB(`mysqldump`)와 팩스 보관 폴더 백업. 스키마 보정 발생
2. **설정**: `local_config.php`의 값을 환경변수로 옮김 (5장 대응표 참고)
   - 최소 필수: `DATABASE_URL`, `AVANTFAX_INSTALLDIR`, `AVANTFAX_ARCHIVE`, `NAMIFAX_SESSION_SECRET`, `NAMIFAX_SECRET_KEY`
3. **기동**: 첫 기동에서 NamiFAX가 새 테이블과 인덱스 생성. 큰 `FaxArchive`는 인덱스 생성에 오래 걸릴 수 있음
4. **로그인**: 모든 사용자 재로그인 필요(PHP 세션은 이어지지 않음). `wasreset` 상태인 계정은 첫 로그인에서 비밀번호 변경
5. **HylaFAX와 cron**: 원본의 PHP 훅과 cron을 NamiFAX 명령으로 변경. `docs/INSTALL_HYLAFAX.md`, `deploy/hylafax/`, `deploy/cron.d/namifax` 참고
6. **웹 서버**: 옛 주소를 새 주소로 보내는 규칙 추가(6장)
7. **SMTP**: 관리자 화면의 SMTP 설정에서 다시 입력(원본의 `SMTP_*` 변수는 읽지 않음)

**병행 운영**: 원본 PHP 앱을 한동안 함께 돌려도 됨(같은 DB). 다만 이 병행 운영은 위 예행연습의 읽기·쓰기 범위에서만 확인됨

### 4장: 달라 보이는 점과 한계

#### 4.1 원본이 HTML 엔티티로 저장한 글자
원본은 이름 같은 텍스트를 **HTML 엔티티로 저장**(모든 폼 값을 `htmlentities(ENT_QUOTES, "UTF-8")`에 통과)

예시:
- 입력: `Müller & Söhne GmbH` → DB: `M&uuml;ller &amp; S&ouml;hne GmbH`
- 입력: `O'Brien "Bob"` → DB: `O&#039;Brien &quot;Bob&quot;`

원본은 값을 HTML에 그대로 출력해 브라우저가 글자로 그렸지만, NamiFAX는 **읽을 때 엔티티를 풀어서** 같은 글자를 보여줌(`models/types.py`의 `LegacyHtmlString`, `LegacyHtmlText`). DB는 건드리지 않으므로 되돌리기에 영향 없음. NamiFAX가 새로 쓰는 값은 순수 UTF-8

**검색**: 입력한 단어와 원본 저장 형태를 모두 비교(`müller`로 `M&uuml;ller` 찾음). 대소문자 구분 안 함

**한계**:
- 원본이 **이중 인코딩**해서 깨뜨린 값은 복원 불가(예: 한글이 `ÃªÂ¹â‚¬`처럼 저장됨. 원본 화면에서도 깨져 보임)
- 사용자가 `&uuml;`처럼 엔티티 모양을 **글자 그대로** 입력하면 풀려서 `ü`로 보임(드문 경우)
- 이름의 중복 검사는 저장된 값끼리 비교하므로 일부 경계 케이스 가능(추론. 시험 미완료)
- 예행연습은 PHP 5.6만 봤으므로 더 오래된 PHP는 저장 방식이 다를 수 있음

`tools/migration_rehearsal/check_text.py --strict`가 원본 데이터로 점검

#### 4.2 기존 팩스의 미리보기
원본의 `thumb.gif`·`prev*.gif` 미사용. NamiFAX는 처음 볼 때 Ghostscript로 `thumb.png`와 `page*.png`를 **팩스 폴더 안에** 새로 생성(원본 파일은 그대로). 웹 서버 사용자가 팩스 폴더에 쓸 수 있어야 하고 Ghostscript 설치 필수. 보관함 첫 화면은 최대 한 쪽(기본 30건)을 한꺼번에 변환. 미리 만들려면 `namifax create-thumbnails` 사용

#### 4.3 NamiFAX가 DB에 추가하는 것 (원본 PHP 앱에 영향 없음)
- 새 테이블 6개: `SystemConfig`, `SystemSettings`, `NetworkPrinters`, `UserTOTP`, `UserWebAuthnCredentials`, `FaxOCR`(+ `alembic_version`)
- 검색용 인덱스 12개
- `AddressBook`에 컬럼 10개 추가
- `UserAccount.last_ip` 길이를 15자에서 45자로 확장(IPv6)
- 기존 행은 지우거나 바꾸지 않음. 기본 카테고리와 표지는 기존 DB에 추가 안 함

#### 4.4 그 밖의 차이
- 비밀번호 길이: 원본과 같게 8~15자(`MIN_PASSWD_SIZE`, `MAX_PASSWD_SIZE`로 변경 가능)
- 화면: Tailwind CSS로 새로 만듦. 원본의 테마와 `custom.css` 미지원
- 대화상자: 별도 창 아님. 페이지. 변경 요청(삭제, 보관 등)은 POST와 CSRF 토큰 필요. 원본의 `ajax/*.php?fid=…` GET 방식 동작 안 함
- 수신함·보관함의 날짜: 고정 형식(원본의 `ARCHIVE_DATE_FORMAT` 설정 없음)
- 번역: 한국어 외는 부분적. 695개 문구 중 번역됨 292~333개(약 42~47%), 나머지는 영어. 원본과 같은 뜻 문구는 원본의 영어 원문 사용하고 원본 번역 가져옴

#### 4.3(재) 비밀번호 해시 (Argon2id)
- 이식본은 **Argon2id로 저장**(솔트 포함, 비용은 `NAMIFAX_ARGON2_TIME_COST`·`_MEMORY_COST`·`_PARALLELISM`로 조정)
- 원본의 MD5(32자리)는 계속 확인. **그 계정이 이식본에 로그인하는 순간** Argon2id로 변경. 로그인 안 한 계정은 MD5 그대로
- `UserAccount.password`와 `UserPasswords.pwdhash`는 마이그레이션 0026이 255자로 확장(원본은 `VARCHAR(32)`)
- **원본 PHP는 Argon2id를 읽지 못함**. 이식본 로그인 계정은 원본으로 돌아가면 로그인 불가. 비밀번호 찾기로 새로 받아야 함
- 병행 운영: `NAMIFAX_PASSWORD_HASH=md5`로 두면 새 비밀번호도 원본 형식. 전환 확정 후 설정 삭제

### 5장: `local_config.php` 설정 대응표

원본의 `local_config.php`는 읽지 않음. 같은 이름의 **환경변수**로 지정(systemd라면 `Environment=` 또는 `EnvironmentFile=`). 켜고 끄는 값은 `1` 또는 `true` 켜짐(PHP `true`/`false` 직접 사용 금지). 미지정이면 기본값. 일부는 원본과 다름(`docs/PORTING_GAPS.md` E6, E7)

**같은 이름으로 지정하는 것**:
- 화면 동작: `SHOW_ALL_CONTACTS`, `RESTRICTED_USER_MODE`, `INBOX_LIST_MODEM`, `FOCUS_ON_NEW_FAX`, 등
- 쪽 크기·길이 제한: `DEFAULT_FAXES_PER_PAGE_INBOX`, `DEFAULT_FAXES_PER_PAGE_ARCHIVE`, 등
- 라우팅·인식: `ENABLE_DID_ROUTING`, `AUTOCONFDID`, `BARDECODE_BINARY`, 등
- 수신·알림: `ARCHIVEFAX2EMAIL`, `FAXRCVD_INCLUDE_PDF`, `PRINTERNAME`, 등
- 표지·보내기: `COVERPAGE_FILE`, `COVERPAGE_MATCH`, `FROM_COMPANY`, 등
- 변환: `PAPERSIZE`, `DPI`, `PREV_TN`, `PREV_SP`
- 경로·실행 파일: `HYLASPOOL`, `BINARYDIR`, `PHONEBOOK`, `WWWUSER`, 등
- 인증: `ALTERNATE_AUTH_ENABLE`, `WEBSERVER_AUTH`, `PWAUTHPATH`

**이름이 바뀌거나 다른 곳에서 설정하는 것**:
- `AFDB_*` → `DATABASE_URL`
- `$INSTALLDIR`, `$ARCHIVE`, `$TMPDIR` → `AVANTFAX_INSTALLDIR`, `AVANTFAX_ARCHIVE`, `AVANTFAX_TMPDIR`
- `SMTP_*` → **관리자 화면의 SMTP 설정**(DB에 저장, 비밀번호는 `NAMIFAX_SECRET_KEY`로 암호화)

**필요 없는 것**:
- 테마와 플러그인: `ADMINTHEME_DIR`, `PLUGINS_DIR` 등
- 변환 도구: `CONVERT`, `TIFFCP`, `GSR` 등(Ghostscript와 Pillow로 대체)
- PHP 환경: `HAS_MIME_FUNCTION`, `AVANTFAX_DEBUG` 등

**날짜 형식**: 문법이 다름. 원본 MySQL 형식(`%i`가 분), NamiFAX 파이썬 형식(`%M`이 분). 값을 그대로 옮기지 마십시오

### 6장: 웹 서버에서 옛 주소를 새 주소로 보내기

북마크와 외부 링크 보존 위해 **웹 서버에서** 영구 이동(301) 설정. 규칙은 `deploy/legacy-redirects/`에 있음. Apache와 nginx에서 17개 주소 시험 완료

**예시**:
- `/inbox.php?pageindex=2` → `/inbox?pageindex=2`
- `/index.php` → `/login`
- `/pdf.php?fid=12` → `/faxes/download/12?format=pdf`
- `/admin/conf_modems_edit.php?devid=1` → `/admin/modems?devid=1`

`tests/unit/test_legacy_redirects.py`가 규칙의 도착 주소 존재 여부 감시

### 7장: 사용자에게 알릴 것
- 처음 한 번 다시 로그인 필요
- 화면 모양과 대화상자 변경. 기능과 권한 규칙은 같음
- 비밀번호 찾기, 2단계 인증(TOTP), 패스키는 새 기능

## 문서가 주장하는 수치·상태

- **예행연습 테스트 대상**: 3.3.5 한 가지. 3.0~3.2.x 업그레이드 이력 있는 DB는 `tests/unit/test_legacy_database_compat.py`의 테스트로만 확인, 실제 데이터 시험 미완료
- **호환성 확인 항목**: 사용자 로그인, 수신함 목록, PDF 열람, 썸네일, 주소록, 보관함 모두 **원본과 일치**
- **번역 커버리지**: 695개 문구. 한국어 빠진 것 0개(테스트 보장). 기타 언어 292~333개(약 42~47%) 번역
- **마이그레이션 재현 시간**: Docker 이미지 있으면 약 15초
- **비밀번호 해시 업그레이드**: 로그인 시점에만 발생
- **리다이렉트 규칙**: Apache와 nginx에서 17개 주소 시험 완료

## 낡았을 가능성이 큰 부분

- **`tools/migration_rehearsal/` 삭제됨**: 실제 예행연습을 재현할 수 없음(커밋 72a7324에서 `dev/` 제거). git에서 복원 가능하지만 원본 PHP 소스도 필요
- **실제 대용량 DB의 첫 기동 시간**: 문서에서 "오래 걸릴 수 있습니다"만 기술. 시간 측정 미완료로 인해 계획 수립 어려움
- **3.0~3.2.x 업그레이드 이력 DB**: `test_legacy_database_compat.py`로 3.2.0 스키마만 확인. 실제 데이터로 시험 미완료
- **날짜 형식 문법**: 원본과 NamiFAX 문법이 다르다는 지적이 있지만, 호환성 확인 불충분할 수 있음
- **비밀번호 찾기 이중 인코딩**: 원본이 깨뜨린 값은 복원 불가라는 기술이지만, 이것이 얼마나 흔한 문제인지 미측정
- **중복 검사 경계 케이스**: 엔티티 저장 값으로 인한 중복 검사 문제는 "추론이며 시험하지 않았습니다"로 표기

## 관련 주제 페이지

[[database-and-migrations]] [[operations-and-deployment]] [[migration-from-avantfax]] [[authentication-and-security]] [[i18n-and-ui]]
