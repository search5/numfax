# Specification: Web Route 01 - Auth Login & Logout

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/index.php`, `legacy/avantfax/logout.php`
- **Target Route**:
  - `home` (`GET /`): 비로그인 시 로그인 페이지 표시, 로그인 상태 시 `/inbox` 리다이렉트
  - `login` (`GET /login`, `POST /login`): 로그인 페이지 표시 및 자격증명 제출 처리
  - `logout` (`GET /logout`): 세션 파기 및 `/login` 리다이렉트
- **ACL Permission**: `public` (Everyone)
- **Request Parameters**:
  - `username` (str, required, max: 64): 사용자 로그인 아이디
  - `password` (str, required, max: 64): 평문 비밀번호
  - `_submit_check` (hidden, value: "1"): 폼 제출 식별자
- **Response Behavior**:
  - GET: HTTP 200 OK + `login.jinja2` 렌더링
  - POST 인증 실패: HTTP 200 OK + `login.jinja2` 재렌더링 (`error="Invalid username or password"`)
  - POST 인증 성공: HTTP 302 Found + `remember` 세션 쿠키 발급 + `Location: /inbox`
  - GET 로그아웃: HTTP 302 Found + `forget` 세션 쿠키 삭제 + `Location: /login`

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$AVANTFAX_SERVERNAME` | `server_name` | str | 서버 식별명 (예: 'AvantFAX Server 3.3.5') |
| `$AVANTFAX_VERSION` | `version` | str | 시스템 버전 ('3.3.5') |
| `$LANG.LOGIN_TEXT` | `lang.LOGIN_TEXT` | str | 로그인 환영 안내 문구 |
| `$LANG.LOST_PASSWORD` | `lang.LOST_PASSWORD`| str | 비밀번호 분실 링크 텍스트 ('Forgot your password?') |
| `$error` | `error` | Optional[str] | 유효성 검증 또는 인증 실패 에러 메시지 |
| `$smarty.server.SCRIPT_NAME` | `action_url` | str | 폼 전송 대상 URL ('/login') |

---

## 3. UI & DOM Structural Contract
- **Page Title**: `- AvantFAX - Login`
- **Container Layout**:
  - 고유한 좌우 분할(Split Grid) 구조:
    - **Header**: `:: AvantFAX LOGIN ::` (좌), 큰 로고 `avantfax-big.png` 및 버전 (우)
    - **Left Column**: 서버 안내 문구, `/forgot` 링크 (`Forgot your password?`), 에러 알림 박스
    - **Vertical Divider**: 세로 구분선 (레거시 `images/line.gif` 또는 모던 border)
    - **Right Column**: Username 필드, Password 필드, Submit 버튼 (`Login`)
- **Required DOM Elements**:
  - `form[action="/login"][method="post"]`
  - `input[name="username"][type="text"]` with autofocus
  - `input[name="password"][type="password"]`
  - `input[name="_submit_check"][type="hidden"][value="1"]`
  - `button[type="submit"]` 또는 `input[type="submit"]`

---

## 4. Tailwind CSS Visual Fidelity Specification
| 레거시 스타일 속성 | Tailwind CSS 유틸리티 클래스 | 적용 대상 |
| :--- | :--- | :--- |
| 헤더 텍스트 `color: #336699` | `text-sky-800 font-bold tracking-wide` | 상단 `:: AvantFAX LOGIN ::` |
| 비밀번호 링크 `color: #993300` | `text-amber-800 underline hover:text-amber-900` | 비밀번호 분실 링크 |
| 인풋 테두리 `border: 1px solid #7f9db9`| `border border-slate-300 focus:ring-1 focus:ring-sky-600 focus:border-sky-600 rounded` | 텍스트/비밀번호 입력창 |
| 로그인 버튼 `.inputsubmit` | `px-6 py-2 bg-sky-800 text-white rounded text-sm font-semibold hover:bg-sky-700 shadow-sm` | 전송 버튼 |
| 에러 메시지 박스 `.error` | `p-3 bg-red-50 border border-red-200 text-red-700 rounded text-xs` | 인증 오류 메시지 |

---

## 5. Golden Master Verification Scenarios
- `W01_login_get`: 기본 로그인 페이지 GET 응답 검증 (DOM 구조, 폼 필드, 링크)
- `W02_login_fail`: 잘못된 비밀번호 POST 시 에러 메시지 및 폼 재렌더링 검증
- `W03_login_success`: 정상 자격증명 POST 시 302 Found 및 `/inbox` 리다이렉트 검증
