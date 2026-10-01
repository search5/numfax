# 4라운드 — 가리고 있는 원인 제거 후 재점검 (round4-unmask)

작업 디렉터리: `scratchpad/agent-r4-unmask/repo` (numfax 를 `.git`/`.venv`/`node_modules`/`legacy` 제외하고 복제, `.venv` 는 `uv sync` 로 재생성).
원본 `scratchpad/numfax` 는 수정하지 않음.

## 적용한 임시 패치 목록 (복제본에만 적용)

| # | 대상 | 내용 |
|---|---|---|
| P1 | `src/namifax/__init__.py` (`create_app`) | `pyramid.session.SignedCookieSessionFactory` 를 세션 팩토리로 등록하고, `config.add_request_method(lambda request: get_default_engine(), "db", reify=True)` 로 모든 요청에 `request.db` 를 주입 (요구사항 a, b) |
| P2 | (P1 과 동일 커밋) | 위와 동일 — 세션 팩토리 등록 부분 |
| P3 | `src/namifax/services/user_account.py` | `AFUserAccount` 에 `load_by_username`(→`load_username`), `load_by_id`(→`load`), `get_username`, `get_name`, `create_user`(→`create`) 얇은 별칭(monkeypatch) 추가. WebAuthn 뷰 전체와 SAML provisioning 이 호출하는 메서드를 연결 (요구사항 c) |
| P4 | `src/namifax/services/{printer,cover_studio,ocr,storage_lifecycle,smtp_settings,webauthn,saml,totp}.py` | `DatabaseEngine()` (미연결) 생성을 `get_default_engine()` 호출로 교체. 또한 `from avantfax.*` 로 남아있던 import 전체를 `from namifax.*` 로 일괄 치환(이중 트리 문제로 avantfax 쪽 구버전 엔진을 참조하던 부분 통일) (요구사항 d) |
| P5 | `src/namifax/db/schema.py` | 기동 시마다 FaxArchive/DIDRoute/AddressBook/DistroList 를 고정값으로 `UPDATE` 하던 시드/마이그레이션 코드 제거 (요구사항 e: 데이터 덮어쓰기 차단). `Modems` 시드의 `INSERT OR REPLACE` 를 `INSERT OR IGNORE` 로 변경 |
| P6 | `src/namifax/db/schema.py` | 누락 테이블/컬럼 보강: `DynConf`(device, callid) 테이블 추가, `UserWebAuthnCredentials` 테이블(SQLite 호환 DDL) 추가, `UserPasswords` 에 `pwdhash` 컬럼 추가, `UserAccount.username/password/email` 의 `NOT NULL` 제약 제거(소프트 삭제 시 NULL 로 비우는 기존 로직과 충돌 — COR-19 의 근본 원인) (요구사항 f) |
| P7 | `src/namifax/db/engine.py` | `QueryResult` 에 `rows` 필드와 `__iter__`/`__getitem__` 추가 — `self.db.query(...)` 의 반환값을 리스트처럼 순회/인덱싱하는 기존 호출부(OCR, WebAuthn 등, K16 이 지적한 부분)가 TypeError 로 죽지 않고 실행되도록 함. 차단 제거 목적의 얇은 패치 |
| P8 | `src/namifax/services/webauthn.py` | `verify_registration_response` 가 `credential_id` bytes 를 `.decode("utf-8")` 하여 거의 항상 예외가 나던 부분(R3D-11/R3B-15 기존 보고)을 `bytes_to_base64url()` 로 교체 — 등록 자체가 차단되어 그 아래의 인증/목록/삭제 로직을 점검할 수 없었기 때문에 최소 수정 |

세션/유저: admin/password 로 로그인, 테스트용 신규 사용자(bob/alice/carol 등)는 관리자 화면을 통해 생성. 가짜 HylaFAX 바이너리(`faxstat`, `faxrm`, `faxalter`)를 `agent-r4-unmask/work/bin` 에 두고 PATH 맨 앞에 추가하여 실행 검증. SQL 인젝션/셸 인젝션 페이로드는 실행하지 않음(규칙 준수).

## 패치 후에만 드러난 결함

