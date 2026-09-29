# Specification: Module 34 - WebOutbox

## 1. Overview
- **Module Name**: `WebOutbox`
- **Legacy Source**: `legacy/avantfax/outbox.php`
- **Target Implementation**: `src/avantfax/web/views/outbox.py`
- **Primary Role**: HylaFAX 송신 대기열(Send Queue) 및 실패 전송 큐 조회, 주소록 회사명 연동 매핑, 작업 취소(Kill Job) 제어.

---

## 2. Interface Specification
- **OutboxHandler**:
  - `get_outbox_queue(user_account) -> Dict[str, Any]`:
    - 슈퍼유저일 경우 전체 큐, 일반 사용자일 경우 본인 소유 팩스 목록 반환
    - 활성 큐(`active_queue`) 및 실패 큐(`failed_queue`) 분리 반환
    - 각 항목에 주소록 연동 회사명(`company`) 매핑
  - `kill_job(jid, user_account) -> bool`:
    - 해당 작업 ID(`jid`)에 대해 소유권 및 권한 검증 후 `FaxQueue.killjob` 호출하여 취소

---

## 3. Verification & Testing Strategy
- **Unit Tests (`tests/unit/test_web_outbox.py`)**:
  - 슈퍼유저와 일반 사용자 큐 조회 권한 분기 검증
  - 작업 취소 성공 및 권한 없는 작업 취소 시 거부 검증
  - 주소록 회사명 자동 보완 검증
