# Specification: Web Route 12 - Admin Dashboard & System Overview

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/admin/admin.php`, `legacy/avantfax/includes/templates/admin_theme/templates/admin.tpl`
- **Target Route**: `admin_dashboard` (`GET /admin`)
- **ACL Permission**: `admin` (시스템 관리자 권한 필수, 비인가 시 403 Forbidden 또는 로그인 리다이렉트)
- **Request Parameters**: 없음
- **Response Behavior**:
  - HTTP 200 OK + `admin/dashboard.jinja2` 렌더링

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$users` | `users` | List[Dict] | 등록된 전체 사용자 목록 (`uid`, `name`, `superuser`, `username`, `last_login`, `last_ip`, `email`) |
| `$hylafax` | `hylafax_version` | str | 현재 연결된 HylaFAX 서버 버전 문자열 |
| `$modems` | `modems` | List[Dict] | 시스템 모뎀 목록 및 실시간 상태 (`alias`, `device`, `status: {"class": str, "status": str}`) |
| `$users|@count` | `total_users` | int | 총 사용자 등록 수 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `admin/layout.jinja2` 상속
- **Navigation Controls**:
  - 상단 관리자 탭/점프 메뉴 (`select#menuObj` 또는 링크 바):
    - `a[href="/admin/users"]` ('Users')
    - `a[href="/admin/modems"]` ('Modems')
    - `a[href="/admin/routing/did"]` ('DID Routing')
    - `a[href="/admin/routing/barcode"]` ('Barcode Routing')
    - `a[href="/admin/system_logs"]` ('System Logs')
- **Heading**: `h1` ('Admin Dashboard')
- **User Overview Table (`table`)**:
  - 컬럼: `Name`, `SU` (슈퍼유저 뱃지/아이콘), `Username`, `Last Login`, `Last IP`, `Email`
  - 각 사용자 이름 클릭 시: `a[href="/admin/users?uid={uid}"]` 상세 편집 이동
  - 이메일 링크: `a[href="mailto:{email}"]`
  - 총 사용자 수 표시: `<small>{n} Users</small>`
- **System Health & Modem Panel (`#modem-status-div`)**:
  - HylaFAX 버전 레이블: `HylaFAX™ version: {version}`
  - 모뎀별 상태 텍스트: `{alias} [{status}]`

---

## 4. Tailwind CSS Visual Fidelity Specification
| 레거시 스타일 속성 | Tailwind CSS 유틸리티 클래스 | 적용 대상 |
| :--- | :--- | :--- |
| 메인 콘텐츠 영역 `#main-content` | `max-w-5xl mx-auto bg-white border border-slate-300 rounded p-6 shadow-sm` | 대시보드 메인 카드 |
| 테이블 헤더 `th` | `bg-slate-200 text-slate-700 font-bold border-b border-slate-300 p-2 text-xs` | 사용자 테이블 헤더 |
| 테이블 데이터 행 `tr.highlight` | `hover:bg-sky-50 even:bg-slate-50 transition border-b border-slate-200 text-xs` | 사용자 행 |
| 슈퍼유저 뱃지 | `inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800` | SU 아이콘/뱃지 |
| 모뎀 상태 컨테이너 `#modem-status-div` | `mt-6 p-4 bg-slate-50 border border-slate-200 rounded text-xs space-y-1` | 하단 모뎀 상태 박스 |

---

## 5. Golden Master Verification Scenarios
- `W18_admin_dash`: 관리자 대시보드 렌더링, 사용자 요약 테이블, HylaFAX 버전 및 모뎀 상태 마크업 전수 검증