### R4U-01 (치명) 관리자(uid=1) 삭제 보호 가드를 0-패딩 문자열로 우회 — 부트스트랩 관리자 소프트 삭제 가능
- 위치: `src/namifax/views/admin.py:96-103` (`admin_users_view`, delete 분기) — `if uid and str(uid) != "1":`
- 어떤 패치 이후 드러났는지: P1(request.db 주입) + P6(UserAccount NOT NULL 제거). 패치 전에는 COR-19(소프트 삭제 UPDATE 가 username/email NOT NULL 위반으로 실패)가 이 가드 우회 자체를 무해하게 만들고 있었음 — 가드를 우회해 `remove(1)` 이 호출돼도 DB 쓰기가 거부되어 admin 계정이 실제로는 그대로 남아 있었음.
- 증상: 관리자 화면에서 `POST /admin/users` 에 `delete=1&uid=01` (혹은 공백/부호가 섞인 다른 숫자 표현)을 보내면 문자열 비교 `"01" != "1"` 이 참이 되어 보호 로직을 통과하고, `int("01")==1` 이므로 실제로 `AFUserAccount.remove(1)` 이 실행되어 부트스트랩 관리자(uid=1) 계정이 소프트 삭제(username/email/password=NULL, deleted=1, acc_enabled=0)됨. 기본 시드에는 다른 관리자(operator 는 is_admin=0)가 없으므로, 이 한 번의 요청으로 시스템 전체에 관리자 계정이 0명이 되어 모든 `/admin/*` 화면이 영구적으로 403 이 됨(새 관리자를 임명할 방법이 없음 — 모든 승격 경로가 `permission="admin"` 필요).
- 재현: 관리자로 로그인 후 `POST /admin/users` body `{"delete":"1","uid":"01"}` 전송 → 302 → `SELECT * FROM UserAccount WHERE uid=1` 확인(username/email NULL, deleted=1). 이후 `/admin/users` 에 새로 로그인한 admin 세션은 403.
- 확인 수준: WSGI TestApp 로 직접 재현, DB 행 변화까지 확인함(실제 실행, 모킹 아님).

### R4U-02 (높음) 비밀번호 재사용 금지 정책이 불린→문자열 왕복 버그로 "항상 재사용 허용"으로 반전됨
- 위치: `src/namifax/services/user_account.py` `change_password()` 의 `pwd_reuse = bool(self.dbdata.get("pwd_reuse", False))` 및 `if not pwd_reuse and self.userpasswords.password_used(pwd, self.uid): ...`
- 어떤 패치 이후 드러났는지: P1+P4(엔진 연결 통일) + P6(UserPasswords 에 `pwdhash` 컬럼 추가로 COR-18 의 스키마 불일치 해소, `password_used()` 가 실제로 과거 비밀번호를 찾아내기 시작함). 패치 전에는 COR-18(스키마 불일치로 이력이 전혀 기록되지 않음)이 이 극성 반전을 가려서, "재사용 검사가 항상 통과(아무 것도 막지 않음)"라는 결과만 보이고 그 이유(검사 자체가 전혀 안 되는 것)와 "검사는 돌지만 설계와 반대로 항상 허용으로 평가되는 것"을 구분할 수 없었음.
- 증상: `QueryBuilder.quote()` 가 Python bool 을 문자열 `'True'`/`'False'` 로 저장하는 기존 결함(COR-09 계열) 때문에 DB 의 `pwd_reuse` 컬럼 값은 항상 리터럴 문자열 `'False'` 로 저장됨. 이를 다시 읽을 때 `bool('False')` 는 **True** 가 되므로(Python 에서 비어있지 않은 문자열은 모두 참), `pwd_reuse` 가 사실상 항상 `True` 로 평가되고 `if not pwd_reuse and ...` 조건이 항상 거짓이 되어 **재사용 금지 검사 자체가 영구적으로 스킵**됨. 즉 관리자가 "비밀번호 재사용 금지"를 켜두어도 사용자는 직전 비밀번호로 다시 바꿀 수 있음 — 의도와 정반대로 동작.
- 재현: 사용자 생성 → 비밀번호 A 로 변경 → 같은 비밀번호 A 로 다시 변경 시도 → 거부되지 않고 그대로 성공, `UserPasswords` 테이블에 같은 `pwdhash` 가 중복 기록됨.
- 확인 수준: 서비스 계층 단위에서 직접 호출해 `pwd_reuse` 컬럼 실제 저장값('False' 문자열)과 `bool()` 평가 결과(True)를 확인, `change_password()` 재호출로 재사용이 실제로 허용됨을 DB 조회로 확인.

