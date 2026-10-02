# Contract Specification: Module 04 - PWAuth

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/PWAuth.php` (클래스 `PWAuth`)
- **타깃 모듈**: `src/avantfax/auth/password.py` (클래스 `PWAuthBackend`, `PasswordManager`)
- **의존 관계**: Leaf (독립 인증 백엔드 모듈)

---

## 2. Interface Contract (인터페이스 명세)

### 2.1 Exit Codes & Statuses
- `STATUS_VALID = 0` (인증 성공)
- `STATUS_NO_USER = 1` (사용자 미존재)
- `STATUS_BAD_PASSWORD = 2` (패스워드 불일치)
- `STATUS_ERROR = 3` (실행 오류 등)

### 2.2 External pwauth Execution
- `login(username: str, password: str, binary_path: str = None) -> bool`
  - **선행 조건**: `username`과 `password` 문자열 전달.
  - **후행 조건**: `pwauth` 바이너리를 서브프로세스로 실행하고 `stdin`에 `{username}\n{password}`를 전달.
  - **반환값**: 반환 코드가 0이면 `True`, 그 외(1, 2 등)는 `False`.
  - **보안 제약**: 명령어 인자가 아닌 stdin 파이프로 비밀번호를 안전하게 전달하여 프로세스 목록 노출 방지.

### 2.3 Legacy MD5 & Modern Hash Utilities
- `hash_password(password: str) -> str`
  - 레거시 AvantFAX MySQL 호환 32자리 16진수 MD5 해시 생성.
- `verify_password(plain_password: str, hashed_password: str) -> bool`
  - 상수 시간 비교(`hmac.compare_digest`)를 사용하여 타이밍 공격(Timing Attack) 방어.

---

## 3. Idiomatic Transformation Rules
1. **Secure Subprocess**: `proc_open` 대신 Python의 `subprocess.run(input=..., capture_output=True)`으로 파이프 누수 및 데드락 방지.
2. **Timing-Safe Comparison**: `password == hash` 직접 비교 대신 `secrets.compare_digest` 또는 `hmac.compare_digest` 적용.
3. **Mocking Support**: 단위 테스트 환경에서 시스템에 `pwauth` 바이너리가 없는 경우에도 테스트 가능하도록 주입식 커맨드 실행기 지원.
