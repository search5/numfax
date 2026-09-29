# Specification: Web Route 10 - Distribution Lists Management

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/distrolist.php`, `legacy/avantfax/distrolist_edit.php`, `legacy/avantfax/includes/templates/main_theme/templates/distrolist.tpl`, `distrolist_edit.tpl`
- **Target Route**:
  - `distrolist` (`GET /distrolist`): 배포 그룹 목록 및 편집기 분할 화면
  - `distrolist_edit` (`GET /distrolist/edit`, `POST /distrolist/edit`): 배포 그룹 생성, 이름 변경, 구성원 추가/제거 및 그룹 삭제
- **ACL Permission**: `view` (일반 인증 사용자)
- **Request Parameters**:
  - `dl_id` (int, optional): 배포 그룹 고유 ID (생성 시 누락, 편집 시 필수)
  - `dlname` (str, optional, max: 100): 배포 그룹명
  - `dl_list` (list[int], optional): 그룹에 할당된 연락처 ID 목록
  - 액션 플래그: `create`, `savename`, `refresh`, `remove`, `delete`
  - `_submit_check` (hidden, value: "1")
- **Response Behavior**:
  - `GET /distrolist`: HTTP 200 OK + `distrolist.jinja2`
  - `GET /distrolist/edit`: HTTP 200 OK + `distrolist_edit.jinja2`
  - `POST /distrolist/edit` (생성/저장/삭제): 성공 시 HTTP 302 Found $\rightarrow$ `/distrolist` (또는 프레임 내 메시지 + 새로고침)

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$distrolists` | `distro_lists` | Dict[int, str] | 전체 배포 그룹 ID-이름 매핑 딕셔너리 |
| `$fvalues.dl_id` | `selected_dl_id` | Optional[int] | 현재 선택된 배포 그룹 ID |
| `$fvalues.dlname`| `dlname` | str | 현재 배포 그룹 명칭 |
| `$contact_list` | `contact_list` | Dict[int, str] | 그룹에 포함된 연락처 목록 |
| `$message` | `message` | Optional[str] | 작업 완료 알림 메시지 |
| `$create` | `is_new` | bool | 신규 그룹 생성 모드 여부 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `layout.jinja2` 상속
- **Sub-navigation Header**:
  - `a[href="/emailbook"]` ('Contacts') | `a[href="/addressbook"]` ('Fax Numbers') | `a[href="/distrolist"]` ('Distribution Lists')
- **Container Layout (2-Column Master-Detail)**:
  - **Left Column (List Selector)**:
    - `<label for="dl_id">`: 'Distribution Lists:'
    - `<select name="dl_id" id="dl_id" size="17">`: 배포 그룹 선택 옵션
  - **Right Column (Edit / Membership Panel)**:
    - 신규 모드: `input[name="dlname"]`, `button[name="create"]` ('Create List')
    - 편집 모드:
      - `input[name="dlname"]`, `button[name="savename"]` ('Save Name')
      - `<select name="dl_list[]" multiple size="13">`: 소속 연락처 다중 선택 박스
      - `button[name="add_contact"]` ('Add Contact' 모달 트리거)
      - `button[name="refresh"]` ('Refresh List')
      - `button[name="remove"]` ('Remove Selected')
      - `button[name="delete"]` ('Delete List')
    - `input[name="_submit_check"][type="hidden"][value="1"]`

---

## 4. Tailwind CSS Visual Fidelity Specification
| 레거시 스타일 속성 | Tailwind CSS 유틸리티 클래스 | 적용 대상 |
| :--- | :--- | :--- |
| 2열 패널 컨테이너 | `grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-50 border border-slate-300 rounded p-6 shadow-sm` | 마스터-디테일 박스 |
| 배포 목록 셀렉트 | `w-full border border-slate-300 rounded text-xs p-2 bg-white focus:ring-1 focus:ring-sky-600` | 좌측 그룹 리스트 박스 |
| 멤버십 다중 선택창 | `w-full border border-slate-300 rounded text-xs p-2 bg-white min-h-[160px]` | 소속 연락처 목록 박스 |
| 저장/생성 버튼 `.inputsubmit` | `px-4 py-1.5 bg-sky-800 text-white rounded text-xs font-semibold hover:bg-sky-700 shadow-sm transition` | 전송 버튼 |
| 삭제 버튼 `.inputcancel` | `px-4 py-1.5 bg-rose-700 text-white rounded text-xs font-semibold hover:bg-rose-600 shadow-sm transition` | 삭제 버튼 |

---

## 5. Golden Master Verification Scenarios
- `W16_distrolist`: 배포 그룹 목록 선택창, 서브 네비게이션, 신규 생성/편집 폼 마크업 및 컨트롤 전수 검증