### R4U-03 (중간) 분류(FaxCategory) 삭제 시 참조 정리가 전혀 없어 UserAccount.faxcats / Modems.faxcatid 가 존재하지 않는 catid 를 가리키게 됨
- 위치: `src/namifax/services/categories.py:112-122` (`delete_category`)
- 어떤 패치 이후 드러났는지: P1(request.db 주입). 패치 전에는 관리자 화면(K01)이 DB 에 전혀 반영되지 않아 분류 삭제 자체가 무해했음.
- 증상: `admin_categories` 화면에서 분류를 삭제하면 `FaxCategory` 행만 지워지고, 그 분류를 참조하던 `Modems.faxcatid` 와 `UserAccount.faxcats`(파이프 구분 문자열) 는 전혀 정리되지 않고 삭제된 catid 를 그대로 남김. 이후 모뎀/사용자 분류 기반 접근 제어·라우팅 로직이 유령 catid 를 참조하게 됨(해당 로직이 다른 결함으로 이미 무력화되어 있어 당장 크래시는 없으나, 참조 정합성이 깨진 상태로 영구히 남음).
- 재현: `FaxCategory` 에 catid=3 생성 → `Modems.devid=1.faxcatid=3`, `UserAccount.uid=2.faxcats='3|1'` 로 설정 → `admin_categories` 에서 catid=3 삭제 → `FaxCategory` 에서는 사라지지만 `Modems.faxcatid` 와 `UserAccount.faxcats` 는 그대로 3 을 포함.
- 확인 수준: 관리자 화면 POST 로 실제 CRUD 수행 후 SQLite 로 3개 테이블을 직접 조회해 불일치 확인.

### R4U-04 (중간~높음) 배포목록(DistroList) 삭제가 GET 요청만으로도 실행됨 — 메서드 제한 없는 상태 변경
- 위치: `src/namifax/views/distrolist.py:40-48` (`distrolist_view`) — `@view_config(route_name="distrolist", ...)` 에 `request_method` 제한이 없고, 뷰 본문이 `request.params.get("delete")` 만으로 삭제를 실행
- 어떤 패치 이후 드러났는지: P1(request.db 주입) + P5(시드 UPDATE 제거로 DistroList 행이 더미로 되돌아가지 않게 됨). 패치 전에는 K01 때문에 삭제가 DB 에 반영되지 않아 증상이 보이지 않았음.
- 증상: 로그인된 사용자가 `GET /distrolist?delete=1&dl_id=1` 을 호출(링크 클릭, `<img>` 프리로드, 브라우저 프리페치 등)하기만 해도 배포목록이 즉시 삭제됨. 같은 기능을 제공하는 `distrolist_edit_view` 는 `request.method == "POST"` 로 올바르게 막아놓았는데, 목록 화면 쪽 삭제만 메서드 제한이 빠져 있어 SEC-09(CSRF 토큰 없음)보다 더 심각한 "GET 으로도 상태 변경"에 해당함 — CSRF 토큰이 있었어도 이 경로는 토큰 없이 그냥 GET 링크로 뚫림.
- 재현: `DistroList` 에 행 존재 확인 → `GET /distrolist?delete=1&dl_id=1` (쿠키만 포함, POST 아님) → 302 → 해당 행이 삭제됨.
- 확인 수준: WSGI TestApp 로 순수 GET 요청을 보내 실제 DB 행 삭제를 확인(모킹 아님).

## 참고: 패치 후 재확인했으나 "이미 known4.md 에 있는 결함"으로 판단해 보고에서 제외한 항목
- TOTP 로그인 전체 흐름 자체는 정상 동작(설정→로그인→코드/백업코드 검증)하지만 코드 재사용·무제한 시도·fail-open 은 R3D-08/09/10 로 이미 보고됨.
- 패스키 등록/인증은 P7/P8 패치로 끝까지 흐르지만 챌린지 재사용, 서명 카운트 미검증 등은 R3B-14/R3D-13 로 이미 보고됨. 삭제된 사용자의 WebAuthn/SAML 세션이 실제 앱 세션과 분리되어 있어 접근 권한 상승으로 이어지지 않는 점은 F3-11/F3-15 범위로 판단.
- SAML 은 서명 검증 없이 ACS 까지 가서 실제로 사용자 생성(JIT)·세션 설정까지 도달함을 확인했으나(위조 응답으로 로그인 가능) 이는 K04 그대로이며, 관리자 설정 화면이 저장은 되지만 로그인 흐름에서 전혀 읽히지 않는 것은 K05/ADM-27 그대로.
- 관리자 바코드/모뎀/DID/커버/Fax2Email CRUD 는 P1 이후 대부분 정상 동작을 확인했고, 바코드만 PK 이름 불일치(barcode_id vs bcr_id)로 수정/삭제가 no-op 인 것을 재확인했으나 이는 ADM-07 그대로.
- 주소록 회사 수정/삭제가 `abook_id` NULL 로 no-op 인 것, 신규 회사의 팩스번호가 저장되지 않는 것은 COR-06/COR-07 그대로. "회사 병합" 기능 자체는 레거시/신규 어디에도 존재하지 않아 테스트 대상이 아님.
- 관리자 자기 강등/마지막 관리자 보호 없음은 ADM-06 그대로(단, R4U-01 은 "삭제" 경로의 더 구체적인 우회 트릭이라 별도 기재).
