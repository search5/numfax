# Specification: Web Route 14 - Admin Modem Lines Configuration

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/admin/conf_modems.php`, `conf_modems_edit.php`, `legacy/avantfax/includes/templates/admin_theme/templates/conf_modems.tpl`, `conf_modems_edit.tpl`
- **Target Route**:
  - `admin_modems` (`GET /admin/modems`, `POST /admin/modems`): 모뎀 라인 목록 조회, 디바이스 등록, 별칭 및 인쇄/카테고리 매핑 설정
- **ACL Permission**: `admin` (시스템 관리자 권한 필수)
- **Request Parameters**:
  - `devid` (int, optional): 모뎀 DB PK ID (신규 등록 시 누락, 수정 시 필수)
  - `device` (str, required, max: 20): 물리/가상 모뎀 장치명 (예: `ttyS0`, `ttyIAX0`)
  - `alias` (str, required, max: 50): 모뎀 표시 별칭 (예: `Sales Inbound`)
  - `contact` (str, optional): 수신 팩스 자동 전달 대상 이메일 주소
  - `printer` (str, optional): 수신 시 자동 인쇄할 CUPS 프린터 큐명
  - `faxcatid` (int, optional): 수신 팩스 자동 분류 카테고리 ID
  - 액션 플래그: `create`, `save`, `delete`, `cancel`
  - `_submit_check` (hidden, value: "1")
- **Response Behavior**:
  - GET: HTTP 200 OK + `admin/modems.jinja2`
  - POST 유효성 오류: HTTP 200 OK + `admin/modems.jinja2` (`error="에러메시지"`)
  - POST 성공(등록/수정/삭제): HTTP 302 Found $\rightarrow$ `/admin/modems`

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$devices` | `devices` | Dict[str, str] | 등록된 전체 모뎀 디바이스 매핑 (`device` -> `alias`) |
| `$fvalues.devid` | `modem_form.devid` | Optional[int] | 현재 편집 대상 모뎀 ID |
| `$fvalues.device`| `modem_form.device`| str | 모뎀 디바이스 장치명 |
| `$fvalues.alias` | `modem_form.alias` | str | 모뎀 표시 별칭 |
| `$fvalues.contact`| `modem_form.contact`| str | 수신 알림 이메일 |
| `$fvalues.printer`| `modem_form.printer`| str | 자동 인쇄 프린터 큐 |
| `$categories` | `categories` | Dict[int, str] | 팩스 카테고리 드롭다운 옵션 |
| `$create` | `is_new` | bool | 신규 모뎀 등록 모드 여부 |
| `$error` | `error` | Optional[str] | 오류 메시지 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `admin/layout.jinja2` 상속
- **Heading**: `h1` ('Configure Modems')
- **Container Layout (2-Column Master-Detail)**:
  - **Left Column**:
    - `<select name="device" size="10">`: 현재 등록된 모뎀 목록 리스트박스
  - **Right Column (Form Controls)**:
    - `form[action="/admin/modems"][method="post"]`
    - `input[name="device"]` (required)
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
  - 모뎀 구성 안내 설명 텍스트

---

## 4. Tailwind CSS Visual Fidelity Specification
| 레거시 스타일 속성 | Tailwind CSS 유틸리티 클래스 | 적용 대상 |
| :--- | :--- | :--- |
| 마스터-디테일 레이아웃 | `grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto bg-white border border-slate-300 rounded p-6 shadow-sm` | 모뎀 설정 박스 |
| 좌측 리스트박스 | `w-full border border-slate-300 rounded text-xs p-2 bg-slate-50 focus:ring-1 focus:ring-sky-600` | 모뎀 디바이스 선택창 |
| 폼 인풋 필드 | `border border-slate-300 rounded px-3 py-1.5 text-xs bg-white focus:ring-1 focus:ring-sky-600 focus:outline-none w-full` | 텍스트 입력창 |
| 설명 박스 `#explain-me` | `mt-6 p-4 bg-slate-50 border border-slate-200 rounded text-xs text-slate-600 leading-relaxed` | 하단 안내문 |
| 저장/생성 버튼 `.inputsubmit` | `px-5 py-2 bg-sky-800 text-white rounded text-xs font-semibold hover:bg-sky-700 shadow-sm transition` | 제출 버튼 |
| 삭제 버튼 `.inputcancel` | `px-5 py-2 bg-rose-700 text-white rounded text-xs font-semibold hover:bg-rose-600 shadow-sm transition` | 삭제 버튼 |

---

## 5. Golden Master Verification Scenarios
- `W20_admin_modems`: 모뎀 라인 목록 선택창, 디바이스/별칭/프린터 입력 폼, 설명 박스 마크업 전수 검증
