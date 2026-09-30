# Spec 43: RFC 6238 TOTP Two-Factor Authentication

## 1. 개요 및 목적
- **목적**: 무차별 대입 및 자격 증명 유출로부터 사용자 및 관리자 계정을 보호하기 위해 표준 RFC 6238 기반 TOTP(Time-Based One-Time Password) 2단계 인증을 제공합니다.
- **주요 기능**:
  - 사용자별 고유 Base32 시크릿 키 발급 및 `otpauth://` 프로비저닝 URI 생성.
  - 6자리 일회용 코드 검증 (30초 타임 윈도우).
  - 8개의 비상 복구 백업 코드(Emergency Recovery Codes) 지원.
  - 사용자 설정 화면(`/settings/security`)에서의 활성화/비활성화 및 챌린지 검증.

---

## 2. 데이터 모델 (`UserTOTP`)

| 필드명 | 타입 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- |
| `uid` | INTEGER PRIMARY KEY | - | 사용자 고유 ID (`UserAccount.uid` 외래키) |
| `secret_key` | TEXT NOT NULL | - | Base32 암호화 시크릿 키 |
| `is_enabled` | INTEGER | 0 | 2FA 활성화 여부 (0: 비활성, 1: 활성) |
| `backup_codes` | TEXT | NULL | 쉼표로 구분된 비상 복구 코드 목록 |
| `created_at` | TEXT | NOW() | 생성 시각 |

---

## 3. 서비스 계층 명세 (`TotpService`)

```python
class TotpService:
    def __init__(self, db: DatabaseEngine = None): ...

    def generate_secret() -> str:
        """Generate a random Base32 secret string."""

    def get_provisioning_uri(username: str, secret: str, issuer: str = "NamiFAX") -> str:
        """Generate otpauth:// URI compatible with Google/MS Authenticator."""

    def verify_code(secret: str, code: str) -> bool:
        """Verify 6-digit TOTP challenge token."""

    def enable_totp(uid: int, secret: str, code: str) -> dict:
        """Validate challenge token and enable TOTP for user, generating backup codes."""

    def disable_totp(uid: int) -> bool:
        """Disable 2FA for the user."""

    def verify_user_login(uid: int, code: str) -> bool:
        """Verify TOTP or emergency recovery backup code during login."""
```

---

## 4. 검증 기준
1. 단위 테스트:
   - `tests/unit/test_totp.py`:
     - 시크릿 생성, URI 생성, 유효 토큰 검증 성공 및 불일치 토큰 실패 검증.
     - 사용자 활성화 및 백업 코드 생성/소모 검증.
     - 비활성화 처리 검증.
2. 무회귀 검증:
   - 기존 327개 테스트 및 88개 골든 마스터 E2E 100% 통과.
