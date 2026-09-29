# Specification: Web Route 08 - Archive & Search

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/archive.php`, `legacy/avantfax/search.php`, `legacy/avantfax/includes/templates/main_theme/templates/archive.tpl`
- **Target Route**: `archive` (`GET /archive`, `POST /archive`)
- **ACL Permission**: `view`
- **Request Parameters**:
  - `search` (str, optional): 키워드 검색어 (회사명, 발신번호, 내용)
  - `category` (str/int, optional): 분류 카테고리 ID
  - `date_from` (str, optional): 검색 시작일 (YYYY-MM-DD)
  - `date_to` (str, optional): 검색 종료일 (YYYY-MM-DD)
- **Response Behavior**:
  - HTTP 200 OK + `archive.jinja2` 렌더링

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$search_string` | `search` | str | 현재 검색 질의어 |
| `$categories` | `categories` | List[Dict] | 팩스 카테고리 셀렉트 옵션 목록 |
| `$archive_results`| `results` | List[Dict] | 검색된 아카이브 팩스 레코드 목록 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `layout.jinja2` 상속
- **Search Form (`form[action="/archive"][method="get"]`)**:
  - `input[name="search"]` (Keywords)
  - `select[name="category"]` (Categories)
  - `input[name="date_from"]`, `input[name="date_to"]`
  - `button[type="submit"]` ('Search')
- **Results Table & Pager**:
  - 검색어에 대한 결과 행 표시, 뷰어 링크, PDF 다운로드 링크
  - 페이징 컨트롤

---

## 4. Tailwind CSS Visual Fidelity Specification
- 검색 필터 박스: `bg-slate-50 border border-slate-200 rounded p-4 mb-6 grid grid-cols-1 md:grid-cols-4 gap-4`
- 검색 버튼: `px-4 py-1.5 bg-sky-800 text-white rounded text-xs font-semibold hover:bg-sky-700`

---

## 5. Golden Master Verification Scenarios
- `W12_archive_form`: 검색 필터 폼 마크업 및 필드 검증
- `W13_archive_res`: 검색 결과 목록 및 페이징 구조 검증
