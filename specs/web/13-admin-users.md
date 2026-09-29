# Specification: Web Route 13 - Admin User Management

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/admin/users.php`, `legacy/avantfax/admin/users_list.php`, `legacy/avantfax/includes/templates/admin_theme/templates/users.tpl`
- **Target Route**:
  - `admin_users` (`GET /admin/users`, `POST /admin/users`): 사용자 생성, 정보 수정 및 권한/회선 매핑 제어
- **ACL Permission**: `admin` (시스템 관리자 권한 필수)
- **Request Parameters**:
  - `uid` (int, optional): 수정 대상 사용자 PK ID (누락 시 신규 사용자 생성)
  - `acc_enabled` (bool, default: 1): 계정 활성화 여부
  - `name` (str, required, max: 40): 사용자 성명
  - `username` (str, required, max: 64): 로그인 아이디
  - `password` (str, optional, max: 64): 비밀번호 (신규 등록 시 필수, 수정 시 입력 시에만 변경)
  - `pwdcycle` (int, default: 0): 비밀번호 변경 주기(일)
  - `pwd_reuse` (bool, default: 0): 이전 비밀번호 재사용 허용 여부
  - `email` (str, required, max: 100): 이메일 주소
  - `language` (str, default: 'en'): 기본 표시 언어
  - `from_company`, `from_location`, `from_voicenumber`, `from_faxnumber`, `user_tsi`: 발송자 메타데이터
  - `coverpage_id` (str/int, optional): 기본 팩스 표지
  - `audiofile` (str, optional): 팩스 수신 시 재생할 오디오 알림
  - `faxperpageinbox`, `faxperpagearchive` (int): 뷰당 표시 건수
  - 권한 플래그 (체크박스):
    - `is_admin` (bool): 관리자 콘솔 접근 권한
    - `superuser` (bool): 슈퍼유저 권한 (모든 팩스 및 설정 접근)
    - `can_del` (bool): 팩스 삭제 권한
    - `any_modem` (bool): 모든 모뎀으로 발송 허용 권한
  - 다중 할당 체크박스 리스트:
    - `didrouting` (list[int]): 할당된 DID 수신 라우팅 규칙 ID 목록
    - `modemdevs` (list[str]): 송수신 허용 모뎀 디바이스명 목록
    - `faxcats` (list[int]): 열람 가능한 팩스 분류 카테고리 ID 목록
  - 액션 플래그: `save`, `delete`, `cancel`
  - `_submit_check` (hidden, value: "1")
- **Response Behavior**:
  - GET: HTTP 200 OK + `admin/users.jinja2`
  - POST 유효성 오류: HTTP 200 OK + `admin/users.jinja2` (`error="에러메시지"`)
  - POST 성공(저장/삭제): HTTP 302 Found $\rightarrow$ `/admin` (또는 `/admin/users`)

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$fvalues.uid` | `user_form.uid` | Optional[int] | 편집 대상 사용자 ID |
| `$fvalues.name` | `user_form.name` | str | 사용자 이름 |
| `$fvalues.username` | `user_form.username` | str | 로그인 아이디 |
| `$fvalues.email` | `user_form.email` | str | 이메일 주소 |
| `$fvalues.acc_enabled` | `user_form.is_active` | bool | 계정 활성화 상태 |
| `$fvalues.is_admin` | `user_form.is_admin` | bool | 관리자 여부 |
| `$fvalues.superuser` | `user_form.is_superuser` | bool | 슈퍼유저 여부 |
| `$fvalues.can_del` | `user_form.can_delete` | bool | 팩스 삭제 허용 여부 |
| `$fvalues.any_modem` | `user_form.any_modem` | bool | 모든 모뎀 사용 허용 |
| `$didroutes` | `did_routes` | List[Dict] | 전체 DID 라우팅 목록 (체크박스 생성용) |
| `$modemdevs` | `modem_devices` | List[Dict] | 전체 모뎀 디바이스 목록 (체크박스 생성용) |
| `$faxcategories` | `fax_categories` | List[Dict] | 전체 팩스 카테고리 목록 (체크박스 생성용) |
| `$error` | `error` | Optional[str] | 유효성 오류 메시지 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `admin/layout.jinja2` 상속
- **Heading**: `h1` ('Edit User' 또는 'New User')
- **Form Controls (`form[action="/admin/users"][method="post"]`)**:
  - 기본 식별자: `input[name="name"]`, `input[name="username"]`, `input[name="password"]`, `input[name="email"]`
  - 계정/권한 플래그: `acc_enabled`, `is_admin`, `superuser`, `can_del`, `any_modem`
  - 3대 권한 범위 필드셋:
    - `<fieldset><legend>DID Routes</legend>`: 각 라우트별 체크박스 리스트
    - `<fieldset><legend>Fax Lines</legend>`: 각 모뎀 디바이스별 체크박스 리스트
    - `<fieldset><legend>Categories</legend>`: 각 카테고리별 체크박스 리스트
  - 액션 버튼:
    - `button[type="submit"]` ('Save')
    - `button[name="delete"]` ('Delete User' - 편집 모드 시)
    - `button[name="cancel"]` ('Cancel' $\rightarrow$ `/admin`)
  - `input[name="_submit_check"][type="hidden"][value="1"]`

---

## 4. Tailwind CSS Visual Fidelity Specification
| 레거시 스타일 속성 | Tailwind CSS 유틸리티 클래스 | 적용 대상 |
| :--- | :--- | :--- |
| 메인 폼 카드 | `max-w-4xl mx-auto bg-white border border-slate-300 rounded p-6 shadow-sm space-y-6` | 유저 폼 컨테이너 |
| 필드셋 영역 `fieldset` | `border border-slate-200 rounded p-4 bg-slate-50/60` | 권한 그룹 경계선 |
| 필드셋 범례 `legend` | `text-xs font-bold text-slate-700 px-2 bg-white rounded border border-slate-200` | 범례 제목 |
| 체크박스 리스트 그리드 | `grid grid-cols-1 md:grid-cols-3 gap-2 mt-2 text-xs` | DID/모뎀/카테고리 다중 체크박스 |
| 저장 버튼 `.inputsubmit` | `px-6 py-2 bg-sky-800 text-white rounded text-xs font-semibold hover:bg-sky-700 shadow-sm transition` | 제출 버튼 |
| 삭제 버튼 `.inputcancel` | `px-6 py-2 bg-rose-700 text-white rounded text-xs font-semibold hover:bg-rose-600 shadow-sm transition` | 유저 삭제 버튼 |

---

## 5. Golden Master Verification Scenarios
- `W19_admin_users`: 관리자 사용자 추가/수정 폼 마크업, 모든 권한 체크박스 및 3대 필드셋(DID, 모뎀, 카테고리) 전수 검증
