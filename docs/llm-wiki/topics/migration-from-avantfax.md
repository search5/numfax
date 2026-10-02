---
title: AvantFAX 3.x 에서 옮기기
type: topic
updated: 2026-10-02
sources: [src/namifax/models/types.py, src/namifax/common/passwords.py, src/namifax/common/settings.py, src/namifax/db/provider.py, src/namifax/db/bootstrap.py, src/namifax/alembic/versions/20261002_0026_password_hash_width.py, src/namifax/cli/import_archive.py, src/namifax/main.py, deploy/legacy-redirects/nginx.conf, deploy/legacy-redirects/apache.conf, tests/unit/test_legacy_redirects.py, tests/unit/test_legacy_database_compat.py, tests/unit/test_legacy_html_entities.py, tests/fixtures/legacy_sql/, tools/migration_rehearsal/, "[[migrating-from-avantfax3]]", "[[install-hylafax]]", "[[operations-checklist]]", "[[porting-gaps]]"]
verified: true
---

기존 AvantFAX 3.x(MySQL/MariaDB) DB 와 팩스 보관 폴더를 NamiFAX 로 이어 쓰는 방법과 규칙. 근거 문서는 [[migrating-from-avantfax3]] 이고 코드와 대조했다.
관련: [[database-and-migrations]] [[authentication-and-security]] [[operations-and-deployment]] [[i18n-and-ui]] [[known-gaps-and-decisions]] [[overview]].

## 0. 먼저 알아둘 것
- [코드] 원본 PHP 소스(`legacy/`)는 현재 저장소에 없다. 원본 설치 SQL 두 개(`create_tables.sql`, `db-update-334.sql`)만 시험 자료로 `tests/fixtures/legacy_sql/` 에 남아 있다. 원본 전체는 `git show 9408385:legacy/...` 또는 `git checkout 9408385 -- legacy` 로 복원한다. `9408385` 는 `git cat-file -t` 로 커밋임을 확인했고 그 트리에 `legacy/avantfax`, `legacy/create_tables.sql` 등이 있다. 삭제 커밋은 `083920e`.
- [코드] AvantFAX 2.x 는 지원하지 않는다(문서 주장). 3.0~3.3.5 를 대상으로 한다.
- [문서] 실제 HylaFAX 와 수년치 대용량 보관소의 첫 기동 시간은 확인하지 못했다.

### 0.1 이전 연습 도구 `tools/migration_rehearsal/` 의 현재 상태
> 모순: [[install-hylafax]] 와 [[migrating-from-avantfax3]] 요약 페이지는 이 디렉터리가 "삭제됨(커밋 72a7324)"이라고 쓴다. 실제로는 **삭제되지 않았다**. `git ls-files tools` 가 `Dockerfile`, `check_text.py`, `make_faxes.py`, `parity.py`, `php-quiet.ini`, `populate_legacy.py`, `register_faxes.php`, `run.sh`, `two_way.py` 9개를 보여 주고 작업 트리에도 있다 [코드]. 72a7324 는 `golden_master`, `specs`, `prompts` 를 `dev/` 로 옮긴 커밋이고 `dev/` 는 01f2f64 에서 지워졌다. `tools/` 는 마지막으로 `083920e`(legacy 삭제 커밋)에서도 건드려지지 않았다.

- [코드] 그러나 **그대로는 실행되지 않는다.** `tools/migration_rehearsal/run.sh` 는 `$ROOT/legacy/avantfax/.` 를 복사하고 `$ROOT/legacy/create_tables.sql`, `db-update-330/334/335.sql` 을 읽는다. 지금은 `legacy/` 가 없다. 실행하려면 먼저 `git checkout 9408385 -- legacy` 로 원본을 되살려야 한다(스크립트 주석과 문서가 같은 방법을 안내). 실행하지는 않았다(Docker와 네트워크가 필요하고, 이 세션은 상태를 바꾸는 실행을 하지 않음).
- [코드] 이 도구는 PHP 5.6 + MDB2 + MariaDB 10.3(`--sql-mode=` 비엄격)에서 원본을 띄워 데이터를 채우고, NamiFAX 를 같은 DB·폴더에 붙여 `parity.py`(수신함·PDF 열람 비교), `two_way.py`(양방향 읽기·쓰기), `check_text.py`(HTML 엔티티 이름 점검)로 비교한다. 결과는 [[migrating-from-avantfax3]] 2장에 있으며, 이 세션에서 다시 돌려 검증하지 않았다 [문서].

