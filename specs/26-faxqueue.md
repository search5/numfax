# Module Specification: 26. FaxQueue

## 1. 개요 (Overview)
- **모듈명**: `FaxQueue` (`src/avantfax/services/faxqueue.py`)
- **레거시 파일**: `legacy/avantfax/includes/FaxQueue.php`
- **의존성**:
  - `AFUserAccount` (`src/avantfax/services/user_account.py`)
- **책임**:
  - HylaFAX 송신 대기열(`faxstat -s`) 및 완료/실패 대기열(`faxstat -d`) 텍스트 파싱.
  - 대기열 항목별 소유자(`owner`)의 AvantFAX 사용자 프로필 연동 매핑.
  - 특정 소유자 작업 필터링 (`list_owner`).
  - HylaFAX 작업 취소 (`killjob` / `faxrm`) 및 속성 변경 (`faxalter`).

---

## 2. 인터페이스 명세 (API Contract)

### `FaxQueue(user_account=None, faxsendq_cmd=None, faxdoneq_cmd=None, faxrm_cmd=None, faxalter_cmd=None)`
- `process_queue(raw_output: Optional[str] = None) -> List[dict]`
- `process_failed_queue(raw_output: Optional[str] = None) -> List[dict]`
- `get_queue() -> List[dict]`
- `list_owner(owner: str) -> List[dict]`
- `killjob(user: str, jid: int) -> bool`
- `faxalter(user: str, jid: int, operations: dict) -> bool`
- 파서 헬퍼: `parse_queue_output(lines: List[str], keys: List[str]) -> List[dict]`

---

## 3. 검증 시나리오 (Test Scenarios)
1. `parse_queue_output`: HylaFAX 모뎀 헤더 및 타이틀 라인 제거, jid, pri, s, owner, number, status 등 필드 정확한 분리 파싱 검증.
2. `process_failed_queue`: 상태 `s == 'F'`인 실패 작업만 필터링되는지 확인.
3. `get_queue` & `list_owner`: 사용자 계정 매핑 및 특정 소유자 필터링 확인.
4. `killjob` & `faxalter`: 파라미터 옵션 구성 및 실행 검증.
