# NamiFAX 저장소 결함 조사 보고서 

- 대상: https://github.com/search5/numfax (클론 시점 HEAD `e3e50c8`)
- 작성일: 2026-10-01
- 성격: 읽기 전용 조사입니다. 저장소 소스는 수정하지 않았습니다.
- 상태: 5라운드까지 반복한 조사 결과입니다. 결함 0건에는 도달하지 못했고, 수렴 판단은 2절에 적었습니다.

## 1. 한 줄 결론

레거시 AvantFAX를 이식했다는 주장과 달리, 실제로 끝까지 동작하는 기능은 극히 일부입니다. 대부분의 화면은 렌더링되지만 저장, 전송, 삭제, 권한 판정 같은 동작이 끊기거나 가짜 성공을 반환합니다. 테스트 362건이 통과한 것은 테스트가 배포 코드를 검증하지 않고, 모킹에 의존하며, 골든 마스터가 가짜 데이터를 정답으로 삼기 때문입니다.

## 2. 집계

원 보고 기준이며 라운드 간 중복은 제거하지 않았습니다. 같은 결함이 여러 영역에서 보고된 경우가 있습니다(4절 참고).

| 구분 | 치명 | 높음 | 중간 | 낮음 | 합계 |
|---|---|---|---|---|---|
| 1라운드 (영역별) | 8 | 39 | 56 | 18 | 121 |
| 2라운드 (업무 흐름별) | 0 | 47 | 39 | 19 | 105 |
| 3라운드 (파일 정독) | 0 | 21 | 83 | 88 | 192 |
| 4라운드 (마스킹 해제, 퍼징, E2E, 미정독 파일) | 1 | 3 | 16 | 14 | 34 |
| 5라운드 (2차 마스킹 해제, 잔여 정독, 레거시 페이지 대조) | 0 | 3 | 16 | 19 | 38 |
| **합계** | **9** | **113** | **210** | **158** | **490** |

별도로 조사 초기에 제가 직접 확인한 K01~K16(16건)이 있으며 `numfax-defects-details/known.md`에 있습니다. 위 합계에는 포함되지 않았습니다.

치명과 높음의 라운드별 추세는 8/39 (1라운드), 0/47 (2라운드), 0/21 (3라운드), 1/3 (4라운드), 0/3 (5라운드)입니다. 건수는 121, 105, 192, 34, 38입니다. 3라운드까지 줄던 건수가 5라운드에서 소폭 늘었는데, 4라운드부터 관점을 바꾸거나 이전에 읽지 못한 영역(테스트 코드, 문서, 레거시 페이지)을 새로 훑었기 때문입니다.

**수렴 판단**: 심각도 기준으로는 수렴에 가깝습니다. 최근 두 라운드의 신규 결함 72건 중 치명 1건, 높음 6건이고 나머지는 중간과 낮음입니다. 건수 기준으로는 수렴하지 않았습니다. 다만 현재 결함 대부분이 다른 결함을 가리고 있어서(R3A-09에서 R4U-01로 이어진 사례), 수정이 진행되면 새 결함이 계속 드러날 가능성이 큽니다. 따라서 조사를 더 반복하기보다 아래 9절의 순서로 수정한 뒤 같은 방법으로 재검증하는 편이 효율적이라고 판단해 5라운드에서 멈췄습니다.

## 3. 근본 원인 10가지

개별 결함 대부분은 아래 원인 중 하나에서 나옵니다. 수정 순서를 정할 때는 개별 항목보다 원인 단위로 접근하는 편이 효율적입니다.

**C1. 연결 없는 DB 엔진과 세션 미구성**: 앱이 `request.db`를 등록하지 않고 세션 팩토리도 등록하지 않습니다. 뷰와 서비스가 연결 없는 `DatabaseEngine()`을 만들어 쓰기를 조용히 잃어버립니다. `avantfax`와 `namifax`의 엔진 클래스가 별개라서 싱글턴도 공유되지 않습니다. 관리자 설정 저장, TOTP 강제, 패스키 저장, 회사 병합 등이 여기서 깨집니다.

**C2. 존재하지 않는 것을 호출하는 계약 불일치**: `AFUserAccount.load_by_username`, `FaxQueue.kill_job`, `DynConf` 테이블, `bcr_id` 컬럼 등 없는 메서드, 테이블, 컬럼을 참조합니다. 모킹 테스트가 이를 가립니다.

**C3. 스텁과 가짜 데이터**: `/viewfax`, `/txreport`, `/ajax/*`, refax, `create_job`(항상 1001 반환), 다운로드 PDF가 하드코딩된 샘플을 돌려줍니다. 검색 0건에도 placeholder를 보여 줍니다.

**C4. 실패를 성공으로 위장**: 예외를 삼키고 성공 메시지를 표시합니다. 설정 저장, 작업 취소, 발송, 비밀번호 변경이 모두 해당합니다.

**C5. 보안**: 비인증 SQL 인젝션, 비인증 원격 명령 실행(팩스 큐 셸 주입), Cover Studio 템플릿 주입, SAML 서명 미검증, IDOR, 반사형 XSS, CSRF 부재, 하드코딩 계정, 평문 비밀 저장, 비밀번호 만료 미적용입니다.

**C6. 데이터 손실과 훼손**: 기동할 때마다 seed와 마이그레이션이 운영 데이터를 덮어씁니다. 변환 실패한 가짜 PDF를 근거로 원본 TIFF를 삭제합니다. `fid` 기본값 1 때문에 1번 팩스가 삭제됩니다. S3 접두사 버그가 다른 팩스 객체까지 지웁니다.

**C7. 레거시 패리티와 이전 갭**: 98개 대조 항목 중 구현은 2개뿐이고 부분 60, 스텁 20, 누락 16입니다. 레거시 MySQL 데이터 이전 도구와 문서가 없고, 기존 아카이브 경로와 해시를 해석하지 못합니다.

**C8. 검증 체계의 결함**: 테스트 대부분이 배포되지 않는 `src/avantfax` 트리를 검증합니다. 골든 마스터는 폼 필드 구조만 비교하고 가짜 데이터를 정답으로 고정합니다. 하드코딩 계정으로 로그인합니다.

**C9. 배포와 패키징**: wheel에는 `namifax`만 들어 있으나 `avantfax`를 런타임에 import해서 19개 모듈이 실패하고, 폴백 앱이 떠서 모든 URL이 200 텍스트를 반환합니다. systemd 기동 경로가 개발 서버입니다. 단일 sqlite 연결을 스레드가 공유해 세그폴트가 납니다.

**C10. UI, CSS, 번역**: 빌드된 CSS에 69개 클래스가 빠져 버튼이 보이지 않습니다. 번역 문자열 68개가 전 로케일에 없고 인코딩 깨짐과 오역이 있습니다. 자동완성과 폴링 JS가 없어서 `/ajax/*` 7개가 호출되지 않습니다.

## 4. 중복 보고된 결함 (같은 원인)

- 기동 시 seed와 마이그레이션의 데이터 덮어쓰기: ADM-01, COR-02, R3F-03(변형), F4-25, F1-01, F1-02
- `send_mail`이 발송하지 않고 성공 반환: ADM-17, COR-04
- `DynConf` 테이블 없음: ADM-08, COR-08
- 주소록 검색 SQL 인젝션: SEC-01, COR-11
- 팩스 큐 셸 명령 주입: COR-10, USR-06 (실제 파일 생성으로 재현됨)
- `fid` 기본값 1 문제: F2-07, R3B-04, R3H-01
- 재전송(refax) 스텁: F2-08, F4-01
- 작업 취소가 동작하지 않고 성공 표시: F2-04, F4-14
- sysfunc 버튼 무동작: UI-03, ADM-10
- `namifax phb` 서브커맨드 실패: R3A-04, R3E-01
- wheel 설치 시 폴백 앱: R3G-01, COR-25, ADM-28, F5-02
- 관리자 삭제 보호 우회: R3A-09 (예고), R4U-01 (마스킹 해제 후 실제 성립)
- 테스트가 없는 메서드를 mock해서 통과: R4F-12 (K03, K13, K16의 은폐 원인)
- 빈 권한 목록이 무제한으로 해석됨: R3C-01, R5U-01
- 분류 삭제 후 유령 참조: R4U-03, R5U-02

## 5. 치명 등급

| ID | 제목 | 라운드 |
|---|---|---|
| ADM-01 | 앱 시작 때마다 seed/migration 이 운영 데이터를 덮어쓰거나 되살림 | 1 |
| COR-01 | 단일 sqlite 연결/커서를 여러 스레드가 공유해 인터프리터가 세그폴트 | 1 |
| COR-02 | 기동할 때마다 seed/migration 이 실제 운영 데이터를 덮어씀 | 1 |
| COR-03 | notify CLI 가 DB 에 있는 모든 사용자에 대해 AttributeError 로 종료 (발송 팩스 미보관, 통지 메일 없음) | 1 |
| COR-04 | CLI/서비스에서 나가는 모든 메일이 실제로는 발송되지 않고 성공(True)을 반환 | 1 |
| SEC-01 | 비인증 SQL 인젝션 — 주소록 검색 (UNION 기반 데이터 탈취) | 1 |
| USR-04 | 사용자별 모뎀/카테고리 기반 팩스 접근 제한이 완전히 동작하지 않음 — 타 사용자 팩스 전체 노출 | 1 |
| USR-06 | `/ajax/faxalter`가 인증 없이 접근 가능하고, 파라미터가 셸 명령에 그대로 삽입되어 명령 주입 가능 | 1 |
| R4U-01 | 관리자(uid=1) 삭제 보호 가드를 0-패딩 문자열로 우회 — 부트스트랩 관리자 소프트 삭제 가능 | 4 |

## 6. 높음 등급

