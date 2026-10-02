# Spec 46: SAML 2.0 Enterprise Single Sign-On (SSO)

## 1. 목적 및 배경
엔터프라이즈 환경에서 Microsoft Entra ID(Azure AD), Okta, Keycloak, Google Workspace 등 기업용 Identity Provider(IdP)와 표준 SAML 2.0 프로토콜을 통해 통합 인증 및 Single Sign-On(SSO), JIT(Just-In-Time) 사용자 프로비저닝을 제공한다.

---

## 2. SAML 설정 모델 (`SAMLSettings`)

- `enabled`: bool (SAML SSO 활성화 여부)
- `idp_entity_id`: str (IdP 발급 엔티티 식별자)
- `idp_sso_url`: str (IdP Single Sign-On Service HTTP-Redirect URL)
- `idp_x509_cert`: str (IdP 전자서명 검증용 공개키 인증서 PEM)
- `sp_entity_id`: str (NamiFAX SP 엔티티 ID)
- `sp_acs_url`: str (Assertion Consumer Service 엔드포인트 URL)
- `sp_sls_url`: str (Single Logout Service 엔드포인트 URL)
- `jit_provisioning`: bool (미등록 사용자 로그인 시 계정 자동 생성 여부)
- `default_role`: str (JIT 생성 시 부여할 기본 역할)

---

## 3. 서비스 계층 명세 (`SAMLService`)

### 모듈 위치
- `src/namifax/services/saml.py`

### 주요 기능
1. **`generate_sp_metadata() -> str`**:
   - NamiFAX Service Provider 메타데이터 XML (`urn:oasis:names:tc:SAML:2.0:metadata`) 생성.
   - SP EntityID, AssertionConsumerService URL, SingleLogoutService URL 명시.
2. **`create_authn_request(relay_state: str = "/") -> dict[str, str]`**:
   - SAML 2.0 AuthnRequest XML 생성.
   - zlib deflate 압축 및 Base64 인코딩.
   - IdP SSO URL로 리다이렉트할 쿼리 파라미터 반환 (`SAMLRequest`, `RelayState`).
3. **`process_saml_response(saml_response_b64: str) -> dict[str, Any]`**:
   - Base64 디코딩된 SAML Response XML 파싱 (`defusedxml` 사용).
   - 상태 코드(`urn:oasis:names:tc:SAML:2.0:status:Success`) 확인.
   - Subject `NameID` 및 속성 매핑 (`email`, `username`, `display_name`).
4. **`provision_or_get_user(name_id: str, attributes: dict[str, Any]) -> AFUserAccount`**:
   - `UserAccount` 테이블에서 사용자 조회.
   - 사용자가 없고 `jit_provisioning`이 켜져 있으면 신규 계정 자동 생성.

---

## 4. 웹 라우트 및 컨트롤러 명세

1. **`GET /auth/saml/metadata`**: SP 메타데이터 XML 다운로드/조회 (`application/xml`).
2. **`GET /auth/saml/login`**: IdP 로그인 페이지로 302 리다이렉트.
3. **`POST /auth/saml/acs`**: IdP SAML Response 수신 및 사용자 세션 생성.
4. **`GET/POST /auth/saml/sls`**: 단일 로그아웃 처리 후 로그인 페이지로 이동.
5. **`GET/POST /admin/saml`**: 관리자 SAML 설정 화면.

---

## 5. 검증 기준 (Acceptance Criteria)

1. 단위 테스트:
   - SP 메타데이터 XML 규격 및 태그 일치 검증.
   - AuthnRequest 생성 및 deflate/base64 인코딩 검증.
   - SAML Response XML 파싱 및 NameID, 이메일 속성 추출 검증.
   - JIT 사용자 프로비저닝 로직 검증.
2. 하위 호환성:
   - SAML이 비활성화된 상태에서는 기존 폼 로그인, WebAuthn, TOTP 로그인에 영향을 주지 않음.
