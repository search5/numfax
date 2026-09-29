# Specification: Web Route 07 - Send Fax Form & Dispatch

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/sendfax.php`, `legacy/avantfax/includes/templates/main_theme/templates/sendfax.tpl`
- **Target Route**: `sendfax` (`GET /sendfax`, `POST /sendfax`)
- **ACL Permission**: `send_fax` (일반 인증 사용자)
- **Request Parameters**:
  - `to_person` (str, optional): 수신 담당자명
  - `to_company` (str, optional): 수신 회사명
  - `faxnumber` (str, required): 착신 팩스 번호
  - `coverpage` (str, optional): 선택된 표지 템플릿
  - `file` (file upload, optional): 첨부 문서 파일 (PDF, PS, TIFF)
  - `_submit_check` (hidden, value: "1")
- **Response Behavior**:
  - GET: HTTP 200 OK + `sendfax.jinja2`
  - POST 검증 실패(번호 누락): HTTP 200 OK + `error="Fax number is required"`
  - POST 정상 발송 성공: HTTP 302 Found $\rightarrow$ `/outbox`

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$formdata.to_person` | `form_data.to_person` | str | 입력된 수신자명 보존 |
| `$formdata.to_company` | `form_data.to_company` | str | 입력된 회사명 보존 |
| `$formdata.faxnumber` | `form_data.faxnumber` | str | 입력된 팩스번호 보존 |
| `$coverpages` | `cover_pages` | List[str] | 사용 가능한 표지 템플릿 목록 |
| `$error` | `error` | Optional[str] | 유효성 오류 메시지 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `layout.jinja2` 상속
- **Required DOM Elements**:
  - `form[action="/sendfax"][method="post"][enctype="multipart/form-data"]`
  - `input[name="to_person"][type="text"]`
  - `input[name="to_company"][type="text"]`
  - `input[name="faxnumber"][type="text"]` with required attribute
  - `select[name="coverpage"]`
  - `input[name="file"][type="file"]`
  - `input[name="_submit_check"][type="hidden"][value="1"]`
  - `button[type="submit"]` ('Send Fax')

---

## 4. Tailwind CSS Visual Fidelity Specification
- 폼 컨테이너: `af-box max-w-3xl mx-auto mb-6`
- 파일 첨부 영역: `border border-dashed border-slate-300 rounded-lg p-4 bg-slate-50`
- 제출 버튼: `px-6 py-2 bg-sky-800 text-white rounded text-sm font-semibold hover:bg-sky-700 shadow-sm transition`

---

## 5. Golden Master Verification Scenarios
- `W09_sendfax_form`: 발송 폼 마크업 및 필드 전수 검증
- `W10_sendfax_err`: 팩스 번호 미입력 시 에러 메시지 렌더링 검증
- `W11_sendfax_post`: 올바른 발송 시 `/outbox` 리다이렉트 검증
