# Module Specification: 13. AFUserPasswords

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/AFUserPasswords.php`
- **신규 타깃 모듈**: `src/avantfax/services/user_passwords.py`
- **역할**: 사용자 비밀번호 변경 이력(`UserPasswords` 테이블) 관리 및 과거 사용된 비밀번호 재사용 방지(Password History Check) 서비스.
- **주요 의존성**:
  - `src/avantfax/models/entities.py` (`UserPasswords`)
  - `src/avantfax/db/repository.py` (`MDBOData` / `Repository`)
  - `src/avantfax/auth/password.py` (`PasswordManager`)
  - `src/avantfax/db/engine.py` (`DatabaseEngine`)

---

## 2. Legacy API Analysis & Behavior

### 속성(Attributes)
- `upid`: 비밀번호 이력 PK
- `uid`: 사용자 ID (UserAccount.uid FK)
- `pwdhash`: MD5 해시화된 비밀번호 문자열
- `userpasswords`: `UserPasswords` 엔티티를 제어하는 `MDBOData` 인스턴스

### 메서드(Methods)
1. `__init__(db: Optional[DatabaseEngine] = None, repo: Optional[MDBOData] = None)`
   - `UserPasswords` 레포지토리를 초기화하거나 주입받음.
2. `log_password(pwd: str, uid: int) -> bool`
   - `pwd`를 MD5 해시화한 후 `uid`와 함께 `UserPasswords` 테이블에 신규 등록.
   - 성공 시 `True`, 실패 시 `False` 반환.
3. `password_used(pwd: str, uid: int) -> bool`
   - 주어진 `pwd`의 MD5 해시와 `uid`가 일치하는 레코드가 존재하는지 검사.
   - 이전에 사용된 적이 있으면 `True`, 없으면 `False` 반환.
4. `clear_hashes(uid: int) -> bool`
   - 해당 `uid`의 모든 비밀번호 이력을 삭제 (`DELETE FROM UserPasswords WHERE uid = :uid`).
   - 성공 여부 반환.

---

## 3. Modern Python Design (Idiomatic)
- `PasswordHistoryService` 및 `AFUserPasswords` 클래스명 별칭 제공
- `PasswordManager.hash_password`를 사용하여 일관된 해싱 보장
- 파라미터화된 쿼리 또는 ORM/QueryBuilder를 통한 안전한 SQL 실행
- CLI/IPC 브리지: `bridge_cli.py`의 `user_passwords` 액션을 통해 레거시 PHP `AFUserPasswordsBridge.php`와 통신 가능
