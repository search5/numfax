# Specification: Web Route 23 - Fax Interaction Modals & Dialogs (W31 ~ W36)

## 1. Overview
수신함, 뷰어, 아카이브에서 팩스 항목을 조작할 때 호출되는 6대 인터랙션 모달 및 다이얼로그 팝업에 대한 명세입니다:
1. `W31_modal_email`: 팩스 PDF 이메일 전달 (`/email`) - `legacy/.../email.tpl`
2. `W32_modal_assign`: 팩스 발신자 회사/담당자 할당 (`/assign`) - `legacy/.../assign.tpl`
3. `W33_modal_note`: 팩스 메모/주석 등록 (`/note`) - `legacy/.../set_note.tpl`
4. `W34_modal_delete`: 팩스 단건/다건 삭제 확인 (`/delete`) - `legacy/.../delete.tpl`
5. `W35_modal_refax`: 송신 실패 팩스 재발송 (`/refax`) - `legacy/.../refax.tpl`
6. `W36_modal_txreport`: 송신 결과 상세 리포트 팝업 (`/txreport`) - `legacy/.../txreport.tpl`

---

## 2. Route & Form Contracts

### 2.1 W31: Email Fax (`/email`)
- **Route**: `fax_modal_email` (`/email`)
- **Inputs**: `emails` (textarea, required), `subject` (text), `msg` (textarea), `fid` (hidden), `_submit_check` (hidden, value="1")
- **Required Text**: `["Send Fax via Email", "Recipients", "Subject"]`

### 2.2 W32: Assign Company (`/assign`)
- **Route**: `fax_modal_assign` (`/assign`)
- **Inputs**: `regexp` (text), `myselect` (select), `abook_id` (hidden), `_submit_check` (hidden, value="1")
- **Required Text**: `["Assign Company Name", "Search", "Save"]`

### 2.3 W33: Add Note (`/note`)
- **Route**: `fax_modal_note` (`/note`)
- **Inputs**: `description` (textarea), `category` (select), `fid` (hidden), `_submit_check` (hidden, value="1")
- **Required Text**: `["Add Note", "Note", "Save"]`

### 2.4 W34: Delete Fax (`/delete`)
- **Route**: `fax_modal_delete` (`/delete`)
- **Inputs**: `fid` (hidden), `_submit_check` (hidden, value="1")
- **Required Text**: `["Delete Fax", "Are you sure you want to delete this fax?"]`

### 2.5 W35: Reply/Refax (`/refax`)
- **Route**: `fax_modal_refax` (`/refax`)
- **Inputs**: `destinations` (textarea), `regarding` (text), `comments` (textarea), `fid` (hidden), `_submit_check` (hidden, value="1")
- **Required Text**: `["Reply to Fax", "Destination", "Comments"]`

### 2.6 W36: Transmission Report (`/txreport`)
- **Route**: `fax_modal_txreport` (`/txreport`)
- **Required Text**: `["Transmission Report", "Company", "Date", "Pages", "Print"]`
