# 3라운드 D 영역 점검 결과 (파일 단위 전수 정독)

## 읽은 파일과 줄 수 (src/namifax 기준, 전부 처음부터 끝까지 읽음)
services/smtp_settings.py 180, storage_lifecycle.py 127, cloud_storage.py 233, printer.py 147, totp.py 101, cover_studio.py 122, webauthn.py 258, saml.py 156, ocr.py 160, scheduler.py 156,
auth/__init__.py 23, auth/pam.py 75, auth/password.py 73, common/__init__.py 42, common/helpers.py 464, common/upload.py 155, common/validators.py 230 (합계 2702줄).
대조용으로 추가로 읽음: NEW_FEATURES_PLAN.md, specs/39~47, legacy includes/FileUpload.php, functions.php, PWAuth.php, PAMAuth.php, views/webauthn.py, views/auth.py(로그인/TOTP), views/admin.py(smtp/storage/saml 일부), cli/cron.py, services/mailer.py 일부, db/engine.py, db/schema.py 일부.
실험은 모두 scratchpad/agent-r3-d/work 에서 NAMIFAX_DB_PATH 를 그 하위로 지정해 실행했고, 외부 네트워크 요청은 없음(boto3 는 클라이언트 생성만, 가짜 클라이언트로 동작 확인).

## 명세 항목별 구현 대조표
| 명세 | 요구 항목 | 코드 상태 |
|---|---|---|
| 39 | SmtpConfig/get_settings/save_settings/test_connection | 구현(함수 존재). 호스트 유효성 검증 없음, 포트 비숫자는 ValueError (ADM-18 범위) |
| 39 | MailerService.get_active_mailer(engine=None) | 없음. from_settings 만 있고 engine=None 이면 DB 를 읽지 않음. from_name 이 메일에 반영되지 않음 -> R3D-27 |
| 39 | /admin/smtp 403, save/test | 뷰 존재(K01 등 기존 결함) |
| 40 | purge_local_tiffs | 구현. 단 PDF 유효성 검증이 크기 > 0 뿐 -> R3D-02 |
| 40 | purge_expired_faxes (FaxArchive/ArchiveIn/ArchiveOut, 로컬, 원격) | FaxArchive 만. 실패 은폐 -> R3D-03 |
| 40 | StorageLifecyclePolicy.remote_sync_delete, delete_remote_tiff_only | 필드만 있고 미사용 -> R3D-04 |
| 40 | 생성자 인자 spool_dir, run_storage_lifecycle_job, APScheduler 자정 실행 | spool_dir 은 archive_dir 로 이름이 다름(R3D-41), run_storage_lifecycle_job 없음, 스케줄러에 lifecycle 잡 없음(COR-23 와 같은 원인) |
| 41 | StorageProvider 5개 메서드, Local, S3Compatible | 구현 |
| 41 | Presigned URL 발급, GCS(HMAC/서비스계정/Project ID) | 없음. GCS 는 endpoint 미설정으로 AWS 로 감 -> R3D-05 |
| 41 | CloudStorageService 명칭 | CloudStorageManager (R3D-41) |
| 41 | 연결 테스트의 읽기/쓰기/삭제 권한 진단 | head_bucket 만(ADM-24 범위) |
| 42 | RAW 9100 전송, test_print | 구현 |
| 42 | LPD/IPP 어댑터 | 없음, test_print 는 protocol 무시 -> R3D-25 |
| 42 | parse_fax_tags/process_print_job, 큐 등록, 태그 마스킹 제거, Draft 저장 | 이름 다름(extract_fax_tags/process_inbound_print_job), 큐 등록/마스킹/Draft 저장 없음 -> R3D-26 (큐 미등록은 COR-26) |
| 43 | generate_secret/uri/verify_code/enable/disable/verify_user_login | 구현. 재사용 방지, fail-open -> R3D-08, 09, 10 |
| 43 | /settings/security UI, 백업코드 bcrypt(계획서) | UI 없음(K08), 평문(SEC-07) |
| 44 | save_template/render_template/get_supported_tags | 구현 |
| 44 | PDF 템플릿 태그 치환, 썸네일 미리보기, 이름변경/활성화/다운로드 | PDF 는 치환 없이 원본 반환, 썸네일/이름변경/활성화 없음(서비스 계층에 없음) -> R3D-19, 20 |
| 45 | 등록/인증 옵션, 검증, list/delete | 구현. 등록 검증 결과 변환 버그, sign_count 갱신 불가 -> R3D-11, 12, 13 |
| 45 | public_key Base64url 저장 | hex 로 저장(명세와 다름, views 와는 일관) |
| 46 | metadata, AuthnRequest, process_saml_response, provision_or_get_user | 구현. XML 이스케이프, 속성 매핑 -> R3D-14~18 |
| 46 | 속성 email/username/display_name, default_role | username, role, default_role 미사용 -> R3D-17 |
| 47 | extract_text_from_image/tiff, index_fax, search_faxes, get_ocr_text | 구현(엔진 연결 문제는 K16/ADM-15) |
| 47 | confidence 평균, FULLTEXT 인덱스, 수신함/아카이브 검색, faxrcvd 연동 | confidence 미기록, FULLTEXT 없음, OcrService 호출자 없음 -> R3D-23, 24 |
| 기존 | common/FileUpload, FormRules, helpers, auth/PWAuth/PAM | 레거시 대조 결과 R3D-30~38, 40 |