## 1. 같은 DB·폴더를 이어 쓰는 규칙

| 항목 | 규칙 | 근거 |
|---|---|---|
| DB 주소 | `DATABASE_URL`(없으면 `AFDB_URL`, 그다음 `NAMIFAX_DB_PATH`) 을 원본 DB 로 지정 | [코드] `src/namifax/db/provider.py` |
| 보관 폴더 | `AVANTFAX_ARCHIVE`(받은), `AVANTFAX_ARCHIVE_SENT`(보낸), `AVANTFAX_INSTALLDIR`, `AVANTFAX_TMPDIR` | [코드] `common/settings.py`, `services/sysfunc.py` |
| 첫 기동 | `ensure_schema` 가 기존 원본 테이블을 "채택(adopt)"하고 Alembic 을 최신으로 올림. 새 테이블·인덱스 추가 | [코드] `db/bootstrap.py`(`adopt_existing_tables`, `upgrade_to_head`) |
| 기본 레코드 | 이미 `UserAccount` 가 있는 DB 에는 기본 카테고리·표지를 추가하지 않음(DB 가 "새것"일 때만) | [코드] `db/bootstrap.py` 의 `fresh` 판정 |
| 데모 계정 | MySQL/MariaDB/PostgreSQL 에서는 만들지 않음 | [코드] `db/bootstrap.py` |
| 되돌리기 | 이식본은 기존 행을 지우거나 바꾸지 않는다고 문서는 말함. 단 `UserAccount.password`·`UserPasswords.pwdhash` 열 폭 확장과 로그인 시 해시 변경은 있음 | [문서] + [코드] 마이그레이션 0026 |
| 백업 | 첫 기동 전에 `mysqldump` 와 보관 폴더 백업. 스키마 보정이 일어난다 | [문서] [[operations-checklist]] |

- [코드] `tests/unit/test_legacy_database_compat.py` 는 실제 MySQL·MariaDB 서버에서 3.3.5 와 3.2.0 설치 스키마로 호환을 시험하도록 작성돼 있다(`pytest.mark.serverdb`). 서버 URL 이 없으면 건너뛴다(`pyproject.toml` 의 마커 설명). 이 세션에서 실행하지 않았다.
- [코드] 새로 생기는 테이블: `SystemConfig`, `SystemSettings`, `NetworkPrinters`, `UserTOTP`, `UserWebAuthnCredentials`, `FaxOCR`(모델 `__tablename__` 에서 확인) + `alembic_version`. 문서가 말한 "6개"와 일치한다. 인덱스 12개, `AddressBook` 열 10개 추가는 개수를 직접 세지 않았다 [문서].
- [코드] 기존 보관 폴더를 DB 없이 들여오는 명령은 `namifax import-archive <폴더> <카테고리ID> [--user-id N] [--modem 장치] [--callid CallID1]` 이다(`src/namifax/cli/import_archive.py`). 같은 DB 를 이어 쓰면 이미 들어 있으므로 필요 없다. 사용자 목록 가져오기는 `namifax import-users`(탭 구분 텍스트), 블랙리스트는 `import-blacklist` 다 [코드: `main.py`].

> 모순(경미): [[migrating-from-avantfax3]] 는 비밀번호 열 원본이 `VARCHAR(32)` 라 0026 이 255자로 늘린다고 쓴다. 마이그레이션 코드는 `String(64)` 에서 `String(255)` 로 바꾼다(`alembic/versions/20261002_0026_password_hash_width.py`). 결론(Argon2id 가 들어갈 만큼 넓어짐)은 같다.

## 2. 비밀번호 해시 정책
- [코드] 새로 저장하는 비밀번호는 Argon2id 다(`common/passwords.py`: `NAMIFAX_ARGON2_TIME_COST` 등으로 비용 조정). 원본의 MD5 32자리 16진수는 계속 로그인에 인정된다(`verify_password` 가 32자리 hex 이면 MD5 비교).
- [코드] MD5 계정은 `needs_rehash` 로 판정해 **그 계정이 로그인할 때** Argon2id 로 바뀐다고 코드 주석이 설명한다(`passwords.py` 머리글). 로그인하지 않은 계정은 MD5 그대로다.
- [코드] 원본 PHP 는 Argon2id 를 읽지 못한다. 병행 운영이나 되돌릴 가능성이 있으면 `NAMIFAX_PASSWORD_HASH=md5` 로 두면 새 비밀번호도 원본 형식이 된다(`hash_password`). 전환이 확정되면 설정을 지운다 [문서].
- [코드] 비밀번호 길이 한도는 원본과 같게 8~15자이며 `MIN_PASSWD_SIZE`, `MAX_PASSWD_SIZE` 로 바꾼다(`common/settings.py`).
- [코드] `wasreset`(재설정된 계정), 만료 계정은 로그인 직후 `/pwdexpired` 에서 새 비밀번호를 정해야 로그인 쿠키가 나간다(`views/auth.py`). 관리자가 비밀번호 없이 만든 사용자는 임의 비밀번호가 생성되어 메일로 가고 `wasreset=1` 이 된다(`services/user_account.py`).

