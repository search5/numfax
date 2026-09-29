# Contract Specification: Module 07 - Mailer

## 1. Overview
- **레거시 모듈**: `legacy/avantfax/includes/Mailer.php` (클래스 `Mailer`, 기반 `htmlMimeMail5`)
- **타깃 모듈**: `src/avantfax/services/mailer.py` (클래스 `MailerService`)
- **의존 관계**: Leaf (파이썬 표준 `email` 및 `smtplib` 기반 독립 서비스)

---

## 2. Interface Contract (인터페이스 명세)

### 2.1 Configuration
- `__init__(smtp_server=None, smtp_port=25, smtp_user=None, smtp_password=None, use_ssl=False, use_tls=False, admin_email="root@localhost", email_sig_text="", email_sig_html="")`
  - 발신자 정보 및 SMTP 전송 매개변수 설정.

### 2.2 Message Assembly
- `set_message(text: str, subject: str = None) -> None`
  - 텍스트 본문과 서명을 결합하여 순수 텍스트(Plaintext)와 HTML 멀티파트 본문 생성.
- `attach_file(file_path: str | Path, alt_name: str = None) -> bool`
  - 첨부파일(PDF, TIFF 등)을 Base64 인코딩하여 MIMEAttachment로 등록.
- `embed_image(image_path: str | Path, cid: str = None) -> bool`
  - 본문에 인라인 표시될 이미지 등록.

### 2.3 Dispatch
- `sendmail(to: str | list[str], subject: str = None) -> bool`
  - **선행 조건**: 유효한 수신자 주소(`to`).
  - **후행 조건**: SMTP 연결 또는 로컬 sendmail을 통해 이메일 발송.
  - **예외 처리**: 발송 실패 시 `last_error`에 원인 기록 후 `False` 반환.

---

## 3. Idiomatic Transformation Rules
1. **표준 email.message 사용**: 레거시의 무거운 `htmlMimeMail5.php` 대신 Python 3의 견고한 표준 라이브러리 `email.mime` 및 `smtplib` 전면 적용.
2. **Mocking & Spooling**: 단위 테스트 및 개발 시 실제 메일 서버 없이도 발송 내역을 검증할 수 있는 `in_memory_spool` 모드 제공.
