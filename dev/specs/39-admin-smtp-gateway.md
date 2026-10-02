# Spec 39: Admin SMTP Gateway & Dynamic Mailer Settings

## 1. 개요 및 목적
- **목적**: 기존 `config.php` 하드코딩 방식에서 탈피하여, 관리자가 웹 UI(`/admin/smtp`)에서 기업 외부 SMTP 서버(AWS SES, Google Workspace, Microsoft 365, 사내 Exchange 등)의 연결 정보를 등록 및 관리하고, 실시간 연결 진단(Self-Test)을 수행할 수 있도록 지원합니다.
- **연동 대상**: `MailerService` (`src/namifax/services/mailer.py`), 관리자 뷰 (`src/namifax/views/admin.py`), 시스템 설정 모델 (`src/namifax/db/schema.py`).

---

## 2. 데이터 모델 및 스키마 명세

### 2.1 테이블: `system_settings`
| 필드명 | 타입 | Nullable | 기본값 | 설명 |
| :--- | :--- | :---: | :--- | :--- |
| `id` | INTEGER | No | PK Auto-Inc | 고유 식별자 (단일 행 또는 키-값) |
| `smtp_host` | VARCHAR(255) | Yes | "localhost" | SMTP 서버 도메인 또는 IP |
| `smtp_port` | INTEGER | No | 25 | 포트 번호 (25, 465, 587 등) |
| `smtp_security` | VARCHAR(32) | No | "NONE" | 보안 모드: `NONE`, `STARTTLS`, `SSL` |
| `smtp_auth` | BOOLEAN | No | FALSE | SMTP 인증 사용 여부 |
| `smtp_username` | VARCHAR(255) | Yes | NULL | 인증 사용자명 |
| `smtp_password` | VARCHAR(255) | Yes | NULL | 인증 비밀번호 |
| `from_email` | VARCHAR(255) | No | "root@localhost"| 기본 발신 이메일 주소 |
| `from_name` | VARCHAR(255) | Yes | "NamiFAX" | 기본 발신자 표시 이름 |
| `email_sig_text`| TEXT | Yes | NULL | 기본 텍스트 서명 |
| `email_sig_html`| TEXT | Yes | NULL | 기본 HTML 서명 |
| `updated_at` | DATETIME | Yes | NOW() | 최종 수정 시각 |

---

## 3. 서비스 계층 명세 (`SmtpSettingsService` & `MailerService`)

### 3.1 `SmtpSettingsService`
- `get_settings() -> SmtpConfig`: 현재 DB에 저장된 SMTP 설정을 반환하며, 데이터가 없을 경우 시스템 기본값을 반환.
- `save_settings(config_dict: dict) -> bool`: 전달된 설정값을 유효성 검증(포트 범위 1~65535, 호스트 유효성 등) 후 저장/업신.
- `test_connection(target_email: str, config: dict | None = None) -> SmtpTestResult`:
  - 지정한 설정(또는 저장된 설정)을 사용하여 실제 SMTP 소켓 연결, TLS/SSL 핸드셰이크, 인증 시도, 테스트 메일 전송을 순차 진행.
  - 각 단계별 상태(SUCCESS/FAIL)와 상세 로그 메시지를 캡슐화한 결과 반환.

### 3.2 `MailerService` 동적 주입 연동
- `MailerService.get_active_mailer(engine=None) -> MailerService`:
  - DB의 `SmtpSettingsService`를 통해 최신 설정을 로드하여 인스턴스를 동적으로 생성 및 반환.
  - DB 설정이 비어있거나 연결할 수 없을 경우 기존 로컬 기본값으로 안전하게 폴백.

---

## 4. 웹 UI 및 API 명세 (`/admin/smtp`)

### 4.1 권한 및 인증
- 슈퍼관리자(`is_superadmin=True`) 권한 전용. 비인가 사용자는 403 Forbidden.

### 4.2 라우트 및 엔드포인트
1. `GET /admin/smtp`:
   - 현재 SMTP 게이트웨이 설정 폼 렌더링 (`templates/admin_smtp.jinja2`).
2. `POST /admin/smtp`:
   - `action=save`: 폼 데이터를 검증 후 DB 저장. 성공 플래시 메시지 출력.
   - `action=test`: 실시간 SMTP 연결 진단 수행. JSON 또는 화면에 성공/실패 상세 로그 렌더링.

---

## 5. 무회귀 및 검증 기준
1. 단위 테스트:
   - `tests/unit/test_smtp_settings.py`: 설정 저장, 조회, 유효성 검사, Mock SMTP 테스트 연결 성공/실패 시나리오 검증.
2. 웹 통합 테스트:
   - `tests/unit/test_pyramid_admin_smtp.py`: `/admin/smtp` 뷰 권한 제어, GET 폼 렌더링, POST 저장 및 테스트 요청 정상 응답 검증.
3. 기존 296개 테스트 및 88개 골든 마스터 E2E 100% 회귀 없음 검증.
