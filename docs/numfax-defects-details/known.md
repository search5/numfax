# 이미 확인된 결함 (중복 보고 금지, 변형이나 추가 사례는 보고)
K01 관리자 화면 4종(smtp, printers, storage, saml)이 request.db 부재로 연결 없는 DatabaseEngine()을 써서 저장이 DB에 반영되지 않음. 화면은 성공 표시.
K02 앱에 세션 팩토리 미등록. request.session 사용처 25곳. /login/totp 는 AttributeError.
K03 AFUserAccount 에 load_by_username, load_by_id, get_username, get_name, create_user 가 없음. WebAuthn 뷰 전체와 SAML provision 이 호출함.
K04 SAML 응답 서명, Audience, NotOnOrAfter, InResponseTo, Issuer 검증 없음. 위조 응답으로 로그인 가능.
K05 SAML 관리자 설정(SystemConfig saml_*)을 views/saml.py 가 읽지 않음. enabled 플래그도 미사용.
K06 CloudStorageManager 는 관리 화면 연결 테스트에서만 사용됨. 팩스 업로드와 다운로드에 미연결. storage_* 설정은 cron 이 읽지 않음.
K07 CoverStudioService 를 호출하는 곳이 없음.
K08 TOTP 활성화 UI 경로 없음. /login/totp?setup=1 과 action=disable 미처리. QR, 백업코드 표시 화면 없음. qrcode 의존성 없음.
K09 WebAuthn DDL 이 MySQL 전용 문법이라 SQLite 에서 실패하고 except pass 로 은폐됨. 서비스가 연결 없는 엔진을 사용함.
K10 login_post_view 에 admin/password 하드코딩 우회. 시드 관리자 비밀번호 평문 password.
K11 /inbox 템플릿의 /archive/move/{id}, /delete/{id} 링크가 404. /ajax/archivefax 404.
K12 namifax/cli/faxrcvd.py:166 의 OCR 호출에서 faxname 미정의(F821).
K13 helpers.py:275-281 MailerService.set_cc, set_bcc 없음, attach_file(filename=) 인자 불일치.
K14 ARCHITECTURE.md 매트릭스가 src/avantfax 경로를 가리키고 README.md 가 0바이트. src/avantfax 와 src/namifax 가 이중 트리.
K15 테스트가 대부분 MagicMock, DummyRequest 기반이라 위 결함을 못 잡음. 골든 마스터는 폼 필드 구조만 비교.
K16 mypy: web/views/*.py 에 존재하지 않는 메서드 호출(del_fax, archivefax, update_settings, get_dynconf, load_category, rename), ocr.py:140 과 webauthn.py 의 QueryResult 반복 불가.
