# Specification: Web Route 09 - Address Book & Company Management

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/addressbook.php`, `legacy/avantfax/addressbook_edit.php`
- **Target Route**:
  - `addressbook` (`GET /addressbook`): 회사 목록 조회 및 키워드 검색
  - `addressbook_edit` (`GET /addressbook/edit`, `POST /addressbook/edit`): 회사 정보 등록 및 수정
- **ACL Permission**: `view`
- **Request Parameters**:
  - `/addressbook`:
    - `q` (str, optional): 검색어
  - `/addressbook/edit`:
    - `id` (int, optional): 수정 시 회사 PK ID
    - `company` (str, required): 회사명
    - `faxnumber` (str, optional): 팩스 번호
    - `email` (str, optional): 이메일 주소
    - `_submit_check` (hidden, value: "1")
- **Response Behavior**:
  - GET `/addressbook`: HTTP 200 OK + `addressbook.jinja2`
  - GET `/addressbook/edit`: HTTP 200 OK + `addressbook_edit.jinja2`
  - POST `/addressbook/edit`: 성공 시 HTTP 302 Found $\rightarrow$ `/addressbook`

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$companies` | `companies` | List[Dict] | 등록된 주소록 회사 목록 (`id`, `company`, `faxnumber`, `email`) |
| `$company_data` | `company` | Dict | 편집 중인 회사 데이터 객체 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `layout.jinja2` 상속
- **Address Book View**:
  - `h2`: 'Address Book'
  - `a[href="/addressbook/edit"]`: '+ New Company' 버튼
  - 회사 목록 테이블 (`Company Name`, `Fax Number`, `Email Contact`, `Actions`)
- **Edit Company Form**:
  - `form[action="/addressbook/edit"][method="post"]`
  - `input[name="company"][type="text"]` (required)
  - `input[name="faxnumber"][type="text"]`
  - `input[name="email"][type="text"]`
  - `button[type="submit"]` ('Save')

---

## 4. Tailwind CSS Visual Fidelity Specification
- 추가 버튼: `inputsubmit text-xs` (`px-3 py-1 bg-sky-800 text-white rounded text-xs font-semibold`)
- 폼 입력 상자: `border border-slate-300 rounded px-3 py-1.5 text-xs bg-white focus:outline-none focus:ring-1 focus:ring-sky-600`

---

## 5. Golden Master Verification Scenarios
- `W14_addressbook`: 주소록 목록 화면 및 신규 등록 링크 검증
- `W15_abook_edit`: 회사 추가/수정 폼 마크업 및 필드 전수 검증
