1: `ARCHITECTURE.md`의 포팅 큐에 따라 다음 모듈(백엔드 서비스 또는 웹 라우트/UI) 이식을 진행합니다.
2: 
3: - 대상 모듈/라우트: `[모듈명 또는 레거시 라우트 (예: inbox.php + inbox.tpl)]`
4: - 타깃 플랫폼: `[Python 3.11+ / Pyramid]`
5: - 템플릿 및 스타일: `[Jinja2 + Tailwind CSS]`
6: 
7: 작업 대상이 **웹 UI / 라우트 템플릿**인 경우 아래 5단계 프로토콜을 엄격히 준수하여 진행해주세요:
8: 
9: 1. **UI & View Data Contract Extraction (명세 및 계약 추출)**:
10:    - 레거시 PHP 컨트롤러의 동작 분석: 요청 파라미터(Query/Form), 세션 인증/권한 검사, 호출하는 서비스 로직.
11:    - Smarty 템플릿(`.tpl`)으로 전달되는 컨텍스트 변수 맵(`$smarty->assign(...)`) 및 제어문(if, foreach) 블록 명세화.
12:    - 화면의 구조적 마크업(DOM 계층, 폼 컨트롤, 테이블 컬럼, 액션 버튼, 에러 알림 등)을 분석하여 `specs/web/<route_name>.md`로 저장.
13: 
14: 2. **View Characterization & Golden Test 작성 (테스트 우선)**:
15:    - Pyramid `pyramid.testing.DummyRequest` 및 `webtest.TestApp`을 활용한 뷰 단위/통합 테스트 작성 (`tests/web/test_<view_name>.py`).
16:    - Phase 2에서 추출한 레거시 Golden Master(HTML DOM 및 `contract.json`)와 폼 필드(`name`, `type`, `action`), HTTP 상태 코드, 리다이렉트 경로를 대조하는 검증 로직 포함.
17: 
18: 3. **Idiomatic Pyramid View Controller 구현**:
19:    - `src/namifax/views/<view_name>.py`에 `@view_config` 데코레이터를 적용한 Pyramid 뷰 컨트롤러 작성.
20:    - 이미 포팅 완료된 NamiFAX 모던 백엔드 서비스 계층(`src/namifax/services/` 등)을 호출하여 데이터 바인딩.
21:    - Pyramid Security Policy 및 ACL(`permission='public'`, `'view'`, `'admin'`, `'send_fax'`) 적용.
22: 
23: 4. **Tailwind CSS 기반 1:1 Layout Template Rewrite (템플릿 및 스타일링 구현)**:
24:    - 레거시 Smarty 템플릿(`.tpl`)을 Jinja2(`.jinja2`)로 변환 (`src/namifax/templates/<view_name>.jinja2`).
25:    - **화면 동일성 원칙**: 레거시의 인라인 스타일 및 구형 CSS를 **Tailwind CSS 유틸리티 클래스로 현대화**하여 레거시 화면과 동일한 비주얼(컬러, 폰트, 여백, 테이블 형태, 모달, 정렬)을 완벽히 재현.
26:    - 공통 레이아웃(`layout.jinja2`) 및 네비게이션 툴바 매크로 재사용.
27: 
28: 5. **Verification, UI Inspection & Status Update**:
29:    - 단위/통합 테스트 실행 (`pytest tests/web/test_<view_name>.py`) 및 Phase 2 웹 차분 테스트를 실행하여 Golden Master와의 100% 일치 확인.
30:    - 브라우저 상에서 화면 레이아웃 및 폼 인터랙션 직접 검증.
31:    - 검증 완료 후 `ARCHITECTURE.md`의 웹 포팅 상태 매트릭스를 `[COMPLETE]`로 업데이트.
32: 
33: *(백엔드 단위 서비스/유틸 모듈 작업 시에는 기존의 [Contract] -> [Unit Test] -> [Idiomatic Rewrite] -> [FFI Bridge] 루프를 따릅니다.)*
34: 

