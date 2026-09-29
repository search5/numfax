# Specification: Web Route 11 - User Settings & Preferences

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/settings.php`, `legacy/avantfax/includes/templates/main_theme/templates/settings.tpl`
- **Target Route**: `settings` (`GET /settings`, `POST /settings`)
- **ACL Permission**: `view` (모든 인증 사용자)
- **Request Parameters**:
  - `name` (str, required, max: 40): 사용자 성명
  - `from_company` (str, optional): 소속 회사명
  - `from_location` (str, optional): 위치/부서
  - `from_voicenumber` (str, optional): 일반 전화번호
  - `from_faxnumber` (str, optional): 개인 팩스번호
  - `user_tsi` (str, optional): 송신자 식별 TSI (슈퍼유저 권한 사용자만 변경 가능)
  - `opass` (str, optional): 기존 비밀번호 (암호 변경 시 필수)
  - `npass` (str, optional): 신규 비밀번호
  - `vpass` (str, optional): 신규 비밀번호 확인
  - `email` (str, required, max: 100): 알림 및 통지용 이메일 주소
  - `email_sig` (str, optional): 발송 팩스/이메일 서명
  - `language` (str, optional): UI 기본 언어
  - `coverpage_id` (str/int, optional): 기본 팩스 표지 템플릿
  - `faxperpageinbox` (int, default: 15): 받은편지함 페이지당 표시 건수
  - `faxperpagearchive` (int, default: 15): 아카이브 페이지당 표시 건수
  - `update` / `cancel` (str, optional): 전송 액션 식별
  - `url` (str, hidden): 이전 페이지 복귀 URL
  - `_submit_check` (hidden, value: "1")
- **Response Behavior**:
  - GET: HTTP 200 OK + `settings.jinja2`
  - POST 유효성 오류(필수 누락, 비밀번호 검증 실패 등): HTTP 200 OK + `settings.jinja2` (`error="에러메시지"`)
  - POST 정상 수정 완료: HTTP 302 Found $\rightarrow$ `url` 또는 `/settings`

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$fvalues.name` | `user.name` | str | 사용자 본명 |
| `$fvalues.email` | `user.email` | str | 기본 이메일 |
| `$fvalues.from_company` | `user.company` | str | 소속 회사명 |
| `$fvalues.from_location`| `user.location` | str | 위치/부서 |
| `$fvalues.from_voicenumber` | `user.voicenumber` | str | 전화번호 |
| `$fvalues.from_faxnumber` | `user.faxnumber` | str | 팩스번호 |
| `$fvalues.user_tsi` | `user.user_tsi` | str | 전송자 TSI ID |
| `$SUPERUSER` | `is_superuser` | bool | 슈퍼유저 여부 (TSI 필드 노출 제어) |
| `$languages` | `languages` | Dict[str, str] | 지원 언어 목록 (en, ko, de, fr 등) |
| `$cover_list` | `cover_pages` | Dict[str, str] | 사용 가능한 커버페이지 목록 |
| `$faxesperpagelist` | `page_size_options`| List[int] | 페이지당 건수 옵션 (10, 15, 20, 50 등) |
| `$error` | `error` | Optional[str] | 유효성 검증 오류 메시지 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `layout.jinja2` 상속
- **Heading**: `h1` ('User Settings')
- **Form Layout (`form[action="/settings"][method="post"]`)**:
  - **개인 정보 섹션**:
    - `input[name="name"]` (required)
    - `input[name="from_company"]`, `input[name="from_location"]`
    - `input[name="from_voicenumber"]`, `input[name="from_faxnumber"]`
    - `input[name="user_tsi"]` (슈퍼유저 조건부 노출)
  - **비밀번호 변경 섹션**:
    - `input[name="opass"][type="password"]`
    - `input[name="npass"][type="password"]`
    - `input[name="vpass"][type="password"]`
  - **통지 및 서명 섹션**:
    - `input[name="email"][type="text"]` (required)
    - `textarea[name="email_sig"][rows="10"]`
  - **표시 환경설정 섹션**:
    - `select[name="language"]`
    - `select[name="coverpage_id"]`
    - `select[name="faxperpageinbox"]`, `select[name="faxperpagearchive"]`
  - **액션 버튼**:
    - `button[name="update"]` ('Update')
    - `button[name="cancel"]` ('Cancel')
  - `input[name="_submit_check"][type="hidden"][value="1"]`

---

## 4. Tailwind CSS Visual Fidelity Specification
| 레거시 스타일 속성 | Tailwind CSS 유틸리티 클래스 | 적용 대상 |
| :--- | :--- | :--- |
| 폼 컨테이너 `.tableForm` | `max-w-3xl mx-auto bg-slate-50 border border-slate-300 rounded p-6 shadow-sm space-y-4` | 메인 설정 카드 |
| 텍스트 라벨 `<label>` | `block text-xs font-bold text-slate-700 w-44 shrink-0` | 폼 라벨 (우측/좌측 정렬) |
| 텍스트/패스워드 인풋 | `border border-slate-300 rounded px-3 py-1.5 text-xs bg-white focus:ring-1 focus:ring-sky-600 focus:outline-none` | 단일 행 입력 필드 |
| 서명 텍스트에어리어 | `border border-slate-300 rounded p-2 text-xs font-mono bg-white w-full focus:ring-1 focus:ring-sky-600` | 이메일 서명 입력창 |
| 업데이트 버튼 `.inputsubmit` | `px-6 py-2 bg-sky-800 text-white rounded text-xs font-semibold hover:bg-sky-700 shadow-sm transition` | 저장 버튼 |
| 취소 버튼 `.inputcancel` | `px-6 py-2 bg-slate-400 text-white rounded text-xs font-semibold hover:bg-slate-500 shadow-sm transition` | 취소 버튼 |

---

## 5. Golden Master Verification Scenarios
- `W17_settings`: 설정 폼 마크업, 모든 섹션(개인정보, 암호, 서명, 환경설정) 필드 및 선택 옵션 전수 검증
