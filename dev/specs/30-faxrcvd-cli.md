# Specification: Module 30 - faxrcvd (CLI)

## 1. Overview
- **Module Name**: `faxrcvd`
- **Legacy Source**: `legacy/avantfax/includes/faxrcvd.php`
- **Target Implementation**: `src/avantfax/cli/faxrcvd.py`
- **Primary Role**: HylaFAX 팩스 수신 훅 스크립트. 수신된 TIFF 파일로부터 발신 정보 및 CID/DID를 추출하고, PDF 변환, 썸네일 생성, 주소록 자동 갱신, 수신함(`ArchiveIn`) 등록, 바코드/OCR 분석 및 최종 이메일/프린터 라우팅을 수행.

---

## 2. CLI Interface & Exit Semantics
- **Command Signature**:
  ```bash
  faxrcvd.php file devID commID error-msg [CIDNumber] [CIDName] [DIDnum]
  ```
- **Arguments**:
  1. `file` (str, required): 수신된 TIFF 파일 경로 (예: `recvq/fax000000001.tif`)
  2. `devID` (str, required): 모뎀 장치 식별자 (예: `ttyS0`)
  3. `commID` (str, optional): HylaFAX 통신 ID
  4. `error-msg` (str, optional): 에러 메시지
  5. `CIDNumber` (str, optional): Caller ID 전화번호
  6. `CIDName` (str, optional): Caller ID 이름
  7. `DIDnum` (str, optional): DID / DTMF 수신 번호
- **Exit & Output Codes**:
  - 인수 개수 < 2 (즉 `argc < 3`):
    - stdout: `Usage: faxrcvd.php file devID commID error-msg [CIDNumber] [CIDName] [DIDnum]\n`
    - exit code: `0`
  - `file` 파일 미존재 시:
    - stdout: 없음
    - exit code: `0`
  - 정상 처리 완료:
    - exit code: `0`

---

## 3. Core Business Logic & State Flow
1. **Modem Verification**:
   - `FaxModem.load_device(modemdev)`: 장치 미등록 시 자동 생성 (`create(modemdev, modemdev, None)`)
2. **TIFF Inspection (`faxinfo`)**:
   - 수신 파일 존재 확인. 미존재 시 실패 로그 후 정상 종료.
   - `Sender`, `Pages`, `Received`, `CIDNumber`, `CIDName`, `DIDNum` 추출
3. **Archive Directory & File Preparation**:
   - 날짜/시간 및 발신자 번호 기반 디렉터리(`ARCHIVE/Y/m/d/clean_fax/faxid`) 생성
   - TIFF 파일 복사 및 PDF 변환 (`tiff2pdf`), 썸네일 생성 (`static_preview`)
4. **AddressBook Auto-Registration**:
   - `AFAddressBook.loadbyfaxnum`: 기존 번호 조회 시 발신 횟수 증가 (`inc_faxfrom`)
   - 미등록 번호 시 회사 및 팩스번호 자동 생성
5. **DID / Modem Routing Determination**:
   - `ENABLE_DID_ROUTING` 활성 시 `DIDRouting` 조회, 비활성 시 `FaxModem` 설정 적용
6. **Inbox Storage (`ArchiveIn`)**:
   - `ArchiveIn.create(faxpath, faxnumid, company_fax, modemdev, pages, recv_date, didr_id)`
7. **Barcode & OCR Processing**:
   - `bardecode` 바코드 검출 시 라우팅 규칙 재정의 및 메모 저장
   - `ocr_faxcontent` 텍스트 추출 시 `set_faxcontent` 저장
8. **Routing Priority Resolution**:
   - 우선순위: `DID/Modem` ➔ `Fax2Email` ➔ `Barcode`
   - 최종 결정된 수신자에게 `send_mail` 발송 및 설정 시 프린터 출력

---

## 4. Verification & Testing Strategy
- **Unit Tests (`tests/unit/test_cli_faxrcvd.py`)**:
  - 인수 누락(`no_args`, `missing_args`) 시 Usage 메시지 및 반환코드 검증
  - 파일 미존재 시 정상 종료 검증
  - 모의 환경에서 수신 처리 및 아카이빙 성공 흐름 검증
- **Golden Master Differential Tests**:
  - `12_faxrcvd_no_args`: 100% PASS
  - `13_faxrcvd_missing_args`: 100% PASS
  - `14_faxrcvd_nonexistent_file`: 100% PASS