## 3. 달라 보이는 점
### 3.1 HTML 엔티티로 저장된 이름
- [코드] 원본은 폼 값을 `htmlentities(ENT_QUOTES, "UTF-8")` 를 거쳐 저장했다(`M&uuml;ller &amp; S&ouml;hne GmbH`). NamiFAX 는 **읽을 때** 완전한 엔티티(`&uuml;`, `&#039;`, `&#xFC;`)만 풀어서 보여 준다. `models/types.py` 의 `LegacyHtmlString`/`LegacyHtmlText`(`TypeDecorator`)와 `legacy_decode` 가 한다. DB 값은 건드리지 않는다.
- [코드] 검색은 입력어(`legacy_encode` 로 원본 저장 형태로 바꾼 것)와 입력 그대로를 모두 비교한다고 코드 주석이 설명한다. 대소문자 구분 안 함은 문서 주장이다 [문서].
- [코드] NamiFAX 가 새로 쓰는 값은 순수 UTF-8 이다(디코드만 하고 인코드는 검색에만 쓴다. 저장 경로는 이 세션에서 끝까지 추적하지 않았다).
- [문서] 한계: 원본이 이중 인코딩해 이미 깨진 값은 복원하지 못한다. 사용자가 `&uuml;` 라는 글자를 그대로 입력해도 `ü` 로 보인다. 중복 이름 검사의 경계 경우는 시험하지 않았다. PHP 5.6 만 확인했다.

### 3.2 기존 팩스의 미리보기
- [문서] 원본의 `thumb.gif`·`prev*.gif` 는 쓰지 않고, 처음 볼 때 Ghostscript 로 `thumb.png`, `page*.png` 를 팩스 폴더 안에 만든다. 웹 서비스 사용자가 팩스 폴더에 쓸 수 있어야 하고 Ghostscript 가 필요하다. 미리 만들려면 `namifax create-thumbnails`(명령은 [코드] `main.py` 에 있음).

### 3.3 그 밖의 차이
- [문서] 화면은 Tailwind 로 새로 만들었고 원본 테마·`custom.css` 는 지원하지 않는다. 대화상자는 별도 창이 아니라 페이지다. 변경 요청(삭제·보관 등)은 POST + CSRF 토큰이며 원본의 `ajax/*.php?fid=…` GET 방식은 동작하지 않는다. 일부 화면에서 토큰 검사가 `check_csrf_token` 으로 쓰이는 것은 확인했다 [코드: `views/auth.py`, `views/modals.py`, `views/inbox.py`].
- [코드] 변경 요청은 `Origin`/`Referer` 가 이 사이트가 아니면 403 으로 막는다(`origin_guard.py`).
- [문서] 수신함·보관함 날짜는 고정 형식(원본의 `ARCHIVE_DATE_FORMAT` 없음). 메일·표지 날짜 형식은 파이썬 형식이다(기본 `%d.%m.%Y %H:%M`, `common/settings.py`). 원본의 MySQL 형식(`%i`=분)과 문법이 달라 값을 그대로 옮기면 안 된다 [코드: 기본값 확인].
- [문서] 번역: 한국어 외에는 일부만 번역(문서 수치 695개 중 292~333개). 수치는 이 세션에서 다시 세지 않았다.

## 4. `local_config.php` 설정 대응
원본의 `local_config.php` 는 읽지 않고 **환경 변수**로 지정한다([코드]: 설정 값은 `common/settings.py` 의 `flag/text/number` 가 `os.environ` 에서 읽음). systemd 에서는 `Environment=`/`EnvironmentFile=`(저장소의 기본 단위 파일에는 `EnvironmentFile` 이 없음. [[operations-and-deployment]] 3.1).

