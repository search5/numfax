# Specification: Module 32 - WebAuth

## 1. Overview
- **Module Name**: `WebAuth`
- **Legacy Source**: `legacy/avantfax/check_login.php`, `legacy/avantfax/logout.php`, `legacy/avantfax/index.php`
- **Target Implementation**: `src/avantfax/web/session.py`, `src/avantfax/web/views/auth.py`
- **Primary Role**: 사용자 웹 로그인, 세션 생성 및 쿠키 발급, 권한 및 만료 확인, 로그아웃 세션 파기.

---

## 2. Interface Specification
- **Session Management (`SessionManager`)**:
  - `create_session(user_id: int, username: str, is_admin: bool) -> Session`: 새 세션 발급 및 토큰 반환
  - `get_session(token: str) -> Optional[Session]`: 세션 유효성 검사 및 조회
  - `destroy_session(token: str) -> bool`: 세션 무효화
- **Auth Views / Handlers (`AuthHandler`)**:
  - `login(username, password, client_ip=None) -> Dict[str, Any]`:
    - `AFUserAccount.login` 인증 수행
    - 만료 여부 확인 (`is_expired()`)
    - 성공 시 세션 생성 후 세션 토큰 반환
  - `check_login(token) -> Optional[Session]`:
    - 세션 존재 여부 및 활성 상태 검증
  - `logout(token) -> bool`:
    - 세션 삭제 및 로그아웃 완료

---

## 3. Verification & Testing Strategy
- **Unit Tests (`tests/unit/test_web_auth.py`)**:
  - 올바른 계정 정보로 로그인 시 세션 생성 확인
  - 잘못된 계정/비밀번호 시 에러 반환 확인
  - 세션 만료 및 로그아웃 시 세션 무효화 확인
  - 미인증 토큰으로 접근 시 거부 확인