## 결함 목록
(총 41건: 높음 7, 중간 17, 낮음 17. 치명 0)

### R3D-01 [높음] S3 delete_fax 의 폴백 prefix 가 슬래시 없이 "fax{fid}" 여서 다른 팩스 객체까지 삭제
- 위치: services/cloud_storage.py:194-202
- 증상: fax1/ 아래 객체가 없으면 `Prefix="fax1"` 로 재조회해 fax10/, fax12/, fax100/ 등 전혀 다른 팩스의 객체를 삭제한다. 또 delete_objects 응답의 Errors 를 검사하지 않고 True 를 반환한다. list_objects_v2 는 1000건까지만 조회(페이지네이션 없음), delete_objects 는 1000건 제한.
- 재현: 가짜 클라이언트(객체 fax10/fax.pdf, fax12/fax.pdf, fax100/fax.tif)로 delete_fax(1) 호출 -> True 반환, 세 객체 모두 삭제 목록에 들어감. delete_objects 가 Errors(AccessDenied)를 돌려줘도 True.
- 확인 수준: 재현 (가짜 클라이언트)

### R3D-02 [높음] purge_local_tiffs 가 변환 실패 시 생기는 14바이트 가짜 PDF 를 "유효한 PDF"로 보고 원본 TIFF 를 삭제
- 위치: services/storage_lifecycle.py:48 (+ common/helpers.py tiff2pdf 의 스텁 PDF 기록)
- 증상: 안전장치가 "PDF 존재 and 크기 > 0" 뿐이다. COR-15 의 스텁 PDF(`%PDF-1.4\n%EOF\n`)가 크기 > 0 이라 통과하고, 유일한 원본 TIFF 가 영구 삭제된다. 명세(계획서 3.9)의 "S3/GCS 업로드가 확인된 원본 TIFF" 조건도 없어 클라우드 업로드 실패 시에도 삭제된다. 수신 팩스 영구 유실.
- 재현: 디코딩 불가능한 fax.tif(30일 전 mtime)로 tiff2pdf() 호출 -> True, fax.pdf 14바이트. purge_local_tiffs(7) -> purged_count 1, fax.tif 삭제됨.
- 확인 수준: 재현

### R3D-03 [중간] purge_expired_faxes 가 원격/로컬 삭제 실패를 삼키고 DB 행은 지움
- 위치: services/storage_lifecycle.py:98-112
- 증상: rmtree(ignore_errors=True), delete_fax 예외와 False 반환 모두 무시한 채 `DELETE FROM FaxArchive` 를 실행한다. 원격 삭제가 실패(네트워크, 권한)하면 DB 행이 사라져 재시도 대상이 없고 원격 객체가 영구 고아가 된다(법적 보존/삭제 요구 위반). 또 fax 마다 아카이브 전체를 os.walk 해 O(팩스 수 x 디렉터리 수). DELETE 결과(executed)도 확인하지 않고 count 를 올린다.
- 확인 수준: 추론(코드 읽기)

### R3D-04 [중간] StorageLifecyclePolicy 의 remote_sync_delete, delete_remote_tiff_only 가 어디에서도 사용되지 않음
- 위치: services/storage_lifecycle.py:14-15, 117-126
- 증상: 명세 40 §2.2(3), 계획서 3.9 의 REMOTE_SYNC_LIFECYCLE / REMOTE_PURGE_TIFF_ONLY / REMOTE_KEEP_FOREVER 모드가 구현되지 않았다. remote_sync_delete=False 여도 storage_provider 가 있으면 항상 원격 삭제하고, delete_remote_tiff_only 는 무시되며, run_lifecycle 은 policy 의 이 두 필드를 읽지 않는다(원격 TIFF 만 삭제하는 코드 자체가 없음).
- 확인 수준: 재현(코드에서 참조 없음 확인)