| ID | 제목 | 라운드 |
|---|---|---|
| ADM-02 | 시스템 로그 화면 SQL 인젝션 (kw, year, month, day) | 1 |
| ADM-03 | 사용자 관리: 삭제가 항상 조용히 실패 (soft delete 가 NOT NULL 위반) | 1 |
| ADM-04 | 사용자 관리: any_modem 이 항상 1, 모뎀/DID/분류 권한이 저장되지 않음 | 1 |
| ADM-05 | 사용자 관리: 빈 비밀번호로 신규 사용자 생성 시 비밀번호가 'password' 로 고정, 수정 시 실패 무시 | 1 |
| ADM-06 | 관리자 자기 강등/마지막 관리자 잠금 방지 없음, 권한 변경이 기존 세션에 반영되지 않음 | 1 |
| ADM-07 | 바코드 라우팅 수정/삭제 불가 (PK 이름 불일치: barcode_id vs bcr_id) | 1 |
| ADM-08 | 동적 설정(블랙리스트) 전체 기능 불능: 서비스가 없는 테이블 DynConf 사용 | 1 |
| ADM-09 | Fax2Email 관리 화면이 규칙을 저장하지 못함 | 1 |
| ADM-10 | 시스템 기능(sysfunc) 화면: 4개 버튼 모두 무동작, 메시지는 가짜 | 1 |
| ADM-11 | 스토리지 수명주기: 음수 일수 저장 시 모든 TIFF 즉시 삭제 | 1 |
| ADM-12 | 스토리지 수명주기 서비스의 만료 삭제가 실제 팩스에 적용되지 않거나 잘못 동작 | 1 |
| ADM-13 | Cover Studio 렌더링: 샌드박스 없는 Jinja2 로 임의 코드 실행 + PS 주입 + 토큰 치환 충돌 | 1 |
| ADM-14 | print-to-fax CLI 가 '큐에 등록됨'이라 출력하지만 아무것도 큐에 넣지 않음, 실패 시에도 종료코드 0 | 1 |
| ADM-15 | OCR 인덱싱이 실제로는 아무것도 저장하지 않음 (연결된 엔진에서도) | 1 |
| COR-05 | AFAddressBook.loadbyfaxnum 이 튜플을 반환해 항상 참 -> faxrcvd/notify 가 회사/팩스번호를 생성하지 않음 | 1 |
| COR-06 | AddressBookFAX 스키마에 레거시 컬럼이 없어 팩스번호 생성, 카운터, Fax2Email 라우팅이 모두 실패 (에러는 삼켜짐) | 1 |
| COR-07 | AddressBook.abook_id 가 신규 행에서 NULL (PK 는 ab_id) -> 신규 회사는 조회/삭제 불가, delete_cid 는 True 를 반환하고 아무것도 안 지움 | 1 |
| COR-08 | DynConf 테이블이 스키마에 없음(DynamicConfig 로 생성) -> 차단(RejectCall) 규칙이 영구 동작하지 않음 | 1 |
| COR-09 | QueryBuilder.quote 가 Python bool 을 'True'/'False' 문자열로 저장 -> 계정이 비활성/비관리자가 됨 | 1 |
| COR-10 | faxqueue 명령 주입 (shell=True, 사용자 입력을 그대로 보간) | 1 |
| COR-11 | SQL 조립/이스케이프 결함 (LIKE 인젝션 재현, MySQL 백슬래시는 추론) | 1 |
| COR-12 | MySQL 백엔드가 사실상 사용 불가 (드라이버 미선언, 문법/파라미터 스타일, 스키마 전부 SQLite 전용) | 1 |
| COR-13 | DB 경로 기본값이 현재 작업 디렉터리 기준이고 CLI 훅마다 seed 까지 실행 -> 호출 위치마다 별개의 DB 가 생김 | 1 |
| COR-14 | 보관 일시(archstamp)를 '/' 구분자로 저장해 보관 기간 정리(prune)가 동작하지 않고 날짜 파싱 실패 | 1 |
| COR-15 | tiff2pdf/convert2pdf/static_preview/faxinfo 가 실패를 성공으로 위장(가짜 PDF, 빈 썸네일, 가짜 팩스 정보) + 저장소 정리 시 원본 TIFF 삭제 | 1 |
| COR-16 | faxcover: 토큰 접두어 치환으로 커버 페이지가 깨지고, DB 조회와 HTML 커버가 동작하지 않음 | 1 |
| SEC-02 | 상태 변경 AJAX/업로드 엔드포인트에 permission 미지정 → 비인증 조작 가능 | 1 |
| SEC-03 | 팩스 상세/다운로드/주석/회전 등에서 모뎀 기반 접근 제어 우회 (IDOR) | 1 |
| SEC-04 | 반사 XSS — `/ajax/deletefaxes`의 `fids` 파라미터 | 1 |
| SEC-05 | 비밀번호 만료/강제 재설정 정책이 로그인 시점에 전혀 강제되지 않음 | 1 |
| UI-01 | 설정 화면이 아무것도 저장하지 않으면서 "Settings updated successfully." 표시 | 1 |
| UI-02 | admin_layout.jinja2 가 `message` 를 렌더하지 않아 관리자 화면 다수에서 성공 피드백이 사라짐 | 1 |
| UI-03 | 시스템 기능 화면(재시작, 종료, 백업 다운로드) 버튼이 뷰와 계약이 안 맞아 전부 무동작 | 1 |
| UI-04 | 빌드된 main.css 가 템플릿과 어긋나 있어 다수 클래스가 스타일 없음 (예: 2FA 활성화 버튼이 흰 글씨 무배경) | 1 |
| UI-05 | 템플릿이 쓰는 문자열 68개가 번역 카탈로그(.pot)와 전 로케일에 없음 | 1 |
| UI-06 | 로그인하지 않은 브라우저 요청이 로그인 화면이 아니라 원시 JSON 401 을 받음 | 1 |
| UI-07 | /viewfax 가 실제 팩스 대신 하드코딩된 가짜 문서를 표시 | 1 |
| USR-01 | 아카이브 검색: 키워드/팩스ID 없이 필터링하면 결과가 항상 숨겨짐 | 1 |
| USR-02 | 검색/조회 결과가 0건일 때 가짜(placeholder) 레코드를 실제 결과처럼 표시 | 1 |
| F1-01 | 마이그레이션이 발신자 미식별 팩스를 매번 "Acme Corp 의 팩스번호(faxnumid=1)"로 귀속시킴 (COR-05 + COR-02 의 결합 변형) | 2 |
| F1-02 | 같은 마이그레이션이 발신 팩스의 modemdev 를 'ttyS0' 으로 채워 "발신" 검색과 구분 기준을 깨뜨림 | 2 |
| F1-03 | faxinfo 출력 해석 실패가 전부 무경고 "더미 팩스 정보"로 대체되어 실제 발신자와 수신 시각이 사라짐 (COR-15 의 유효 TIFF 변형) | 2 |
| F1-04 | DB 가 잠깐 잠기면(5초 초과) 훅이 종료코드 0 으로 아무 로그 없이 끝나고, 아카이브 파일만 고아로 남아 팩스가 수신함에 나타나지 않음 | 2 |
| F1-08 | 수신함이 최신 25건만 보여주고 "25 of 25" 로 표시, 26번째 이후 팩스는 웹에서 접근 불가 | 2 |
| F1-10 | 보관(아카이브)된 수신 팩스가 보관함 화면에 나타나지 않음: 결과 행을 로드하지 않고 존재하지 않는 get_company 호출 | 2 |
| F2-01 | sendfax 제출에 소유자(-o)와 발신자(-f) 바인딩이 없어 모든 작업이 서비스 계정 소유가 됨 (notify 와 이음새 단절) | 2 |
| F2-02 | 다중 수신처가 하나의 -d 문자열로 전달되어 엉뚱한 번호로 발신됨 (화면 안내/팝업/서비스 구분자 3중 불일치) | 2 |
| F2-03 | sendfax 실패를 사용자에게 알리지 않고 항상 outbox 로 성공 리다이렉트, 바이너리가 없으면 가짜 작업번호로 성공 처리 | 2 |
| F2-04 | outbox 작업 취소가 실제로는 아무것도 하지 않고 항상 성공 메시지를 표시 | 2 |
| F2-05 | outbox 가 로그인한 모든 사용자에게 전체 사용자의 송신 작업을 보여줌 (소유자 필터 없음) | 2 |
| F2-07 | 작업 수정(/ajax/faxalter)이 항상 작업 #1 을 대상으로 하고, 전달되는 faxalter 옵션도 레거시와 다름 | 2 |
| F2-08 | 재전송(refax) 모달이 아무것도 제출하지 않으면서 작업번호 1001 로 성공 처리 | 2 |
| F2-09 | 업로드 검증 부재: MIME/크기 제한 미적용(FileUpload 미연결), 빈 파일과 임의 형식 모두 sendfax 로 전달, 긴 파일명은 500 | 2 |
| F3-01 | 2FA(TOTP) 가 로그인에서 전혀 강제되지 않음: TotpService 가 연결 없는 avantfax 엔진을 사용 | 2 |
| F3-02 | 일반 사용자가 자기 비밀번호를 바꿀 수 있는 경로가 하나도 없고, 세 화면 모두 성공을 위장함 | 2 |
| F3-03 | can_del 권한이 어디에서도 검사되지 않음 (삭제 경로 3곳 + UI) | 2 |
| F3-04 | 주소록/배포목록/이메일북/모뎀 상태가 로그아웃 상태에서 그대로 조회됨 (SEC-02 의 읽기 쪽 변형) | 2 |
| F3-05 | superuser 만 있는 계정이 관리자 영역 전체에 접근하고, 관리자 폼에서 저장만 해도 is_admin 이 영구 부여됨 | 2 |
| F3-07 | 팩스 발송이 사용자별 모뎀 권한(modemdevs, any_modem)을 무시함 | 2 |
| F3-08 | 발송 시 사용자 신원(-o 사용자, -f 이메일, from_*/TSI)이 전혀 전달되지 않음 | 2 |
| F3-09 | 송신 큐(outbox)가 모든 사용자에게 전체 사용자의 작업을 노출 | 2 |
| F3-10 | 관리자 하드코딩 로그인이 비밀번호 변경, 계정 비활성화, 마지막 로그인 기록을 모두 무력화 (K10 의 변형) | 2 |
| F3-11 | 비활성화/삭제/비밀번호 변경이 이미 발급된 세션과 다른 인증 경로에 반영되지 않음 | 2 |
| F3-12 | 관리자 사용자 폼에 활성화, 비밀번호 주기, 재사용 금지, 언어 등 레거시 필드가 없어 비활성화와 만료 정책을 설정할 방법이 없음 | 2 |
| F4-01 | 팩스 재전송/답장(refax)이 스텁: 항상 잡 ID 1001 을 반환하고 아무것도 전송하지 않음 | 2 |
| F4-02 | "비밀번호 찾기"(forgot.php)가 스텁: 성공 문구만 출력하고 재설정/메일 발송 없음 | 2 |
| F4-03 | 비밀번호 만료/초기화 강제 변경 화면(pwdexpired)이 스텁: 비밀번호를 바꾸지 않고 로그인 화면으로 리다이렉트 | 2 |
| F4-04 | 대체 인증(ALTERNATE_AUTH: PAM/pwauth)과 웹서버 인증(REMOTE_USER)이 로그인에 연결되지 않음 | 2 |
| F4-05 | 이메일 → 팩스(email2fax) 기능 전체 누락 | 2 |
| F4-06 | sendfax 화면이 레거시 옵션 대부분을 폼에서도 서버에서도 처리하지 않음 | 2 |
| F4-07 | 팩스 발송 실패가 은폐되고, sendfax 가 없으면 가짜 잡 ID 로 성공 처리. 소유자(-o), 발신 이메일(-f) 미전달 | 2 |
| F4-10 | 기존 아카이브 파일 경로를 해석하지 못함: DB 의 faxpath 는 INSTALLDIR 기준 상대경로, NamiFAX 웹은 installdir="" 로 루트 기준 조회 | 2 |
| F4-12 | 팩스 다운로드가 파일이 없거나 fid 가 없어도 "합성 PDF" 를 200 으로 반환 | 2 |
| F4-14 | 아웃박스 작업 삭제가 실제로 호출할 수 없는 메서드를 쓰면서 항상 "삭제되었다" 는 메시지를 표시 | 2 |
| F4-15 | 레거시 주소록의 팩스번호/이메일이 화면에 나타나지 않고 편집 폼도 비어 있음 | 2 |
| F4-16 | AJAX 자동완성/프리필 엔드포인트가 결과가 없을 때 가짜 데이터를 반환하고, 실제 연락처의 빈 칸도 가짜 값으로 채움 | 2 |
| F4-17 | 바코드 라우팅이 영구 비활성: bardecode 헬퍼가 항상 None 을 반환 | 2 |
| F4-19 | import_archive 도구가 스텁이고 진입점에도 없음: "Imported N faxes" 만 출력 | 2 |
| F4-24 | MySQL 레거시 스키마 이전 경로가 없고, 이전 도구/문서도 없음 | 2 |
| F4-26 | 레거시 '\|' 구분자(modemdevs, didrouting, faxcats)와 수신함 모뎀 필터의 ',' 분리가 불일치 | 2 |
| F5-01 | 운영 기동 경로(systemd, namifax serve, namifax-server)가 waitress 가 아니라 wsgiref 개발 서버이고 ini 를 전혀 읽지 않음 | 2 |
| F5-02 | 임포트/앱 생성 오류가 조용히 전혀 다른 JSON 스텁 앱으로 대체됨 | 2 |
| F5-03 | DB 열기/스키마 초기화 실패를 삼키고 200 + 가짜 데이터로 서비스 계속 | 2 |
| F5-04 | 팩스 전송 결과 무시 + sendfax 바이너리 부재 시 가짜 성공 + 업로드 임시파일 미삭제 | 2 |
| F5-05 | 테스트 48개 파일 중 다수가 wheel 에 포함되지 않는 src/avantfax 트리를 검증 | 2 |
| F5-06 | Web golden master 가 자기 참조적이며 가짜 데이터를 "정답"으로 고정 | 2 |
| R3B-01 | 새 이메일 연락처 폼이 숨은 id=1 을 보내 "추가"가 1번 연락처를 덮어쓰고 "삭제"가 1번을 지움 | 3 |
| R3B-02 | 배포목록 도우미가 회사 ID 를 목록 항목으로 저장하고, 레거시 "fnid\|팩스번호" 형식은 ajax/dlist 와 목록 화면이 해석하지 못함 | 3 |
| R3B-03 | /assign 모달: 회사명 변경 분기는 회사를 로드하지 않아 항상 무동작이고, 회사 병합(reassign)은 db 없는 인스턴스라 항상 실패하는데 결과는 조용함 | 3 |
| R3B-04 | 필수 파라미터가 없으면 fid 가 "1" 로 기본값이 되어, fid 없는 POST /delete 가 1번 팩스를 삭제함 | 3 |
| R3C-01 | 모뎀/라우트 목록이 비어 있거나 None 이면 접근 제한이 사라짐 (fail-open) | 3 |
| R3D-01 | S3 delete_fax 의 폴백 prefix 가 슬래시 없이 "fax{fid}" 여서 다른 팩스 객체까지 삭제 | 3 |
| R3D-02 | purge_local_tiffs 가 변환 실패 시 생기는 14바이트 가짜 PDF 를 "유효한 PDF"로 보고 원본 TIFF 를 삭제 | 3 |
| R3D-08 | TOTP 검증이 DB 오류에 fail-open: 오류면 2FA 없이 통과 | 3 |
| R3D-11 | WebAuthn 등록 검증이 credential_id(바이트)를 UTF-8 로 디코딩해 거의 항상 예외 | 3 |
| R3D-12 | sign_count/last_used_at 갱신이 NOW() 를 써서 SQLite 에서 항상 실패하고 예외를 삼킴 | 3 |
| R3D-14 | SAML AuthnRequest 와 메타데이터를 f-string 으로 만들어 & 등이 이스케이프되지 않아 XML 이 깨짐 | 3 |
| R3D-30 | FileUpload 가 클라이언트가 보낸 size/type 을 신뢰해 크기 제한과 MIME 화이트리스트가 우회됨 | 3 |
| R3E-02 | faxcover: 번들 표지 템플릿(cover.ps, 바이너리 포함)을 UTF-8 텍스트로 읽고 써서 출력이 손상됨 | 3 |
| R3E-03 | faxcover: PostScript 문자열 정화/이스케이프가 없어 괄호, 백슬래시가 PS 구문을 깨고 PS 코드 주입이 가능함 | 3 |
| R3F-01 | AFAddressBook 을 기본 생성하면 reassign 과 delete_companyfaxids 가 조용히 실패하고, 회사 삭제가 팩스번호와 이메일 행을 고아로 남김 | 3 |
| R3F-02 | 쓰기 실패 시 롤백하지 않아 트랜잭션과 쓰기 잠금이 열린 채 남고 다른 프로세스가 "database is locked" 를 받음 | 3 |
| R3F-03 | seed 의 `INSERT OR REPLACE ... fid=1` 이 수신함이 비어 있는 기존 DB 에서 실제 보관 팩스 #1 을 데모 레코드로 덮어씀 (COR-02, ADM-01 의 다른 원인 변형) | 3 |
| R3F-04 | 폴백 웹앱 `/api/inbox/list` 가 종료되지 않는 무한 루프에 빠지고 메모리가 계속 늘어남 | 3 |
| R3G-01 | wheel/ini 로 배포하면 사이트 전체가 "Ready" 텍스트 스텁이 되고 모든 URL 이 200 | 3 |
| R3G-02 | 폴백 JSON 로그인이 올바른 비밀번호에서도 AttributeError 로 죽고, 시드 계정은 로그인 자체가 불가 | 3 |
| R3H-01 | POST /delete 가 fid 없이도 1번 팩스를 삭제 | 3 |
| R4F-12 | 테스트가 클래스에 없는 메서드를 mock 해서, 운영에서 AttributeError 가 나는 경로가 통과함 | 4 |
| R4U-02 | 비밀번호 재사용 금지 정책이 불린→문자열 왕복 버그로 "항상 재사용 허용"으로 반전됨 | 4 |
| R4Z-01 | 텍스트 파라미터에 멀티파트 파일 파트를 보내면 40개 라우트가 500 | 4 |
| R5L-06 | 주소록 편집이 팩스번호별 속성 편집과 복수 번호 관리를 지원하지 않음 | 5 |
| R5U-01 | 모뎀/분류/DID 가 하나도 없는 사용자는 아카이브 검색에서 제한 없이 전체 팩스를 본다 (빈 목록 = 무제한) | 5 |
| R5U-07 | 재전송(/refax) 모달이 원본 팩스 문서를 전혀 첨부하지 않고 fid 를 사용하지 않음 | 5 |

## 7. 조사 방법과 한계

- 1라운드: 영역별 5개(인증과 보안, 관리자, 사용자 화면, 코어, UI) 독립 점검.
- 2라운드: 업무 흐름별 5개(수신, 발송, 계정과 권한, 레거시 패리티와 이전, 운영과 테스트 품질).
- 3라운드: 소스 파일 8묶음 전수 정독. 코드의 SQL 200건을 스키마에 대해 EXPLAIN으로 교차 검증했습니다.
- 4라운드: 마스킹 해제 실험(임시 패치 8건을 적용한 복제본에서 재시험), 입력 퍼징(약 53,500회 호출), 브라우저 E2E 12개 시나리오, 미정독 파일과 테스트 코드 정독.
- 각 라운드는 앞선 결함 목록을 제외 목록으로 받아 새 결함만 보고했습니다.
- 대부분 실제 앱을 임시 DB로 띄워 재현했고, 재현하지 못한 것은 '추론'으로 표시되어 있습니다.
- 공격 페이로드(셸 주입, SQL 주입)는 원칙적으로 실행하지 않았습니다. 다만 사용자 화면 에이전트가 셸 주입을 임시 파일 생성으로 재현했고 삭제했다고 보고했습니다.
- 4라운드에서도 일부는 기계 검사로만 확인했습니다: `tests/` 69개 파일 중 줄 단위로 읽은 것은 약 13개이고, 일부 소형 서비스와 PHP 브리지는 메서드 이름 대조만 했습니다. 이 환경에 php가 없어 PHP 브리지 결함은 Python 호출로 모사해 재현했습니다.
- `namifax-server` 명령이 한 환경에서 포트를 열지 않고 멈춘 현상을 관찰했으나 원인은 분석하지 못했습니다.
- Cover Studio, OCR, 실제 HylaFAX, 실제 IdP(SAML), 실제 S3/GCS와의 연동은 실환경에서 검증하지 못했습니다.
- 5라운드: 2차 마스킹 해제(패치 20건), 테스트 69개 파일 7,149줄 전수 정독, 레거시 페이지 약 67개 대조.
- 5라운드에서도 시험하지 못한 것: `cli/notify.py` 실행과 송신 후 `ArchiveOut`, 레거시 admin `conf_*` 편집 화면과 `upload_*`의 완전한 대조, `ARCHITECTURE.md` 98~215줄(DAG 절), specs 대부분의 전문 정독(식별자 추출 스크립트로 구현 존재만 대조), 요청을 번갈아 보내는 동시성 시험.
- 문서의 시험 통계 주장은 사실과 다릅니다. `ARCHITECTURE.md`의 '296/296', '374/374'는 실측과 맞지 않고(실측: `pytest tests` 362 passed, `pytest golden_master` 88 passed), '68/68, 20/20'만 사실입니다.
- 세부 증상, 위치, 재현 방법은 `numfax-defects-details/round*.md`에 있습니다.

