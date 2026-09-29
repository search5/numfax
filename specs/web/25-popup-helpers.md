# Specification: 25-popup-helpers (Popup Helpers & vCard Uploads)

## 1. Overview
레거시 AvantFAX의 Web 1.0 주소록 팝업 헬퍼 및 vCard 주소록 업로드 화면 명세서입니다.

- `distrolist_helper.php` -> `/helper/distrolist`
- `distrocontacts.php` -> `/helper/distrocontacts`
- `faxcontacts.php` -> `/helper/faxcontacts`
- `emailcontacts.php` -> `/helper/emailcontacts`
- `upload_contacts.php` -> `/upload/contacts`
- `upload_faxcontacts.php` -> `/upload/faxcontacts`

---

## 2. Route & Screen Contracts

### 2.1 Distribution List Helper (`/helper/distrolist`)
- **Legacy**: `distrolist_helper.php`
- **Method**: GET / POST
- **Parameters**: `dl_id` (Distribution List ID), `myselect` (선택된 연락처 배열), `add` (제출 플래그)
- **Template**: `distrolist_helper.tpl`
- **UI Elements**:
  - 모달 윈도우 스타일
  - 추가할 주소록 연락처 다중 선택 체크박스/셀렉트
  - 부모 창 연동 스크립트

### 2.2 Distro Contacts Selector Popup (`/helper/distrocontacts`)
- **Legacy**: `distrocontacts.php`
- **Method**: GET
- **Template**: `distrocontacts.tpl`
- **UI Elements**:
  - 발송 화면에서 호출되는 배포 그룹 목록 팝업
  - 그룹 클릭 시 부모 창 `destinations` 필드에 배포 목록의 팩스 번호들을 자동 삽입

### 2.3 Fax Contacts Selector Popup (`/helper/faxcontacts`)
- **Legacy**: `faxcontacts.php`
- **Method**: GET
- **Parameters**: `list_type` (`to`, `cc`, `bcc`)
- **Template**: `faxcontacts.tpl`
- **UI Elements**:
  - 주소록 회사 및 팩스 번호 목록 표시
  - 선택 시 부모 창에 회사명, 팩스 번호, 수신자 이름 자동 전송

### 2.4 Email Contacts Selector Popup (`/helper/emailcontacts`)
- **Legacy**: `emailcontacts.php`
- **Method**: GET
- **Parameters**: `emaildest_id` (부모 창의 이메일 입력 필드 ID)
- **Template**: `emailcontacts.tpl`
- **UI Elements**:
  - 등록된 이메일 주소 목록 표시
  - 클릭 시 부모 창의 해당 입력 필드로 이메일 자동 입력

### 2.5 Upload Email Contacts (`/upload/contacts`)
- **Legacy**: `upload_contacts.php`
- **Method**: GET / POST
- **Form Fields**: `upload` (vCard .vcf 파일 필드), `_submit_check`
- **Template**: `upload_contacts.tpl`
- **Behavior**:
  - 업로드된 .vcf 파일 파싱하여 `FN:`(이름) 및 `EMAIL;` 추출 후 이메일 연락처 추가

### 2.6 Upload Fax Contacts (`/upload/faxcontacts`)
- **Legacy**: `upload_faxcontacts.php`
- **Method**: GET / POST
- **Form Fields**: `upload` (vCard .vcf 파일 필드), `catid` (카테고리 ID), `_submit_check`
- **Template**: `upload_faxcontacts.tpl`
- **Behavior**:
  - 업로드된 .vcf 파일 파싱하여 `FN:`(이름), `TEL;FAX:`(팩스 번호), `TEL;WORK:`(전화번호), `ORG:`(회사명) 추출 후 주소록에 추가
