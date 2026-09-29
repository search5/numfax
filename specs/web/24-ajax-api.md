# Specification: 24-ajax-api (Asynchronous AJAX Endpoints)

## 1. Overview
레거시 AvantFAX의 비동기 XML/텍스트/JSON 통신 엔드포인트(`legacy/avantfax/ajax/`) 명세서입니다.

- `ajaxmodemstatus.php` -> `/ajax/modemstatus`
- `ajaxinbox.php` -> `/ajax/inbox`
- `ajaxbook.php` -> `/ajax/book`
- `ajaxemailbook.php` -> `/ajax/emailbook`
- `ajaxprefillto.php` -> `/ajax/prefillto`
- `ajaxdlist.php` -> `/ajax/dlist`
- `ajaxarchivefax.php` -> `/ajax/archivefax`
- `faxalter.php` -> `/ajax/faxalter`

---

## 2. Route & Contract Specifications

### 2.1 Modem Status (`/ajax/modemstatus`)
- **Legacy**: `ajax/ajaxmodemstatus.php`
- **Method**: GET / POST
- **Parameters**: `modems` (comma-separated device list, e.g. `ttyS0,ttyS1`)
- **Content-Type**: `text/xml`
- **Response Format**:
  ```xml
  <response>
  <row>
  <modem>ttyS0</modem>
  <status>Idle</status>
  <class>2.0</class>
  </row>
  </response>
  ```

### 2.2 Inbox Fax Count Poller (`/ajax/inbox`)
- **Legacy**: `ajax/ajaxinbox.php`
- **Method**: GET
- **Authentication**: Session required
- **Content-Type**: `text/plain`
- **Response Format**:
  - 미확인 팩스 건수 문자열: `0` 또는 `{count}`
  - 사용자 알림음 설정 시: `{count}|{audiofile}` (예: `2|beep.wav`)

### 2.3 Address Book Suggest (`/ajax/book`)
- **Legacy**: `ajax/ajaxbook.php`
- **Method**: GET
- **Parameters**: `q` (검색어)
- **Content-Type**: `text/xml`
- **Response Format**:
  ```xml
  <response>
  <row>
  <company>Acme Corp - 1234567</company>
  <cid>1</cid>
  <faxnum>1234567</faxnum>
  <fnid>1</fnid>
  </row>
  </response>
  ```

### 2.4 Email Book Suggest (`/ajax/emailbook`)
- **Legacy**: `ajax/ajaxemailbook.php`
- **Method**: GET
- **Parameters**: `q` (검색어)
- **Content-Type**: `text/xml`
- **Response Format**:
  ```xml
  <response>
  <row>
  <id>1</id>
  <email>user@example.com</email>
  </row>
  </response>
  ```

### 2.5 Prefill Contact Info (`/ajax/prefillto`)
- **Legacy**: `ajax/ajaxprefillto.php`
- **Method**: GET
- **Parameters**: `fnid` (Address Book Fax Number ID)
- **Content-Type**: `text/xml`
- **Response Format**:
  ```xml
  <response>
    <row>
      <to_company>Acme Corp</to_company>
      <to_person>John Doe</to_person>
      <to_address>123 Street</to_address>
      <to_zip>12345</to_zip>
      <to_city>City</to_city>
      <to_location>HQ</to_location>
      <to_voicenumber>555-1234</to_voicenumber>
    </row>
  </response>
  ```

### 2.6 Distribution List Fax Numbers (`/ajax/dlist`)
- **Legacy**: `ajax/ajaxdlist.php`
- **Method**: GET
- **Parameters**: `dl_id` (Distribution List ID)
- **Content-Type**: `text/plain`
- **Response Format**:
  - 세미콜론과 공백으로 연결된 팩스번호 문자열 (예: `1234567; 9876543`)

### 2.7 Archive Fax (`/ajax/archivefax`)
- **Legacy**: `ajax/ajaxarchivefax.php`
- **Method**: POST / GET
- **Parameters**: `fids` (comma-separated fax IDs)
- **Authentication**: Session required with archive rights
- **Response**: HTTP 200 OK (Empty body)

### 2.8 Queue Job Alteration (`/ajax/faxalter`)
- **Legacy**: `ajax/faxalter.php`
- **Method**: GET (Form dialog modal) / POST (Execute alteration)
- **Parameters (POST)**:
  - `jid`: Job ID
  - `_submit_check`: "1"
  - `destination`: New destination
  - `modem`: Selected device
  - `priority`: Priority value
  - `sendtime`, `sendtimeHour`, `sendtimeMin`, `sendtime_unit`, `sendnow`
  - `killtime`, `killtime_unit`
  - `numtries`, `resubmit`, `owner`
- **GET Response**: HTML 폼 모달 (`faxalter.tpl`)
- **POST Response**: HTTP 200 OK
