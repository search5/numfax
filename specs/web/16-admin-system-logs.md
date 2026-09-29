# Specification: Web Route 16 - Admin System Logs Viewer

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/admin/system_logs.php`, `legacy/avantfax/includes/templates/admin_theme/templates/system_logs.tpl`
- **Target Route**:
  - `admin_system_logs` (`GET /admin/system_logs`): 시스템 이벤트 및 HylaFAX 감사 로그 검색 및 열람
- **ACL Permission**: `admin` (시스템 관리자 권한 필수)
- **Request Parameters**:
  - `kw` (str, optional): 로그 내용 검색 키워드
  - `day` (str/int, optional): 조회 일자 (01~31)
  - `month` (str/int, optional): 조회 월 (01~12)
  - `year` (str/int, optional): 조회 연도 (YYYY)
  - `_submit_check` (hidden, value: "1")
- **Response Behavior**:
  - HTTP 200 OK + `admin/system_logs.jinja2` 렌더링

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$syslog` | `log_entries` | List[Dict] | 조회된 시스템 로그 항목 리스트 (`logdate`, `logtext`) |
| `$fvalues.kw` | `filter_kw` | str | 입력된 검색 키워드 보존 |
| `$fvalues.day` | `filter_day` | str | 선택된 일자 |
| `$fvalues.month`| `filter_month`| str | 선택된 월 |
| `$fvalues.year` | `filter_year` | str | 선택된 연도 |
| `$days`, `$months`, `$years` | `date_options` | Dict[str, Dict] | 날짜 필터 드롭다운 옵션 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `admin/layout.jinja2` 상속
- **Heading**: `h1` ('System Logs')
- **Filter Form (`form[action="/admin/system_logs"][method="get"]`)**:
  - `input[name="kw"][type="text"]` (키워드 입력창, 자동 포커스)
  - `select[name="day"]`, `select[name="month"]`, `select[name="year"]`
  - `button[type="submit"]` ('Search')
  - `input[name="_submit_check"][type="hidden"][value="1"]`
- **Log Table (`table`)**:
  - 컬럼: `DATE` (110px, 고정폭), `LOGTEXT` (가변폭)
  - 각 로그 행: `<td class="logdate">`, `<td class="logtext">`
  - 결과 없을 시 빈 상태: 'No log entries found for given criteria'

---

## 4. Tailwind CSS Visual Fidelity Specification
| 레거시 스타일 속성 | Tailwind CSS 유틸리티 클래스 | 적용 대상 |
| :--- | :--- | :--- |
| 검색 필터 박스 | `max-w-4xl mx-auto bg-slate-50 border border-slate-300 rounded p-4 mb-6 flex flex-wrap items-center gap-3 justify-center text-xs shadow-sm` | 상단 검색 툴바 |
| 키워드 입력창 | `border border-slate-300 rounded px-3 py-1.5 text-xs bg-white focus:ring-1 focus:ring-sky-600 focus:outline-none w-72` | 검색어 입력 필드 |
| 로그 테이블 | `w-full max-w-5xl mx-auto bg-white border border-slate-300 rounded shadow-sm text-xs font-mono` | 시스템 로그 테이블 |
| 로그 일시 칼럼 | `w-36 p-2 text-slate-500 font-semibold border-b border-slate-200 whitespace-nowrap align-top` | 날짜 셀 |
| 로그 본문 칼럼 | `p-2 text-slate-800 border-b border-slate-200 whitespace-pre-wrap break-all align-top` | 로그 본문 셀 |

---

## 5. Golden Master Verification Scenarios
- `W22_admin_system_logs`: 시스템 로그 검색 툴바(키워드/날짜 셀렉트) 및 로그 테이블 마크업 전수 검증
