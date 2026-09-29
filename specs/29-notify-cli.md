# Specification: Module 29 - notify (CLI)

## 1. Overview
- **Module Name**: `notify`
- **Legacy Source**: `legacy/avantfax/includes/notify.php`
- **Target Implementation**: `src/avantfax/cli/notify.py`
- **Primary Role**: HylaFAX 발신 훅 스크립트. 전송 완료, 재시도, 또는 실패 상태에 따라 `qfile`을 파싱하고, 주소록(`AFAddressBook`) 및 송신 내역(`ArchiveOut`)을 갱신하며, 사용자/관리자에게 상태 알림 이메일을 전송.

---

## 2. CLI Interface & Exit Semantics
- **Command Signature**:
  ```bash
  notify.php qfile why jobtime [nextTry]
  ```
- **Arguments**:
  1. `qfile` (str, required): HylaFAX 큐 파일 경로 (예: `/var/spool/hylafax/doneq/q123`)
  2. `why` (str, required): 발송 완료 사유/상태 코드 (예: `done`, `requeued`, `blocked`, `killed`, `format_failed` 등)
  3. `jobtime` (str, optional): 전송 소요 시간 (예: `00:01:23`)
  4. `nextTry` (str, optional): 다음 재시도 예정 시간
- **Exit & Output Codes**:
  - 인수 개수 < 2 (즉 `argc < 3`):
    - stdout: `Usage: notify.php qfile why jobtime [nextTry]\n`
    - exit code: `0`
  - `qfile` 파일이 존재하지 않음:
    - stdout: `{qfile} doesn't exist\n`
    - exit code: `0`
  - 정상 처리 완료:
    - exit code: `0`

---

## 3. Core Business Logic & State Handling
1. **qfile Parsing**:
   - `totpages`: 전체 팩스 페이지 수
   - `status`: HylaFAX 상태 메시지
   - `external`: 수신자 팩스 번호 (`clean_faxnum` 적용)
   - `jobid`: HylaFAX 작업 ID
   - `mailaddr`: 송신자 이메일
   - `groupid`: 그룹 ID
   - `location`: 수신자 위치 (`to_location`)
   - `voice`: 수신자 음성 전화번호 (`to_voice`)
   - `receiver`: 수신자 담당자명 (`to_person`)
   - `company`: 수신 회사명 (`to_company`, 누락 시 `external` 번호로 대체)
   - `regarding`: 비고/제목 (`regarding`)
   - `owner`: 발송자 사용자명 (`owner.lower()`)
   - `postscript` / `pdf` / `tiff`: 첨부 파일 목록 (세미콜론 구분자 제외)
2. **AddressBook (`AFAddressBook`) Integration**:
   - `loadbyfaxnum(external)`:
     - 기존 번호 존재 시: 단일 회사면 `inc_faxto()`, 회사 ID 취득
     - 미존재 시: 신규 회사 및 팩스 번호 자동 등록, 설정(`to_person`, `to_location`, `to_voice`) 저장 후 `inc_faxto()`
3. **User Account (`AFUserAccount`) Lookup**:
   - `owner`가 시스템 유저(`FAXMAILUSER` 또는 `WWWUSER`)인 경우 `mailaddr`로 계정 조회
   - 그 외의 경우 `owner` 사용자명으로 계정 조회
   - 실패 시 수신자 이메일을 `mailaddr`로 직접 사용
4. **Notification Dispatch (`why` Branches)**:
   - **`why == "done"` (성공)**:
     - `$ARCHIVE_SENT/Y/m/d/external/His/jobid` 보관 디렉터리 생성
     - `convert2pdf`로 PDF 병합 및 `pdf_preview`로 썸네일 생성
     - `ArchiveOut.create`로 발신 아카이브 레코드 생성 및 `regarding` 노트 등록
     - `NOTIFY_ON_SUCCESS` 설정이 참이면 결과 이메일 발송
     - stdout: `Done\n`
   - **`why in ("blocked", "requeued")` (재시도/대기)**:
     - 재시도 알림 이메일 발송 (상태, 다음 시도 시간 포함)
   - **그 외의 경우 (실패 - `fatal`)**:
     - 실패 알림 이메일 발송 (임시 디렉터리에서 생성한 PDF 첨부 포함)

---

## 4. Verification & Testing Strategy
- **Unit Tests (`tests/unit/test_cli_notify.py`)**:
  - 인자 누락 시 사용법 출력 및 정상 종료 검증
  - 존재하지 않는 qfile 경로 지정 시 에러 메시지 및 정상 종료 검증
  - qfile 파싱 및 모의 DB/메일러 연동 검증
- **Golden Master Differential Tests**:
  - `09_notify_no_args`: 100% 동일한 stdout 및 exit code 0
  - `10_notify_missing_why`: 100% 동일한 stdout 및 exit code 0
  - `11_notify_missing_qfile_file`: 100% 동일한 stdout 및 exit code 0
