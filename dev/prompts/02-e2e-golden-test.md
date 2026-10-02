1: 레거시 프로그램(백엔드 CLI 및 Smarty 기반 웹 프런트엔드 전체)을 실행하고 출력 결과와 화면 렌더링을 검증할 수 있는 E2E Golden Master 추출 및 차분 테스트 스위트를 작성해주세요.
2: 
3: [웹 프런트엔드 & 백엔드 골든 마스터 추출 요구사항]
4: 
5: 1. **레거시 웹 실행 및 시드 데이터 준비**:
6:    - 레거시 PHP 환경(PHP 내장 서버 `php -S` 또는 Docker 환경)을 구동하고 일관된 테스트 시드 DB(관리자/일반 계정, 모뎀, 주소록, 수신/송신 팩스 아카이브)를 준비할 것.
7: 
8: 2. **라우팅별 웹 Golden Master 시나리오 구성 (최소 20개 이상)**:
9:    - **인증 플로우**: 로그인 페이지(`GET /`), 로그인 실패(잘못된 비밀번호 에러 렌더링), 로그인 성공(세션 발급 및 `inbox.php` 리다이렉트), 비밀번호 찾기(`forgot.php`), 로그아웃.
10:    - **인박스 (Inbox)**: 수신함 목록(`inbox.php`), 빈 인박스 화면, 팩스 상세 뷰어(`viewfax.php?fid=...`), PDF 다운로드 스트리밍.
11:    - **아웃박스 (Outbox)**: 송신 큐 모니터링 테이블(`outbox.php`), 발송 작업 취소 동작.
12:    - **팩스 발송 (SendFax)**: 팩스 발송 입력 폼(`sendfax.php`), 유효성 검증 실패(필수 필드 누락), 정상 발송 POST 요청.
13:    - **아카이브 및 검색 (Archive)**: 아카이브 목록, 검색 조건 필터 폼(`archive.php`, `search.php`), 페이징 네비게이션.
14:    - **주소록 및 배포 그룹**: 주소록 목록(`addressbook.php`), 연락처 추가/수정 폼(`addressbook_edit.php`), 배포 그룹(`distrolist.php`).
15:    - **관리자 포털 (Admin)**: 대시보드(`admin/index.php`), 사용자 관리(`admin/users.php`), 모뎀 설정(`admin/modems.php`), DID 라우팅(`admin/did.php`), 바코드 라우팅(`admin/barcodes.php`), 시스템 로그(`admin/syslog.php`).
16: 
17: 3. **Golden Master 데이터 아티팩트 저장 (`dev/golden_master/web/<scenario_id>/`)**:
18:    - `response.html`: 레거시 PHP 서버가 Smarty로 렌더링한 원본 HTML 마크업 스냅샷
19:    - `contract.json`: HTTP 상태 코드, 리다이렉트 URL(Location), 폼 필드 명세(`name`, `type`, `value`, `method`, `action`), 세션 쿠키 키
20:    - `screenshot.png` (선택/권장): Playwright 또는 헤드리스 브라우저로 캡처한 화면 기준 스크린샷
21: 
22: 4. **웹 차분 검증(Differential Web Verification) 스크립트 작성 (`dev/golden_master/web_runner.py`)**:
23:    - Pyramid 웹 서버를 대상으로 동일한 HTTP 요청(GET/POST, 쿠키, 파라미터)을 전송하여 레거시 Golden Master와 비교 검증:
24:      1) **HTTP 응답 및 라우팅 일치성**: Status Code, Content-Type, Redirect Location 일치 여부
25:      2) **HTML 시맨틱 & 폼 계약 일치성**: 폼 필드(input, select, hidden 등), 버튼, 링크, 테이블 컬럼 헤더, 오류 메시지 엘리먼트 100% 매칭 검증
26:      3) **텍스트 및 비즈니스 데이터 일치성**: 렌더링된 본문 텍스트 및 데이터 테이블 내용 정규화 비교
27:      4) **Tailwind CSS 레이아웃 건전성**: 주요 컨테이너 구조 및 Tailwind 스타일 적용 상태 무결성 확인
28: 
29: 5. **기존 백엔드 CLI Golden Master와의 통합**:
30:    - 기존 백엔드 CLI 훅(dynconf, avantfaxcron, faxcover, notify, faxrcvd) Golden Master 검증과 웹 프런트엔드 차분 검증을 단일 pytest 명령(`pytest dev/golden_master/`)으로 일괄 실행할 수 있도록 통합할 것.
31: 

