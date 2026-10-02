# Specification: Web Route 02 - Lost Password & Password Expired

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/forgot.php`, `legacy/avantfax/pwdexpired.php`
- **Target Route**:
  - `forgot` (`GET /forgot`, `POST /forgot`): 비밀번호 분실 계정 조회 및 초기화 메일 발송
  - `pwdexpired` (`GET /pwdexpired`, `POST /pwdexpired`): 비밀번호 만료 시 새 비밀번호 강제 설정
- **ACL Permission**: `public`
- **Request Parameters**:
  - `/forgot`:
    - `username` (str, required): 등록된 아이디 또는 이메일 주소
    - `_submit_check` (hidden, value: "1")
  - `/pwdexpired`:
    - `old_password` (str, required): 기존 만료된 비밀번호
    - `new_password` (str, required): 새로운 비밀번호
    - `confirm_password` (str, required): 새 비밀번호 확인
    - `_submit_check` (hidden, value: "1")
- **Response Behavior**:
  - GET `/forgot`: HTTP 200 OK + `forgot.jinja2`
  - POST `/forgot`: HTTP 200 OK + 안내 문구 또는 오류 알림
  - GET `/pwdexpired`: HTTP 200 OK + `pwdexpired.jinja2`
  - POST `/pwdexpired` 성공 시: HTTP 302 Found $\rightarrow$ `/inbox`

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$LANG.LOST_PASSWORD` | `title` | str | 페이지 타이틀 ('Lost Password Recovery') |
| `$msg` | `message` | Optional[str] | 비밀번호 초기화 메일 발송 안내 문구 |
| `$error` | `error` | Optional[str] | 입력 검증 오류 메시지 |

---

## 3. UI & DOM Structural Contract
- **Page Title**: `- AvantFAX - Lost Password` / `- AvantFAX - Password Expired`
- **Layout**: 중앙 정렬된 카드 박스 (`af-box max-w-lg mx-auto`)
- **Required DOM Elements**:
  - `form[action="/forgot"][method="post"]`
  - `input[name="username"][type="text"]`
  - `a[href="/login"]` (로그인으로 돌아가기 링크)
  - `button[type="submit"]` ('Reset Password')

---

## 4. Tailwind CSS Visual Fidelity Specification
- 상단 헤더: `border-b border-slate-200 pb-3 mb-6 text-sky-800 font-bold`
- 성공 메시지: `bg-emerald-50 border border-emerald-200 text-emerald-800 rounded p-3 text-xs`
- 취소 링크: `text-xs text-sky-800 hover:underline`
- 제출 버튼: `px-5 py-2 bg-sky-800 text-white rounded text-sm font-semibold hover:bg-sky-700`
