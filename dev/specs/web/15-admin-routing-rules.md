# Specification: Web Route 15 - Admin Inbound DID & Barcode Routing Rules

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/admin/conf_didroute.php`, `conf_didroute_edit.php`, `conf_barcoderoute.php`, `conf_barcoderoute_edit.php`, `legacy/avantfax/includes/templates/admin_theme/templates/conf_didroute.tpl`, `conf_didroute_edit.tpl`
- **Target Route**:
  - `admin_routing_did` (`GET /admin/routing/did`, `POST /admin/routing/did`): 착신 DID 번호별 자동 라우팅 규칙 목록 및 편집
  - `admin_routing_barcode` (`GET /admin/routing/barcode`, `POST /admin/routing/barcode`): 바코드 인식 기반 자동 라우팅 규칙 관리
- **ACL Permission**: `admin` (시스템 관리자 권한 필수)
- **Request Parameters**:
  - `didr_id` (int, optional): DID 라우팅 규칙 PK ID (수정 시 필수, 생성 시 누락)
  - `route` (str, required, max: 50): 수신 DID 착신 번호 또는 바코드 정규식 패턴
  - `alias` (str, required, max: 50): 라우팅 규칙 식별용 별칭
  - `contact` (str, optional): 수신 팩스 자동 전송 대상 이메일 주소
  - `printer` (str, optional): 자동 인쇄할 프린터 큐명
  - `faxcatid` (int, optional): 팩스 자동 분류 카테고리 ID
  - 액션 플래그: `create`, `save`, `delete`, `cancel`
  - `_submit_check` (hidden, value: "1")
- **Response Behavior**:
  - GET: HTTP 200 OK + `admin/routing_did.jinja2`
  - POST 유효성 오류: HTTP 200 OK + `admin/routing_did.jinja2` (`error="에러메시지"`)
  - POST 성공(등록/수정/삭제): HTTP 302 Found $\rightarrow$ `/admin/routing/did`

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$didroutes` | `did_routes` | Dict[int, str] | 등록된 전체 DID 라우팅 규칙 (`didr_id` -> `alias`) |
| `$fvalues.didr_id` | `route_form.didr_id` | Optional[int] | 현재 선택된 라우팅 규칙 ID |
| `$fvalues.route` | `route_form.route` | str | 착신 DID 번호 또는 코드 |
| `$fvalues.alias` | `route_form.alias` | str | 라우팅 규칙 별칭 |
| `$fvalues.contact`| `route_form.contact`| str | 수신 통지 이메일 주소 |
| `$fvalues.printer`| `route_form.printer`| str | 자동 인쇄 대상 프린터 |
| `$categories` | `categories` | Dict[int, str] | 팩스 카테고리 목록 |
| `$create` | `is_new` | bool | 신규 규칙 등록 모드 여부 |
| `$error` | `error` | Optional[str] | 오류 메시지 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `admin/layout.jinja2` 상속
- **Heading**: `h1` ('Configure DID Routing')
- **Container Layout (2-Column Master-Detail)**:
  - **Left Column**:
    - `<select name="didr_id" size="10">`: 현재 등록된 라우팅 규칙 목록 리스트박스
  - **Right Column (Form Controls)**:
    - `form[action="/admin/routing/did"][method="post"]`
    - `input[name="route"]` (required)
    - `input[name="alias"]` (required)
    - `input[name="contact"]`
    - `input[name="printer"]`
    - `select[name="faxcatid"]`
    - 액션 버튼:
      - `button[name="create"]` ('Create') 또는 `button[name="save"]` ('Save')
      - `button[name="delete"]` ('Delete')
      - `button[name="cancel"]` ('Cancel')
    - `input[name="_submit_check"][type="hidden"][value="1"]`
- **Bottom Explanation Box (`#explain-me`)**:
  - DID 라우팅 동작 원리 설명 안내문

---

## 4. Tailwind CSS Visual Fidelity Specification
| 레거시 스타일 속성 | Tailwind CSS 유틸리티 클래스 | 적용 대상 |
| :--- | :--- | :--- |
| 마스터-디테일 레이아웃 | `grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto bg-white border border-slate-300 rounded p-6 shadow-sm` | 라우팅 규칙 설정 박스 |
| 좌측 리스트박스 | `w-full border border-slate-300 rounded text-xs p-2 bg-slate-50 focus:ring-1 focus:ring-sky-600` | 규칙 선택창 |
| 폼 인풋 필드 | `border border-slate-300 rounded px-3 py-1.5 text-xs bg-white focus:ring-1 focus:ring-sky-600 focus:outline-none w-full` | DID 번호/별칭 입력창 |
| 설명 박스 `#explain-me` | `mt-6 p-4 bg-slate-50 border border-slate-200 rounded text-xs text-slate-600 leading-relaxed` | 하단 DID 라우팅 설명문 |
| 저장/생성 버튼 `.inputsubmit` | `px-5 py-2 bg-sky-800 text-white rounded text-xs font-semibold hover:bg-sky-700 shadow-sm transition` | 제출 버튼 |
| 삭제 버튼 `.inputcancel` | `px-5 py-2 bg-rose-700 text-white rounded text-xs font-semibold hover:bg-rose-600 shadow-sm transition` | 규칙 삭제 버튼 |

---

## 5. Golden Master Verification Scenarios
- `W21_admin_routing`: DID 라우팅 목록 선택창, 착신 번호/별칭/프린터 설정 폼 및 설명 안내문 전수 검증
