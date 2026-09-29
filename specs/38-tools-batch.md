# Specification: 38-tools-batch (Administrative Batch CLI Tools)

## 1. Overview
레거시 AvantFAX의 `tools/` 디렉터리에 위치한 관리자용 배치 및 마이그레이션 CLI 도구 군의 인터페이스 및 동작 계약 명세서입니다.

- `ocr_import.php` -> `avantfax.cli.ocr_import`
- `create_thumbnails.php` -> `avantfax.cli.create_thumbnails`
- `import_users.php` -> `avantfax.cli.import_users`
- `import_blacklist.php` -> `avantfax.cli.import_blacklist`
- `reroute.php` -> `avantfax.cli.reroute`

---

## 2. Tool Contracts

### 2.1 OCR Import (`avantfax.cli.ocr_import`)
- **Usage**: `ocr_import.py`
- **Precondition**: `ENABLE_OCR_SUPPORT` 환경설정 확인 (미설정 시 오류 메시지 출력 후 종료)
- **Behavior**:
  - `FaxPDFArchive`의 아카이브 팩스 목록을 검색
  - 각 팩스의 TIFF 파일 경로에 대해 `ocr_faxcontent()` 실행
  - 팩스 레코드의 `faxcontent` 필드에 OCR 텍스트 갱신
- **Stdout Format**:
  ```text
  {num_results} faxes in the Archive
  Processing faxid {fid}
  ```

### 2.2 Create Thumbnails (`avantfax.cli.create_thumbnails`)
- **Usage**: `create_thumbnails.py`
- **Behavior**:
  - `FaxPDFArchive`의 모든 팩스 검색
  - 썸네일(`.png`/`.gif`) 및 미리보기 이미지가 없는 팩스 감지
  - `pdf_preview(path)` 호출하여 썸네일 및 미리보기 생성
- **Stdout Format**:
  ```text
  {results} faxes in Archive
  Creating images in: {path}
  Done
  ```
  또는 아카이브가 비어 있을 경우:
  ```text
  No faxes found
  Done
  ```

### 2.3 Import Users (`avantfax.cli.import_users`)
- **Usage**: `import_users.py <filename>`
- **Arguments Check**:
  - 인수 누락 시 종료:
  ```text
  usage: import_users.py filename
  Example: import_users.py users.txt
  One user entry per line with fields: name, username, password, and email separated by 1 tab
  Example:
  John Doe	johndoe	passw0rd	john.doe@mycompany.com
  NOTE: Be sure to set $AVANTFAX_SERVERNAME in includes/local_config.php before running this script
  ```
- **Behavior**:
  - 탭 구분 텍스트 파일을 한 줄씩 읽어 사용자 계정 생성 (`AFUserAccount::create`)

### 2.4 Import Blacklist (`avantfax.cli.import_blacklist`)
- **Usage**: `import_blacklist.py <filename> [device]`
- **Arguments Check**:
  - 인수 누락 시 종료:
  ```text
  usage: import_blacklist.py filename [device]
  Example: import_blacklist.py blacklist.txt ttyS0
  One CallID (fax number) per line
  ```
- **Behavior**:
  - 줄바꿈으로 구분된 CallID(팩스 번호)를 읽어 `DynamicConfig::create` 호출
- **Stdout Format**:
  ```text
  Created Rule: {callid}
  Skipping existing rule: {callid}
  Created {cnt} rules
  ```

### 2.5 Reroute (`avantfax.cli.reroute`)
- **Usage**: `reroute.py <device | DIDnum> <email-address>`
- **Arguments Check**:
  - 인수 2개 미만일 시 종료:
  ```text
  Usage: reroute.py [device | DIDnum] email-address
  ```
- **Behavior**:
  - DID 모드인 경우 DIDRoute 컨택트 이메일 수정, 모뎀 모드인 경우 Modem 컨택트 이메일 수정
