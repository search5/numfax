# Spec 45: WebAuthn / Passkeys (FIDO2) Authentication

## 1. 목적 및 배경
엔터프라이즈 환경에서 보안성을 극대화하고 비밀번호 유출 위협을 원천 차단하기 위해 W3C 표준 WebAuthn(FIDO2) 기반의 패스워드리스(Passwordless) 로그인 및 생체인증(Face ID, Touch ID, Windows Hello, YubiKey)을 구현한다.

---

## 2. 데이터 모델 명세 (`UserWebAuthnCredential`)

### 테이블 정의 (`UserWebAuthnCredentials`)
- `id`: INTEGER PRIMARY KEY AUTO_INCREMENT
- `uid`: INTEGER (FK -> `UserAccount.uid`, ON DELETE CASCADE)
- `credential_id`: VARCHAR(255) UNIQUE NOT NULL (Base64url 인코딩된 자격증명 ID)
- `public_key`: TEXT NOT NULL (Base64url 인코딩된 공개키)
- `sign_count`: INTEGER DEFAULT 0 (재전송 공격 방지 카운터)
- `transports`: VARCHAR(100) (예: "usb,nfc,ble,internal")
- `device_name`: VARCHAR(100) NOT NULL (예: "MacBook Touch ID", "YubiKey 5 NFC")
- `created_at`: DATETIME DEFAULT CURRENT_TIMESTAMP
- `last_used_at`: DATETIME NULL

---

## 3. 서비스 계층 명세 (`WebAuthnService`)

### 모듈 위치
- `src/namifax/services/webauthn.py`

### 주요 기능
1. **등록 옵션 생성 (`generate_registration_options`)**:
   - WebAuthn 표준 규격에 따라 Relying Party (RP) 이름, ID, 사용자 정보(id, name, display_name) 및 암호화 난수 challenge 생성.
   - 세션에 challenge 저장.
2. **등록 응답 검증 (`verify_registration_response`)**:
   - 클라이언트 `navigator.credentials.create()` 결과(attestation object, clientDataJSON)를 검증.
   - 공개키, 자격증명 ID, sign_count를 추출하여 DB에 저장.
3. **인증 옵션 생성 (`generate_authentication_options`)**:
   - 패스워드리스 로그인 또는 2FA를 위한 challenge 생성 및 사용자 허용 자격증명 목록 제공.
4. **인증 응답 검증 (`verify_authentication_response`)**:
   - 클라이언트 `navigator.credentials.get()` 결과 검증.
   - 서명 검증 및 서명 카운터(sign_count) 증가 검증으로 복제 공격 차단.
5. **자격증명 관리**:
   - 사용자별 등록된 Passkey 목록 조회 (`list_credentials`)
   - 등록된 Passkey 삭제 (`delete_credential`)

---

## 4. API 엔드포인트 명세

1. **`POST /api/webauthn/register/options`**:
   - 로그인된 사용자 세션에서 등록 옵션 생성 및 반환.
2. **`POST /api/webauthn/register/verify`**:
   - 등록 응답 수신, 검증 및 자격증명 저장.
3. **`POST /api/webauthn/auth/options`**:
   - 인증 옵션 생성 (username 파라미터가 있으면 해당 사용자 키 매핑, 없으면 discoverable credential 지원).
4. **`POST /api/webauthn/auth/verify`**:
   - 클라이언트 서명 검증 후 성공 시 로그인 세션 발급.

---

## 5. 검증 기준 (Acceptance Criteria)

1. 단위 테스트:
   - 옵션 생성 시 올바른 challenge 및 RP 메타데이터가 생성되는지 검증.
   - 등록 및 인증 성공/실패 시나리오 검증.
   - 자격증명 목록 조회 및 삭제가 정상 작동하는지 검증.
2. 하위 호환성:
   - 기존 비밀번호 및 TOTP 인증 시스템과 100% 무회귀 호환 유지.
