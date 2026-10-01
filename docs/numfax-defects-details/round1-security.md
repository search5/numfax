# NamiFAX 보안 결함 조사 (Round 1 - 인증/보안 담당)

조사 대상: /tmp/claude-1000/-home-jiho-yona-convert-yona/71c0ff67-554f-46a6-8fb3-3f0735cbea93/scratchpad/numfax
DB: NAMIFAX_DB_PATH=scratchpad/agent-sec/sec.db (SQLite), 실행: `uv run python` + `webtest.TestApp(namifax.create_app({}))`
known.md(K01~K16)에 있는 결함은 제외하고, 새로 발견했거나 변형된 결함만 기록함.

---

## SEC-01 (치명) 비인증 SQL 인젝션 — 주소록 검색 (UNION 기반 데이터 탈취)

- **위치**: `src/namifax/services/addressbook.py:104-106` (`AFAddressBook.search_companies`), 진입점 `src/namifax/views/ajax.py:66`(`ajax_book`, route `/ajax/book`), `views/ajax.py:318`(`ajax_archivebook`, route `/ajax/archivebook`). 두 뷰 모두 `@view_config`에 `permission`이 지정되어 있지 않아 인증 없이 접근 가능.
- **증상**: `q` 쿼리 파라미터가 이스케이프 없이 곧바로 SQL 문자열에 삽입됨.
  ```python
  keywords = query.strip().replace(" ", "%")
  sql = f"SELECT * FROM AddressBook WHERE company LIKE '%{keywords}%' ORDER BY company"
  ```
  공백만 `%`로 치환하고 따옴표(`'`)는 전혀 처리하지 않음. 공백 대신 탭 문자(`\t`)를 쓰면 필터를 그대로 통과함.
- **재현 방법** (실제 실행, 인증 없음):
  ```python
  payload = "x'\tUNION\tSELECT\t1,password,username,1,1,1,1,1,1,1,1,1,1\tFROM\tUserAccount\tWHERE\tusername='admin'--\t"
  app.get("/ajax/book", {"q": payload})
  ```
  응답 XML에 `<company>password - 1</company>` 가 반환되어 `UserAccount.password` 컬럼 값이 그대로 유출됨. `UserAccount`, `UserTOTP`, `UserWebAuthnCredentials`, `SystemSettings`(SMTP 비밀번호) 등 모든 테이블을 UNION으로 읽어낼 수 있고, `sqlite_master`를 통해 전체 스키마도 열거 가능.
- **확인 수준**: 재현 (완전한 비인증 데이터 탈취까지 실증).

## SEC-02 (높음) 상태 변경 AJAX/업로드 엔드포인트에 permission 미지정 → 비인증 조작 가능

- **위치**: `src/namifax/views/ajax.py:207`(`ajax_archivefax`, POST), `:222`(`ajax_faxalter`), `:283`(`ajax_deletefaxes`), `views/helpers.py:230`(`upload_contacts`), `:275`(`upload_faxcontacts`). 모두 `@view_config(route_name=...)`에 `permission` 인자가 없음(기본값=public).
- **증상**: 로그인하지 않은 사용자가 팩스 작업 변경(`faxalter`), 팩스 삭제(`deletefaxes`), 팩스 보관 처리(`archivefax`), 주소록에 임의 연락처 주입(vCard 업로드)을 실행할 수 있음.
- **재현 방법**: 쿠키/토큰 없이
  ```python
  app.post("/ajax/faxalter", {"jid":"1","destination":"666"})        # 200 OK
  app.post("/ajax/deletefaxes", {"fids":"1,2,3"})                    # 200 OK
  app.post("/ajax/archivefax", {"fid":"1"})                          # 200 OK
  app.post("/upload/contacts", upload_files=[("upload","a.vcf", b"BEGIN:VCARD\nFN:Evil\nEMAIL:evil@x.com\nEND:VCARD")])  # 200 OK
  ```
  전부 인증 없이 200 OK로 처리됨(모두 실제 서비스 레이어 호출까지 도달).
