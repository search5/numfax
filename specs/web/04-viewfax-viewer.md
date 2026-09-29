# Specification: Web Route 04 - Fax Viewer Modal & Detail

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/viewfax.php`, `legacy/avantfax/includes/templates/main_theme/templates/viewfax.tpl`
- **Target Route**: `viewfax` (`GET /viewfax`)
- **ACL Permission**: `view`
- **Request Parameters**:
  - `fid` (int, required): 조회 대상 팩스 아카이브 고유 ID
  - `page` (int, default: 1): 현재 조회할 팩스 페이지 번호
- **Response Behavior**:
  - HTTP 200 OK + `viewfax.jinja2` 렌더링
  - 비인증 접근 시 302 Found $\rightarrow$ `/login`

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$fid` | `fid` | int | 팩스 ID |
| `$pages` | `pages` | int | 전체 페이지 수 |
| `$curpage` | `current_page` | int | 현재 페이지 번호 |
| `$faxdata.archstamp` | `archstamp` | str | 수신 일시 |
| `$faxdata.modemdev` | `modemdev` | str | 수신 모뎀 디바이스명 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `layout.jinja2` 상속
- **Toolbar Controls**:
  - `a[href*="/faxes/rotate/"]`: 'Rotate 90°' 버튼
  - `a[href*="/faxes/download/"]`: 'Download PDF' 버튼
  - `a[href="/inbox"]`: 'Back to Inbox' 링크
- **Viewer Area (`#viewer-container`)**:
  - 그레이 배경의 문서 프리뷰 캔버스
  - 문서 헤더: `FACSIMILE TRANSMISSION`, 로고, 일시
  - 문서 풋터: `Page {n} of {total} | Device: {modemdev}`

---

## 4. Tailwind CSS Visual Fidelity Specification
- 프리뷰 캔버스: `bg-slate-200/70 border border-slate-300 rounded p-4 flex items-center justify-center min-h-[500px]`
- 문서 시트: `bg-white shadow-lg border border-slate-300 p-8 max-w-2xl w-full min-h-[600px]`
- 버튼 스타일: `inputbutton text-xs inline-flex items-center space-x-1`

---

## 5. Golden Master Verification Scenarios
- `W06_viewfax_modal`: 팩스 뷰어 화면 렌더링, 다운로드/회전 링크 검증