| 원본 | NamiFAX | 근거 |
|---|---|---|
| `AFDB_*`(엔진·호스트·사용자·비밀번호·DB 이름) | `DATABASE_URL`(`AFDB_URL` 도 인정) | [코드] `db/provider.py` |
| `$INSTALLDIR`, `$ARCHIVE`, `$TMPDIR` | `AVANTFAX_INSTALLDIR`, `AVANTFAX_ARCHIVE`, `AVANTFAX_TMPDIR` | [코드] |
| `SMTP_*` | 읽지 않음. 관리자 화면의 SMTP 설정(DB 저장, 비밀번호는 `NAMIFAX_SECRET_KEY` 로 암호화) | [코드] `services/smtp_settings.py`, `common/secretbox.py` |
| `ENABLE_DID_ROUTING`, `ARCHIVEFAX2EMAIL`, `PAPERSIZE`, `DPI`, `PREV_TN`, `PREV_SP`, `HYLASPOOL`, `BINARYDIR`, `WWWUSER`, `FAXMAILUSER` 등 | 같은 이름의 환경 변수 | [코드] 전체 목록은 [[operations-and-deployment]] 2.2 |
| 테마·플러그인(`ADMINTHEME_DIR`, `PLUGINS_DIR`), 변환 도구 경로(`CONVERT`, `TIFFCP`, `GSR`), PHP 환경 | 필요 없음(Ghostscript·Pillow 로 대체) | [문서] |

- 켜고 끄는 값은 `1`/`true`/`True`/`yes`. PHP 의 `true`/`false` 를 그대로 쓰면 안 된다 [코드: `settings.TRUE`].
- [문서] 설정 기본값이 원본과 다른 것이 있었으나(`PORTING_GAPS` E6, E7) 현재 코드 기본값은 이 세션에서 변수별로 모두 대조하지 않았다. 중요한 변수는 이전 전에 기본값을 코드에서 확인한다.

## 5. 옛 주소 리다이렉트
- [코드] `deploy/legacy-redirects/nginx.conf`, `apache.conf` 는 각각 26줄이다. nginx 파일은 `deploy/nginx/namifax.conf` 의 `server` 블록 안에서 `include` 하도록 쓰여 있고, 옛 `*.php` 주소를 쿼리 문자열을 보존하며 301 로 새 주소에 보낸다(`/index.php` → `/login`, `/inbox.php` → `/inbox`, `/pdf.php?fid=N` → `/faxes/download/N?format=pdf`, `/refax.php?fid=N` → `/sendfax?refax=N`, `/admin/conf_modems*.php` → `/admin/modems` 등). 숫자가 아닌 `fid` 는 404.
- [코드] `tests/unit/test_legacy_redirects.py` 가 규칙의 도착 주소가 앱에 있는지와 Apache·nginx 파일이 같은 옛 페이지를 다루는지 지킨다. 규칙 자체는 실제 Apache·nginx 로 바꿀 때 시험한다고 파일 머리글이 말한다. "17개 주소 시험 완료"는 [문서] 이며 이 세션에서 재현하지 않았다.

## 6. 사용자에게 알릴 것
- [문서] 이전 직후 모든 사용자가 한 번 다시 로그인해야 한다(PHP 세션·로그인 쿠키는 이어지지 않음).
- [문서] 화면 모양과 대화상자가 바뀐다. 기능과 권한 규칙은 같다고 문서는 말한다.
- [문서] 비밀번호 찾기, 2단계 인증(TOTP), 패스키, SAML 은 새 기능이다.
- [문서] 병행 운영 중 NamiFAX 에서 로그인한 계정은 원본에서 로그인되지 않을 수 있다(`NAMIFAX_PASSWORD_HASH=md5` 가 아닐 때). 이 경우 비밀번호 찾기로 새로 받는다.
- [문서] SMTP 는 관리자 화면에서 다시 입력해야 한다.
- [문서] 큰 `FaxArchive` 의 첫 기동은 인덱스 생성으로 오래 걸릴 수 있으니 점검 시간대에 한다.

## 7. 확인하지 못한 것
- 실제 HylaFAX 와의 병행 운영, 3.0~3.2.x 업그레이드 이력이 있는 실제 DB, 대용량 보관소 시간(문서도 미확인이라고 명시).
- 예행연습 결과 자체(Docker 실행 필요). 파일 존재와 의존 경로만 확인했다.