- **확인 수준**: 재현.

## SEC-03 (높음) 팩스 상세/다운로드/주석/회전 등에서 모뎀 기반 접근 제어 우회 (IDOR)

- **위치**: `src/namifax/views/inbox.py`의 `viewfax_view`(:73), `fax_download_view`(:102), `fax_rotate_view`(:129), `setcompany_view`(:146), `src/namifax/views/modals.py`의 모든 모달(`modal_note`, `modal_delete`, `modal_email`, `modal_refax`, `modal_txreport`). 근본 원인은 `services/archive_base.py:385`의 `load_fax()`가 `fid`만으로 무조건 조회하며 호출자 신원을 전혀 확인하지 않는 것.
- **증상**: `/inbox` 목록 화면은 `identity.get("modemdevs")`로 사용자가 볼 수 있는 모뎀 장치를 제한하지만(`views/inbox.py:25-29`), 이 제한은 목록 조회에만 적용되고 `viewfax`, `fax_download`, `fax_rotate`, `setcompany`, 모든 모달 뷰는 `fid`만 알면 소속 모뎀/부서와 무관하게 조회·다운로드·주석 작성·회전·재전송·이메일 전달이 가능함. `permission="view"`만 있으면 되므로 로그인한 일반 사용자 누구나 다른 사용자의 팩스를 `fid` 순차 증가만으로 열람 가능.
- **재현 방법**: `modemdev='ttyS9'`로 새 팩스(fid=3, 내용 "Confidential HR Fax")를 만들고, 해당 모뎀 권한이 전혀 없는 일반 사용자 `alice`로 로그인한 뒤
  ```python
  app.get(f"/viewfax?fid=3")            # 200 OK, 내용 노출
  app.get(f"/faxes/download/3?format=pdf")  # 200 OK, PDF 바이트 반환
  app.post(f"/note?fid=3", {"description": "HACKED note by alice"})  # 200 OK, 주석 변경까지 허용
  ```
- **확인 수준**: 재현.

## SEC-04 (높음) 반사 XSS — `/ajax/deletefaxes`의 `fids` 파라미터

- **위치**: `src/namifax/views/ajax.py` (`ajax_deletefaxes_view`, GET 분기, hidden input 렌더링 부분, 약 296-306번째 줄).
- **증상**: `fids` 쿼리 파라미터가 HTML 이스케이프 없이 `<input type="hidden" name="fids" value="{fids}" />` 에 직접 삽입됨.
  ```python
  html = f"""... <input type="hidden" name="fids" value="{fids}" /> ..."""
  ```
- **재현 방법**:
  ```python
  app.get('/ajax/deletefaxes?fids=%22%3E%3Cscript%3Ealert(1)%3C/script%3E')
  ```
  응답 본문에 `"><script>alert(1)</script>` 가 그대로 포함됨(속성 탈출 + 스크립트 삽입 확인).
- **확인 수준**: 재현.

## SEC-05 (높음) 비밀번호 만료/강제 재설정 정책이 로그인 시점에 전혀 강제되지 않음

- **위치**: `src/namifax/views/auth.py` `login_post_view` (약 29-74번째 줄). 원인 로직은 `src/namifax/services/user_account.py` `AFUserAccount.login()`에서 `self.pwdexpired` 를 계산하지만, `login_post_view`는 이 값을 확인하지 않고 곧바로 `/inbox`로 리다이렉트함. `/pwdexpired` 라우트는 존재하지만 로그인 흐름에서 절대 호출되지 않음.
- **증상**: `pwdexpire` 만료, `wasreset=1`(관리자 강제 초기화), 최초 로그인(`last_login IS NULL`) 등 `AFUserAccount.login()`이 `pwdexpired=True`로 판정하는 모든 경우에도 사용자는 정상적으로 `/inbox`에 도달함. 강제 비밀번호 변경이 실제로는 절대 발생하지 않음.
- **재현 방법**: `pwdcycle=3`, `pwdexpire='2000-01-01'`, `wasreset=1`, `last_login='2020-01-01'`로 세팅한 계정 `expired`로 로그인:
  ```python
  app.post("/login", {"username":"expired","password":"Passw0rdXY"})  # 302 -> /inbox
  app.get("/inbox")                                                    # 200 OK (정상 접근)
  ```