### R3D-05 [중간] GCS 유형이 endpoint 를 채우지 않아 AWS S3 로 접속, GCS 전용 설정과 Presigned URL 없음
- 위치: services/cloud_storage.py:131-143, 225-233
- 증상: storage_type=GCS 여도 S3CompatibleStorageProvider 에 endpoint_url 이 비어 있으면 boto3 기본 AWS 엔드포인트로 간다(명세 §3.8 은 https://storage.googleapis.com). Project ID, 서비스 계정 JSON 인증(google-cloud-storage), generate_presigned_url(명세 41 §2.2, 계획서 3.8) 모두 없다.
- 재현: GCS + HMAC 키로 get_provider()._get_client().meta.endpoint_url -> `https://s3.ap-northeast-2.amazonaws.com`. hasattr(provider, "generate_presigned_url") -> False.
- 확인 수준: 재현

### R3D-06 [중간] download_file 이 파일명만 있는 target_path 에서 예외(FileNotFoundError)를 던짐
- 위치: services/cloud_storage.py:71-73(로컬), 160(S3) — `os.makedirs(os.path.dirname(target_path))` 가 try 밖
- 증상: target_path="out.pdf" 이면 dirname 이 "" 라 makedirs("") 가 예외. 반환형 bool 계약이 깨지고 호출자는 False 만 기대한다.
- 재현: LocalStorageProvider.download_file("a/b.bin", "out.bin") -> FileNotFoundError: ''.
- 확인 수준: 재현

### R3D-07 [낮음] boto3 클라이언트에 타임아웃/재시도 설정이 없음
- 위치: services/cloud_storage.py:142
- 증상: botocore 기본 connect/read 60초, legacy 재시도 5회. 엔드포인트가 응답 없으면 관리자 "연결 테스트"나 수명주기 배치가 수 분간 멈춘다(요청 스레드 점유).
- 재현: 클라이언트 meta.config -> connect_timeout 60, read_timeout 60, retries legacy.
- 확인 수준: 재현(설정값 확인)

### R3D-08 [높음] TOTP 검증이 DB 오류에 fail-open: 오류면 2FA 없이 통과
- 위치: services/totp.py:34-38, 73-78
- 증상: `records = ... if res.executed else []` 후 `if not records: return True`. 쿼리가 실패(DB 잠김, 연결 끊김, 테이블 없음)하면 verify_user_login 이 True, is_totp_enabled 가 False 를 반환해 2FA 를 요구하지 않고 로그인시킨다(F1-04 의 5초 잠김 같은 상황과 결합 가능). "행 없음"과 "조회 실패"를 구분하지 않는다.
- 재현: query 가 executed=False 를 돌려주는 엔진으로 TotpService 생성 -> 활성화된 사용자 uid 5 에 대해 verify_user_login(5, "000000") True, is_totp_enabled(5) False.
- 확인 수준: 재현

### R3D-09 [중간] TOTP 코드 재사용 가능, 시도 횟수 제한 없음
- 위치: services/totp.py:24-31, 71-100
- 증상: RFC 6238 §5.2 의 "검증된 OTP 는 1회만" 을 지키지 않는다. 같은 코드를 30초 안에 몇 번이든 재사용 가능(훔친 코드 재생). 또 `/login/totp` 에 실패 횟수 제한/잠금이 없어(SEC-10 은 비밀번호 로그인 기준) 6자리 코드 무차별 대입이 세션 유지 동안 무제한.
- 재현: enable_totp 후 같은 코드로 verify_user_login 을 두 번 호출 -> 둘 다 True.
- 확인 수준: 재현(재사용), 추론(무차별 대입)

### R3D-10 [낮음] TOTP 입력 정규화 불일치와 비원자적 갱신
- 위치: services/totp.py:30-31, 52-58, 92-98
- 증상: (1) 인증 앱이 "123 456" 처럼 띄어 보여 주는 코드를 사용자가 그대로 입력하면 거부(내부 공백 미제거). (2) 전각 숫자 "１２３４５６" 는 pyotp 의 NFKC 비교로 통과(입력 정규화 일관성 없음). (3) enable_totp 는 DELETE 후 INSERT 사이에 실패하면 행이 없어져 2FA 가 조용히 꺼짐(fail-open). (4) 백업코드 소모가 읽고-수정-쓰기라 동시 요청 두 개가 같은 코드로 모두 성공. (5) disable_totp 는 현재 코드/비밀번호 재확인 없음(서비스 계층).
- 재현: 공백 포함 코드 False, 전각 코드 True 확인.
- 확인 수준: 재현((1)(2)), 추론((3)~(5))

### R3D-11 [높음] WebAuthn 등록 검증이 credential_id(바이트)를 UTF-8 로 디코딩해 거의 항상 예외
- 위치: services/webauthn.py:107
- 증상: verification.credential_id 는 임의 바이트인데 `.decode("utf-8")` 한다. 실제 인증기의 credential id 는 UTF-8 이 아니므로 UnicodeDecodeError 가 나고 뷰가 400 으로 돌려준다 -> 패스키 등록이 사실상 전부 실패. 저장/조회 키는 Base64url(명세 45, 인증 시 base64url_to_bytes(cid))이어야 하므로 bytes_to_base64url 을 써야 한다. (K03/K09/K16 의 호출/엔진 결함과는 별개 원인이며, 그것을 고쳐도 남는다.)
- 재현: os.urandom(32).decode("utf-8") -> UnicodeDecodeError(확률적으로 거의 항상). 설치된 webauthn 3.0.1 의 verify_registration_response 가 bytes credential_id 를 반환함을 코드로 확인.
- 확인 수준: 재현(디코딩), 추론(실제 인증기 흐름)

### R3D-12 [높음] sign_count/last_used_at 갱신이 NOW() 를 써서 SQLite 에서 항상 실패하고 예외를 삼킴
- 위치: services/webauthn.py:251-258
- 증상: SQLite 에는 NOW() 함수가 없다("no such function: NOW"). except: pass 로 은폐되어 sign_count 가 영원히 갱신되지 않는다. 복제된 인증기 탐지(명세 45 "sign_count 증가 검증으로 복제 공격 차단")가 무력화되고, sign_count 가 0 으로 남는 한 동일 assertion 재전송이 가능하다. last_used_at 도 기록되지 않는다. delete_credential 도 영향 행 수를 보지 않고 True 반환.
- 재현: sqlite3 에서 `SELECT NOW()` -> no such function: NOW.
- 확인 수준: 재현

### R3D-13 [중간] WebAuthn 사용자 검증(UV) 미요구, 중복 등록 방지 없음
- 위치: services/webauthn.py:79-90, 99-106, 154-162
- 증상: 패스워드리스 로그인(단일 요소)인데 UV 를 PREFERRED 로 요청하고 검증도 require_user_verification=False 라서, PIN/생체 없이 키 터치만으로 로그인된다(분실/탈취된 보안키 단독으로 계정 접근). 등록 옵션에 exclude_credentials 가 없어 같은 인증기를 반복 등록할 수 있고(UNIQUE 위반 시 500/400), resident key(discoverable) 요구도 없어 명세의 "username 없는 discoverable credential" 흐름이 일부 인증기에서 동작하지 않는다.
- 확인 수준: 추론

### R3D-14 [높음] SAML AuthnRequest 와 메타데이터를 f-string 으로 만들어 & 등이 이스케이프되지 않아 XML 이 깨짐
- 위치: services/saml.py:40, 65-71
- 증상: idp_sso_url, sp_entity_id, sp_acs_url 등에 `&`(쿼리스트링), `"`, `<` 가 있으면 not well-formed XML 이 된다. IdP 에 전달되는 AuthnRequest 가 파싱 실패하고, 메타데이터도 IdP 가 받아들이지 못한다. 설정값 주입 지점이므로 관리자 입력이 XML 구조를 바꿀 수도 있다.
- 재현: idp_sso_url="https://accounts.google.com/o/saml2/idp?idpid=C0123&x=1&y=2" -> AuthnRequest 를 defusedxml 이 "not well-formed (invalid token)" 으로 거부. sp_entity_id="https://x/a?b=1&c=2" 로 만든 메타데이터도 동일.
- 확인 수준: 재현

### R3D-15 [중간] idp_sso_url 에 이미 쿼리가 있으면 "?" 를 또 붙여 잘못된 URL 을 만든다
- 위치: services/saml.py:82
- 증상: Google Workspace(명세가 지원 대상으로 명시)의 SSO URL 은 `...?idpid=C0123` 형태다. 결과가 `...idp?idpid=C0123&x=1?SAMLRequest=...` 가 되어 SAMLRequest 파라미터가 idpid 값에 붙고 요청이 유실된다. 또한 RelayState 길이 제한(SAML 규격 80바이트)을 검사하지 않는다.
- 재현: 위 URL 로 create_authn_request()["redirect_url"] 출력 확인.
- 확인 수준: 재현

### R3D-16 [중간] 빈 NameID 도 성공으로 처리하고 빈 사용자명 계정 조회/생성으로 이어짐
- 위치: services/saml.py:113-114, 130-152
- 증상: NameID 가 없거나 공백이면 name_id "" 로 success=True 를 반환한다. provision_or_get_user("") 는 username "" 으로 조회하고, JIT 가 켜져 있으면 사용자명이 빈 계정을 생성하려 한다(email 은 "@local"). NameID 부재는 오류여야 한다. 또 `.//saml:Subject/saml:NameID` 로 문서 어디의 Subject 든 매칭하고(Assertion 여러 개/래핑 구조 미구분), 이메일 NameID 의 local-part 만 쓰는 F3-16 과 별개로 name_id 형식(Format)을 보지 않는다.
- 재현: NameID 빈 Response -> `{'success': True, 'name_id': '', 'attributes': {}}`.
- 확인 수준: 재현(파싱), 추론(프로비저닝)

### R3D-17 [중간] SAML 속성 매핑이 명세와 달라 Entra ID/Okta 실속성을 못 읽고 default_role/role 을 무시
- 위치: services/saml.py:116-123, 136-139
- 증상: 명세 46 은 email/username/display_name(계획서는 Role)을 매핑하라고 한다. 코드는 `email`, `displayName`, `name` 이라는 짧은 이름만 보고 `username`·role 은 무시한다. Entra ID 는 `http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress` 같은 URI 이름으로 보내므로 이메일이 매칭되지 않아 `f"{username}@local"` 가짜 주소가 저장된다. 다중 값 속성은 첫 값만 취한다(그룹 매핑 불가). SAMLSettings.default_role 은 어디에서도 쓰이지 않고 JIT 계정은 항상 일반 사용자로 만들어진다.
- 재현: URI 이름의 emailaddress 속성과 다중 값 groups 를 넣은 응답 -> attributes 에 URI 키 그대로, groups 는 'g1' 만.
- 확인 수준: 재현

### R3D-18 [낮음] SP 메타데이터가 WantAssertionsSigned="false", KeyDescriptor 없음
- 위치: services/saml.py:39-55
- 증상: 계획서 3.4 는 메타데이터에 X.509 인증서 포함을 요구하나 없고, WantAssertionsSigned 를 false 로 광고해 IdP 가 서명 없는 Assertion 을 보내도 되는 것으로 오해하게 한다(K04 의 서명 미검증과 결합해 설정 차원에서도 보안 광고가 반대). SLS 는 HTTP-Redirect 만 광고하고 SingleLogoutService 응답 처리는 서비스 계층에 없다.
- 확인 수준: 재현(메타데이터 출력 읽기)

### R3D-19 [중간] 커버 .ps 렌더링이 한글 등 비 latin-1 값에서 UnicodeEncodeError 로 터지고, .pdf 는 태그 치환 없이 그대로 반환
- 위치: services/cover_studio.py:111-122
- 증상: 템플릿을 latin-1 로 디코딩/인코딩하므로 수신자명이나 comments 에 한글이 있으면 `ps_text.encode("latin-1")` 이 예외를 던진다(try 없음 -> 커버 생성 500). 명세가 지원 형식으로 내세운 .pdf 는 context 를 적용하지 않고 원본을 반환한다(태그 기능 없음). 썸네일 미리보기, 이름 변경, 활성화/비활성화는 서비스 계층에 없다. (ADM-13 의 PS 주입/토큰 충돌과는 별개.)
- 재현: `(XXXX-to) show` 템플릿에 {"to_person": "홍길동"} -> UnicodeEncodeError 'latin-1' codec can't encode characters.
- 확인 수준: 재현

### R3D-20 [중간] HTML 커버: 디코딩 오류 무시로 EUC-KR 템플릿 훼손, Jinja 오류 시 원본 템플릿을 조용히 반환, autoescape 없음
- 위치: services/cover_studio.py:101-108
- 증상: `decode("utf-8", errors="ignore")` 라 EUC-KR/CP949 로 저장된 한국어 템플릿이 조용히 깨진다("안녕 {{ to_person }}" -> 글자 소실). 템플릿 문법 오류면 except 로 raw_content(치환 안 된 `{{ }}` 그대로)를 반환해 고객에게 깨진 커버가 발송된다. jinja2.Template 은 autoescape 기본 꺼짐이라 comments 의 `<script>` 등이 그대로 HTML 에 들어간다.
- 재현: EUC-KR 바이트 템플릿 렌더링 결과 `b'\xc8\xb3 x'`(한글 손실), 문법 오류 템플릿은 원문 반환, comments `<script>alert(1)</script>` 가 이스케이프 없이 출력.
- 확인 수준: 재현

### R3D-21 [낮음] save_template 이 DB 등록 실패를 확인하지 않고 성공 + 엉뚱한 cover_id 를 반환
- 위치: services/cover_studio.py:66-72
- 증상: INSERT 결과(executed)를 보지 않고 get_insert_id() 를 호출한다. 엔진은 실패 시 `_last_insert_id` 를 갱신하지 않으므로 이전에 다른 테이블에 넣은 행의 id 가 cover_id 로 반환되고 "saved and registered successfully" 가 표시된다. 파일은 디스크에 남아 고아가 된다. 파일 크기 상한, 동일 이름 덮어쓰기 확인도 없다.
- 확인 수준: 추론(engine.py 의 _last_insert_id 동작 기반)

### R3D-22 [중간] Tesseract 미설치/오류를 빈 문자열로 삼켜 index_fax 가 "성공"으로 끝남
- 위치: services/ocr.py:40-48, 57-63, 75-85
- 증상: pytesseract.TesseractNotFoundError, 타임아웃, 언어 데이터 없음 모두 `except Exception: return ""`. extract_text_from_tiff 는 success=True 와 빈 text 를 돌려주고 index_fax 는 True 를 반환한다. 호출자는 OCR 이 된 것으로 알고, 운영자는 원인을 알 수 없다(로그 없음). 명세 47 의 fail-safe 는 "예외 미전파" 이지 "성공 위장" 이 아니다.
- 재현: pytesseract.image_to_string 을 TesseractNotFoundError 로 교체 후 index_fax("f1","p.tif",1) -> True.
- 확인 수준: 재현

### R3D-23 [낮음] OCR: confidence 미기록, 언어 고정(eng), 타임아웃/페이지 상한 없음, FULLTEXT 없음, LIKE 와일드카드 미이스케이프
- 위치: services/ocr.py:13-14, 40-48, 100-130
- 증상: (1) confidence 컬럼이 항상 0.0(image_to_data 미사용, 명세 "평균 인식 신뢰도"). (2) lang 기본 "eng" 이고 설정 경로가 없어(레거시 OCR_LANGUAGE 상수 있었음) 한글 팩스는 인식되지 않는다. (3) pytesseract timeout 미지정, 페이지 수 상한 없어 수백 쪽 TIFF 가 요청/훅을 오래 붙잡는다. (4) 명세의 FULLTEXT 인덱스 DDL 없이 `LIKE '%kw%'` 전체 스캔. (5) 키워드의 `%`, `_` 를 이스케이프하지 않아 "100%" 가 모든 행에 매치되고 snippet 도 어긋남. limit 상한도 없음.
- 확인 수준: 추론(코드 읽기; (5)는 K16 때문에 실행 검증 불가)

### R3D-24 [중간] OcrService 호출자가 없고 faxrcvd 가 쓰는 helpers.ocr_faxcontent 는 항상 None 스텁
- 위치: common/helpers.py:460-462, services/ocr.py 전체
- 증상: src 전체에서 OcrService 를 참조하는 코드가 없어 index_fax/search_faxes 가 수신 파이프라인과 수신함/아카이브 검색(명세 47 §1, 계획서 3.6 "OCR 텍스트 추출 순차 실행")에 연결되어 있지 않다. 레거시 ocr_faxcontent 는 tiffsplit + tesseract 로 구현되어 있었는데 포팅본은 `return None` 이라 faxrcvd 의 OCR 결과는 항상 비어 있다. (COR-27/ADM-15 는 엔진/저장 결함, 이 항목은 호출 지점 부재와 스텁.)
- 확인 수준: 재현(grep 으로 호출자 0건)

### R3D-25 [중간] 네트워크 프린터: LPD/IPP 전송 어댑터 없음, test_print 가 protocol 을 무시하고 항상 RAW+PJL 전송
- 위치: services/printer.py:66-103
- 증상: 명세 42 §3.1 의 LPD/IPP 지원이 없다. test_print(host, port, protocol) 은 protocol 을 읽지도 않고 RAW 페이로드(PJL+PostScript)를 그대로 보내므로, LPD(515)/IPP(631)로 등록한 프린터에 프로토콜 위반 바이트가 전송되고 "성공" 메시지가 나온다. RAW 전송은 sendall 후 응답/오류(프린터 오프라인 시 버퍼링)를 확인하지 않는다. queue_name 은 어디에도 쓰이지 않는다. PJL 헤더는 비 PostScript 프린터에서 쓰레기 출력.
- 확인 수준: 재현(코드 읽기로 확정)

### R3D-26 [낮음] print-in: 여러 태그 중 첫 번째만 사용, 번호 미정규화, 마스킹/Draft 저장 없이 "Saved to drafts" 메시지
- 위치: services/printer.py:106-147
- 증상: `[[FAX: A]] ... [[FAX: B]]` 는 A 만 발송하고 B 는 조용히 버린다. 번호는 `02-123-4567 ` 처럼 공백/괄호가 그대로 destination 이 된다(clean_faxnum 미적용, 정규식의 `\s` 때문에 줄바꿈 포함 가능). 계획서의 "태그 텍스트는 최종 팩스에서 마스킹 제거" 미구현. 태그가 없을 때 message 는 "Saved to drafts" 라고 하지만 어디에도 저장하지 않는다. 입력이 PostScript 이면 텍스트가 `( ... ) show` 조각과 글리프 단위로 쪼개져 있어 `[[FAX:` 패턴이 사실상 매치되지 않는다(추론). 함수 이름도 명세(parse_fax_tags, process_print_job)와 다르다.
- 확인 수준: 재현(코드 읽기), 추론(PostScript)

### R3D-27 [중간] MailerService 가 설정의 from_name 을 쓰지 않고, 명세의 get_active_mailer 가 없으며 engine=None 이면 DB 를 읽지 않음
- 위치: services/mailer.py:45-78 (명세 39 §3.2), services/smtp_settings.py SmtpConfig.from_name
- 증상: 발신 표시 이름이 `f"NamiFAX <{admin_email}>"` 로 하드코딩되어 관리자가 from_name 을 바꿔도 반영되지 않는다(from_settings 는 from_name 을 전달하지 않음). 명세의 `MailerService.get_active_mailer(engine=None)` 은 없고, 대응 from_settings(engine=None) 은 기본값 `cls()` 를 돌려줘 "DB 설정 로드 후 폴백" 동작이 아니다.
- 확인 수준: 재현(코드 읽기, grep get_active_mailer 0건)

### R3D-28 [낮음] from_name 에 쉼표가 있으면 From 헤더가 두 주소로 쪼개짐
- 위치: services/smtp_settings.py:144
- 증상: `f"{config.from_name} <{config.from_email}>"` 를 그대로 헤더에 넣는다. "Acme, Inc." 같은 회사명이면 From 이 두 개의 mailbox 가 되어 일부 MTA 가 거부한다. 개행이 들어가면 ValueError 로 테스트 메일이 실패한다. 저장 시에는 from_name/from_email 을 검증하지 않아 이 상태로 저장된다.
- 재현: EmailMessage()["From"]="Acme, Inc. <a@b.com>" -> addresses = [('', 'Acme'), ('Inc.', 'a@b.com')].
- 확인 수준: 재현

### R3D-29 [낮음] SMTP 인증을 보안 모드 NONE 과 함께 허용(평문 자격 증명 전송), 비 ASCII 비밀번호는 원인 불명 예외
- 위치: services/smtp_settings.py:88-95(저장), 126-133(로그인)
- 증상: smtp_auth=true 이면서 smtp_security=NONE 이면 비밀번호가 평문으로 전송되는데 저장/테스트 어디서도 경고나 거부가 없다. 한글 등이 들어간 비밀번호는 smtplib.login 이 UnicodeEncodeError('ascii' codec...)를 내고, 화면에는 "Failed to connect to SMTP server: 'ascii' codec can't encode..." 로 표시되어 연결 문제처럼 오인된다. 또 포트와 보안 방식의 불일치(465+NONE 등)를 검증하지 않는다.
- 재현: smtplib.SMTP.login("user","비밀번호1") -> UnicodeEncodeError.
- 확인 수준: 재현

### R3D-30 [높음] FileUpload 가 클라이언트가 보낸 size/type 을 신뢰해 크기 제한과 MIME 화이트리스트가 우회됨
- 위치: common/upload.py:94, 101-109
- 증상: 레거시는 mime_content_type/finfo 로 파일 내용을 판별했는데 포팅본은 요청 dict 의 "type"(클라이언트 제공 Content-Type)을 그대로 쓴다. size 도 dict 의 값을 쓰고 실제 파일 크기를 재지 않는다. ELF 바이너리를 type=application/pdf, size=10 으로 올리면 size 100 제한과 pdf 화이트리스트를 통과한다. 이미 F2-09 에서 "FileUpload 미연결"이 보고됐으나, 연결하더라도 이 클래스로는 검증이 성립하지 않는다(별개 원인).
- 재현: 5004바이트 파일, limit_size(100), limit_mimetype(["application/pdf"]), dict{size:10,type:"application/pdf"} -> load_file True, get_filesize() 10.
- 확인 수준: 재현

### R3D-31 [낮음] FileUpload 의 오류 처리/경계 결함
- 위치: common/upload.py:55-117, 145-155
- 증상: (1) movefile 실패 시 get_error() 가 None 이라 호출자가 원인을 알 수 없다. (2) 한글 파일명 100자(300바이트)는 sanitize 후에도 255바이트 제한을 넘겨 movefile 이 조용히 False. (3) 이름이 빈 문자열이면 target 이 디렉터리 자체가 되어 copy2 가 임시파일 이름으로 디렉터리에 복사한다. (4) load_file(str 경로)는 서버의 임의 경로(/etc/hostname 등)를 받아들이고 is_uploaded_file 에 해당하는 검사가 없다(bridge_cli 같은 호출자가 경로를 넘기면 임의 파일을 업로드 대상으로 취급). (5) PHP 오류 코드 8(확장에 의해 중단)을 FU_NO_FILE 로 잘못 매핑. (6) 레거시 move_uploaded_file 은 이동이었으나 copy2 라 임시 파일이 남는다(F2-10 과 중복되는 부분 제외). (7) set_randname 은 md5(time_pid_이름)라 같은 이름을 같은 tick 에 올리면 충돌.
- 재현: (2)(3)(4)(5) 위 실험에서 확인.
- 확인 수준: 재현

### R3D-32 [낮음] FormRules 경계값/타입 결함
- 위치: common/validators.py:142, 158-162, 163-164, 226-227, 148-208
- 증상: (1) FR_NUMBER 에 리스트(`x[]=1&x[]=2`)가 오면 float() 가 TypeError 로 500. (2) "nan", "inf", "1e999", "1_0", 아랍 숫자가 숫자로 통과하고 db_ready() 가 원본 문자열 그대로 돌려줘 숫자 컬럼에 "nan" 이 들어간다(미인용 보간 시 SQL 오류). (3) required 가 공백만 있는 값("   ")을 통과시킨다. (4) 이메일 "a@b.com\n" 이 통과하고 값은 개행 포함 그대로 저장된다(검사는 strip 하지만 저장값은 원본). 한글 도메인(IDN)은 거부되고 punycode 만 통과. (5) 규칙 인스턴스를 재사용하면 이전 호출의 오류 목록/값이 남는다(process_form 이 초기화하지 않음). (6) minlen 이 빈 문자열(비필수)에는 적용되지 않는다. (7) execfunc 예외를 잡지 않는다.
- 재현: 위 실험(리스트 TypeError, nan/1e999 통과, 공백 required 통과, 개행 이메일 통과, 재사용 시 이전 오류 유지).
- 확인 수준: 재현

### R3D-33 [낮음] is_valid_date 가 비정상 연도/유니코드 숫자를 허용
- 위치: common/validators.py:38-53
- 증상: year<100 이면 무조건 +2000 이라 "0/1/1" 이 유효(2000년), "-5/2/3" 이 유효(음수 연도가 1995 로 해석). int() 가 아랍 인디아 숫자 등 유니코드 숫자를 받아 "٢٠٢٤/١/١" 이 유효. 레거시 FormRules 는 checkdate 기반.
- 재현: 위 실험에서 세 입력 모두 True.
- 확인 수준: 재현

### R3D-34 [중간] clean_faxnum 이 전각/아랍 숫자를 통과시키고 레거시와 달리 영문자를 제거
- 위치: common/helpers.py:49-53
- 증상: 정규식 `[^\d+]` 의 `\d` 가 유니코드 숫자라, 한글 IME 로 입력한 전각 숫자 "０２－１２３４－５６７８" 이 `０２１２３４５６７８` 그대로 남아 sendfax -d 와 주소록에 저장된다(HylaFAX 는 ASCII 숫자만 처리 -> 발송 실패/오발신). 레거시 clean_faxnum 은 `[^\+\w]` 로 영숫자를 유지했는데(내선/SIP/알파 번호) 포팅본은 영문자를 전부 지워 "1-800-FLOWERS" 가 "1800" 이 된다. `+` 가 어느 위치에 있든 유지("12+34").
- 재현: clean_faxnum("０２－１２３４－５６７８") -> '０２１２３４５６７８', clean_faxnum("1-800-FLOWERS") -> '1800'.
- 확인 수준: 재현

### R3D-35 [낮음] process_template 가 치환된 값 안의 토큰을 다음 값으로 다시 치환해 값이 오염됨
- 위치: common/helpers.py:106-119
- 증상: 순차 replace(count=1)라서 값에 match 토큰이 들어 있으면 그 자리가 다음 값으로 덮인다. 예: 템플릿 "A=@ B=@", values ["XX@","SECRET"] -> "A=XXSECRET B=@". 사용자 입력(회사명/코멘트)이 토큰을 포함하면 다른 필드 값이 끼어들거나 뒤 필드가 비어 버린다. (같은 함수가 cli/faxcover.py 에는 별도로 재구현되어 있음.)
- 재현: 위와 같음.
- 확인 수준: 재현

### R3D-36 [낮음] 레거시와 다르게 동작하는 잡다한 helpers
- 위치: common/helpers.py:74-79, 90-95, 128-131, 238-250
- 증상: (1) unaccent 는 NFKD->ASCII 로 한글/한자 전체를 삭제한다("홍길동 (주)" -> " ()"). 레거시는 PostScript 이스케이프(괄호, 백슬래시 등)가 목적이었는데 괄호는 이스케이프하지 않고 비 ASCII 는 지운다. (2) split_emails 는 레거시와 달리 공백/쉼표로 분할해 "Kim Ji <a@b.com>" 이 ['Kim','Ji','<a@b.com>'] 로 깨지고 decode_entity 를 적용하지 않는다. (3) get_filetype 은 확장자(`pdf`)를 돌려주는데 레거시는 MIME 타입이라 호출자 기대값과 다르다. (4) list_languages 는 8개 언어를 하드코딩하고 pt 만 있어 실제 로케일(22개, pt_BR 포함)과 불일치하며 language 입력 인자도 무시한다.
- 재현: (1)(2) 위 실험 출력.
- 확인 수준: 재현((1)(2)), 추론((3)(4))

### R3D-37 [낮음] PasswordManager.verify_password 가 NULL/비 ASCII 해시에서 예외(500)
- 위치: auth/password.py:28-32
- 증상: 저장된 해시가 None(SAML JIT 계정, 비밀번호 미설정, 삭제된 이력)이면 `hashed_password.lower()` 가 AttributeError, 해시에 비 ASCII 문자가 섞여 있으면 hmac.compare_digest 가 TypeError 를 던져 로그인 요청이 500 이 된다(인증 실패로 처리되어야 함). 빈 문자열 비밀번호도 해시가 일치하면 True(빈 비밀번호 계정 허용 여부를 호출자가 막아야 함).
- 재현: verify_password("a", None) -> AttributeError, verify_password("a", "é"*32) -> TypeError.
- 확인 수준: 재현

### R3D-38 [낮음] PWAuthBackend 가 빈 자격 증명/개행을 검사하지 않음 (PAM 백엔드와 불일치)
- 위치: auth/password.py:46-52
- 증상: PAMAuthBackend 는 빈 username/password 를 거부하지만 PWAuth 는 그대로 pwauth 에 보낸다(`nullok` 설정에서는 빈 비밀번호 계정이 통과할 수 있음 - 추론). username 에 개행이 들어 있으면 프로토콜의 두 줄 입력 구조가 깨져 비밀번호 줄이 사용자 제어 문자열로 바뀐다. 종료코드 3 이상(UID 범위/차단 등)은 모두 "pwauth exited with code N" 으로 뭉뚱그려 진단 불가.
- 확인 수준: 추론

### R3D-39 [낮음] 스케줄러: 폴백 스레드는 자정 정리를 하지 않고, 시작 실패 시 is_running 이 고정됨
- 위치: services/scheduler.py:66-68(상태 선설정), 99-118(폴백), 77-96
- 증상: (1) apscheduler 미설치(또는 apscheduler 내부 의존성 ImportError)이면 except ImportError 폴백이 phonebook 동기화만 주기 실행하고 cron_maintenance(임시파일/보관 정리)는 영원히 실행하지 않는다(경고 로그 한 줄뿐). 이 폴백은 첫 주기 대기 후에야 첫 동기화(시작 직후 미실행). (2) is_running=True 를 start 시작에 먼저 세우므로 add_job/start 가 다른 예외로 실패하면 이후 start() 는 조용히 return 하고 stop() 만 정리한다. (3) misfire_grace_time/coalesce 미설정이라 자정에 프로세스가 내려가 있으면 그날 정리를 건너뛴다. (4) job_cron_maintenance 는 run_cron 이 사용법 오류에도 0 을 반환하므로 "completed successfully" 로그가 실제 성공을 뜻하지 않는다. (F5-19 "스케줄러 운영 결함"의 세부 변형일 수 있음.)
- 확인 수준: 추론

### R3D-40 [중간] avantfaxlog 가 SysLog 테이블이 아니라 OS syslog 에만 기록
- 위치: common/helpers.py:155-165
- 증상: 레거시 avantfaxlog 는 MDBOData('SysLog')->new_entry 로 DB 시스템 로그(관리자 "System Log" 화면)에 기록했다. 포팅본은 syslog(LOCAL0)만 쓰며 실패는 무시한다(개발 환경에서는 기록이 전혀 남지 않음). 그래서 이 함수를 쓰는 모든 경로(faxrcvd 등)의 이벤트가 관리자 시스템 로그 화면에 나타나지 않는다. F3-18 의 "SysLog 에 기록 없음" 의 직접 원인이며, 만들어 둔 `msg`(접두어 포함)는 사용되지 않고 접두어 없는 text 가 기록된다.
- 확인 수준: 재현(레거시 대조, 코드 읽기)

### R3D-41 [낮음] 명세의 인터페이스 이름/시그니처와 구현이 달라 명세 기반 테스트가 실패
- 위치: services/storage_lifecycle.py:26-33, services/cloud_storage.py:225, services/printer.py:106-121
- 증상: 명세 40 은 `StorageLifecycleService(db, storage_provider, spool_dir)` 인데 코드는 archive_dir, 명세 41 의 CloudStorageService 는 CloudStorageManager(정적 팩토리), 명세 42 의 parse_fax_tags/process_print_job 은 extract_fax_tags/process_inbound_print_job, 명세 39 의 get_active_mailer 는 from_settings. 명세에 적힌 검증 기준(test_*.py)을 그대로 재현하면 AttributeError/TypeError.
- 확인 수준: 재현(이름 대조)

## 새 결함이 적은 영역
- auth/pam.py: 줄 단위로 읽었으나 새 결함은 위 R3D-38 외에 없음(python-pam 미선언은 F3-17, ctypes 분기가 pam_driver 를 못 만드는 것도 F3-17 범위).
- common/__init__.py, auth/__init__.py: 재수출 목록만 있고 결함 없음.