## 8. 수정 순서 권고

결함끼리 서로 가리고 있으므로 아래 순서를 지키지 않으면 수정이 오히려 새 위험을 드러냅니다. 예를 들어 사용자 삭제 실패(ADM-03)를 먼저 고치면 관리자 삭제 보호 우회(R3A-09, R4U-01)가 실제로 발현해 기본 관리자 계정이 사라집니다.

**0단계: 즉시 차단(수정 전이라도 운영하지 말 것)**: 팩스 큐 셸 명령 주입(COR-10, USR-06), 주소록 검색 SQL 인젝션(SEC-01), 권한 없는 상태 변경 AJAX(SEC-02), Cover Studio 템플릿 주입(ADM-13), SAML 서명 미검증(K04), 하드코딩 계정 admin/password(K10)를 먼저 닫습니다. 이 항목들은 배포하면 곧바로 침해로 이어집니다.

**1단계: 기반 복구**: 연결된 DB 엔진을 요청 단위로 주입하고 단일 sqlite 연결 공유를 없애며(COR-01), 세션 팩토리를 등록하고, 두 트리(`avantfax`, `namifax`)를 하나로 합쳐 클래스 이중 정의를 없앱니다. 기동 시 seed와 마이그레이션이 데이터를 덮어쓰는 문제(ADM-01, COR-02)도 이 단계에서 막아야 합니다. 이 단계 전에는 다른 결함의 수정 결과를 검증할 수 없습니다.

**2단계: 계약 정합**: 존재하지 않는 메서드, 테이블, 컬럼 참조(K03, ADM-07, ADM-08 등)를 스키마와 서비스에 맞춥니다. `QueryBuilder.quote`의 bool 처리 버그(R4U-02)와 `QueryResult` 순회 문제를 함께 고칩니다.

**3단계: 안전장치 선행 후 기능 수정**: 관리자 삭제 보호(R3A-09, R4U-01)와 마지막 관리자 보호를 먼저 넣은 뒤에 사용자 삭제(ADM-03)를 고칩니다. `fid` 기본값 1 패턴(R3B-04 등)을 제거한 뒤에 삭제와 수정 액션을 활성화합니다. 빈 권한 목록 처리(R3C-01, R5U-01)를 고친 뒤에 수신함과 검색을 열어 줍니다.

**4단계: 스텁 제거와 기능 구현**: 가짜 데이터를 반환하는 화면(`/viewfax`, `/txreport`, 아카이브 검색, `/ajax/*`), 재전송, 작업 취소, 메일 발송, TOTP 등록 UI와 로그인 강제, 패스키, SAML 설정 연동을 실제 구현으로 바꿉니다. 이때 실패를 성공으로 위장하는 코드(예외 삼키기)를 함께 제거합니다.

**5단계: 검증 체계 재구축**: 실제 앱과 실제 DB를 쓰는 통합 테스트로 전환하고, 없는 메서드를 mock하는 테스트(R4F-12)를 정리합니다. 골든 마스터는 실제 레거시 실행 결과로 다시 만들고, 숨은 문구(`sr-only`)와 가짜 기대값을 제거합니다. 이후 이 보고서의 1~5라운드 방법(영역별, 흐름별, 파일 정독, 마스킹 해제, 퍼징, E2E)을 그대로 다시 실행해 회귀를 확인합니다.

**6단계: 데이터 이전과 배포**: 레거시 MySQL 데이터 이전 도구와 문서를 만들고(F4-24), 아카이브 경로와 비밀번호 해시 호환을 해결합니다. wheel 설치 시 폴백 앱이 뜨는 문제(R3G-01)와 기동 경로(F5-01)를 고칩니다.

## 9. 전체 색인

