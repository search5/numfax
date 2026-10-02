# Module Specification: 21. AFUserAccount

## 1. 개요 (Overview)
- **모듈명**: `AFUserAccount` (`user_account.py`)
- **레거시 파일**: `legacy/avantfax/includes/AFUserAccount.php`
- **의존성**:
  - `MDBOData` (`src/avantfax/db/repository.py` - 테이블: `UserAccount`)
  - `AFUserPasswords` (`src/avantfax/services/user_passwords.py`)
  - `DatabaseEngine` (`src/avantfax/db/engine.py`)
- **책임**:
  - 사용자 계정 생성, 수정, 삭제(소프트 삭제), 목록 조회.
  - 로그인 인증, 관리자 권한 검증, 비밀번호 만료/리셋 여부 판별.
  - 비밀번호 변경 및 과거 비밀번호 재사용 방지 정책 적용.
  - 모뎀 장치, 팩스 카테고리, DID 라우트 접근 권한 설정(`|` 구분자 직렬화).

---

## 2. 인터페이스 명세 (API Contract)

### `UserAccountService(db_engine=None, user_passwords=None)`
- `create(details: dict) -> bool`
- `list_accounts() -> List[dict]`
- `update() -> bool`
- `user_update() -> bool`
- `change_password(pwd: str) -> bool`
- `reset_password(email: str) -> Tuple[bool, Optional[str]]`
- `set_newpassword(oldpwd: str, newpwd: str) -> bool`
- `login(username: str, password: str, admin: bool = False, remote_ip: str = "127.0.0.1") -> bool`
- `login_webauth(username: str, admin: bool = False, remote_ip: str = "127.0.0.1") -> bool`
- `load(userid: int) -> bool`
- `load_username(username: str) -> bool`
- `loadbyemail(email: str) -> bool`
- `remove(userid: int) -> bool`
- `get_uid() -> Optional[int]`
- `get_error() -> Optional[str]`
- `is_expired() -> bool`
- `check_login() -> bool`
- `check_admin_login() -> bool`
- `get_allvalues() -> dict`
- `get_modemdevs() -> List[str]`
- `set_modemdevs(val: Optional[List[str]]) -> bool`
- `get_faxcats() -> List[str]`
- `set_faxcats(val: Optional[List[str]]) -> bool`
- `get_didrouting() -> List[str]`
- `set_didrouting(val: Optional[List[str]]) -> bool`
- `set_username(username: str) -> bool`
- `set_email(email: str) -> bool`

---

## 3. 검증 시나리오 (Test Scenarios)
1. `create`: 정상 계정 생성, 중복 username/email 거부, 유효하지 않은 username 정규식 검증.
2. `login`: 올바른/잘못된 패스워드, 비활성화 계정 거부, 관리자 로그인 플래그 확인, 만료 플래그 확인.
3. `change_password`: 최소/최대 길이 검증, 이전 패스워드 재사용 방지 확인 (`pwd_reuse=False`).
4. `remove`: 사용자 계정 소프트 삭제 (`deleted=True`, `email=None`, `username=None`) 및 패스워드 해시 정리 확인.
5. 권한 목록 직렬화: `modemdevs`, `faxcats`, `didrouting`의 파이프(`|`) 구분자 입출력 검증.
