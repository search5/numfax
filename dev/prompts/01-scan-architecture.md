1: [System Context & Full-Stack Architecture Check]
2: 프로젝트 전체 파일 목록과 소스 코드 구조(백엔드 서비스, CLI 훅, 레거시 PHP 웹 라우트 및 Smarty 템플릿, 정적 리소스)를 전수 스캔해주세요.
3: 
4: 다음 작업을 수행하고 그 결과를 `ARCHITECTURE.md` 파일에 체계적으로 작성 또는 업데이트해주세요:
5: 
6: 1. **백엔드 모듈 및 의존성 관계 분석**:
7:    - 전체 백엔드 모듈 간의 의존성 관계 및 데이터 모델/서비스 계층 분석
8:    - 위상 정렬(Topological Sort)을 기반으로 한 하위 모듈부터 상위 서비스까지의 '포팅 순서 목록(Migration Queue)' 정리
9: 
10: 2. **웹 라우팅 & PHP 엔드포인트 전수 분석**:
11:    - 사용자 포털(`legacy/avantfax/*.php`), 관리자 포털(`legacy/avantfax/admin/*.php`), 비동기 엔드포인트(`legacy/avantfax/ajax/*.php`) 전수 목록화
12:    - 각 엔드포인트의 HTTP 메서드(GET/POST), 필수/선택 요청 파라미터(Query/Form/Uploads), 인증 및 권한 제어 요구사항(비로그인, 일반 사용자, 관리자) 명세화
13:    - 대응될 **Pyramid 라우팅 테이블(Route Name, Pattern, Permission)** 매핑 계획 수립
14: 
15: 3. **Smarty 템플릿 계층 & 뷰 데이터 계약(View Data Contract) 분석**:
16:    - 레거시 Smarty 템플릿(`main_theme/templates/*.tpl`, `admin_theme/templates/*.tpl`)의 계층 구조 분석 (공통 레이아웃 `header.tpl`, `bar.tpl`, `menu.tpl`, `footer.tpl` 및 각 페이지별 본문 템플릿)
17:    - PHP 컨트롤러에서 템플릿으로 전달되는 컨텍스트 변수(`$smarty->assign(...)`) 및 루프/조건문 블록 데이터 명세화
18:    - 타깃 템플릿 엔진인 **Jinja2**로의 1:1 변환 계층 및 템플릿 상속(`layout.jinja2`) 아키텍처 정의
19: 
20: 4. **Tailwind CSS 프런트엔드 UI 아키텍처 및 디자인 시스템 정의**:
21:    - 레거시 CSS(`css/*.css`, `interface.css`)의 디자인 토큰(색상표, 그리드/테이블, 폼 인풋/버튼 스타일, 탭/네비게이션 바, 팩스 뷰어 모달) 분석
22:    - 레거시 화면과 **100% 동일한 비주얼과 레이아웃(Visual & Layout Fidelity)**을 달성하기 위한 **Tailwind CSS** 유틸리티 클래스 매핑 전략 수립
23:    - Tailwind CSS 빌드/통합 방식(Standalone CLI 또는 Vite/PostCSS 빌드 파이프라인) 및 Pyramid 정적 에셋(`src/namifax/static/`) 구조 설계
24: 
25: 5. **웹 UI 포팅 매트릭스(Web UI Porting Status Matrix) 작성**:
26:    - `[공통 레이아웃/컴포넌트] -> [인증/로그인] -> [코어 뷰(Inbox, Outbox, Archive, SendFax)] -> [관리자 뷰(Admin Pages)] -> [Ajax API 엔드포인트]` 순으로 정렬된 위상 포팅 큐 구성
27:    - 상태값: `[PENDING]`, `[IN_PROGRESS]`, `[COMPLETE]` 관리
28: 