| ID | 등급 | 제목 | 파일 |
|---|---|---|---|
| ADM-01 | 치명 | 앱 시작 때마다 seed/migration 이 운영 데이터를 덮어쓰거나 되살림 | round1-admin.md |
| ADM-02 | 높음 | 시스템 로그 화면 SQL 인젝션 (kw, year, month, day) | round1-admin.md |
| ADM-03 | 높음 | 사용자 관리: 삭제가 항상 조용히 실패 (soft delete 가 NOT NULL 위반) | round1-admin.md |
| ADM-04 | 높음 | 사용자 관리: any_modem 이 항상 1, 모뎀/DID/분류 권한이 저장되지 않음 | round1-admin.md |
| ADM-05 | 높음 | 사용자 관리: 빈 비밀번호로 신규 사용자 생성 시 비밀번호가 'password' 로 고정, 수정 시 실패 무시 | round1-admin.md |
| ADM-06 | 높음 | 관리자 자기 강등/마지막 관리자 잠금 방지 없음, 권한 변경이 기존 세션에 반영되지 않음 | round1-admin.md |
| ADM-07 | 높음 | 바코드 라우팅 수정/삭제 불가 (PK 이름 불일치: barcode_id vs bcr_id) | round1-admin.md |
| ADM-08 | 높음 | 동적 설정(블랙리스트) 전체 기능 불능: 서비스가 없는 테이블 DynConf 사용 | round1-admin.md |
| ADM-09 | 높음 | Fax2Email 관리 화면이 규칙을 저장하지 못함 | round1-admin.md |
| ADM-10 | 높음 | 시스템 기능(sysfunc) 화면: 4개 버튼 모두 무동작, 메시지는 가짜 | round1-admin.md |
| ADM-11 | 높음 | 스토리지 수명주기: 음수 일수 저장 시 모든 TIFF 즉시 삭제 | round1-admin.md |
| ADM-12 | 높음 | 스토리지 수명주기 서비스의 만료 삭제가 실제 팩스에 적용되지 않거나 잘못 동작 | round1-admin.md |
| ADM-13 | 높음 | Cover Studio 렌더링: 샌드박스 없는 Jinja2 로 임의 코드 실행 + PS 주입 + 토큰 치환 충돌 | round1-admin.md |
| ADM-14 | 높음 | print-to-fax CLI 가 '큐에 등록됨'이라 출력하지만 아무것도 큐에 넣지 않음, 실패 시에도 종료코드 0 | round1-admin.md |
| ADM-15 | 높음 | OCR 인덱싱이 실제로는 아무것도 저장하지 않음 (연결된 엔진에서도) | round1-admin.md |
| ADM-16 | 중간 | 저장된 네트워크 프린터/라우팅의 printer 값이 어디서도 소비되지 않음 | round1-admin.md |
| ADM-17 | 중간 | SMTP 게이트웨이 설정이 실제 메일 발송에 쓰이지 않고 send_mail 은 메일을 보내지 않음 | round1-admin.md |
| ADM-18 | 중간 | SMTP 설정 저장 시 HTML 서명 삭제, 비밀번호 평문 노출, 검증 부족 | round1-admin.md |
| ADM-19 | 중간 | 스토리지/SAML 설정 저장이 MySQL 에서 동작하지 않는 SQLite 전용 SQL | round1-admin.md |
| ADM-20 | 중간 | DB 스키마와 엔티티 불일치로 비밀번호 이력과 시스템 로그 PK 오류 | round1-admin.md |
| ADM-21 | 중간 | 관리 화면이 빈 테이블/삭제 후 가짜 데이터를 표시하고 그 행은 수정/삭제 불가 | round1-admin.md |
| ADM-22 | 중간 | DID/카테고리/모뎀/커버 액션이 실패해도 성공 메시지, 존재하지 않는 대상 삭제도 성공 | round1-admin.md |
| ADM-23 | 중간 | 모뎀 화면: 삭제 버튼, devid, faxcatid 필드가 폼에 없음 | round1-admin.md |
| ADM-24 | 중간 | Local/Cloud 스토리지 제공자의 경로 탈출, 연결 테스트 오판 | round1-admin.md |
| ADM-25 | 중간 | 프린터 화면 입력 검증 부재 및 예외 500 | round1-admin.md |
| ADM-26 | 낮음 | 시스템 로그 화면 기능 한계 | round1-admin.md |
| ADM-27 | 낮음 | SAML 관리 설정 검증 없음 | round1-admin.md |
| ADM-28 | 낮음 | 패키징: avantfax 패키지가 wheel 에 포함되지 않지만 namifax.views.admin 이 avantfax 를 import | round1-admin.md |
| ADM-29 | 낮음 | 설정 화면 안내/태그 불일치 | round1-admin.md |
| ADM-30 | 낮음 | 커버 관리: 파일명 검증 없음, 중복 등록 | round1-admin.md |
| COR-01 | 치명 | 단일 sqlite 연결/커서를 여러 스레드가 공유해 인터프리터가 세그폴트 | round1-core.md |
| COR-02 | 치명 | 기동할 때마다 seed/migration 이 실제 운영 데이터를 덮어씀 | round1-core.md |
| COR-03 | 치명 | notify CLI 가 DB 에 있는 모든 사용자에 대해 AttributeError 로 종료 (발송 팩스 미보관, 통지 메일 없음) | round1-core.md |
| COR-04 | 치명 | CLI/서비스에서 나가는 모든 메일이 실제로는 발송되지 않고 성공(True)을 반환 | round1-core.md |
| COR-05 | 높음 | AFAddressBook.loadbyfaxnum 이 튜플을 반환해 항상 참 -> faxrcvd/notify 가 회사/팩스번호를 생성하지 않음 | round1-core.md |
| COR-06 | 높음 | AddressBookFAX 스키마에 레거시 컬럼이 없어 팩스번호 생성, 카운터, Fax2Email 라우팅이 모두 실패 (에러는 삼켜짐) | round1-core.md |
| COR-07 | 높음 | AddressBook.abook_id 가 신규 행에서 NULL (PK 는 ab_id) -> 신규 회사는 조회/삭제 불가, delete_cid 는 True 를 반환하고 아무것도 안 지움 | round1-core.md |
| COR-08 | 높음 | DynConf 테이블이 스키마에 없음(DynamicConfig 로 생성) -> 차단(RejectCall) 규칙이 영구 동작하지 않음 | round1-core.md |
| COR-09 | 높음 | QueryBuilder.quote 가 Python bool 을 'True'/'False' 문자열로 저장 -> 계정이 비활성/비관리자가 됨 | round1-core.md |
| COR-10 | 높음 | faxqueue 명령 주입 (shell=True, 사용자 입력을 그대로 보간) | round1-core.md |
| COR-11 | 높음 | SQL 조립/이스케이프 결함 (LIKE 인젝션 재현, MySQL 백슬래시는 추론) | round1-core.md |
| COR-12 | 높음 | MySQL 백엔드가 사실상 사용 불가 (드라이버 미선언, 문법/파라미터 스타일, 스키마 전부 SQLite 전용) | round1-core.md |
| COR-13 | 높음 | DB 경로 기본값이 현재 작업 디렉터리 기준이고 CLI 훅마다 seed 까지 실행 -> 호출 위치마다 별개의 DB 가 생김 | round1-core.md |
| COR-14 | 높음 | 보관 일시(archstamp)를 '/' 구분자로 저장해 보관 기간 정리(prune)가 동작하지 않고 날짜 파싱 실패 | round1-core.md |
| COR-15 | 높음 | tiff2pdf/convert2pdf/static_preview/faxinfo 가 실패를 성공으로 위장(가짜 PDF, 빈 썸네일, 가짜 팩스 정보) + 저장소 정리 시 원본 TIFF 삭제 | round1-core.md |
| COR-16 | 높음 | faxcover: 토큰 접두어 치환으로 커버 페이지가 깨지고, DB 조회와 HTML 커버가 동작하지 않음 | round1-core.md |
| COR-17 | 중간 | createuser CLI 의 "기존 사용자 갱신" 분기가 비밀번호를 바꾸지 않고 성공 메시지를 출력 | round1-core.md |
| COR-18 | 중간 | 비밀번호 이력(UserPasswords) 스키마 불일치로 이력이 기록되지 않고 재사용 검사가 무력 | round1-core.md |
| COR-19 | 중간 | AFUserAccount.remove 가 NOT NULL 제약 위반으로 실패하는데 True 반환 (계정 삭제 불능) | round1-core.md |
| COR-20 | 중간 | faxrcvd 가 레거시 PHP 동작에서 벗어남 (누락/은폐) | round1-core.md |
| COR-21 | 중간 | FaxQueue 의 사용자 표시명/소유자 해석이 존재하지 않는 속성에 의존 | round1-core.md |
| COR-22 | 중간 | DatabaseEngine 의미론: transaction() 무력, 오류 은폐, SELECT 판별/insert id 오류 | round1-core.md |
| COR-23 | 중간 | 스케줄러/서비스 기동 결함 (서비스 중복 실행, 보관 정책 미적용, 진입점 인자 무시) | round1-core.md |
| COR-24 | 중간 | 설정 키 체계 불일치: 같은 디렉터리를 서로 다른 환경변수로 참조 | round1-core.md |
| COR-25 | 중간 | 이중 트리/패키징: namifax 가 avantfax 를 import 하지만 휠에는 avantfax 가 없고, CLI 서브커맨드 5개가 avantfax 전용 | round1-core.md |
| COR-26 | 중간 | print_in(CUPS 인쇄-팩스) 경로가 실제로 큐에 넣지 않고 "enqueued" 를 출력하며 진입점에도 미등록 | round1-core.md |
| COR-27 | 중간 | OCR 서비스: 미연결 엔진 + MySQL 전용 DDL -> 인덱싱/검색이 영구 불능 (K12/K16 의 원인 차원 변형) | round1-core.md |
| COR-28 | 중간 | archive_base: 파일 삭제 불능, 미리보기 파일명 불일치, 권한 조건 생성 오류 | round1-core.md |
| COR-29 | 중간 | 스키마 PK/컬럼 불일치로 엔티티 기반 CRUD 가 실패하는 테이블 | round1-core.md |
| COR-30 | 중간 | 사용하지 않는 PHP 브리지 + bridge_cli 가 요청 파라미터로 임의 바이너리 실행/임의 SQL 허용 | round1-core.md |
| COR-31 | 낮음 | 의존성 선언 불일치 | round1-core.md |
| COR-32 | 낮음 | storage_lifecycle.purge_expired_faxes 가 미연결 엔진과 잘못된 디렉터리 규칙으로 동작 | round1-core.md |
| COR-33 | 낮음 | 파일 경로/권한, 로그 처리 | round1-core.md |
| SEC-01 | 치명 | 비인증 SQL 인젝션 — 주소록 검색 (UNION 기반 데이터 탈취) | round1-security.md |
| SEC-02 | 높음 | 상태 변경 AJAX/업로드 엔드포인트에 permission 미지정 → 비인증 조작 가능 | round1-security.md |
| SEC-03 | 높음 | 팩스 상세/다운로드/주석/회전 등에서 모뎀 기반 접근 제어 우회 (IDOR) | round1-security.md |
| SEC-04 | 높음 | 반사 XSS — `/ajax/deletefaxes`의 `fids` 파라미터 | round1-security.md |
| SEC-05 | 높음 | 비밀번호 만료/강제 재설정 정책이 로그인 시점에 전혀 강제되지 않음 | round1-security.md |
| SEC-06 | 중간 | 비밀번호 해시가 salt 없는 단순 MD5 | round1-security.md |
| SEC-07 | 중간 | TOTP 비밀키/백업코드가 DB에 평문 저장 | round1-security.md |
| SEC-08 | 중간 | SMTP 비밀번호 / 클라우드 스토리지 secret_key 평문 저장 | round1-security.md |
| SEC-09 | 낮음 | CSRF 방어가 전혀 없음 | round1-security.md |
| SEC-10 | 중간 | 로그인 무차별 대입 시도에 대한 잠금/속도제한 전혀 없음 | round1-security.md |
| SEC-11 | 낮음 | MySQL 백엔드에서 `DatabaseEngine.quote()`의 백슬래시 미처리로 인한 2차 SQL 인젝션 가능성 | round1-security.md |
| UI-01 | 높음 | 설정 화면이 아무것도 저장하지 않으면서 "Settings updated successfully." 표시 | round1-ui.md |
| UI-02 | 높음 | admin_layout.jinja2 가 `message` 를 렌더하지 않아 관리자 화면 다수에서 성공 피드백이 사라짐 | round1-ui.md |
| UI-03 | 높음 | 시스템 기능 화면(재시작, 종료, 백업 다운로드) 버튼이 뷰와 계약이 안 맞아 전부 무동작 | round1-ui.md |
| UI-04 | 높음 | 빌드된 main.css 가 템플릿과 어긋나 있어 다수 클래스가 스타일 없음 (예: 2FA 활성화 버튼이 흰 글씨 무배경) | round1-ui.md |
| UI-05 | 높음 | 템플릿이 쓰는 문자열 68개가 번역 카탈로그(.pot)와 전 로케일에 없음 | round1-ui.md |
| UI-06 | 높음 | 로그인하지 않은 브라우저 요청이 로그인 화면이 아니라 원시 JSON 401 을 받음 | round1-ui.md |
| UI-07 | 높음 | /viewfax 가 실제 팩스 대신 하드코딩된 가짜 문서를 표시 | round1-ui.md |
| UI-08 | 중간 | login_totp.jinja2 는 main.css 대신 cdn.tailwindcss.com 런타임 스크립트에 의존 | round1-ui.md |
| UI-09 | 중간 | 전역 `input[type=text\|password]` 규칙이 관리자 다크 테마 입력 필드를 덮어쓸 가능성 | round1-ui.md |
| UI-10 | 중간 | 22개 로케일에 fuzzy 100건, 미번역 30건 -> .mo 에서 빠져 영어 노출, fuzzy 내용은 오역 | round1-ui.md |
| UI-11 | 중간 | 스웨덴어(sv) 카탈로그에 깨진 인코딩(U+FFFD) 13건, 네덜란드어(nl) 1건 | round1-ui.md |
| UI-12 | 중간 | fr, pt_BR, de 번역에 HTML 엔티티가 그대로 들어 있어 화면에 "&eacute;" 문자열로 표시 | round1-ui.md |
| UI-13 | 중간 | 레거시에서 이관된 번역이 용어 충돌로 오역: "Address Book"이 20개 로케일에서 "이메일 주소록" | round1-ui.md |
| UI-14 | 중간 | 뷰에서 만든 `_()` 메시지(TranslationString)는 템플릿에서 번역되지 않음 | round1-ui.md |
| UI-15 | 중간 | `<html lang>` 이 항상 "en", 아랍어 RTL 미지원 | round1-ui.md |
| UI-16 | 중간 | 영문 하드코딩과 `_()` 미적용 문자열이 화면, 플레이스홀더, alert, confirm 전반에 다수 | round1-ui.md |
| UI-17 | 중간 | 문장 조각을 이어 붙이는 번역 구조와 가짜 복수형 | round1-ui.md |
| UI-18 | 중간 | 모달 6종이 뷰가 넘기는 `message`/`error` 를 전혀 출력하지 않음 | round1-ui.md |
| UI-19 | 중간 | 모달의 취소/닫기 버튼이 window.close() 인데 링크는 같은 탭 이동 | round1-ui.md |
| UI-20 | 중간 | modal_assign 이 abook_id 를 1로 고정하고 txreport 는 항상 "전송 성공"을 표시 | round1-ui.md |
| UI-21 | 중간 | 팩스 답장/재시도/주소록 "팩스 보내기" 링크의 prefill 파라미터를 sendfax 가 무시 | round1-ui.md |
| UI-22 | 중간 | 주소록 검색 링크가 잘못된 파라미터 이름(search) 사용 | round1-ui.md |
| UI-23 | 중간 | 수신함이 레거시 대비 핵심 요소 누락, 일괄 동작 버튼은 무동작 | round1-ui.md |
| UI-24 | 중간 | 헤더의 회선 상태와 배지가 페이지마다 다르게 나옴, 모바일 내비게이션 없음 | round1-ui.md |
| UI-25 | 중간 | 표지 템플릿, 카테고리 선택지가 하드코딩되어 관리자가 만든 값이 UI에 반영되지 않음 | round1-ui.md |
| UI-26 | 중간 | 보관함: 키워드 없는 필터는 결과를 숨기고, 결과 없을 때 가짜 "Acme" 레코드를 표시 | round1-ui.md |
| UI-27 | 중간 | 폼 필드 중 뷰가 읽지 않는 것들(입력해도 버려짐) | round1-ui.md |
| UI-28 | 중간 | 상태 변경 동작이 GET 링크로 구현됨 | round1-ui.md |
| UI-29 | 중간 | 모든 POST 폼에 CSRF 토큰이 없음 | round1-ui.md |
| UI-30 | 중간 | SMTP 비밀번호가 HTML 에 평문 value 로 다시 출력됨 | round1-ui.md |
| UI-31 | 중간 | 관리자 화면에 하드코딩된 가짜 상태/수치 | round1-ui.md |
| UI-32 | 중간 | 접근성: label 미연결, 중복 id, 아이콘 전용 버튼, 대체 텍스트 | round1-ui.md |
| UI-33 | 낮음 | 404 페이지가 Pyramid 스타터 문구이고 로그인 사용자여도 내비게이션 없음, 죽은 템플릿/자산 잔존 | round1-ui.md |
| UI-34 | 낮음 | 관리자 빠른 이동, 브레드크럼에 프린터, 스토리지, SAML 누락 | round1-ui.md |
| UI-35 | 낮음 | 브랜드, 버전 표기 불일치, 캐시 버스터 불일치 | round1-ui.md |
| UI-36 | 낮음 | 배포 리스트 편집의 "Remove"/"Add Member" 버튼과 입력이 무동작 | round1-ui.md |
| UI-37 | 낮음 | 정적 디렉터리에 표지 원본과 불필요 자산이 공개 | round1-ui.md |
| UI-38 | 낮음 | 번역 카탈로그 메타데이터 손상 | round1-ui.md |
| USR-01 | 높음 | 아카이브 검색: 키워드/팩스ID 없이 필터링하면 결과가 항상 숨겨짐 | round1-user.md |
| USR-02 | 높음 | 검색/조회 결과가 0건일 때 가짜(placeholder) 레코드를 실제 결과처럼 표시 | round1-user.md |
| USR-03 | 중간 | 주소록/이메일북/배포목록 생성·수정 폼이 유효성 오류를 삼키고 무조건 성공 리다이렉트 | round1-user.md |
| USR-04 | 치명 | 사용자별 모뎀/카테고리 기반 팩스 접근 제한이 완전히 동작하지 않음 — 타 사용자 팩스 전체 노출 | round1-user.md |
| USR-05 | 중간 | 팩스 회전(rotate)이 실패해도 항상 성공 응답을 반환 | round1-user.md |
| USR-06 | 치명 | `/ajax/faxalter`가 인증 없이 접근 가능하고, 파라미터가 셸 명령에 그대로 삽입되어 명령 주입 가능 | round1-user.md |
| USR-07 | 낮음 | 작업 큐 조작(killjob/faxalter)에 요청자와 대상 작업의 소유자 일치 검증이 없음 | round1-user.md |
| USR-08 | 중간 | 모달 액션의 "작성자(lastmoduser)" 기록이 실제 로그인 사용자가 아니라 항상 admin(uid=1)로 기록됨 | round1-user.md |
| USR-09 | 낮음 | `_submit_check` 히든 필드가 모든 폼(24개 템플릿)에 존재하지만 서버에서 전혀 검증되지 않음 | round1-user.md |
| F3-01 | 높음 | 2FA(TOTP) 가 로그인에서 전혀 강제되지 않음: TotpService 가 연결 없는 avantfax 엔진을 사용 | round2-acct.md |
| F3-02 | 높음 | 일반 사용자가 자기 비밀번호를 바꿀 수 있는 경로가 하나도 없고, 세 화면 모두 성공을 위장함 | round2-acct.md |
| F3-03 | 높음 | can_del 권한이 어디에서도 검사되지 않음 (삭제 경로 3곳 + UI) | round2-acct.md |
| F3-04 | 높음 | 주소록/배포목록/이메일북/모뎀 상태가 로그아웃 상태에서 그대로 조회됨 (SEC-02 의 읽기 쪽 변형) | round2-acct.md |
| F3-05 | 높음 | superuser 만 있는 계정이 관리자 영역 전체에 접근하고, 관리자 폼에서 저장만 해도 is_admin 이 영구 부여됨 | round2-acct.md |
| F3-06 | 중간 | 아카이브 검색이 권한 조건(모뎀/카테고리/userid)을 전혀 넘기지 않고 superuser 를 is_admin 으로 대체함 | round2-acct.md |
| F3-07 | 높음 | 팩스 발송이 사용자별 모뎀 권한(modemdevs, any_modem)을 무시함 | round2-acct.md |
| F3-08 | 높음 | 발송 시 사용자 신원(-o 사용자, -f 이메일, from_*/TSI)이 전혀 전달되지 않음 | round2-acct.md |
| F3-09 | 높음 | 송신 큐(outbox)가 모든 사용자에게 전체 사용자의 작업을 노출 | round2-acct.md |
| F3-10 | 높음 | 관리자 하드코딩 로그인이 비밀번호 변경, 계정 비활성화, 마지막 로그인 기록을 모두 무력화 (K10 의 변형) | round2-acct.md |
| F3-11 | 높음 | 비활성화/삭제/비밀번호 변경이 이미 발급된 세션과 다른 인증 경로에 반영되지 않음 | round2-acct.md |
| F3-12 | 높음 | 관리자 사용자 폼에 활성화, 비밀번호 주기, 재사용 금지, 언어 등 레거시 필드가 없어 비활성화와 만료 정책을 설정할 방법이 없음 | round2-acct.md |
| F3-13 | 중간 | 설정 화면이 모든 사용자에게 하드코딩된 관리자 프로필과 고정 발신자 정보를 표시 | round2-acct.md |
| F3-14 | 중간 | 설정 화면의 2FA 상태가 항상 "미사용"으로 표시되어 해제 폼이 나타나지 않음 | round2-acct.md |
| F3-15 | 중간 | SAML/패스키 로그인이 성공해도 보안 정책이 인식하는 세션이 만들어지지 않음, RelayState 오픈 리다이렉트 | round2-acct.md |
| F3-16 | 중간 | SAML 사용자 매핑이 NameID 의 로컬 파트로 로컬 계정(admin 포함)에 매핑되고 로컬 정책을 우회 | round2-acct.md |
| F3-17 | 중간 | PAM/pwauth/웹서버 인증이 로그인 흐름에 연결되어 있지 않고, PAM 은 python-pam 없이는 항상 실패 | round2-acct.md |
| F3-18 | 중간 | 계정 관련 이벤트가 SysLog 에 전혀 기록되지 않아 감사 추적이 없음 | round2-acct.md |
| F3-19 | 중간 | HylaFAX 사용자 동기화(faxadduser/faxdeluser)가 계정 생성/비밀번호 변경/비활성화/삭제 어디에도 없음 | round2-acct.md |
| F3-20 | 중간 | remember() 가 계정 플래그를 bool() 로 해석해 login() 의 엄격 판정과 어긋남 (COR-09 와 결합하면 비관리자가 관리자 세션) | round2-acct.md |
| F3-21 | 낮음 | 사용자명/이메일 대소문자 구분 때문에 대소문자만 다른 계정이 공존하고 로그인이 어긋남 | round2-acct.md |
| F3-22 | 낮음 | 로그인 실패 사유와 복귀 경로(next) 유실 | round2-acct.md |
| F3-23 | 중간 | createuser CLI 의 기본값이 위험: 지정만 해도 관리자/superuser 승격, 비활성 계정 재활성화, 첫 로그인 변경 우회, 기본 비밀번호 고정 | round2-acct.md |
| F3-24 | 낮음 | 헤더 받은편지함 배지 엔드포인트가 TypeError 로 항상 0 을 반환 | round2-acct.md |
| F3-25 | 낮음 | 관리자 사용자 생성/수정의 검증 오류와 약한 비밀번호가 조용히 무시됨 (ADM-05 변형) | round2-acct.md |
| F3-26 | 낮음 | 세션 쿠키에 Secure 속성이 없고 세션이 프로세스 메모리에만 존재 | round2-acct.md |
| F5-01 | 높음 | 운영 기동 경로(systemd, namifax serve, namifax-server)가 waitress 가 아니라 wsgiref 개발 서버이고 ini 를 전혀 읽지 않음 | round2-ops.md |
| F5-02 | 높음 | 임포트/앱 생성 오류가 조용히 전혀 다른 JSON 스텁 앱으로 대체됨 | round2-ops.md |
| F5-03 | 높음 | DB 열기/스키마 초기화 실패를 삼키고 200 + 가짜 데이터로 서비스 계속 | round2-ops.md |
| F5-04 | 높음 | 팩스 전송 결과 무시 + sendfax 바이너리 부재 시 가짜 성공 + 업로드 임시파일 미삭제 | round2-ops.md |
| F5-05 | 높음 | 테스트 48개 파일 중 다수가 wheel 에 포함되지 않는 src/avantfax 트리를 검증 | round2-ops.md |
| F5-06 | 높음 | Web golden master 가 자기 참조적이며 가짜 데이터를 "정답"으로 고정 | round2-ops.md |
| F5-07 | 중간 | CLI golden master 20건이 모두 "인자 없음/누락" 사용법 출력뿐 | round2-ops.md |
| F5-08 | 중간 | 테스트가 실행 순서에 의존 (pytest-randomly 로 재현) | round2-ops.md |
| F5-09 | 중간 | 테스트가 작업 트리와 CWD 의 DB 를 오염시킴 | round2-ops.md |
| F5-10 | 낮음 | 기본 pytest 가 golden_master 를 실행하지 않고, xfail 분기는 죽은 코드, 수치 문서 불일치, CI 부재 | round2-ops.md |
| F5-11 | 중간 | 세션이 프로세스 메모리에만 있고 정리되지 않으며 쿠키 속성이 부족함 | round2-ops.md |
| F5-12 | 중간 | DATABASE_URL, AFDB_URL, sqlalchemy.* 설정과 SQLAlchemy 계층 전체가 아무 효과 없음 (설정 주입 수단이 문서와 실제 모두 없음) | round2-ops.md |
| F5-13 | 중간 | requirements.txt 가 pyproject/uv.lock 과 크게 다르고 잘못된 소스를 가리킴 | round2-ops.md |
| F5-14 | 중간 | createuser CLI 기본값이 위험함 (기본 관리자 + 공개된 기본 비밀번호 + 중복 이메일) | round2-ops.md |
| F5-15 | 중간 | 스키마 버전 관리/업그레이드 경로와 레거시 DB 이관 수단이 없음 | round2-ops.md |
| F5-16 | 중간 | 외부 바이너리 의존이 문서화되지 않았고 기동 시 사전 점검이 없어 부재 시 조용히 성공한 척 동작 | round2-ops.md |
| F5-17 | 중간 | 로깅이 사실상 없고 130곳의 광범위 except 가 오류를 은폐하며 크래시 흔적도 남지 않음 | round2-ops.md |
| F5-18 | 중간 | DatabaseEngine 전역 결과 상태로 인한 요청 간 데이터 혼선 (COR-01 세그폴트와 별개의 동시성 문제) | round2-ops.md |
| F5-19 | 낮음 | 스케줄러 운영 결함 | round2-ops.md |
| F5-20 | 낮음 | systemd 유닛 구성 문제 | round2-ops.md |
| F5-21 | 낮음 | 라이선스 표기 누락 (GPLv2 파생물) | round2-ops.md |
| F5-22 | 낮음 | 저장소 위생과 문서 불일치, 죽은 코드 | round2-ops.md |
| F5-23 | 낮음 | server/scheduler 엔트리포인트가 --help 를 해석하지 않고 그대로 구동됨 (COR-23 의 "인자 무시" 와 별개의 사용성 결함) | round2-ops.md |
| F4-01 | 높음 | 팩스 재전송/답장(refax)이 스텁: 항상 잡 ID 1001 을 반환하고 아무것도 전송하지 않음 | round2-parity.md |
| F4-02 | 높음 | "비밀번호 찾기"(forgot.php)가 스텁: 성공 문구만 출력하고 재설정/메일 발송 없음 | round2-parity.md |
| F4-03 | 높음 | 비밀번호 만료/초기화 강제 변경 화면(pwdexpired)이 스텁: 비밀번호를 바꾸지 않고 로그인 화면으로 리다이렉트 | round2-parity.md |
| F4-04 | 높음 | 대체 인증(ALTERNATE_AUTH: PAM/pwauth)과 웹서버 인증(REMOTE_USER)이 로그인에 연결되지 않음 | round2-parity.md |
| F4-05 | 높음 | 이메일 → 팩스(email2fax) 기능 전체 누락 | round2-parity.md |
| F4-06 | 높음 | sendfax 화면이 레거시 옵션 대부분을 폼에서도 서버에서도 처리하지 않음 | round2-parity.md |
| F4-07 | 높음 | 팩스 발송 실패가 은폐되고, sendfax 가 없으면 가짜 잡 ID 로 성공 처리. 소유자(-o), 발신 이메일(-f) 미전달 | round2-parity.md |
| F4-08 | 낮음 | 임시 업로드 정리가 cron 과 어긋남 | round2-parity.md |
| F4-09 | 중간 | 수신함/아카이브에 페이지네이션, 사용자별 페이지 크기, 회사/사용자 필터가 없음 | round2-parity.md |
| F4-10 | 높음 | 기존 아카이브 파일 경로를 해석하지 못함: DB 의 faxpath 는 INSTALLDIR 기준 상대경로, NamiFAX 웹은 installdir="" 로 루트 기준 조회 | round2-parity.md |
| F4-11 | 중간 | 미리보기/썸네일 파일명 규칙이 달라 기존 이미지가 전부 무효 | round2-parity.md |
| F4-12 | 높음 | 팩스 다운로드가 파일이 없거나 fid 가 없어도 "합성 PDF" 를 200 으로 반환 | round2-parity.md |
| F4-13 | 중간 | 설정 화면이 본인 데이터를 읽지 않고 가짜 프로필을 표시하며, 레거시 항목(커버 페이지, 아카이브당 건수, 비밀번호 변경 필드)이 없음 | round2-parity.md |
| F4-14 | 높음 | 아웃박스 작업 삭제가 실제로 호출할 수 없는 메서드를 쓰면서 항상 "삭제되었다" 는 메시지를 표시 | round2-parity.md |
| F4-15 | 높음 | 레거시 주소록의 팩스번호/이메일이 화면에 나타나지 않고 편집 폼도 비어 있음 | round2-parity.md |
| F4-16 | 높음 | AJAX 자동완성/프리필 엔드포인트가 결과가 없을 때 가짜 데이터를 반환하고, 실제 연락처의 빈 칸도 가짜 값으로 채움 | round2-parity.md |
| F4-17 | 높음 | 바코드 라우팅이 영구 비활성: bardecode 헬퍼가 항상 None 을 반환 | round2-parity.md |
| F4-18 | 중간 | 수신 팩스 주석(annotate_fax / ENABLE_FAX_ANNOTATION / ANN_GRAVITY)이 구현되지 않음 | round2-parity.md |
| F4-19 | 높음 | import_archive 도구가 스텁이고 진입점에도 없음: "Imported N faxes" 만 출력 | round2-parity.md |
| F4-20 | 낮음 | tools/update_contacts.php 대응 없음 | round2-parity.md |
| F4-21 | 낮음 | 플러그인/테마, 설치, 업그레이드 스크립트와 HylaFAX 연동 설치 문서 없음 | round2-parity.md |
| F4-22 | 중간 | 사용자 DB 의 language 설정이 화면 언어에 적용되지 않음 | round2-parity.md |
| F4-23 | 중간 | 설정 기본값 변경과 설정 이전 경로 없음 | round2-parity.md |
| F4-24 | 높음 | MySQL 레거시 스키마 이전 경로가 없고, 이전 도구/문서도 없음 | round2-parity.md |
| F4-25 | 중간 | 스키마 마이그레이션이 이전 데이터 행 전체를 수정: faxnumid, modemdev 기본값 강제 | round2-parity.md |
| F4-26 | 높음 | 레거시 '\|' 구분자(modemdevs, didrouting, faxcats)와 수신함 모뎀 필터의 ',' 분리가 불일치 | round2-parity.md |
| F1-01 | 높음 | 마이그레이션이 발신자 미식별 팩스를 매번 "Acme Corp 의 팩스번호(faxnumid=1)"로 귀속시킴 (COR-05 + COR-02 의 결합 변형) | round2-recv.md |
| F1-02 | 높음 | 같은 마이그레이션이 발신 팩스의 modemdev 를 'ttyS0' 으로 채워 "발신" 검색과 구분 기준을 깨뜨림 | round2-recv.md |
| F1-03 | 높음 | faxinfo 출력 해석 실패가 전부 무경고 "더미 팩스 정보"로 대체되어 실제 발신자와 수신 시각이 사라짐 (COR-15 의 유효 TIFF 변형) | round2-recv.md |
| F1-04 | 높음 | DB 가 잠깐 잠기면(5초 초과) 훅이 종료코드 0 으로 아무 로그 없이 끝나고, 아카이브 파일만 고아로 남아 팩스가 수신함에 나타나지 않음 | round2-recv.md |
| F1-05 | 중간 | Pillow 폴백 PDF/미리보기가 TIFF 해상도 태그를 무시해 페이지 크기와 비율이 틀어짐 | round2-recv.md |
| F1-06 | 중간 | 다쪽 수신 팩스를 모든 페이지 RGB 비트맵으로 메모리에 올려 PDF 를 만듦: 크기 70배, 메모리 수백 MB | round2-recv.md |
| F1-07 | 중간 | 회전: 경로가 맞는 경우 다쪽 TIFF 를 1쪽으로 잘라 저장(데이터 손실), 기본 구성에서는 아무것도 안 하면서 "rotation: 90" 응답 | round2-recv.md |
| F1-08 | 높음 | 수신함이 최신 25건만 보여주고 "25 of 25" 로 표시, 26번째 이후 팩스는 웹에서 접근 불가 | round2-recv.md |
| F1-09 | 중간 | /ajax/inbox 신규 팩스 카운트가 항상 0 (TypeError 삼킴) | round2-recv.md |
| F1-10 | 높음 | 보관(아카이브)된 수신 팩스가 보관함 화면에 나타나지 않음: 결과 행을 로드하지 않고 존재하지 않는 get_company 호출 | round2-recv.md |
| F1-11 | 중간 | 수신함 행의 빈 값을 가짜 기본값으로 채움: 미식별 발신자가 "Acme Corp", 수신 시각이 2026-09-29, 모뎀이 ttyS0 (USR-02 의 수신함판) | round2-recv.md |
| F1-12 | 중간 | 훅이 받은 원격 팩스 송신자의 TSI/CallerID 이름이 검증 없이 SQL 문자열 값이 됨 (SEC-11 의 공격 출처 변형, MySQL 전용) | round2-recv.md |
| F1-13 | 중간 | 훅 실행 시 모뎀 라우팅 설정이 훅 자신의 seed 로 파괴되어 알림 메일, 분류, 프린터 지정이 사라짐 (COR-02 의 수신 흐름 변형) | round2-recv.md |
| F1-14 | 낮음 | 레거시 faxinfo() 후처리 누락: UNKNOWN/UNSPECIFIED 발신자 예약번호 치환, CallID 인덱스 설정, 알림 제목 날짜 형식 | round2-recv.md |
| F1-15 | 낮음 | fax_download: 없는 fid 나 없는 파일에 200 + 64바이트 가짜 PDF, TIFF 요청에도 PDF 본문을 image/tiff 로 전송, format 값이 파일명 헤더에 검증 없이 삽 | round2-recv.md |
| F2-01 | 높음 | sendfax 제출에 소유자(-o)와 발신자(-f) 바인딩이 없어 모든 작업이 서비스 계정 소유가 됨 (notify 와 이음새 단절) | round2-send.md |
| F2-02 | 높음 | 다중 수신처가 하나의 -d 문자열로 전달되어 엉뚱한 번호로 발신됨 (화면 안내/팝업/서비스 구분자 3중 불일치) | round2-send.md |
| F2-03 | 높음 | sendfax 실패를 사용자에게 알리지 않고 항상 outbox 로 성공 리다이렉트, 바이너리가 없으면 가짜 작업번호로 성공 처리 | round2-send.md |
| F2-04 | 높음 | outbox 작업 취소가 실제로는 아무것도 하지 않고 항상 성공 메시지를 표시 | round2-send.md |
| F2-05 | 높음 | outbox 가 로그인한 모든 사용자에게 전체 사용자의 송신 작업을 보여줌 (소유자 필터 없음) | round2-send.md |
| F2-06 | 중간 | outbox 템플릿과 뷰의 키 불일치: 수신처, 회사, 실패 작업 번호가 비어 있고 재시도/수정/실패작업 취소 동선이 없음 | round2-send.md |
| F2-07 | 높음 | 작업 수정(/ajax/faxalter)이 항상 작업 #1 을 대상으로 하고, 전달되는 faxalter 옵션도 레거시와 다름 | round2-send.md |
| F2-08 | 높음 | 재전송(refax) 모달이 아무것도 제출하지 않으면서 작업번호 1001 로 성공 처리 | round2-send.md |
| F2-09 | 높음 | 업로드 검증 부재: MIME/크기 제한 미적용(FileUpload 미연결), 빈 파일과 임의 형식 모두 sendfax 로 전달, 긴 파일명은 500 | round2-send.md |
| F2-10 | 중간 | 업로드 임시 파일이 지워지지 않고, 크론이 청소하는 디렉터리와도 다른 곳에 저장됨 | round2-send.md |
| F2-11 | 중간 | 표지(-C) 값이 템플릿 파일로 해석되지 않고 사용자 입력이 그대로 전달됨, 표지만 발송 경로도 없음 | round2-send.md |
| F2-12 | 중간 | 주소록, 배포 목록 선택 팝업이 작성 화면과 연결되지 않고, 비어 있으면 가짜 수신처를 만들어 냄 | round2-send.md |
| F2-13 | 낮음 | 송신 큐 조회 오류가 "큐 비어 있음"으로 표시됨 (faxstat 실패 은폐) | round2-send.md |
| F2-14 | 낮음 | 작성 화면 오류 재표시 때 표지 체크 해제 상태와 입력이 복원되지 않음, 주소록 "Send Fax" 링크가 URL 인코딩되지 않음 | round2-send.md |
| F2-15 | 낮음 | txreport 모달: 권한 검사 없음, 존재하지 않는 fid 에도 가짜 전송 확인서를 발급 (UI-20, SEC-03, USR-02 의 변형) | round2-send.md |
| R3A-01 | 중간 | 유니코드 숫자("²")가 isdigit() 검사를 통과해 int() 에서 500 | round3-a.md |
| R3A-02 | 낮음 | 사용자 관리 화면의 DID 권한 체크박스에서 라우트 번호가 비어 표시됨 | round3-a.md |
| R3A-03 | 중간 | 저장소/SMTP 화면의 숫자 입력 오류가 500 이 되거나 내부 예외 문구를 그대로 노출 | round3-a.md |
| R3A-04 | 중간 | `namifax phb` 서브커맨드가 어떤 경우에도 실패함 | round3-a.md |
| R3A-05 | 낮음 | 일부 서브커맨드가 `--help` 를 해석하지 않아 실제 작업을 실행하거나 파일명으로 처리 | round3-a.md |
| R3A-06 | 중간 | fax2email 의 "삭제"가 회사 행만 지우고 팩스번호와 아카이브 참조를 고아로 남김 (레거시는 예약 회사로 재배정) | round3-a.md |
| R3A-07 | 중간 | fax2email "create" 가 주소록에 고아 회사를 만들고 성공 메시지를 표시 (회사명을 팩스번호로 사용) | round3-a.md |
| R3A-08 | 낮음 | fax2email 목록이 실제 회사의 빈 값을 가짜 이메일/프린터로 채움 | round3-a.md |
| R3A-09 | 중간 | 사용자 삭제의 admin 보호 검사("uid != 1")가 "01" 로 우회되고, 삭제 실패에도 비밀번호 이력이 지워짐 | round3-a.md |
| R3A-10 | 낮음 | 모뎀 수정에서 팩스 분류(faxcatid)를 해제할 수 없음 | round3-a.md |
| R3A-11 | 중간 | 설정 화면의 2FA 상태 조회가 존재하지 않는 키 identity["uid"] 를 사용 | round3-a.md |
| R3A-12 | 낮음 | 비-GET 요청이 죽은 default.py 뷰로 가서 하드코딩 통계 홈을 공개 렌더링 | round3-a.md |
| R3A-13 | 낮음 | /admin 이 Accept 부분 문자열만으로 JSON 을 반환하고 모뎀 상태도 고정 문자열 | round3-a.md |
| R3A-14 | 낮음 | 시드가 SysLog 에 조작된 감사 기록을 삽입해 시스템 로그 화면이 가짜 이벤트만 보여줌 | round3-a.md |
| R3A-15 | 낮음 | 권한 없는 로그인 사용자가 관리자 URL 에 접근하면 안내 없이 받은편지함으로 리다이렉트 | round3-a.md |
| R3A-16 | 낮음 | SessionManager 가 "Thread-safe" 라고 적혀 있으나 락이 없어 경쟁 시 KeyError 가능 | round3-a.md |
| R3B-01 | 높음 | 새 이메일 연락처 폼이 숨은 id=1 을 보내 "추가"가 1번 연락처를 덮어쓰고 "삭제"가 1번을 지움 | round3-b.md |
| R3B-02 | 높음 | 배포목록 도우미가 회사 ID 를 목록 항목으로 저장하고, 레거시 "fnid\|팩스번호" 형식은 ajax/dlist 와 목록 화면이 해석하지 못함 | round3-b.md |
| R3B-03 | 높음 | /assign 모달: 회사명 변경 분기는 회사를 로드하지 않아 항상 무동작이고, 회사 병합(reassign)은 db 없는 인스턴스라 항상 실패하는데 결과는 조용함 | round3-b.md |
| R3B-04 | 높음 | 필수 파라미터가 없으면 fid 가 "1" 로 기본값이 되어, fid 없는 POST /delete 가 1번 팩스를 삭제함 | round3-b.md |
| R3B-05 | 중간 | /note 저장이 팩스의 카테고리를 NULL 로 지움 | round3-b.md |
| R3B-06 | 중간 | 이메일북 수정 경로가 서비스의 검증을 우회해 빈 이름과 잘못된 주소를 그대로 저장 | round3-b.md |
| R3B-07 | 중간 | 보관함 방향(sentrecvd) 필터 값이 서비스가 이해하는 값과 달라 필터가 무시되고, 비관리자는 잘못된 SQL 이 됨 | round3-b.md |
| R3B-08 | 중간 | 보관함 날짜 필터가 원시 YYYY-MM-DD 를 넘겨 종료일이 제외되고, 종료일만 주면 무시되며, 시작일만 주면 그 하루만 검색 | round3-b.md |
| R3B-09 | 중간 | 보관함 faxid 에 유니코드 숫자(예: "²")를 주면 500, 매우 큰 수는 오류가 삼켜져 가짜 결과 표시 (webauthn.py 에 같은 패턴) | round3-b.md |
| R3B-10 | 중간 | /ajax/book 이 fnid 에 회사 ID 를 넣고 회사당 1행만 반환해, 이어지는 /ajax/prefillto 가 엉뚱한 레코드(또는 가짜 값)를 읽음 | round3-b.md |
| R3B-11 | 중간 | vCard 가져오기: 카드 경계를 무시한 이름 이월, ORG 연결, 연락처 미표시, 기존 회사 팩스번호 누락 | round3-b.md |
| R3B-12 | 중간 | 대시보드(home) 수신함 카운트 fetch 가 HTML 을 받아 영구히 0 으로 표시 | round3-b.md |
| R3B-13 | 중간 | /email 모달이 팩스 로드 실패를 무시하고 첨부 없는 메일을 보내며 발신자, 파일명, cc, bcc 를 전달하지 않음 | round3-b.md |
| R3B-14 | 중간 | WebAuthn 챌린지가 일회용이 아님 (등록, 인증 모두 세션에서 읽기만 하고 삭제하지 않음) | round3-b.md |
| R3B-15 | 중간 | WebAuthn 등록: credential_id 를 원시 바이트 .decode("utf-8") 하여 실패하고, 성공해도 저장 형식이 인증 조회 형식(base64url)과 다름 | round3-b.md |
| R3B-16 | 중간 | /distrolist/edit 의 리다이렉트가 dl_id 를 인코딩 없이 Location 에 넣어 제어문자 입력이 500 을 일으키고 임의 문자열이 반사됨 | round3-b.md |
| R3B-17 | 낮음 | 배포목록 도우미는 dl_id 가 없으면 기본값 1 번 목록에 항목을 추가함 | round3-b.md |
| R3B-18 | 낮음 | 이메일북 목록 및 자동완성이 `"이름" <주소>` 문자열을 재파싱하여 이름에 따옴표나 "<" 가 있으면 주소가 깨짐 | round3-b.md |
| R3B-19 | 낮음 | 회전 링크가 원시 JSON 페이지로 이동하고, viewfax 는 이전/다음 탐색 컨텍스트를 전혀 전달하지 않음 | round3-b.md |
| R3B-20 | 낮음 | /ajax/archivefax 가 목록 중 잘못된 ID 를 만나면 나머지를 처리하지 않고 200 으로 응답 | round3-b.md |
| R3B-21 | 낮음 | SAML 메타데이터/AuthnRequest 가 Host 헤더로 만든 URL 을 XML 에 이스케이프 없이 삽입 | round3-b.md |
| R3B-22 | 낮음 | SAML ACS 실패 시 내부 예외 문자열을 인코딩 없이 /login?error= 로 반사 | round3-b.md |
| R3B-23 | 낮음 | /auth/saml/sls 는 서명 없는 GET 으로 호출되고 실제 세션을 끊지도 못함 | round3-b.md |
| R3B-24 | 낮음 | /ajax/modemstatus 가 요청의 modems 파라미터를 무시하고 모든 모뎀을 반환하며, 요청마다 모뎀 수만큼 faxstat 을 재시도할 수 있음 | round3-b.md |
| R3B-25 | 낮음 | 존재하지 않는 id "1" 을 요청하면 첫 번째 레코드를 대신 보여 주는 폴백이 있음 | round3-b.md |
| R3B-26 | 낮음 | /setcompany 가 팩스 갱신 성공 여부와 무관하게 회사 카운터를 증가시킴 (GET) | round3-b.md |
| R3B-27 | 낮음 | WebAuthn 자격 삭제는 대상이 없거나 남의 것이어도 success:true | round3-b.md |
| R3C-01 | 높음 | 모뎀/라우트 목록이 비어 있거나 None 이면 접근 제한이 사라짐 (fail-open) | round3-c.md |
| R3C-02 | 중간 | user_has_rights 의 카테고리 비교가 문자열 대 정수라 카테고리 권한만 있는 사용자는 상세 접근이 거부됨 | round3-c.md |
| R3C-03 | 중간 | DID 라우팅 모드, RESTRICTED_USER_MODE, INBOX_LIST_MODEM 설정이 아카이브 서비스에 연결되지 않음 | round3-c.md |
| R3C-04 | 중간 | delete_fax 가 DB 삭제 실패를 무시하고 파일부터 지운 뒤 True 를 반환, prune_archive 는 실패를 세어 성공으로 집계 | round3-c.md |
| R3C-05 | 중간 | create_fax 가 installdir 접두어를 구분자 없이 잘라 faxpath 가 "/"로 시작, get_pdfpath/get_tiffpath/get_thumbnail/get_faximages | round3-c.md |
| R3C-06 | 중간 | Repository.update_entry 가 기본키가 없으면 UPDATE 대신 INSERT 로 떨어지고, 서비스들은 set_id 실패를 무시해 잘못된 행을 만들거나 지움 | round3-c.md |
| R3C-07 | 중간 | QueryBuilder 가 None 조건을 `col = NULL` 로 만들어 영원히 일치하지 않음 (중복 검사/조회 실패) | round3-c.md |
| R3C-08 | 중간 | 사용자 생성이 공백 제거한 값으로 검증하고 원본을 저장; 줄바꿈과 유니코드 사용자명 통과 | round3-c.md |
| R3C-09 | 낮음 | is_valid_email 이 앞뒤 공백/끝 개행을 허용하고 호출 서비스들은 원본을 저장 (DID, 바코드, 모뎀 연락처, 주소록 이메일) | round3-c.md |
| R3C-10 | 중간 | 비밀번호 없이 사용자를 만들면 생성된 임시 비밀번호가 어디에도 전달되지 않아 계정을 쓸 수 없음 | round3-c.md |
| R3C-11 | 중간 | change_password/reset_password/update 가 캐시된 dbdata 전체를 되써서 동시 변경을 되돌림 (비활성화한 계정이 되살아남) | round3-c.md |
| R3C-12 | 중간 | AFUserAccount.load() 가 NULL 컬럼을 dbdata 에 반영하지 않아 같은 인스턴스를 재사용하면 이전 사용자의 값이 남음 | round3-c.md |
| R3C-13 | 낮음 | 로그인 상태 플래그가 성공 시에만 True 로 바뀌고 초기화되지 않음 (admin_logged_in 잔존) | round3-c.md |
| R3C-14 | 낮음 | 비밀번호 주기 계산/검사가 레거시와 다름 (pwdexpire NULL 은 만료 아님, 3/6개월을 90/180일로 계산) | round3-c.md |
| R3C-15 | 낮음 | reset_password 가 (bool, str\|None) 튜플을 반환해 실패도 참으로 평가됨 | round3-c.md |
| R3C-16 | 낮음 | AFUserPasswords.clear_hashes 가 db 없이 만들어지면 삭제에 성공해도 False 를 반환 | round3-c.md |
| R3C-17 | 중간 | AFAddressBook.reassign / delete_companyfaxids 가 db 를 명시하지 않으면 아무것도 하지 않고 False 를 반환, 회사 삭제는 팩스번호를 고아로 남김 | round3-c.md |
| R3C-18 | 낮음 | 모뎀 상태 표시가 수신 중 발신자 회사 조회(phone_lookup)와 modem-recv-from 클래스를 구현하지 않음 | round3-c.md |
| R3C-19 | 낮음 | 같은 MailerService 인스턴스로 sendmail 을 여러 번 호출하면 첨부가 중복되고 스풀 목록의 메시지가 동일 객체 | round3-c.md |
| R3C-20 | 중간 | embed_image 로 넣은 인라인 이미지가 메일에 전혀 포함되지 않음 | round3-c.md |
| R3C-21 | 중간 | 제목/수신자에 개행이 있으면 set_message/sendmail 이 예외를 던지고 bool 계약을 깨며, 빈 수신자도 스풀 모드에서 True | round3-c.md |
| R3C-22 | 낮음 | 생성 메일에 Date/Message-ID 헤더가 없고 본문 텍스트를 HTML 이스케이프하지 않고 HTML 파트에 삽입 | round3-c.md |
| R3C-23 | 중간 | SMTP STARTTLS/SSL 이 인증서와 호스트명을 검증하지 않음 | round3-c.md |
| R3C-24 | 중간 | rotate_fax 가 회전 후 TIFF 의 해상도 정보를 잃고 원본을 제자리 덮어쓰며 실패를 삼킴 | round3-c.md |
| R3C-25 | 낮음 | 페이지 크기 검증 부재: pagelimit=0 이면 ZeroDivisionError, 음수면 전체 행 반환 | round3-c.md |
| R3C-26 | 낮음 | FaxQueue 가 타임아웃 없는 셸 실행을 생성자에서 수행 | round3-c.md |
| R3C-27 | 낮음 | set_note, set_faxcontent 가 DB 갱신 결과를 무시하고 True 를 반환; ArchiveIn.create 는 비원자적 | round3-c.md |
| R3C-28 | 낮음 | ARCHIVE_DATE_FORMAT 설정이 반영되지 않고 기본 표기도 레거시와 다름 | round3-c.md |
| R3C-29 | 낮음 | 고유 제약 위반으로 이름/코드 변경이 실패해도 get_error() 가 비어 있음 | round3-c.md |
| R3C-30 | 낮음 | DistroList.lastmod_date, UserAccount.last_mod, FaxArchive.lastoperation 이 갱신되지 않음 | round3-c.md |
| R3C-31 | 낮음 | FaxPDFArchive.search_archive 의 superuser + DID 모드 "*" 분기가 레거시와 다르게 userid 필터를 적용 | round3-c.md |
| R3D-01 | 높음 | S3 delete_fax 의 폴백 prefix 가 슬래시 없이 "fax{fid}" 여서 다른 팩스 객체까지 삭제 | round3-d.md |
| R3D-02 | 높음 | purge_local_tiffs 가 변환 실패 시 생기는 14바이트 가짜 PDF 를 "유효한 PDF"로 보고 원본 TIFF 를 삭제 | round3-d.md |
| R3D-03 | 중간 | purge_expired_faxes 가 원격/로컬 삭제 실패를 삼키고 DB 행은 지움 | round3-d.md |
| R3D-04 | 중간 | StorageLifecyclePolicy 의 remote_sync_delete, delete_remote_tiff_only 가 어디에서도 사용되지 않음 | round3-d.md |
| R3D-05 | 중간 | GCS 유형이 endpoint 를 채우지 않아 AWS S3 로 접속, GCS 전용 설정과 Presigned URL 없음 | round3-d.md |
| R3D-06 | 중간 | download_file 이 파일명만 있는 target_path 에서 예외(FileNotFoundError)를 던짐 | round3-d.md |
| R3D-07 | 낮음 | boto3 클라이언트에 타임아웃/재시도 설정이 없음 | round3-d.md |
| R3D-08 | 높음 | TOTP 검증이 DB 오류에 fail-open: 오류면 2FA 없이 통과 | round3-d.md |
| R3D-09 | 중간 | TOTP 코드 재사용 가능, 시도 횟수 제한 없음 | round3-d.md |
| R3D-10 | 낮음 | TOTP 입력 정규화 불일치와 비원자적 갱신 | round3-d.md |
| R3D-11 | 높음 | WebAuthn 등록 검증이 credential_id(바이트)를 UTF-8 로 디코딩해 거의 항상 예외 | round3-d.md |
| R3D-12 | 높음 | sign_count/last_used_at 갱신이 NOW() 를 써서 SQLite 에서 항상 실패하고 예외를 삼킴 | round3-d.md |
| R3D-13 | 중간 | WebAuthn 사용자 검증(UV) 미요구, 중복 등록 방지 없음 | round3-d.md |
| R3D-14 | 높음 | SAML AuthnRequest 와 메타데이터를 f-string 으로 만들어 & 등이 이스케이프되지 않아 XML 이 깨짐 | round3-d.md |
| R3D-15 | 중간 | idp_sso_url 에 이미 쿼리가 있으면 "?" 를 또 붙여 잘못된 URL 을 만든다 | round3-d.md |
| R3D-16 | 중간 | 빈 NameID 도 성공으로 처리하고 빈 사용자명 계정 조회/생성으로 이어짐 | round3-d.md |
| R3D-17 | 중간 | SAML 속성 매핑이 명세와 달라 Entra ID/Okta 실속성을 못 읽고 default_role/role 을 무시 | round3-d.md |
| R3D-18 | 낮음 | SP 메타데이터가 WantAssertionsSigned="false", KeyDescriptor 없음 | round3-d.md |
| R3D-19 | 중간 | 커버 .ps 렌더링이 한글 등 비 latin-1 값에서 UnicodeEncodeError 로 터지고, .pdf 는 태그 치환 없이 그대로 반환 | round3-d.md |
| R3D-20 | 중간 | HTML 커버: 디코딩 오류 무시로 EUC-KR 템플릿 훼손, Jinja 오류 시 원본 템플릿을 조용히 반환, autoescape 없음 | round3-d.md |
| R3D-21 | 낮음 | save_template 이 DB 등록 실패를 확인하지 않고 성공 + 엉뚱한 cover_id 를 반환 | round3-d.md |
| R3D-22 | 중간 | Tesseract 미설치/오류를 빈 문자열로 삼켜 index_fax 가 "성공"으로 끝남 | round3-d.md |
| R3D-23 | 낮음 | OCR: confidence 미기록, 언어 고정(eng), 타임아웃/페이지 상한 없음, FULLTEXT 없음, LIKE 와일드카드 미이스케이프 | round3-d.md |
| R3D-24 | 중간 | OcrService 호출자가 없고 faxrcvd 가 쓰는 helpers.ocr_faxcontent 는 항상 None 스텁 | round3-d.md |
| R3D-25 | 중간 | 네트워크 프린터: LPD/IPP 전송 어댑터 없음, test_print 가 protocol 을 무시하고 항상 RAW+PJL 전송 | round3-d.md |
| R3D-26 | 낮음 | print-in: 여러 태그 중 첫 번째만 사용, 번호 미정규화, 마스킹/Draft 저장 없이 "Saved to drafts" 메시지 | round3-d.md |
| R3D-27 | 중간 | MailerService 가 설정의 from_name 을 쓰지 않고, 명세의 get_active_mailer 가 없으며 engine=None 이면 DB 를 읽지 않음 | round3-d.md |
| R3D-28 | 낮음 | from_name 에 쉼표가 있으면 From 헤더가 두 주소로 쪼개짐 | round3-d.md |
| R3D-29 | 낮음 | SMTP 인증을 보안 모드 NONE 과 함께 허용(평문 자격 증명 전송), 비 ASCII 비밀번호는 원인 불명 예외 | round3-d.md |
| R3D-30 | 높음 | FileUpload 가 클라이언트가 보낸 size/type 을 신뢰해 크기 제한과 MIME 화이트리스트가 우회됨 | round3-d.md |
| R3D-31 | 낮음 | FileUpload 의 오류 처리/경계 결함 | round3-d.md |
| R3D-32 | 낮음 | FormRules 경계값/타입 결함 | round3-d.md |
| R3D-33 | 낮음 | is_valid_date 가 비정상 연도/유니코드 숫자를 허용 | round3-d.md |
| R3D-34 | 중간 | clean_faxnum 이 전각/아랍 숫자를 통과시키고 레거시와 달리 영문자를 제거 | round3-d.md |
| R3D-35 | 낮음 | process_template 가 치환된 값 안의 토큰을 다음 값으로 다시 치환해 값이 오염됨 | round3-d.md |
| R3D-36 | 낮음 | 레거시와 다르게 동작하는 잡다한 helpers | round3-d.md |
| R3D-37 | 낮음 | PasswordManager.verify_password 가 NULL/비 ASCII 해시에서 예외(500) | round3-d.md |
| R3D-38 | 낮음 | PWAuthBackend 가 빈 자격 증명/개행을 검사하지 않음 (PAM 백엔드와 불일치) | round3-d.md |
| R3D-39 | 낮음 | 스케줄러: 폴백 스레드는 자정 정리를 하지 않고, 시작 실패 시 is_running 이 고정됨 | round3-d.md |
| R3D-40 | 중간 | avantfaxlog 가 SysLog 테이블이 아니라 OS syslog 에만 기록 | round3-d.md |
| R3D-41 | 낮음 | 명세의 인터페이스 이름/시그니처와 구현이 달라 명세 기반 테스트가 실패 | round3-d.md |
| R3E-01 | 중간 | `namifax phb` 서브커맨드가 항상 argparse 오류로 종료됨 (종료코드 2) | round3-e.md |
| R3E-02 | 높음 | faxcover: 번들 표지 템플릿(cover.ps, 바이너리 포함)을 UTF-8 텍스트로 읽고 써서 출력이 손상됨 | round3-e.md |
| R3E-03 | 높음 | faxcover: PostScript 문자열 정화/이스케이프가 없어 괄호, 백슬래시가 PS 구문을 깨고 PS 코드 주입이 가능함 | round3-e.md |
| R3E-04 | 중간 | faxcover -C 가 확장자 제한 없이 임의 경로의 파일을 템플릿으로 읽어 그대로 출력함 | round3-e.md |
| R3E-05 | 중간 | faxinfo 출력에 UTF-8 이 아닌 바이트가 있으면 전체 해석을 버리고 발신자 00000000, 현재 시각으로 접수함 | round3-e.md |
| R3E-06 | 낮음 | clean_faxnum 이 영문자, 밑줄을 제거해 레거시와 다른 번호가 저장됨 | round3-e.md |
| R3E-07 | 낮음 | `i18n init -l <이미 있는 로케일>` 이 기존 번역 카탈로그를 경고 없이 빈 카탈로그로 덮어씀 | round3-e.md |
| R3E-08 | 낮음 | `i18n update -l ko` 가 -l 을 무시하고 24개 로케일을 모두 갱신하며, 퍼지 매칭을 기본으로 켜 둠 | round3-e.md |
| R3E-09 | 낮음 | `i18n extract` 가 절대 경로 위치 주석과 자리표시자 헤더를 만들고 커밋된 .pot 와 크게 어긋남 | round3-e.md |
| R3E-10 | 낮음 | populate_missing_translations.py 는 CWD 와 존재하지 않는 scratch/ 에 의존하고 실패해도 종료코드 0 | round3-e.md |
| R3E-11 | 중간 | import_users: 비 UTF-8 입력이 조용히 깨지고, 탭이 아닌 줄은 오류 없이 건너뜀 | round3-e.md |
| R3E-12 | 낮음 | cron 인자 검증이 옵션마다 제각각이고 끊어진 심볼릭 링크는 영원히 정리되지 않음 | round3-e.md |
| R3E-13 | 낮음 | faxcover: -z 가 0 이거나 숫자가 아니면 트레이스백으로 죽어 표지가 생성되지 않음 | round3-e.md |
| R3E-14 | 낮음 | 보관 디렉터리/파일 권한이 레거시와 다름: 디렉터리 0755, fax.tif 는 원본의 0600 을 상속 | round3-e.md |
| R3E-15 | 낮음 | 알림 메일 문구가 레거시와 다르고, 보관 등록 실패 시 본문에 "fax id: None" 이 찍힘 | round3-e.md |
| R3E-16 | 낮음 | dynconf CLI 에 로그가 전혀 없고 DB 오류는 트레이스백으로 종료됨 | round3-e.md |
| R3E-17 | 낮음 | CLI 스크립트 실행 비트가 제각각이라 경로 지정 실행이 일부만 가능함 | round3-e.md |
| R3E-18 | 낮음 | createuser: 비밀번호가 명령행 인자라 ps 에 노출되고, 길이와 이메일 형식 검증이 없음 | round3-e.md |
| R3E-19 | 낮음 | golden_master/runner.py: 빈 인자가 사라지고, 셸 인용이 없으며, 이미지를 빌드하지 않고, docker 실패를 골든으로 기록함 | round3-e.md |
| R3E-20 | 낮음 | generate_web_golden.py 는 50건만 만들고 meta 를 덮어써 수작업 필드가 사라지며, web_runner 검증이 느슨함 | round3-e.md |
| R3E-21 | 낮음 | ini 파일: 개발 설정이 모든 인터페이스에 바인딩되고, 운영 설정에 waitress 제한값이 없음 | round3-e.md |
| R3E-22 | 낮음 | systemd 유닛에 PYTHONUNBUFFERED 가 없어 `serve` 의 시작 안내가 journald 에 남지 않음 | round3-e.md |
| R3F-01 | 높음 | AFAddressBook 을 기본 생성하면 reassign 과 delete_companyfaxids 가 조용히 실패하고, 회사 삭제가 팩스번호와 이메일 행을 고아로 남김 | round3-f.md |
| R3F-02 | 높음 | 쓰기 실패 시 롤백하지 않아 트랜잭션과 쓰기 잠금이 열린 채 남고 다른 프로세스가 "database is locked" 를 받음 | round3-f.md |
| R3F-03 | 높음 | seed 의 `INSERT OR REPLACE ... fid=1` 이 수신함이 비어 있는 기존 DB 에서 실제 보관 팩스 #1 을 데모 레코드로 덮어씀 (COR-02, ADM-01 의 다른 원인 변 | round3-f.md |
| R3F-04 | 높음 | 폴백 웹앱 `/api/inbox/list` 가 종료되지 않는 무한 루프에 빠지고 메모리가 계속 늘어남 | round3-f.md |
| R3F-05 | 중간 | 폴백 웹앱 핸들러가 Session 객체를 받아 AFUserAccount 전용 API 를 호출해 일반 사용자는 전 기능이 500 | round3-f.md |
| R3F-06 | 중간 | 폴백 웹앱 로그인이 구조적으로 성공할 수 없음 | round3-f.md |
| R3F-07 | 중간 | 폴백 웹앱 입력 처리 부재와 가짜 팩스 발송 | round3-f.md |
| R3F-08 | 중간 | TOTP 검증이 DB 오류에서 fail-open: 오류나 연결 끊김이면 아무 코드나 통과 | round3-f.md |
| R3F-09 | 중간 | enable_totp 가 DELETE 후 INSERT 를 비원자적으로 실행하고 INSERT 실패를 무시한 채 성공과 백업 코드를 반환 | round3-f.md |
| R3F-10 | 중간 | `find()` 반환 형태가 0건/1건/N건에서 list, dict, list 로 달라 호출부가 중복 행에서 깨지거나 "없음" 으로 오판 | round3-f.md |
| R3F-11 | 중간 | DIDRouting->DIDRoute, FaxPDFCategory->FaxCategory 이름 변경 마이그레이션이 실행 순서 때문에 영원히 동작하지 않음 | round3-f.md |
| R3F-12 | 중간 | 새 DB 에 데모 데이터를 심고 위조된 SysLog 감사 기록까지 만든다. 시드 순서 때문에 첫 기동의 시드 회사는 조회 불가 | round3-f.md |
| R3F-13 | 중간 | 스키마 기본값과 제약이 레거시와 달라 새 행의 의미가 바뀜 | round3-f.md |
| R3F-14 | 중간 | 시드 CoverPages 가 레거시 표지 3종 중 1종만 등록하고 이름도 다름 | round3-f.md |
| R3F-15 | 중간 | 전체 행 write-back 방식 update_entry 로 동시 수정이 서로를 덮어씀 (lost update) | round3-f.md |
| R3F-16 | 낮음 | QueryBuilder 가 None 조건을 `= NULL` 로 만들어 영원히 불일치하고, offset 은 limit 없이는 무시됨 | round3-f.md |
| R3F-17 | 낮음 | QueryBuilder.quote 가 사용자 문자열 "now()", "curdate()" 등을 SQL 함수로 취급하고, bytes 는 repr 로 저장 | round3-f.md |
| R3F-18 | 낮음 | get_default_engine 이 연결과 스키마 초기화가 끝나기 전에 전역 엔진을 공개함 | round3-f.md |
| R3F-19 | 낮음 | PHP 브리지가 호출마다 새 프로세스라 connect 상태가 유지되지 않고, bridge_cli 는 BLOB/날짜를 JSON 직렬화하지 못함 | round3-f.md |
| R3F-20 | 낮음 | SQLite DB 파일이 기본 umask 로 0644 로 만들어져 해시, TOTP 비밀키, SMTP 비밀번호가 다른 로컬 사용자에게 읽힘. 외래키 PRAGMA 도 꺼져 있음 | round3-f.md |
| R3F-21 | 낮음 | MySQL 연결에 재연결/ping 이 없어 wait_timeout 이후 모든 쿼리가 영구히 실패하고 오류는 삼켜짐 | round3-f.md |
| R3F-22 | 낮음 | DatabaseEngine.gen_xml 이 본문의 리터럴 "&amp;" 를 "&" 로 바꾸고 XML 금지 제어문자를 그대로 내보냄 | round3-f.md |
| R3G-01 | 높음 | wheel/ini 로 배포하면 사이트 전체가 "Ready" 텍스트 스텁이 되고 모든 URL 이 200 | round3-g.md |
| R3G-02 | 높음 | 폴백 JSON 로그인이 올바른 비밀번호에서도 AttributeError 로 죽고, 시드 계정은 로그인 자체가 불가 | round3-g.md |
| R3G-03 | 중간 | paste 진입점 `namifax:main` 이 서브모듈 namifax.main 과 이름 충돌 | round3-g.md |
| R3G-04 | 중간 | 개발 환경이 avantfax 의존을 가리고, wheel 설치 검증과 이중 모듈 루트가 테스트에 섞임 | round3-g.md |
| R3G-05 | 중간 | namifax 뷰가 avantfax 스텁 구현에 묶여 있어 namifax 쪽 수정이 닿지 않고, 엔진 클래스가 이종 | round3-g.md |
| R3G-06 | 중간 | namifax CLI 서브명령 5개가 미디어 스텁이 남아 있는 avantfax 코드를 실행 (namifax 의 개선이 우회됨) | round3-g.md |
| R3G-07 | 중간 | ] `namifax ocr-import` 는 OCR 을 하지 않는 스텁이고 OcrService 와 연결되지 않음 | round3-g.md |
| R3G-08 | 낮음 | cron 의 namifax 전용 `-p` 옵션이 도움말에 없고 -t 없이 동작하지 않으며 오류를 삼키고, -i/-d 는 잘못된 값에서 트레이스백 | round3-g.md |
| R3G-09 | 중간 | 선택 기능용 라이브러리 하나가 없어도 전체 UI 가 폴백 스텁으로 교체됨 | round3-g.md |
| R3G-10 | 낮음 | 테스트가 avantfax 복제본을 검증해 namifax 전용 분기와 53개 모듈이 미검증 | round3-g.md |
| R3H-01 | 높음 | POST /delete 가 fid 없이도 1번 팩스를 삭제 | round3-h.md |
| R3H-02 | 중간 | 링크 쿼리 값이 URL 인코딩되지 않아 '&', '+', '#' 가 포함되면 깨짐 | round3-h.md |
| R3H-03 | 중간 | Rotate 링크가 GET 으로 JSON 엔드포인트를 열어 사용자가 원시 JSON 화면으로 이동 | round3-h.md |
| R3H-04 | 중간 | 플래시/오류 배너가 두 번 출력됨 (layout 과 페이지가 각각 출력) | round3-h.md |
| R3H-05 | 중간 | "실시간 갱신" 문구와 달리 폴링/자동완성 JS 가 전혀 없고 /ajax/* 엔드포인트 7개가 어떤 템플릿에서도 호출되지 않음 | round3-h.md |
| R3H-06 | 중간 | 설정 화면 패스키 목록: 서버 오류(500)를 "등록된 키 없음" 으로 표시, 삭제 결과도 무시 | round3-h.md |
| R3H-07 | 낮음 | 패스키 목록이 서버 문자열을 innerHTML 에 그대로 삽입 | round3-h.md |
| R3H-08 | 중간 | WebAuthn credential_id 저장/조회 형식이 브라우저가 보내는 형식과 어긋남 | round3-h.md |
| R3H-09 | 중간 | Email Book 화면으로 가는 링크가 어디에도 없음 | round3-h.md |
| R3H-10 | 낮음 | 이메일북 "새 연락처" 폼의 기본 id 가 1 이고 새 폼에도 Delete 버튼이 있음 | round3-h.md |
| R3H-11 | 낮음 | 수신함 View 버튼 아이콘이 흰 사각형으로 보임 | round3-h.md |
| R3H-12 | 중간 | 모바일(375px): 관리자 사이드바가 본문 앞에 전부 펼쳐지고 표가 잘리며, 주소록은 가로 스크롤 발생 | round3-h.md |
| R3H-13 | 중간 | 송신함이 레거시 대비 열/조작 누락: 사용자, 시도 횟수, 우선순위, 작업 수정(Modify) 링크가 없음 | round3-h.md |
| R3H-14 | 중간 | 팩스 보기 화면에서 Archive/Delete/Note/Assign 동작과 이전/다음 이동이 빠짐 | round3-h.md |
| R3H-15 | 낮음 | 설정 화면이 레거시 필드/안내를 일부 누락하고 일부 select 가 하드코딩 | round3-h.md |
| R3H-16 | 낮음 | assign 모달: 회사 검색 입력이 무동작이고 fid 를 제출하지 않음 | round3-h.md |
| R3H-17 | 중간 | refax/note 모달이 GET 으로 열릴 때 가짜 기본값을 입력칸에 미리 채움 | round3-h.md |
| R3H-18 | 낮음 | sendfax 파일 입력의 접근성/검증: sr-only 입력에 포커스 표시가 없고 파일이 필수가 아님 | round3-h.md |
| R3H-19 | 낮음 | home.jinja2 는 도달 불가이거나 깨진 죽은 템플릿 | round3-h.md |
| R3H-20 | 낮음 | 로그인 화면의 사실과 다른 문구와 항상 보이는 SSO/패스키 버튼 | round3-h.md |
| R3H-21 | 낮음 | 수신함 드롭다운/전체 선택의 키보드 및 상태 동기화 결함 | round3-h.md |
| R3H-22 | 낮음 | 주소록 검색어가 소문자로 바뀌어 다시 표시됨 | round3-h.md |
| R3H-23 | 낮음 | 프린터 삭제 confirm 이 번역 문자열을 JS 작은따옴표 안에 직접 삽입 | round3-h.md |
| R4E-01 | 중간 | 아카이브 검색이 일치 결과가 없으면 조작된 결과를 만들어 냄 | round4-e2e.md |
| R4E-02 | 낮음 | SMTP 진단 테스트를 누르면 폼이 입력한 호스트/포트를 잃고 기본값으로 재렌더됨 | round4-e2e.md |
| R4E-03 | 낮음 | 태블릿 폭(768px)에서 공통 헤더가 넘쳐 가로 스크롤이 생기고 수신함 표의 작업 열이 잘림 | round4-e2e.md |
| R4E-04 | 중간 | 설정에서 저장한 표시 언어가 계정이 아니라 브라우저 쿠키에만 남음 | round4-e2e.md |
| R4E-05 | 낮음 | 로그인 화면의 SAML 버튼이 미설정 상태에서도 노출되고 누르면 안내 없이 /login 으로 되돌아옴 | round4-e2e.md |
| R4F-01 | 중간 | PHP 브리지가 공개 속성 `debug` 를 DB 컬럼으로 보내 insert, update, find 가 항상 실패 | round4-files.md |
| R4F-02 | 낮음 | bridge_cli 인자 모드는 예외를 처리하지 않고, PHP 의 빈 배열이 JSON `[]` 가 되어 `.items()` 에서 죽음 | round4-files.md |
| R4F-03 | 낮음 | FileUploadBridge: 무작위 파일명이 호출마다 다시 만들어져 PHP 가 아는 이름과 저장된 이름이 다르고, set_name 은 전달되지 않음 | round4-files.md |
| R4F-04 | 중간 | AFUserAccountBridge: 캐시된 dbdata 로 update() 하면 이미 바꾼 비밀번호가 옛 해시로 되돌아감 (R3C-11 의 PHP 쪽 변형) | round4-files.md |
| R4F-05 | 낮음 | FaxPDFArchiveBridge: PHP 가 기대하는 `m_archstamp` 키를 브리지가 보내지 않아 보관일시, 수정일시가 항상 NULL | round4-files.md |
| R4F-06 | 낮음 | create_thumbnails, ocr_import 가 레거시의 `$INSTALLDIR` 접두어를 빼먹어 경로가 현재 디렉터리 기준이 됨 | round4-files.md |
| R4F-07 | 중간 | 폴백 웹앱의 쿼리 파라미터 파싱 예외가 처리되지 않아 서버 오류가 됨 | round4-files.md |
| R4F-08 | 낮음 | 수신함 뷰에 테스트용 `?empty=1` 스위치가 운영 코드로 남아 있음 | round4-files.md |
| R4F-09 | 중간 | 골든 마스터의 required_text 를 통과시키려고 템플릿에 눈에 안 보이는 문구를 심어 둠 | round4-files.md |
| R4F-10 | 중간 | 이메일북 빈 목록 안내문이 9개 로케일에서 `\"` 를 글자 그대로 표시 | round4-files.md |
| R4F-11 | 낮음 | populate_all_locales.py 의 레거시 가져오기 범위가 좁고, 스크립트 설명과 산출물이 서로 맞지 않음 | round4-files.md |
| R4F-12 | 높음 | 테스트가 클래스에 없는 메서드를 mock 해서, 운영에서 AttributeError 가 나는 경로가 통과함 | round4-files.md |
| R4F-13 | 중간 | 테스트 간 전역 DB 공유로 순서 의존 (원인 쌍 규명, F5-08 의 구체화) | round4-files.md |
| R4F-14 | 낮음 | `test_i18n_cli_compile` 이 작업 트리의 .mo 를 다시 써서 오래된 .mo 를 가려 줌 | round4-files.md |
| R4F-15 | 낮음 | 항상 참이거나 아무것도 증명하지 못하는 assert | round4-files.md |
| R4F-16 | 중간 | 결함을 정답으로 고정한 테스트 (K15, F5-06 의 구체 목록) | round4-files.md |
| R4F-17 | 낮음 | 경계값과 오류 경로 테스트가 거의 없음 | round4-files.md |
| R4F-18 | 중간 | CLI 골든 마스터가 DB 없는 환경에서 기록되었고 stderr 를 비교하지 않으며 오류 출력을 끔 | round4-files.md |
| R4F-19 | 중간 | 웹 골든 러너가 계약의 상당 부분을 읽지 않음 | round4-files.md |
| R4F-20 | 중간 | 웹 골든 계약의 required_text 상당수가 레거시에 없는 문구 (F5-06 의 수치화) | round4-files.md |
| R4Z-01 | 높음 | 텍스트 파라미터에 멀티파트 파일 파트를 보내면 40개 라우트가 500 | round4-fuzz.md |
| R4Z-02 | 중간 | fax_download 가 fid/format 을 Content-Disposition 헤더에 검증 없이 넣어 CR/LF, 비 latin-1 문자에서 500, NUL 은 통과 | round4-fuzz.md |
| R4Z-03 | 중간 | /admin/fax2email 생성이 회사 행만 남기고 팩스 행 저장은 실패하는데 성공 화면 (부분 저장) | round4-fuzz.md |
| R4Z-04 | 낮음 | NUL 문자 또는 10만자 입력이 SQL 오류로 조용히 삼켜져 성공/빈 결과 응답 | round4-fuzz.md |
| R4Z-05 | 낮음 | /admin/covers 의 `file` 필드가 업로드 파트일 때 500 (R4Z-01 의 admin 변형이 아니라 신규 업로드 경로) | round4-fuzz.md |
| R4U-01 | 치명 | 관리자(uid=1) 삭제 보호 가드를 0-패딩 문자열로 우회 — 부트스트랩 관리자 소프트 삭제 가능 | round4-unmask.md |
| R4U-02 | 높음 | 비밀번호 재사용 금지 정책이 불린→문자열 왕복 버그로 "항상 재사용 허용"으로 반전됨 | round4-unmask.md |
| R4U-03 | 중간 | 분류(FaxCategory) 삭제 시 참조 정리가 전혀 없어 UserAccount.faxcats / Modems.faxcatid 가 존재하지 않는 catid 를 가리키게 됨 | round4-unmask.md |
| R4U-04 | 중간 | 배포목록(DistroList) 삭제가 GET 요청만으로도 실행됨 — 메서드 제한 없는 상태 변경 | round4-unmask.md |
| R5F-01 | 중간 | WebAuthn 서비스가 QueryResult 를 리스트처럼 반복·인덱싱해, 저장된 패스키가 목록에도 인증에도 쓰이지 않음 (K16 의 실행 결과, ADM-15 와 같은 원인) | round5-files.md |
| R5F-02 | 중간 | `pserve development.ini` / `production.ini` 로 기동하면 스케줄러(자정 정리, 전화부 동기화)가 전혀 시작되지 않음 (문서 §8.3 은 반대로 주장) | round5-files.md |
| R5F-03 | 중간 | `phb` 가 실제 스키마에서 모든 회사의 팩스번호를 빈 값으로 내보내 HylaFAX 전화부가 번호 없는 항목만 가짐 (COR-06/07 의 변형) | round5-files.md |
| R5F-04 | 낮음 | DynamicConfig.create 가 device 가 비어 있는(전체 모뎀 적용) 규칙의 중복을 막지 못함 (명세 14 위반, R3C-07 의 변형) | round5-files.md |
| R5F-05 | 낮음 | 스케줄러의 전화부 동기화 로그가 항상 "synchronized 0 entries" (종료 코드를 항목 수로 사용) | round5-files.md |
| R5F-06 | 낮음 | FileUpload 가 이름 `..` 을 허용해 파일이 대상 디렉터리의 상위에 임시 파일 이름으로 저장됨 (R3D-31 (3) 의 변형) | round5-files.md |
| R5F-07 | 낮음 | 로케일 협상이 Accept-Language 를 쓰지 않고, `ko-KR` 같은 지역 코드는 인식하지 못함 (문서 §7.1 과 다름) | round5-files.md |
| R5F-08 | 낮음 | TOTP 검증 창이 0 이라 시계 오차나 30초 경계에서 정상 코드가 거부됨 | round5-files.md |
| R5F-09 | 낮음 | 관리자 프린터 화면의 "테스트" 동작이 임의 host:port 로 서버가 소켓 연결을 맺고, 성공/실패와 예외 문자열을 돌려줌 (SSRF/내부망 포트 스캔 오라클, 관리자 한정) | round5-files.md |
| R5F-10 | 낮음 | PHP 브리지가 레거시 공개 인터페이스를 크게 덜 구현하고, bridge_cli 에는 호출자 없는 분기가 남아 있음 | round5-files.md |
| R5F-11 | 낮음 | 테스트가 같은 소스를 세 가지 모듈 이름(`avantfax.*`, `src.namifax.*`, `namifax.*`)으로 임포트해, 서로 다른 클래스와 전역 싱글턴을 검증함 (R3G-10 의 확장 | round5-files.md |
| R5F-12 | 낮음 | 명세 01~38 의 인터페이스 요구와 구현이 어긋남 (명세 39~47 은 R3D-41 이 다룸) | round5-files.md |
| R5F-13 | 낮음 | docs/ 운영 문서가 안내하는 설정과 기능이 실제로는 없음 | round5-files.md |
| R5F-14 | 낮음 | ARCHITECTURE.md 의 수치와 구조 서술이 서로 모순되거나 실제와 다름 | round5-files.md |
| R5F-15 | 낮음 | NEW_FEATURES_PLAN.md 가 `[완료]` 로 표기한 기능 중 구현되지 않은 것: 스케줄러 TIFF 정리 연동, Presigned URL 뷰어 | round5-files.md |
| R5L-01 | 중간 | viewfax 가 이전/다음 팩스 이동 정보를 전혀 넘기지 않아 이동 버튼이 영원히 안 보임 | round5-legacy.md |
| R5L-02 | 중간 | 수신함에서 이미 보관(inbox=0)된 팩스나 존재하지 않는 fid 도 viewfax 가 정상 화면(200)으로 열림 | round5-legacy.md |
| R5L-03 | 중간 | 표지도 첨부파일도 없는 팩스 제출이 허용되고 outbox 로 리다이렉트됨 | round5-legacy.md |
| R5L-04 | 낮음 | 단일 수신번호의 공백, 개행, 세미콜론 정규화가 없음 | round5-legacy.md |
| R5L-05 | 중간 | 주소록 회사 삭제 시 수신 팩스 재지정과 팩스번호 정리가 없음 | round5-legacy.md |
| R5L-06 | 높음 | 주소록 편집이 팩스번호별 속성 편집과 복수 번호 관리를 지원하지 않음 | round5-legacy.md |
| R5L-07 | 낮음 | /setcompany 가 rurl/vf/va 복귀 경로를 무시하고 GET 으로도 동작 | round5-legacy.md |
| R5L-08 | 중간 | 새 팩스 도착 알림음(audiofile) 기능이 통째로 없음 | round5-legacy.md |
| R5L-09 | 낮음 | outbox 의 60초 자동 새로고침(meta refresh)이 없음 | round5-legacy.md |
| R5L-10 | 중간 | 관리자 사용자 폼에 프로필, 환경 필드가 없고 신규 사용자 기본값도 적용되지 않음 | round5-legacy.md |
| R5L-11 | 중간 | 이메일 전송 모달이 cc/bcc, 첨부 파일명, 분류, 보관 옵션과 레거시 기본값을 모두 누락 | round5-legacy.md |
| R5L-12 | 낮음 | 주소 자동완성이 최소 2자 조건, 예약 번호 제외, "(설명)" 표기를 지키지 않음 | round5-legacy.md |
| R5L-13 | 중간 | faxalter 모달의 폼 필드/연산 키가 서비스가 이해하는 키와 달라 대부분의 수정이 적용되지 않음 | round5-legacy.md |
| R5L-14 | 낮음 | 보관/삭제/노트 등 사용자 동작이 SysLog 감사 기록을 남기지 않음 | round5-legacy.md |
| R5U-01 | 높음 | 모뎀/분류/DID 가 하나도 없는 사용자는 아카이브 검색에서 제한 없이 전체 팩스를 본다 (빈 목록 = 무제한) | round5-unmask.md |
| R5U-02 | 중간 | 분류 삭제 시 FaxArchive.faxcatid 도 정리되지 않음 (R4U-03 의 추가 사례), remove_category 는 호출처 없음 | round5-unmask.md |
| R5U-03 | 중간 | 모뎀 삭제 후 UserAccount.modemdevs 에 장치 이름이 남아 같은 이름으로 모뎀을 다시 만들면 권한이 조용히 부활 | round5-unmask.md |
| R5U-04 | 중간 | 주소록 UI/훅으로 만든 회사의 팩스번호가 목록, 검색, 자동완성에서 보이지 않음 | round5-unmask.md |
| R5U-05 | 중간 | faxrcvd: 이미 있는 회사명으로 들어온 새 번호는 번호 등록이 건너뛰어져 faxnumid=0 으로 보관함에 들어감 | round5-unmask.md |
| R5U-06 | 중간 | /ajax/inbox 신규 팩스 수가 사용자별 접근 제한을 무시 | round5-unmask.md |
| R5U-07 | 높음 | 재전송(/refax) 모달이 원본 팩스 문서를 전혀 첨부하지 않고 fid 를 사용하지 않음 | round5-unmask.md |
| R5U-08 | 낮음 | 작업 삭제(`/outbox?kill=`) 가 존재하지 않는 작업에도 성공 메시지를 표시 | round5-unmask.md |
| R5U-09 | 낮음 | 이메일북 폼의 `company` 입력이 버려져 연락처가 회사에 연결되지 않음 | round5-unmask.md |
