# Specification: Web Route 03 - Inbox List

## 1. Route & Controller Contract
- **Legacy Source**: `legacy/avantfax/inbox.php`, `legacy/avantfax/includes/templates/main_theme/templates/inbox.tpl`
- **Target Route**: `inbox` (`GET /inbox`, `POST /inbox`)
- **ACL Permission**: `view` (로그인된 모든 사용자)
- **Request Parameters**:
  - `page` (int, default: 0): 페이징 오프셋
  - `limit` (int, default: 15): 페이지당 팩스 수
  - `empty` (bool, optional): 테스트용 빈 인박스 시뮬레이션 플래그
- **Response Behavior**:
  - HTTP 200 OK + `inbox.jinja2` 렌더링
  - 비인증 접근 시 HTTP 302 Found $\rightarrow$ `/login` 리다이렉트

---

## 2. View Data Contract (Context Mapping)
| Smarty Variable | Jinja2 Context Key | Type | Description |
| :--- | :--- | :--- | :--- |
| `$current_user` | `current_user` | Dict | 인증된 사용자 세션 데이터 |
| `$modemlist` | `modem_list` | List[Dict] | 팩스 모뎀 장치 목록 (`device`, `alias`, `status`) |
| `$inbox` | `faxes` | List[Dict] | 수신 팩스 목록 (`id`, `company`, `origfaxnum`, `archstamp`, `modemdev`, `pages`, `description`) |
| `$numfaxesinbox` | `total_faxes` | int | 총 수신 팩스 건수 |
| `$numpages` | `num_pages` | int | 총 페이지 수 |
| `$SESSION_CAN_DEL` | `can_delete` | bool | 팩스 삭제 권한 여부 |

---

## 3. UI & DOM Structural Contract
- **Inheritance Layout**: `layout.jinja2` 상속
- **Sub-navigation Toolbar**:
  - `input#selectAll[type="checkbox"]` ('Select All Faxes')
  - 'Archive Selected' 버튼 (`images/folder.png`)
  - 'Delete Selected' 버튼 (`images/remove.png`)
- **Modem Status Bar**:
  - 컨테이너: `#modem-status-div`
  - 각 모뎀 상태 뱃지: `MODEM ttyS0: [IDLE]`
- **Fax Row Component (`#faxid_{id}`)**:
  - **Left**: 썸네일 이미지 링크 (`/viewfax?fid={id}`), 체크박스 (`name="removefax[]"`)
  - **Center**:
    - `FROM: {company_name}` (주소록 링크)
    - `DATE: {archstamp}`
    - `MODEM/DID: {modem_alias}`
    - `PAGES: {pages}`
  - **Right (9 Action Icons)**:
    1. 상세보기: `/viewfax?fid={id}` (`images/viewfax.png`)
    2. 90도 회전: `/faxes/rotate/{id}` (`images/rotate.png`)
    3. PDF 다운로드: `/faxes/download/{id}?format=pdf` (`images/pdf.png`)
    4. TIFF 다운로드: `/faxes/download/{id}?format=tiff` (`images/tiff.png`)
    5. 답장: `/sendfax?refax={id}` (`images/refax.png`)
    6. 이메일: `/email?fid={id}` (`images/email.png`)
    7. 메모: `/note?fid={id}` (`images/note.png`)
    8. 아카이브: `/archive/move/{id}` (`images/folder.png`)
    9. 삭제: `/delete/{id}` (`images/remove.png`)
- **Bottom Pager**:
  - `({total} FAXES)` 텍스트
  - 이전/다음 화살표 및 페이지 번호 리스트

---

## 4. Tailwind CSS Visual Fidelity Specification
| 레거시 요소 | Tailwind CSS 매핑 | 설명 |
| :--- | :--- | :--- |
| 컨테이너 `.af-box` | `rounded-lg border border-slate-300 bg-white shadow-sm p-4` | 인박스 메인 박스 |
| 툴바 구분자 | `text-slate-300` (`\|`) | 툴바 버튼 사이 구분 |
| 썸네일 테두리 | `border border-dashed border-amber-300 rounded hover:border-amber-500` | 레거시 점선 테두리 재현 |
| 액션 아이콘 호버 | `p-1 hover:bg-slate-200 rounded transition` | 액션 버튼 인터랙션 |
| 모뎀 상태 뱃지 | `px-1.5 py-0.5 rounded text-[11px] font-bold bg-white border border-slate-300 text-emerald-700` | 모뎀 상태 표시 |

---

## 5. Golden Master Verification Scenarios
- `W04_inbox_empty`: 빈 인박스 화면 렌더링 (`0 FAXES`, 모뎀 바) 검증
- `W05_inbox_list`: 팩스 목록, 발신자, 9개 액션 링크 전수 검증
