# Specification: Web Route 06 - Outbox Queue Monitoring

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/outbox.php`, `legacy/avantfax/includes/templates/main_theme/templates/outbox.tpl`
- **Target Route**: `outbox` (`GET /outbox`, `POST /outbox`)
- **ACL Permission**: `view`
- **Request Parameters**:
  - `action` (str, optional): 작업 제어 ('cancel' 등)
  - `jobid` (int, optional): 대상 HylaFAX 송신 큐 Job ID
- **Response Behavior**:
  - HTTP 200 OK + `outbox.jinja2` 렌더링

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$outbox` | `jobs` | List[Dict] | 송신 대기 큐 작업 목록 (`jobid`, `destination`, `pages`, `status`) |
| `$modemlist` | `modem_list` | List[Dict] | 모뎀 장치 및 실시간 상태 목록 |
| `$current_user` | `current_user` | Dict | 사용자 세션 정보 |

---

## 3. UI & DOM Structural Contract
- **Layout**: `layout.jinja2` 상속
- **Queue Table**:
  - 컬럼: `Job ID`, `Destination`, `Pages`, `Status`, `Actions`
  - 각 행의 Cancel 버튼: 작업 취소 트리거
- **Empty State**:
  - 대기 팩스가 없을 경우: `No jobs in queue` 텍스트 노출

---

## 4. Tailwind CSS Visual Fidelity Specification
- 테이블 헤더: `bg-slate-200 text-slate-700 font-bold border-b border-slate-300 p-2.5`
- 테이블 행: `hover:bg-sky-50 even:bg-slate-50 transition p-2.5`
- 상태 뱃지: `px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300`

---

## 5. Golden Master Verification Scenarios
- `W08_outbox_queue`: 대기열 테이블, 상태 헤더, 빈 큐 문구 렌더링 검증