- **확인 수준**: 재현.

## SEC-06 (중간) 비밀번호 해시가 salt 없는 단순 MD5

- **위치**: `src/namifax/auth/password.py:16-19` (`PasswordManager.hash_password`), `src/namifax/services/user_account.py:22-23` (`md5_hash`) — 로그인, 생성, 변경, 재설정 전 경로에서 사용.
- **증상**: `hashlib.md5(password)`만 사용하고 salt/pepper가 전혀 없음. 동일 비밀번호는 모든 사용자에서 동일 해시가 되어 레인보우 테이블 공격에 취약하고, MD5는 GPU로 초당 수십억 회 계산 가능해 사실상 무방비.
- **확인 수준**: 재현(코드 경로 확인 + SEC-01의 UNION 인젝션으로 실제 평문/약해시 값이 그대로 노출됨을 실증).

## SEC-07 (중간) TOTP 비밀키/백업코드가 DB에 평문 저장

- **위치**: `src/namifax/services/totp.py` `enable_totp()` (약 44-59번째 줄).
  ```python
  sql = (f"INSERT INTO UserTOTP (uid, secret_key, is_enabled, backup_codes, created_at) "
         f"VALUES ({int(uid)}, {self.db.quote(secret)}, 1, {self.db.quote(codes_str)}, {self.db.quote(now_str)})")
  ```
- **증상**: Base32 TOTP secret과 8개의 백업 복구코드가 암호화 없이 그대로 저장됨. SEC-01의 SQL 인젝션과 결합하면 인증 없이 모든 사용자의 TOTP 비밀키/백업코드를 탈취해 2FA를 완전히 무력화할 수 있음.
- **재현 방법**: `TotpService(eng).enable_totp(uid=3, secret=..., code=...)` 직접 호출 후 `SELECT secret_key, backup_codes FROM UserTOTP` 조회 → 평문 그대로 저장됨을 확인(예: `secret_key='REDACTED_MOCK_TOTP_KEY'`). <!-- gitleaks:allow -->
- **확인 수준**: 재현.

## SEC-08 (중간) SMTP 비밀번호 / 클라우드 스토리지 secret_key 평문 저장

- **위치**: `src/namifax/services/smtp_settings.py` `get_settings`/`save_settings` (SystemSettings.smtp_password 컬럼), `src/namifax/views/admin.py` `admin_storage_view` 약 1089-1099번째 줄(`set_cfg("cloud_secret_key", secret_key)`, DynConf 키-값 저장).
- **증상**: 두 경로 모두 암호화/봉인 없이 원문 그대로 DB에 저장함.
- **재현 방법(SMTP)**: `SmtpSettingsService(db=eng).save_settings({... "smtp_password":"SuperSecretPW!" ...})` 후 `SELECT smtp_password FROM SystemSettings` → `'SuperSecretPW!'` 그대로 조회됨.
- **클라우드 secret_key**: `admin_storage_view`가 동일한 `set_cfg()`(DynConf 평문 키-값) 경로를 사용함을 코드로 확인(추론 — 관리자 화면 저장 자체는 K01 결함으로 실제 DB에 반영되지 않아, 연결된 엔진을 직접 넘겨 별도로 검증하지 않았음).
- **확인 수준**: SMTP는 재현, 클라우드 secret_key는 추론.

## SEC-09 (낮음~중간) CSRF 방어가 전혀 없음

