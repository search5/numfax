# Contract Specification: Module 05 - PAMAuth

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/PAMAuth.php` (클래스 `PAMAuth`)
- **타깃 모듈**: `src/avantfax/auth/pam.py` (클래스 `PAMAuthBackend`)
- **의존 관계**: Leaf (독립 시스템 PAM 인증 모듈)

---

## 2. Interface Contract (인터페이스 명세)

### 2.1 PAM Authentication
- `login(username: str, password: str, service: str = "login") -> bool`
  - **선행 조건**: `username`과 `password` 문자열이 주어져야 함.
  - **후행 조건**:
    - 시스템의 PAM 서비스 스택(`pam_authenticate`)을 통해 자격 증명 검증.
    - 인증 성공 시 `True`, 실패 또는 라이브러리 미지원 시 `False` 반환.
    - 실패 원인을 `last_error`에 기록.

### 2.2 Driver Architecture
- `PAMDriver`:
  1. `python-pam` 라이브러리가 있을 경우 우선 사용.
  2. 시스템의 `libpam.so` (Linux) / `libpam.dylib` (macOS)를 `ctypes`로 바인딩하여 무의존성 직접 호출 지원.
  3. 테스트 및 모의 환경을 위한 Mock 드라이버 주입 지원.

---

## 3. Idiomatic Transformation Rules
1. **Graceful Fallback**: PAM 라이브러리가 없는 컨테이너나 환경에서도 충돌(Crash) 없이 명확한 에러 메시지와 함께 `False` 반환.
2. **Memory Safety**: `ctypes` 또는 C-API 호출 시 자격증명 메모리 버퍼(conversation function)를 즉각 해제하여 메모리 누수 방지.