- **위치**: 전체 코드베이스. `grep -rn "csrf"` 결과 0건. `_submit_check` hidden 필드(`views/ajax.py`, `views/helpers.py`)는 고정값 `"1"`이며 서버측에서 검사하는 코드가 없음(진짜 CSRF 토큰이 아니라 레거시 PHP의 잔재 필드로 보임).
- **증상**: 로그인 세션 쿠키는 `SameSite=Lax`로만 설정되어 있어(`security.py` `remember()`), 교차 사이트 POST는 기본적으로 차단되지만, `permission="view"`만 요구하는 GET 기반 상태변경 라우트(`/rotate`, `/faxes/rotate/{fid}`, `/setcompany`)는 최상위 탐색(top-level navigation, 예: 공격자 페이지의 링크 클릭이나 `location.href` 리다이렉트)에서는 Lax 쿠키가 여전히 전송되므로 CSRF에 노출됨. 여기에 더해 SEC-02에서 확인한, permission이 아예 없는 POST 엔드포인트들은 인증 자체가 없으므로 CSRF 여부와 무관하게 이미 공격 가능.
- **확인 수준**: CSRF 토큰 부재 자체는 재현(grep 및 코드 검토로 서버측 검증 부재를 확인), 실제 타 사이트에서의 크로스사이트 공격 시연은 추론.

## SEC-10 (중간) 로그인 무차별 대입 시도에 대한 잠금/속도제한 전혀 없음

- **위치**: `src/namifax/views/auth.py` `login_post_view`, `src/namifax/services/user_account.py` `AFUserAccount.login()`. 실패 횟수 카운트, 계정 잠금, 지연(backoff), IP 차단 등 어떤 메커니즘도 없음(스키마에도 `failed_attempts` 류 컬럼 없음).
- **재현 방법**: 동일 계정으로 20회 연속 잘못된 비밀번호를 보낸 뒤에도 정상 비밀번호로 즉시 로그인 성공(지연/잠금 없음).
- **확인 수준**: 재현.

## SEC-11 (낮음, 추론) MySQL 백엔드에서 `DatabaseEngine.quote()`의 백슬래시 미처리로 인한 2차 SQL 인젝션 가능성

- **위치**: `src/namifax/db/engine.py` `DatabaseEngine.quote()`.
  ```python
  escaped = str(string).replace("'", "''")
  return f"'{escaped}'"
  ```
- **증상**: 단일 인용부호만 두 배로 치환하고 백슬래시는 전혀 처리하지 않음. SQLite/PostgreSQL 표준 문자열 리터럴에서는 백슬래시가 특별한 의미가 없어 문제가 없지만, 이 프로젝트가 지원을 명시한 MySQL(`connect(db_engine="mysql")`, `pymysql` 사용)은 기본 `sql_mode`에서 백슬래시를 이스케이프 문자로 해석하므로, 입력값 끝에 백슬래시가 포함되면 `''`로 이스케이프된 인용부호 중 하나가 백슬래시에 의해 "소비"되어 문자열 리터럴이 예상보다 일찍 닫히고 그 뒤 내용이 SQL로 실행될 수 있음(고전적인 MySQL backslash-escape 우회).
- **확인 수준**: 추론(환경 규칙상 `NAMIFAX_DB_PATH`로 SQLite만 사용해야 하여 실제 MySQL 연결로는 재현하지 않음; SQLite에서는 백슬래시가 특별하지 않아 이 경로로는 재현되지 않음을 확인함).

---

## 요약

- **총 결함 수**: 11건 (SEC-01 ~ SEC-11)
- **심각도별 건수**: 치명 1, 높음 4, 중간 5, 낮음 1 (SEC-09는 낮음~중간 경계로 "중간" 쪽에 가깝게 취급 가능)
- **가장 중요한 5건**:
  1. SEC-01 — 비인증 SQL 인젝션(주소록 검색) — 전체 DB 데이터 탈취 가능
  2. SEC-02 — 상태 변경 AJAX/업로드 엔드포인트 permission 누락 — 비인증 데이터 조작
  3. SEC-03 — 팩스 상세/다운로드 등 모뎀 기반 접근 제어 우회(IDOR)
  4. SEC-04 — `/ajax/deletefaxes` 반사 XSS
  5. SEC-05 — 비밀번호 만료/강제 재설정 정책이 로그인 시 전혀 강제되지 않음
